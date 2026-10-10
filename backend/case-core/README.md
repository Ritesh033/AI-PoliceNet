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
python -m pytest -q                                   # 54 tests
APN_ENV=demo APN_CHECKPOINT_KEY=change-me uvicorn app.main:app --port 8100
# interactive docs: http://localhost:8100/docs
```

Environment: `APN_ENV` (must be `demo`), `DATABASE_URL` (default SQLite file), `APN_RESPONSE_WINDOW_DAYS`
(default 10), `APN_CHECKPOINT_KEY` (signs ledger checkpoints).

Demo auth: send `X-Actor-Id` and `X-Actor-Role` (`ai_service`, `reviewer`, `authorized_officer`,
`supervisory_authority`, `judicial_authority`, `citizen`, `auditor`).

## Workflow

```
received -> in_review -> referred -> inquiry -> fir_registered -> closed_by_court
                \-> closed_no_action  (reviewer, officer or supervisory authority; always with a written reason)
```

| Endpoint | Who | What |
| --- | --- | --- |
| `POST /alerts` | AI service | Raise an alert. Evidence is a hash plus label; media is never stored. |
| `POST /complaints` | Citizen | File a conduct complaint naming the official or office. |
| `POST /cases/{id}/actions` | Humans, by role | `assign`, `record_check`, `request_context`, `no_action`, `refer`, `open_inquiry`, `decline`, `register_fir`, `serve_notice`, `court_proceed`, `court_close`, `appeal`, `resolve_appeal` |
| `POST /cases/{id}/advisory` | AI service | Attach a recommendation. Recorded as non-binding; never moves a case. |
| `POST /cases/{id}/responses` | A party | Submit counter-material. Always accepted while the matter is open; late ones are marked late. |
| `GET /attention/window-elapsed` | Staff | Cases whose response window passed. Asks a human to follow up; changes nothing. |
| `GET /ledger`, `/ledger/verify`, `/ledger/checkpoint` | Auditor, judicial authority | Read, verify and sign the audit chain. |

## Guardrails (each is a test)

| Rule | Where | Tests |
| --- | --- | --- |
| AI can raise alerts and add advisory notes only; every workflow action by an AI is refused | `service._authorize` | `test_ai_cannot_perform_any_workflow_action` (one per action), `test_ai_advisory_is_recorded_but_never_moves_a_case` |
| Only an authorized officer registers an FIR, and must state a basis | `domain.ACTIONS` | `test_only_an_authorized_officer_registers_an_fir_and_must_state_a_basis` |
| Only a judicial authority closes a registered FIR; a response never cancels one | `domain.ACTIONS` | `test_only_a_judicial_authority_can_close_a_registered_fir`, `test_the_accused_cannot_cancel_their_own_fir_by_uploading` |
| The response window starts only when a human records that notice was served | `service.act` | `test_window_starts_only_when_notice_is_recorded_as_served` |
| Expiry changes nothing; it only asks a human to follow up | `service.window_elapsed_cases` | `test_expiry_never_changes_a_case_and_only_asks_a_human_to_follow_up` |
| Late responses are accepted and marked, never refused | `service.submit_response` | `test_a_late_response_is_accepted_and_marked_late_not_refused` |
| Conduct complaints go to a supervisory authority and need an inquiry before any FIR decision | `domain.REFERRAL_TARGET` | `test_conduct_complaints_route_to_a_supervisory_authority_not_the_force`, `test_conduct_complaint_cannot_jump_straight_to_an_fir` |
| Nobody named in a case can act on it | `service._authorize` | `test_a_named_subject_can_never_act_on_their_own_case` |
| Self-uploaded confession videos need human wellbeing and authenticity checks first | `domain.CONFESSION_GATED_ACTIONS` | `test_confession_video_needs_human_wellbeing_and_authenticity_checks_before_referral` |
| No strike, flag or lock state exists that could restrict a court | `domain`, `models` | `test_no_flag_or_strike_state_exists_that_could_block_judicial_relief` |
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

- Real authentication: OIDC, MFA, role assignment and revocation.
- PostgreSQL deployment, including append-only triggers (SQLite triggers exist and are tested).
- External checkpoint publishing; evidence vault storage; notification delivery for served notices.
- Persisting review notes and checks from the console UI (the console still runs on mock data).
