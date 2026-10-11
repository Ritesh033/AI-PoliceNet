"""Civic violations, official misconduct and the review a count of recorded sanctions can ask for.

The rules under test: a civic violation leads to a challan and never to an FIR or a flag; official misconduct that
is not an offence leads to a sanction recorded by a competent human authority after notice; each person is decided
and penalised separately; whoever filmed or posted a clip is never penalised; and a count of recorded sanctions can
ask a human authority to review but suspends, removes and fines no one and restricts no court.
"""

import pytest

from app.domain import (
    ACTIONS, Category, CIVIC_BEHAVIORS, DEPARTMENTAL_BEHAVIORS, PolicyViolation, Stage, behavior_tracks, decide_flag,
)
from app.ledger import Ledger

from .conftest import (
    AI, AUDITOR, CITIZEN, JUDGE, OFFICER, REVIEWER, SUPERVISOR, SYSTEM, alert_kwargs, complete_context, fingerprint, headers,
    new_alert,
)

OWNER = {"ref": "veh:owner-41", "role": "vehicle_owner", "rationale": "registered owner of the vehicle"}
POSTER = {"ref": "acct:poster-9", "role": "uploader", "rationale": "posted the clip; not involved"}
OFFICIAL = {"ref": "emp:official-12", "role": "public_servant", "rationale": "stops vehicles and fines people"}
HELPER = {"ref": "acct:helper-2", "role": "private_agent_of_official", "rationale": "collects payment"}
CONTRACTOR = {"ref": "firm:contractor-5", "role": "contractor_or_licensee", "rationale": "holds the tender"}
BASIS = "Municipal bylaw schedule, item 4 (sample)"
SERVICE_BASIS = "Service conduct rules, rule 3 (sample)"


def code(exc: pytest.ExceptionInfo) -> str:
    return exc.value.code


def refer(svc, case):
    svc.act(REVIEWER, case.id, "assign")
    complete_context(svc, case)
    svc.act(REVIEWER, case.id, "refer", note="context reviewed")


def civic_case(svc, parties=(OWNER, POSTER), **kw):
    case = new_alert(svc, category=Category.CIVIC, behaviors=["obstructive_parking"], priority="routine", **kw)
    svc.propose_parties(AI, case.id, list(parties))
    refer(svc, case)
    return case


def departmental_case(svc, parties=(OFFICIAL, HELPER, POSTER), behaviors=("abuse_of_official_power",), **kw):
    case = new_alert(
        svc, category=Category.OFFICIAL_MISCONDUCT, behaviors=list(behaviors),
        situation=["acting_in_official_capacity"], priority="routine", **kw,
    )
    svc.propose_parties(AI, case.id, list(parties))
    refer(svc, case)
    return case


def handler_for(case):
    """The authority that deals with the people in a case: the supervisory authority on a departmental case."""
    return SUPERVISOR if case.track == "departmental" else OFFICER


def determine(svc, case, party, determination="subject"):
    return svc.act(
        handler_for(case), case.id, "determine_party", note="decided on the facts",
        party_ref=party["ref"], party_role=party["role"], determination=determination,
    )


def notice(svc, case, party):
    return svc.act(handler_for(case), case.id, "serve_notice", party_ref=party["ref"])


def challan(svc, case, party, amount=10_000, who=OFFICER):
    return svc.act(
        who, case.id, "issue_challan", note="clip reviewed; challan issued", party_ref=party["ref"],
        amount_inr=amount, legal_basis=BASIS,
    )


def sanction(svc, case, party, kind="warning", amount=None, who=SUPERVISOR):
    params = dict(party_ref=party["ref"], sanction_kind=kind, legal_basis=SERVICE_BASIS)
    if amount is not None:
        params["amount_inr"] = amount
    return svc.act(who, case.id, "impose_sanction", note="response read; sanction recorded", **params)


def warned_case(svc, official=OFFICIAL):
    """A departmental case in which the official has been determined, notified and given a warning."""
    case = departmental_case(svc, parties=(official, POSTER))
    determine(svc, case, official)
    notice(svc, case, official)
    sanction(svc, case, official)
    return case


# ------------------------------------------------------------- the flagging policy

