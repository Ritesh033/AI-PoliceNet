# Case core

The backend foundation for AI Policing Net: a case workflow where **decision boundaries are enforced in code**,
and a **tamper-evident ledger** that records every step.

> **Status: working prototype with demo authentication.** Identity is a header stub (`APN_ENV=demo`) and the
> service refuses to run it any other way. Real identity, MFA and RBAC are not wired in yet.

## Run

```bash
cd backend/case-core
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q                                   # 202 tests
APN_ENV=demo APN_CHECKPOINT_KEY=change-me python -m app.demo_seed      # optional: 11 invented sample cases
APN_ENV=demo APN_CHECKPOINT_KEY=change-me APN_CORS_ORIGINS=http://localhost:3100 uvicorn app.main:app --port 8100
# interactive docs: http://localhost:8100/docs
```

Environment: `APN_ENV` (must be `demo`), `DATABASE_URL` (default SQLite file), `APN_RESPONSE_WINDOW_DAYS`
(default 10), `APN_DECISION_SLA_HOURS` (default 24), `APN_CHECKPOINT_KEY` (signs ledger checkpoints),
`APN_CORS_ORIGINS` (comma-separated browser origins allowed to call the API, such as the console; none by default),
`APN_CIVIC_CHALLAN_MIN_INR` (default 10000) and `APN_DEPARTMENTAL_FINE_MIN_INR` (default 1000000). The last two are
**policy settings, not law**: a challan or a fine must come from the statute, rule or schedule that applies, so a
deployment has to replace them with figures the law supports (0 leaves the amount to the issuing authority).

Demo auth: send `X-Actor-Id` and `X-Actor-Role` (`ai_service`, `system` (scheduler), `reviewer`,
`authorized_officer`, `supervisory_authority`, `judicial_authority`, `citizen`, `auditor`).

## Workflow

```
received -> in_review -> referred -> inquiry -> fir_registered -> closed_by_court
                \-> closed_no_action  (reviewer, officer or supervisory authority; always with a written reason)
                \-> linked           (related clip merged into an existing case as supplementary information)
                \-> penalty_recorded (a human issued a challan, or a competent authority recorded a sanction)
```

Every case is on one **track**, fixed when it opens. Only a `criminal` case can reach `fir_registered`.

| Track | What it is | What can follow | Never |
| --- | --- | --- | --- |
| `criminal` | An offence (threat, bribe demand, beating, intimate imagery without consent, ...) | An FIR registered by an authorized officer | |
| `civic` | Parking that blocks a road, spitting, urinating on a public wall, dumping waste in a river | `issue_challan` by an authorized officer, to each person decided to be a subject | An FIR; counted as a flag |
| `departmental` | Official misconduct that is not an offence in itself (using power without papers or inquiry, private persons doing official work, official misbehaviour), only when the clip shows a person acting in an official capacity | `impose_sanction` by the supervisory authority, to each person decided to be a subject, after a notice (and a hearing for a fine, licence cancellation or removal) | An FIR; a sanction by software |

A count of recorded warnings and fines against the same public servant asks a supervisory authority for a written
review at 3 (`interim_suspension_review`) and at 7 (`removal_inquiry_review`). The count suspends, removes and fines
no one, restricts no court, and falls when a sanction is revoked. See `docs/legal-compliance/design-guardrails.md`.

| Endpoint | Who | What |
| --- | --- | --- |
| `POST /alerts` | AI service | Submit what the model saw (`behaviors`, `situation`, a clip `content_fingerprint`). Returns `outcome`: `flagged` (201, temporary flag on the clip), `no_flag` (200, dropped by policy, recorded without any person) or `duplicate` (200, attached to the case already tracking that clip). Evidence is a hash plus label; media is never stored. |
| `POST /cases/{id}/parties` | AI service | Propose who appears in a case and in what role, using pseudonymous references only (never an email or phone number). Proposals decide nothing. |
| `POST /public/responses/{token}` | Anyone holding the case's private link (no login) | Upload the full original video or any other material from any account. A human reads it. Also works when staff auth is not configured. |
| `POST /cases/{id}/context-findings` | AI service | Full-context research: `media_source` (film, show, skit), `edit_detection`, `full_context`, `cross_platform_copies`. Referral is blocked until all four exist and a human records `record_check: context`. |
| `POST /complaints` | Citizen | File a conduct complaint naming the official or office. |
| `POST /cases/{id}/actions` | Humans, by role | `assign`, `record_check`, `request_context`, `no_action`, `refer`, `open_inquiry`, `decline`, `register_fir`, `serve_notice`, `determine_party`, `request_identification`, `court_proceed`, `court_close`, `permit_fresh_registration`, `link_supplementary`, `issue_challan`, `impose_sanction`, `revoke_penalty`, `resolve_review`, `appeal`, `resolve_appeal` |
| `POST /cases/{id}/advisory` | AI service | Attach a recommendation (`kind`: `info` or `dismissal`). Recorded as non-binding; never moves a case. A `dismissal` advisory puts an FIR in the court's queue. |
| `POST /cases/{id}/responses` | A party | Submit counter-material. Always accepted while the matter is open; late ones are marked late. |
| `GET /attention/window-elapsed` | Staff | Cases whose response window passed. Asks a human to follow up; changes nothing. |
| `POST /attention/sweep`, `GET /attention/overdue-decisions` | Scheduler, staff | Records once that a case missed its 24-hour human-decision deadline and must go to a supervisor. Files nothing. |
| `GET /attention/reviews-due` | Supervisory authority, judicial authority, auditor | Cases where a count of recorded sanctions asked for a human review. Informational: nothing is suspended or removed by the count. |
| `GET /attention/dismissal-recommendations` | Judicial authority, auditor | FIRs where the AI's continuing research recommends dismissal. Only a court can act. |
| `GET /ledger`, `/ledger/verify`, `/ledger/checkpoint` | Auditor, judicial authority | Read, verify and sign the audit chain. |
| `GET /meta/actions` | Any identity | The workflow rules (roles, stages, required notes and inputs) straight from the code that enforces them, so clients never keep a drifting copy. |

