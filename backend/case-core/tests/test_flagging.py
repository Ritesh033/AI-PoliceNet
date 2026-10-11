"""The flagging policy, full-context checks, one-FIR-per-clip rule and the 24-hour human decision clock."""

import pytest

from app.domain import Category, PolicyViolation, Stage
from app.ledger import Ledger

from .conftest import (
    AI, AUDITOR, CITIZEN, FINDINGS, HASH, JUDGE, OFFICER, REVIEWER, SUPERVISOR, SYSTEM, alert_kwargs,
    complete_context, fingerprint, new_alert,
)


def code(exc: pytest.ExceptionInfo) -> str:
    return exc.value.code


# ------------------------------------------------ lies and plain abuse are not flagged

@pytest.mark.parametrize(
    "behaviors",
    [["insult"], ["false_statement"], ["criticism"], ["insult", "false_statement"], ["insult", "criticism"]],
)
def test_insults_lies_and_criticism_alone_are_never_flagged(svc, session, behaviors):
    result = svc.create_alert(AI, **alert_kwargs(behaviors=behaviors, category=Category.HATE))
    assert result.outcome == "no_flag" and result.case is None
    entry = [e for e in Ledger(session).entries() if e.action == "triage.no_flag"][-1]
    assert entry.case_id is None  # the drop is auditable, and no case or person record exists
    assert entry.payload["behaviors"] == sorted(behaviors)


@pytest.mark.parametrize(
    "extra",
    ["threat", "sexual_content", "sexual_harassment", "targeted_hate", "incitement_to_violence", "extortion", "child_involved"],
)
def test_abuse_combined_with_an_actionable_behaviour_is_flagged(svc, extra):
    result = svc.create_alert(AI, **alert_kwargs(behaviors=["insult", extra]))
    assert result.outcome == "flagged" and result.case.stage == Stage.RECEIVED.value


def test_the_behaviour_vocabulary_is_closed_so_free_text_cannot_bypass_policy(svc):
    with pytest.raises(PolicyViolation) as exc:
        svc.create_alert(AI, **alert_kwargs(behaviors=["totally_a_threat_trust_me"]))
    assert code(exc) == "unknown_behavior"
    with pytest.raises(PolicyViolation) as exc:
        svc.create_alert(AI, **alert_kwargs(behaviors=[]))
    assert code(exc) == "behaviors_required"


def test_the_flag_attaches_to_the_clip_and_there_is_no_person_record(svc):
    case = new_alert(svc)
    assert case.content_fingerprint.startswith("fp-")
    assert case.subject_ids == []  # nobody is named by a social-media flag


# ------------------------------------------------------ full-context checks first

def test_a_human_cannot_refer_until_the_full_context_checks_are_done(svc, social_case):
    svc.act(REVIEWER, social_case.id, "assign")
    with pytest.raises(PolicyViolation) as exc:
        svc.act(REVIEWER, social_case.id, "refer", note="looks bad")
    assert code(exc) == "context_incomplete"
    for key in FINDINGS[:-1]:
        svc.add_context_finding(AI, social_case.id, key=key, outcome="supports_flag", summary="examined")
    with pytest.raises(PolicyViolation):
        svc.act(REVIEWER, social_case.id, "refer", note="still one finding short")
    svc.add_context_finding(AI, social_case.id, key=FINDINGS[-1], outcome="inconclusive", summary="no other copies found")
    with pytest.raises(PolicyViolation) as exc:
        svc.act(REVIEWER, social_case.id, "refer", note="AI done, but no human acknowledgement")
    assert "acknowledgement" in exc.value.message
    svc.act(REVIEWER, social_case.id, "record_check", check="context")
    svc.act(REVIEWER, social_case.id, "refer", note="all context reviewed")
    assert social_case.stage == Stage.REFERRED.value


def test_a_film_or_show_clip_is_surfaced_and_a_human_can_close_it(svc, social_case):
    svc.add_context_finding(AI, social_case.id, key="media_source", outcome="undermines_flag",
                            summary="Matches a scene from a streaming drama (confidence 0.96)")
    svc.add_advisory(AI, social_case.id, recommendation="Likely fiction clip; recommend no action", kind="info")
    assert social_case.stage == Stage.RECEIVED.value  # advice moves nothing
    svc.act(REVIEWER, social_case.id, "no_action", note="Confirmed: scene from a TV drama")
    assert social_case.stage == Stage.CLOSED_NO_ACTION.value