@pytest.mark.parametrize("behavior", sorted(CIVIC_BEHAVIORS))
def test_a_civic_violation_opens_a_challan_case_that_is_not_a_crime_and_not_a_flag(behavior):
    decision = decide_flag([behavior])
    assert decision.flag and decision.track == "civic"
    assert "not a crime" in decision.reason and "not counted as a flag" in decision.reason


def test_a_civic_violation_in_a_film_scene_is_not_flagged():
    assert not decide_flag(["public_spitting"], ["quoted_or_fictional"]).flag


@pytest.mark.parametrize("behavior", sorted(DEPARTMENTAL_BEHAVIORS))
def test_official_misconduct_is_considered_only_when_the_clip_shows_an_official_acting_as_one(behavior):
    assert not decide_flag([behavior]).flag
    assert not decide_flag([behavior], ["political_commentary"]).flag
    flagged = decide_flag([behavior], ["acting_in_official_capacity"])
    assert flagged.flag and flagged.track == "departmental" and "not a crime" in flagged.reason
    assert not decide_flag([behavior], ["acting_in_official_capacity", "quoted_or_fictional"]).flag


@pytest.mark.parametrize("behavior", ["physical_assault", "bribe_demand"])
def test_beating_and_demanding_a_bribe_are_flagged_for_everyone_officials_included(behavior):
    for situation in ([], ["acting_in_official_capacity"], ["public_official_target"]):
        decision = decide_flag([behavior], situation)
        assert decision.flag and decision.track == "criminal"


def test_abuse_aimed_at_an_official_is_still_not_flagged():
    assert not decide_flag(["aggressive_abuse"], ["public_official_target"]).flag


def test_casual_speech_can_accompany_an_alert_but_consequence_families_cannot_be_mixed(svc):
    assert behavior_tracks(["casual_profanity", "public_spitting"]) == {"civic"}
    with pytest.raises(PolicyViolation) as exc:
        svc.create_alert(AI, **alert_kwargs(category=Category.CIVIC, behaviors=["public_spitting", "threat"]))
    assert code(exc) == "mixed_tracks"


def test_a_civic_alert_takes_the_civic_scenario_and_a_criminal_alert_cannot_use_it(svc):
    case = new_alert(svc, category=Category.CIVIC, behaviors=["public_urination"])
    assert case.track == "civic" and case.scenario == "civic_violation"
    with pytest.raises(PolicyViolation) as exc:
        svc.create_alert(AI, **alert_kwargs(scenario="civic_violation", behaviors=["threat"]))
    assert code(exc) == "scenario_track_mismatch"


def test_one_clip_can_have_a_case_on_each_track_but_still_only_one_fir(svc):
    fp = fingerprint()
    criminal = svc.create_alert(AI, **alert_kwargs(content_fingerprint=fp, behaviors=["bribe_demand"])).case
    departmental = svc.create_alert(
        AI, **alert_kwargs(content_fingerprint=fp, category=Category.OFFICIAL_MISCONDUCT,
                           behaviors=["abuse_of_official_power"], situation=["acting_in_official_capacity"])
    ).case
    assert criminal.track == "criminal" and departmental.track == "departmental" and criminal.id != departmental.id
    again = svc.create_alert(
        AI, **alert_kwargs(content_fingerprint=fp, category=Category.OFFICIAL_MISCONDUCT,
                           behaviors=["official_misbehavior"], situation=["acting_in_official_capacity"])
    )
    assert again.outcome == "duplicate" and again.case.id == departmental.id


# --------------------------------------------------------------------- civic: the challan

def test_the_supervisory_authority_not_the_force_being_filmed_deals_with_the_people_on_a_departmental_case(svc):
    case = departmental_case(svc)
    for action, extra in (
        ("determine_party", dict(party_ref=OFFICIAL["ref"], party_role=OFFICIAL["role"], determination="subject")),
        ("serve_notice", dict(party_ref=OFFICIAL["ref"])),
    ):
        with pytest.raises(PolicyViolation) as exc:
            svc.act(OFFICER, case.id, action, note="x", **extra)
        assert code(exc) == "wrong_handler"
    determine(svc, case, OFFICIAL)
    assert notice(svc, case, OFFICIAL).issued_response_token
    # And on every other track the supervisory authority does not take over the officer's part.
    civic = civic_case(svc)
    with pytest.raises(PolicyViolation) as exc:
        svc.act(SUPERVISOR, civic.id, "determine_party", note="x", party_ref=OWNER["ref"], party_role="vehicle_owner", determination="subject")
    assert code(exc) == "role_not_permitted"