## Guardrails (each is a test)

| Rule | Where | Tests |
| --- | --- | --- |
| AI can raise alerts and add advisory notes only; every workflow action by an AI is refused | `service._authorize` | `test_automated_actors_cannot_perform_any_workflow_action` (every action, for the AI and the scheduler), `test_ai_advisory_is_recorded_but_never_moves_a_case` |
| Only an authorized officer registers an FIR, and must state a basis | `domain.ACTIONS` | `test_only_an_authorized_officer_registers_an_fir_and_must_state_a_basis` |
| Only a judicial authority closes a registered FIR; a response never cancels one | `domain.ACTIONS` | `test_only_a_judicial_authority_can_close_a_registered_fir`, `test_the_accused_cannot_cancel_their_own_fir_by_uploading` |
| The response window starts only when a human records that notice was served | `service.act` | `test_window_starts_only_when_notice_is_recorded_as_served` |
| Expiry changes nothing; it only asks a human to follow up | `service.window_elapsed_cases` | `test_expiry_never_changes_a_case_and_only_asks_a_human_to_follow_up` |
| Late responses are accepted and marked, never refused | `service.submit_response` | `test_a_late_response_is_accepted_and_marked_late_not_refused` |
| Conduct complaints go to a supervisory authority and need an inquiry before any FIR decision | `domain.REFERRAL_TARGET` | `test_conduct_complaints_route_to_a_supervisory_authority_not_the_force`, `test_conduct_complaint_cannot_jump_straight_to_an_fir` |
| Nobody named in a case can act on it | `service._authorize` | `test_a_named_subject_can_never_act_on_their_own_case` |
| Self-uploaded confession videos need human wellbeing and authenticity checks first | `domain.CONFESSION_GATED_ACTIONS` | `test_confession_video_needs_human_wellbeing_and_authenticity_checks_before_referral` |
| No strike, flag or lock state exists that could restrict a court | `domain`, `models` | `test_no_flag_or_strike_state_exists_that_could_block_judicial_relief` |
| Lies, criticism and everyday abuse are not flagged; aggressive abuse is flagged only with an aggravating situation | `domain.decide_flag` | `test_everyday_abuse_criticism_and_abuse_of_officials_are_not_flagged`, `test_aggressive_abuse_with_context_and_hard_behaviours_are_flagged_for_human_review` |
| Crude abuse of a public official or leader is not flagged on that basis; threats against anyone are | `domain.decide_flag` | `test_the_policy_gives_officials_and_leaders_no_extra_protection` |
| Closed vocabularies, so free text cannot bypass the policy; classification is by intent, not keywords | `service.create_alert` | `test_the_vocabularies_are_closed_so_free_text_cannot_bypass_policy` |
| The flag attaches to a clip, never a person | `models.Case` | `test_the_flag_attaches_to_the_clip_and_there_is_no_person_record` |
| No referral until the AI has checked for film/show source, edits, the full original and other copies, and a human acknowledges | `service._authorize` | `test_a_human_cannot_refer_until_the_full_context_checks_are_done` |
| One FIR per clip; repeats and related clips add information to the existing case; a court can permit a fresh registration | `service.create_alert`, `service._authorize` | `test_a_repeat_alert_on_the_same_clip_adds_information_and_never_opens_a_second_case`, `test_an_fir_cannot_be_registered_twice_on_the_same_clip_even_by_a_path_that_skips_dedupe`, `test_a_court_can_permit_a_fresh_registration_so_the_rule_is_not_a_trap` |
| A missed 24-hour deadline escalates to a supervisor and files nothing | `service.sweep_deadlines` | `test_a_missed_deadline_escalates_to_a_supervisor_and_files_nothing` |
| AI dismissal recommendations reach the court queue and cancel nothing | `service.add_advisory` | `test_an_ai_dismissal_recommendation_reaches_the_court_queue_but_cancels_nothing` |
| The victim is never the suspect: people shown in intimate imagery shared without consent cannot be named subjects; in a public indecent act the performer, not the person who filmed or posted it, is the subject | `domain.explain_subject_rule` | `test_people_depicted_in_intimate_imagery_shared_without_consent_are_never_subjects`, `test_two_adults_in_a_private_video_are_victims_of_the_person_who_leaked_it`, `test_in_a_public_indecent_act_the_performer_is_the_subject_not_whoever_recorded_or_posted_it` |
| Only an officer decides who is a subject; the AI only proposes; an FIR in these cases needs the parties decided first | `service._authorize_determination` | `test_only_an_authorized_officer_determines_parties_and_only_among_proposed_parties`, `test_an_fir_in_a_scenario_case_needs_the_parties_decided_first` |
| A notice goes only to a determined subject, never to a victim; its text explains why and how to respond | `service._authorize_notice`, `notice.build_notice` | `test_a_notice_goes_only_to_a_determined_subject_never_to_a_victim`, `test_the_notice_explains_why_what_it_means_and_how_to_respond_without_logging_in` |
| Respond with no login via a private link; the link is shown once and only its hash is stored | `service.submit_response_by_token` | `test_anyone_holding_the_link_can_respond_from_any_account_without_identifying_themselves`, `test_the_response_link_is_shown_once_and_only_its_hash_is_stored` |
| Identification is a recorded officer step with a legal basis, never for a victim | `service._authorize_identification` | `test_identification_is_a_recorded_officer_step_with_a_legal_basis_and_never_for_a_victim` |
| No place to store a name, phone, email or address, and nothing is ever sent | `models`, whole `app/` package | `test_the_schema_has_no_place_to_store_a_name_phone_number_email_or_address`, `test_the_service_never_sends_anything_or_calls_out` |
| A civic violation or official misconduct that is not an offence can never reach an FIR | `service._authorize` | `test_no_fir_can_ever_be_registered_on_a_civic_or_departmental_matter` |
| A challan or sanction goes only to a determined subject, one person at a time, recorded by a named human with a legal basis; whoever posted the clip is never penalised | `service._authorize_penalty` | `test_a_challan_goes_to_the_person_determined_to_be_the_subject_never_to_whoever_posted_the_clip`, `test_each_person_is_challaned_separately_and_only_once`, `test_a_sanction_needs_a_determined_subject_a_notice_and_a_human_authority` |
| A fine, licence cancellation or removal needs the person to have been heard; a removal follows an inquiry; each sanction fits the person's role | `service._authorize_penalty` | `test_a_fine_needs_the_floor_and_a_hearing_and_other_sanctions_carry_no_amount`, `test_a_removal_order_follows_an_inquiry`, `test_each_sanction_fits_the_role_of_the_person_it_is_recorded_against` |
| A count of sanctions only asks a human to review; it acts on no one and restricts no court | `service._review_triggers` | `test_the_third_recorded_sanction_asks_a_human_authority_for_a_review_and_does_nothing_else`, `test_the_seventh_asks_for_a_removal_inquiry_review_and_still_acts_on_no_one`, `test_no_count_restricts_any_court_even_after_seven_sanctions` |
| Challans are not flags and are never counted; revoking a sanction lowers the count | `service.active_sanction_count` | `test_a_challan_is_not_a_flag_and_nothing_counts_it`, `test_revoking_a_sanction_lowers_the_count_and_withdraws_a_review_that_is_no_longer_supported` |
| Sensitive media is hash-only and marked preview-withheld | `service._new_case` | `test_sensitive_evidence_stores_hash_only_and_marks_preview_withheld` |

## The ledger: tamper-evident, not tamper-proof

Every action appends a SHA-256 hash-chained entry. The database rejects `UPDATE` and `DELETE` on it, and
`/ledger/verify` re-computes the whole chain and replays it against the `cases` table.

No system can honestly promise that nobody, including an administrator, can ever change data. What this
provides is that **changes are detectable**: edits, deletions and silent state changes are caught by
verification (see `tests/test_ledger.py`). To make rewriting history impractical, periodically publish the
signed `/ledger/checkpoint` to independent custodians (for example a court registry, an audit body and a
civil-society archive). Corrections are new entries that reference the old ones; nothing is silently erased.

## Not built yet

- A public web page for the response link (today the link is an API path); translations of the notice.

- Real authentication: OIDC, MFA, role assignment and revocation.
- PostgreSQL deployment, including append-only triggers (SQLite triggers exist and are tested).
- External checkpoint publishing; evidence vault storage; notification delivery for served notices.
- The console's Overview charts and counts still run on mock data; only its "Case core (live)" tab uses this API.