def test_context_findings_are_ai_only_and_validated(svc, social_case):
    with pytest.raises(PolicyViolation):
        svc.add_context_finding(REVIEWER, social_case.id, key="media_source", outcome="supports_flag", summary="x")
    with pytest.raises(PolicyViolation) as exc:
        svc.add_context_finding(AI, social_case.id, key="vibes", outcome="supports_flag", summary="x")
    assert code(exc) == "unknown_finding"
    with pytest.raises(PolicyViolation) as exc:
        svc.add_context_finding(AI, social_case.id, key="media_source", outcome="guilty", summary="x")
    assert code(exc) == "bad_outcome"


def test_the_ai_keeps_researching_after_an_fir_and_findings_are_still_accepted(svc, fir_case):
    item = svc.add_context_finding(AI, fir_case.id, key="full_context", outcome="undermines_flag",
                                   summary="Original upload shows the remark was a quote", sha256=HASH)
    assert item.outcome == "undermines_flag"


# ------------------------------------------- one FIR per clip, and the related-issue rule

def test_a_repeat_alert_on_the_same_clip_adds_information_and_never_opens_a_second_case(svc, session, fir_case):
    result = svc.create_alert(AI, **alert_kwargs(content_fingerprint=fir_case.content_fingerprint, behaviors=["threat"]))
    assert result.outcome == "duplicate" and result.case.id == fir_case.id
    assert result.case.stage == Stage.FIR_REGISTERED.value
    dup = [e for e in Ledger(session).entries() if e.action == "alert.duplicate"]
    assert len(dup) == 1 and dup[0].case_id == fir_case.id


def test_an_fir_cannot_be_registered_twice_on_the_same_clip_even_by_a_path_that_skips_dedupe(svc, fir_case):
    # Defence in depth: build a second case on the same fingerprint directly, as a bug or manual path might.
    from app.models import Case

    twin = Case(
        id="APN-9999", kind="social", category="threat", title="twin", summary="twin", priority="routine",
        confidence=0.5, stage=Stage.REFERRED.value, signals=[], behaviors=["threat"],
        content_fingerprint=fir_case.content_fingerprint, subject_ids=[], checks=["context"],
        referred_to_role="authorized_officer", created_at="2026-10-10T10:00:00+00:00", updated_at="2026-10-10T10:00:00+00:00",
    )
    svc.session.add(twin)
    complete_findings = [
        __import__("app.models", fromlist=["CaseItem"]).CaseItem(
            case_id="APN-9999", kind="context_finding", label=k, outcome="supports_flag", description="x",
            added_by="model-v1", added_at="2026-10-10T10:00:00+00:00",
        )
        for k in FINDINGS
    ]
    svc.session.add_all(complete_findings)
    svc.session.commit()
    with pytest.raises(PolicyViolation) as exc:
        svc.act(OFFICER, "APN-9999", "register_fir", note="second FIR on the same clip")
    assert code(exc) == "duplicate_fir" and fir_case.id in exc.value.message


def test_related_information_is_linked_by_a_human_and_cannot_become_a_second_fir(svc, fir_case):
    other = new_alert(svc)  # a different clip about the same issue, judged related by a human
    svc.act(REVIEWER, other.id, "assign")
    with pytest.raises(PolicyViolation) as exc:
        svc.act(REVIEWER, other.id, "link_supplementary", note="same incident")
    assert code(exc) == "link_target_required"
    svc.act(REVIEWER, other.id, "link_supplementary", note="same incident, second clip", link_to=fir_case.id)
    assert other.stage == Stage.LINKED.value and other.linked_to == fir_case.id
    for action in ("refer", "register_fir"):
        with pytest.raises(PolicyViolation):
            svc.act(OFFICER if action == "register_fir" else REVIEWER, other.id, action, note="x")
    # An alert on the linked clip goes to the case it was merged into.
    again = svc.create_alert(AI, **alert_kwargs(content_fingerprint=other.content_fingerprint))
    assert again.outcome == "duplicate" and again.case.id == fir_case.id