def test_no_fir_can_ever_be_registered_on_a_civic_or_departmental_matter(svc):
    for case in (civic_case(svc), departmental_case(svc)):
        with pytest.raises(PolicyViolation) as exc:
            svc.act(OFFICER, case.id, "register_fir", note="trying")
        assert code(exc) == "not_a_criminal_matter" and case.stage == Stage.REFERRED.value


def test_a_challan_goes_to_the_person_determined_to_be_the_subject_never_to_whoever_posted_the_clip(svc):
    case = civic_case(svc)
    with pytest.raises(PolicyViolation) as exc:
        determine(svc, case, POSTER)
    assert code(exc) == "not_a_subject_role"
    with pytest.raises(PolicyViolation) as exc:
        challan(svc, case, OWNER)  # not yet determined
    assert code(exc) == "penalty_only_to_subjects"
    determine(svc, case, OWNER)
    done = challan(svc, case, OWNER)
    assert done.stage == Stage.PENALTY_RECORDED.value
    (record,) = done.penalties
    assert (record.party_ref, record.kind, record.amount_inr, record.issued_by) == ("veh:owner-41", "challan", 10_000, "off-1")
    assert [p.ref for p in done.parties if p.determination == "subject"] == ["veh:owner-41"]


def test_a_challan_needs_the_minimum_amount_a_legal_basis_and_a_human_officer(svc):
    case = civic_case(svc)
    determine(svc, case, OWNER)
    with pytest.raises(PolicyViolation) as exc:
        challan(svc, case, OWNER, amount=9_999)
    assert code(exc) == "amount_below_minimum"
    with pytest.raises(PolicyViolation) as exc:
        svc.act(OFFICER, case.id, "issue_challan", note="n", party_ref=OWNER["ref"], amount_inr=10_000)
    assert code(exc) == "legal_basis_required"
    for who, expected in ((AI, "ai_cannot_decide"), (SYSTEM, "ai_cannot_decide"), (REVIEWER, "role_not_permitted"),
                          (SUPERVISOR, "role_not_permitted"), (JUDGE, "role_not_permitted")):
        with pytest.raises(PolicyViolation) as exc:
            challan(svc, case, OWNER, who=who)
        assert code(exc) == expected
    assert case.penalties == []


def test_each_person_is_challaned_separately_and_only_once(svc):
    second = {"ref": "acct:driver-2", "role": "performer_in_public_act", "rationale": "was driving"}
    case = civic_case(svc, parties=(OWNER, second, POSTER))
    determine(svc, case, OWNER)
    determine(svc, case, second)
    challan(svc, case, OWNER)
    with pytest.raises(PolicyViolation) as exc:
        challan(svc, case, OWNER)
    assert code(exc) == "already_recorded"
    challan(svc, case, second, amount=15_000)
    assert sorted((p.party_ref, p.amount_inr) for p in case.penalties) == [("acct:driver-2", 15_000), ("veh:owner-41", 10_000)]
    assert case.stage == Stage.PENALTY_RECORDED.value


def test_the_challan_floor_is_a_setting_not_a_law(svc):
    svc.settings = type(svc.settings)(**{**svc.settings.__dict__, "civic_challan_min_inr": 500})
    case = civic_case(svc)
    determine(svc, case, OWNER)
    assert challan(svc, case, OWNER, amount=500).penalties[0].amount_inr == 500


def test_a_challan_is_not_a_flag_and_nothing_counts_it(svc):
    case = civic_case(svc)
    determine(svc, case, OWNER)
    challan(svc, case, OWNER)
    assert svc.active_sanction_count(OWNER["ref"]) == 0 and case.reviews_due == []
    assert not [e for e in Ledger(svc.session).entries(limit=500) if e.action.startswith("conduct.")]


def test_a_challaned_person_can_still_respond_and_a_party_can_appeal(svc):
    case = civic_case(svc)
    determine(svc, case, OWNER)
    served = notice(svc, case, OWNER)
    assert "no FIR will be registered" in served.issued_notice_text and "contest" in served.issued_notice_text
    challan(svc, case, OWNER)
    item = svc.submit_response_by_token(served.issued_response_token, label="Full dashcam video")
    assert item.kind == "response"
    assert svc.act(CITIZEN, case.id, "appeal", note="the vehicle had broken down").appeal_open


def test_a_challan_can_only_be_issued_on_a_civic_case(svc):
    case = departmental_case(svc)
    determine(svc, case, OFFICIAL)
    with pytest.raises(PolicyViolation) as exc:
        challan(svc, case, OFFICIAL)
    assert code(exc) == "wrong_track"


# ----------------------------------------------------------- departmental: the sanction

def test_a_departmental_case_goes_to_the_supervisory_authority_not_the_force_being_filmed(svc):
    case = departmental_case(svc)
    assert case.referred_to_role == "supervisory_authority"
    with pytest.raises(PolicyViolation) as exc:
        svc.act(OFFICER, case.id, "open_inquiry", note="x")
    assert code(exc) == "wrong_handler"
    assert svc.act(SUPERVISOR, case.id, "open_inquiry", note="departmental inquiry opened").stage == "inquiry"


def test_a_sanction_needs_a_determined_subject_a_notice_and_a_human_authority(svc):
    case = departmental_case(svc)
    with pytest.raises(PolicyViolation) as exc:
        sanction(svc, case, OFFICIAL)
    assert code(exc) == "penalty_only_to_subjects"
    determine(svc, case, OFFICIAL)
    with pytest.raises(PolicyViolation) as exc:
        sanction(svc, case, OFFICIAL)
    assert code(exc) == "notice_required"
    notice(svc, case, OFFICIAL)
    for who, expected in ((AI, "ai_cannot_decide"), (SYSTEM, "ai_cannot_decide"), (OFFICER, "role_not_permitted"),
                          (REVIEWER, "role_not_permitted"), (JUDGE, "role_not_permitted")):
        with pytest.raises(PolicyViolation) as exc:
            sanction(svc, case, OFFICIAL, who=who)
        assert code(exc) == expected
    done = sanction(svc, case, OFFICIAL)
    assert done.stage == Stage.PENALTY_RECORDED.value and done.penalties[0].kind == "warning"


def test_whoever_posted_or_was_treated_that_way_is_never_sanctioned(svc):
    case = departmental_case(svc)
    with pytest.raises(PolicyViolation) as exc:
        determine(svc, case, POSTER)
    assert code(exc) == "not_a_subject_role"
    determine(svc, case, POSTER, "witness")
    with pytest.raises(PolicyViolation) as exc:
        notice(svc, case, POSTER)
    assert code(exc) == "notice_only_to_subjects"


def test_each_sanction_fits_the_role_of_the_person_it_is_recorded_against(svc, clock):
    case = departmental_case(svc, parties=(OFFICIAL, HELPER, CONTRACTOR, POSTER))
    for party in (OFFICIAL, HELPER, CONTRACTOR):
        determine(svc, case, party)
        notice(svc, case, party)
    for party, kind in ((HELPER, "suspension"), (CONTRACTOR, "suspension"), (OFFICIAL, "licence_cancellation"),
                        (HELPER, "removal_order"), (CONTRACTOR, "warning")):
        with pytest.raises(PolicyViolation) as exc:
            sanction(svc, case, party, kind)
        assert code(exc) == "sanction_not_for_role", (party["role"], kind)
    sanction(svc, case, OFFICIAL, "suspension")
    sanction(svc, case, HELPER, "warning")
    clock.advance(days=11)  # a licence cancellation needs the person to have been heard
    sanction(svc, case, CONTRACTOR, "licence_cancellation")
    assert sorted((p.party_ref, p.kind) for p in case.penalties) == [
        ("acct:helper-2", "warning"), ("emp:official-12", "suspension"), ("firm:contractor-5", "licence_cancellation"),
    ]