def test_link_targets_are_validated(svc, social_case):
    svc.act(REVIEWER, social_case.id, "assign")
    for bad in (social_case.id, "APN-0000"):
        with pytest.raises(PolicyViolation) as exc:
            svc.act(REVIEWER, social_case.id, "link_supplementary", note="x", link_to=bad)
        assert code(exc) == "bad_link_target"


def test_a_case_closed_with_no_action_does_not_block_fresh_review_of_new_information(svc, social_case):
    svc.act(REVIEWER, social_case.id, "no_action", note="no offence on this clip as first seen")
    again = svc.create_alert(AI, **alert_kwargs(content_fingerprint=social_case.content_fingerprint))
    assert again.outcome == "flagged" and again.case.id != social_case.id


def test_a_court_can_permit_a_fresh_registration_so_the_rule_is_not_a_trap(svc, fir_case):
    svc.act(JUDGE, fir_case.id, "court_close", note="clip appeared edited; closed")
    # Without permission, a new alert on the same clip is attached to the closed case.
    blocked = svc.create_alert(AI, **alert_kwargs(content_fingerprint=fir_case.content_fingerprint))
    assert blocked.outcome == "duplicate"
    with pytest.raises(PolicyViolation):
        svc.act(OFFICER, fir_case.id, "permit_fresh_registration", note="not mine to give")
    svc.act(JUDGE, fir_case.id, "permit_fresh_registration", note="the full original has surfaced")
    fresh = svc.create_alert(AI, **alert_kwargs(content_fingerprint=fir_case.content_fingerprint))
    assert fresh.outcome == "flagged" and fresh.case.id != fir_case.id
    svc.act(REVIEWER, fresh.case.id, "assign")
    complete_context(svc, fresh.case)
    svc.act(REVIEWER, fresh.case.id, "refer", note="full original reviewed")
    svc.act(OFFICER, fresh.case.id, "register_fir", note="new material; court permitted fresh registration")
    assert fresh.case.stage == Stage.FIR_REGISTERED.value


# --------------------------------- the 24-hour clock asks a human; it never files anything

def test_the_decision_clock_starts_at_the_flag(svc, social_case):
    assert social_case.decision_due_at.startswith("2026-10-11T10:00")


def test_a_missed_deadline_escalates_to_a_supervisor_and_files_nothing(svc, session, social_case, clock):
    assert svc.sweep_deadlines(SYSTEM) == []
    clock.advance(hours=25)
    breached = svc.sweep_deadlines(SYSTEM)
    assert [c.id for c in breached] == [social_case.id]
    assert social_case.stage == Stage.RECEIVED.value  # no automatic FIR, referral or closure
    assert social_case.fir_registered_at is None
    assert [c.id for c in svc.overdue_decisions()] == [social_case.id]
    entry = [e for e in Ledger(session).entries() if e.action == "sla.breached"][0]
    assert entry.actor_kind == "system" and entry.payload["escalate_to"] == "supervisory_authority"
    assert svc.sweep_deadlines(SYSTEM) == []  # recorded once, not repeatedly


def test_a_case_handled_in_time_is_not_flagged_overdue_and_only_the_scheduler_sweeps(svc, social_case, clock):
    svc.act(REVIEWER, social_case.id, "no_action", note="satire; protected expression")
    clock.advance(hours=48)
    assert svc.sweep_deadlines(SYSTEM) == []
    for who in (AI, REVIEWER, OFFICER, SUPERVISOR, AUDITOR, CITIZEN):
        with pytest.raises(PolicyViolation) as exc:
            svc.sweep_deadlines(who)
        assert code(exc) == "system_only"


# ------------ the AI keeps researching for the response period and can only recommend dismissal

def test_an_ai_dismissal_recommendation_reaches_the_court_queue_but_cancels_nothing(svc, fir_case):
    assert svc.dismissal_recommendations() == []
    svc.add_advisory(AI, fir_case.id, recommendation="Recommend dismissal", kind="dismissal",
                     rationale="Full original shows the line was quoted from a film")
    assert [c.id for c in svc.dismissal_recommendations()] == [fir_case.id]
    assert fir_case.stage == Stage.FIR_REGISTERED.value  # the FIR stands until a court decides
    svc.act(JUDGE, fir_case.id, "court_close", note="Reviewed the AI's findings and the original; no case to answer")
    assert fir_case.stage == Stage.CLOSED_BY_COURT.value
    assert svc.dismissal_recommendations() == []