def test_a_fine_needs_the_floor_and_a_hearing_and_other_sanctions_carry_no_amount(svc):
    case = departmental_case(svc)
    determine(svc, case, OFFICIAL)
    served = notice(svc, case, OFFICIAL)
    with pytest.raises(PolicyViolation) as exc:
        sanction(svc, case, OFFICIAL, "fine", amount=999_999)
    assert code(exc) == "amount_below_minimum"
    with pytest.raises(PolicyViolation) as exc:
        sanction(svc, case, OFFICIAL, "fine", amount=1_000_000)
    assert code(exc) == "hearing_pending"
    with pytest.raises(PolicyViolation) as exc:
        sanction(svc, case, OFFICIAL, "warning", amount=5)
    assert code(exc) == "amount_not_allowed"
    # Answering is enough; so is the window passing. Silence is never an admission, it only means the chance was given.
    svc.submit_response_by_token(served.issued_response_token, label="My account of the stop")
    done = sanction(svc, case, OFFICIAL, "fine", amount=1_000_000)
    assert done.penalties[-1].amount_inr == 1_000_000


def test_the_hearing_window_passing_also_lets_a_fine_be_recorded(svc, clock):
    case = departmental_case(svc)
    determine(svc, case, OFFICIAL)
    notice(svc, case, OFFICIAL)
    clock.advance(days=9)
    with pytest.raises(PolicyViolation) as exc:
        sanction(svc, case, OFFICIAL, "fine", amount=1_000_000)
    assert code(exc) == "hearing_pending"
    clock.advance(days=2)
    assert sanction(svc, case, OFFICIAL, "fine", amount=1_000_000).penalties[-1].kind == "fine"


def test_one_persons_response_does_not_open_the_hearing_for_another(svc):
    case = departmental_case(svc)
    determine(svc, case, OFFICIAL)
    determine(svc, case, HELPER)
    official_token = notice(svc, case, OFFICIAL).issued_response_token  # read it before the next notice replaces it
    notice(svc, case, HELPER)
    svc.submit_response_by_token(official_token, label="official's reply")
    sanction(svc, case, OFFICIAL, "fine", amount=1_000_000)
    with pytest.raises(PolicyViolation) as exc:
        sanction(svc, case, HELPER, "fine", amount=1_000_000)
    assert code(exc) == "hearing_pending"


def test_a_removal_order_follows_an_inquiry(svc):
    case = departmental_case(svc)
    determine(svc, case, OFFICIAL)
    served = notice(svc, case, OFFICIAL)
    svc.submit_response_by_token(served.issued_response_token, label="reply")
    with pytest.raises(PolicyViolation) as exc:
        sanction(svc, case, OFFICIAL, "removal_order")
    assert code(exc) == "inquiry_required"
    svc.act(SUPERVISOR, case.id, "open_inquiry", note="departmental inquiry")
    assert sanction(svc, case, OFFICIAL, "removal_order").penalties[-1].kind == "removal_order"


def test_a_public_servant_and_a_private_helper_are_each_sanctioned_separately(svc):
    case = departmental_case(svc, behaviors=("abuse_of_official_power", "private_agents_in_official_acts"))
    for party in (OFFICIAL, HELPER):
        determine(svc, case, party)
        notice(svc, case, party)
    sanction(svc, case, OFFICIAL)
    sanction(svc, case, HELPER)
    with pytest.raises(PolicyViolation) as exc:
        sanction(svc, case, HELPER)
    assert code(exc) == "already_recorded"
    assert {p.party_ref for p in case.penalties} == {OFFICIAL["ref"], HELPER["ref"]}


def test_a_sanction_can_only_be_recorded_on_a_departmental_case(svc):
    case = civic_case(svc)
    determine(svc, case, OWNER)
    with pytest.raises(PolicyViolation) as exc:
        sanction(svc, case, OWNER)
    assert code(exc) == "wrong_track"


def test_a_departmental_notice_does_not_claim_an_fir(svc):
    case = departmental_case(svc)
    determine(svc, case, OFFICIAL)
    text = notice(svc, case, OFFICIAL).issued_notice_text.lower()
    assert "not a criminal case" in text and "register an fir" not in text and "presumed innocent" not in text
    assert "only after it has read your response" in text


# -------------------------------- a count asks for a human review; it never acts

def test_the_third_recorded_sanction_asks_a_human_authority_for_a_review_and_does_nothing_else(svc):
    cases = [warned_case(svc) for _ in range(3)]
    assert svc.active_sanction_count(OFFICIAL["ref"]) == 3
    assert [c.reviews_due for c in cases[:2]] == [[], []]
    (due,) = cases[2].reviews_due
    assert due["threshold"] == 3 and due["kind"] == "interim_suspension_review"
    entry = next(e for e in Ledger(svc.session).entries(limit=500) if e.action == "conduct.review_due")
    assert entry.actor_kind == "system" and entry.payload["binding"] is False and entry.case_id == cases[2].id
    # No one was suspended or removed by the count, and every penalty was recorded by a human.
    penalties = [p for c in cases for p in c.penalties]
    assert {p.kind for p in penalties} == {"warning"} and {p.issued_by for p in penalties} == {"sup-1"}
    assert svc.reviews_due_cases() == [cases[2]]


def test_the_seventh_asks_for_a_removal_inquiry_review_and_still_acts_on_no_one(svc):
    cases = [warned_case(svc) for _ in range(7)]
    kinds = [r["kind"] for c in cases for r in c.reviews_due]
    assert kinds == ["interim_suspension_review", "removal_inquiry_review"]
    assert {p.kind for c in cases for p in c.penalties} == {"warning"}
    assert not any(p.kind in ("suspension", "removal_order") for c in cases for p in c.penalties)


def test_a_review_is_answered_in_writing_by_a_human_authority(svc):
    cases = [warned_case(svc) for _ in range(3)]
    case = cases[2]
    for who in (AI, SYSTEM, OFFICER, REVIEWER, JUDGE):
        with pytest.raises(PolicyViolation):
            svc.act(who, case.id, "resolve_review", note="x", party_ref=OFFICIAL["ref"])
    with pytest.raises(PolicyViolation) as exc:
        svc.act(SUPERVISOR, case.id, "resolve_review", note="", party_ref=OFFICIAL["ref"])
    assert code(exc) == "note_required"
    with pytest.raises(PolicyViolation) as exc:
        svc.act(SUPERVISOR, case.id, "resolve_review", note="x", party_ref="emp:someone-else")
    assert code(exc) == "no_review_due"
    done = svc.act(SUPERVISOR, case.id, "resolve_review", note="Reviewed the three records; proceeding by notice, not suspension", party_ref=OFFICIAL["ref"])
    assert done.reviews_due == [] and svc.reviews_due_cases() == []


def test_a_review_is_not_asked_for_by_challans_contractor_fines_helpers_or_other_officials(svc, clock):
    other = {"ref": "emp:official-99", "role": "public_servant", "rationale": "another official"}
    for _ in range(3):
        civic = civic_case(svc)
        determine(svc, civic, OWNER)
        challan(svc, civic, OWNER)
    for party in (HELPER, CONTRACTOR):
        for _ in range(3):
            case = departmental_case(svc, parties=(party, POSTER))
            determine(svc, case, party)
            notice(svc, case, party)
            clock.advance(days=11)
            sanction(svc, case, party, "warning" if party is HELPER else "licence_cancellation")
    for _ in range(2):
        warned_case(svc, official=other)
    assert svc.reviews_due_cases() == []
    assert svc.active_sanction_count(OFFICIAL["ref"]) == 0 and svc.active_sanction_count(other["ref"]) == 2


def test_revoking_a_sanction_lowers_the_count_and_withdraws_a_review_that_is_no_longer_supported(svc):
    cases = [warned_case(svc) for _ in range(3)]
    penalty = cases[0].penalties[0]
    for who in (OFFICER, REVIEWER, CITIZEN):
        with pytest.raises(PolicyViolation):
            svc.act(who, cases[0].id, "revoke_penalty", note="x", penalty_id=penalty.id)
    svc.act(JUDGE, cases[0].id, "revoke_penalty", note="the stop was lawful on the full video", penalty_id=penalty.id)
    assert penalty.revoked and penalty.revoked_by == "judge-1"
    assert svc.active_sanction_count(OFFICIAL["ref"]) == 2
    assert cases[2].reviews_due == [] and svc.reviews_due_cases() == []
    actions = [e.action for e in Ledger(svc.session).entries(limit=500)]
    assert "conduct.review_withdrawn" in actions
    with pytest.raises(PolicyViolation) as exc:
        svc.act(SUPERVISOR, cases[0].id, "revoke_penalty", note="again", penalty_id=penalty.id)
    assert code(exc) == "already_revoked"
    # Reaching three again asks again.
    again = warned_case(svc)
    assert [r["threshold"] for r in again.reviews_due] == [3]


def test_no_count_restricts_any_court_even_after_seven_sanctions(svc):
    cases = [warned_case(svc) for _ in range(7)]
    # A court can still revoke any penalty; nothing about the count blocks a judicial action.
    penalty = cases[6].penalties[0]
    svc.act(JUDGE, cases[6].id, "revoke_penalty", note="set aside on review", penalty_id=penalty.id)
    assert svc.active_sanction_count(OFFICIAL["ref"]) == 6
    # The only automated entries are informational requests for review, written by the system and marked non-binding.
    automated = [e for e in Ledger(svc.session).entries(limit=1000) if e.actor_kind == "system"]
    assert automated and all(e.action.startswith("conduct.") for e in automated)
    assert all(e.payload.get("binding") is False or e.action == "conduct.review_withdrawn" for e in automated)


def test_the_ledger_and_projection_stay_consistent_through_penalties_and_revocations(svc):
    cases = [warned_case(svc) for _ in range(3)]
    svc.act(JUDGE, cases[0].id, "revoke_penalty", note="set aside", penalty_id=cases[0].penalties[0].id)
    assert Ledger(svc.session).verify().ok and svc.verify_projection() == []


# ----------------------------------------------------------------------------- over HTTP

def test_over_http_a_challan_and_a_review_queue_work_and_the_public_sees_neither(client, svc, session):
    case = civic_case(svc)
    determine(svc, case, OWNER)
    body = {"action": "issue_challan", "note": "clip reviewed", "party_ref": OWNER["ref"], "amount_inr": 12_000, "legal_basis": BASIS}
    r = client.post(f"/cases/{case.id}/actions", json=body, headers=headers(OFFICER))
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["stage"] == "penalty_recorded" and out["track"] == "civic"
    assert out["penalties"][0]["amount_inr"] == 12_000 and out["penalties"][0]["issued_by"] == "off-1"
    # A citizen who is a party sees the case but not who was penalised.
    seen = client.get(f"/cases/{case.id}", headers=headers(CITIZEN)).json()
    assert "penalties" not in seen and "parties" not in seen
    # A challan below the floor is a policy violation with a clear code.
    bad = client.post(f"/cases/{case.id}/actions", json={**body, "amount_inr": 5}, headers=headers(OFFICER))
    assert bad.status_code == 422 and bad.json()["error"] == "amount_below_minimum"


def test_over_http_the_review_queue_is_for_supervisory_and_judicial_authorities_and_auditors(client, svc):
    cases = [warned_case(svc) for _ in range(3)]
    for who in (REVIEWER, OFFICER, CITIZEN):
        assert client.get("/attention/reviews-due", headers=headers(who)).status_code == 403
    for who in (SUPERVISOR, JUDGE, AUDITOR):
        r = client.get("/attention/reviews-due", headers=headers(who))
        assert r.status_code == 200 and [c["id"] for c in r.json()["cases"]] == [cases[2].id]
        assert "suspends, removes and fines no one" in r.json()["note"]


def test_the_action_matrix_exposes_the_new_actions_and_their_roles(client):
    meta = client.get("/meta/actions", headers=headers(REVIEWER)).json()
    assert meta["actions"]["issue_challan"]["roles"] == ["authorized_officer"]
    assert meta["actions"]["impose_sanction"]["roles"] == ["supervisory_authority"]
    assert set(meta["actions"]["impose_sanction"]["params"]) == {"party_ref", "sanction_kind", "amount_inr", "legal_basis"}
    assert set(meta["sanction_kinds"]) == {"warning", "fine", "suspension", "licence_cancellation", "removal_order"}
    assert meta["review_thresholds"] == {"3": "interim_suspension_review", "7": "removal_inquiry_review"}
    assert ACTIONS["issue_challan"].to_stage is Stage.PENALTY_RECORDED
