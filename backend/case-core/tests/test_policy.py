import pytest

from app.domain import ACTIONS, Category, PolicyViolation, Role, Stage
from app.ledger import Ledger

from .conftest import (
    AI, AUDITOR, CITIZEN, HASH, HASH2, JUDGE, OFFICER, REVIEWER, SUPERVISOR, SYSTEM, actor, alert_kwargs,
    complete_context, new_alert,
)


def code(exc: pytest.ExceptionInfo) -> str:
    return exc.value.code


# ----------------------------------------------------------- AI cannot decide

@pytest.mark.parametrize("who", [AI, SYSTEM], ids=["ai_service", "scheduler"])
@pytest.mark.parametrize("action", sorted(ACTIONS))
def test_automated_actors_cannot_perform_any_workflow_action(svc, social_case, action, who):
    with pytest.raises(PolicyViolation) as exc:
        svc.act(who, social_case.id, action, note="x", check="wellbeing", link_to="APN-1001")
    assert code(exc) == "ai_cannot_decide"


def test_ai_advisory_is_recorded_but_never_moves_a_case(svc, session, social_case):
    before = social_case.stage
    item = svc.add_advisory(AI, social_case.id, recommendation="Recommend dismissal", rationale="alibi video looks authentic")
    assert social_case.stage == before == Stage.RECEIVED.value
    entry = [e for e in Ledger(session).entries() if e.action == "advisory.added"][0]
    assert entry.payload["binding"] is False and entry.actor_kind == "ai"
    assert item.kind == "advisory"


def test_only_ai_can_raise_alerts_and_only_citizens_file_complaints(svc):
    with pytest.raises(PolicyViolation):
        svc.create_alert(REVIEWER, **alert_kwargs())
    with pytest.raises(PolicyViolation):
        svc.file_complaint(OFFICER, title="t", summary="s", subject_ids=["x"])


# ------------------------------------------------------------- role boundaries

def test_reviewer_cannot_register_an_fir(svc, referred_case):
    with pytest.raises(PolicyViolation) as exc:
        svc.act(REVIEWER, referred_case.id, "register_fir", note="basis")
    assert code(exc) == "role_not_permitted"


def test_only_an_authorized_officer_registers_an_fir_and_must_state_a_basis(svc, referred_case):
    with pytest.raises(PolicyViolation) as exc:
        svc.act(OFFICER, referred_case.id, "register_fir")
    assert code(exc) == "note_required"
    for other in (SUPERVISOR, JUDGE, CITIZEN, AUDITOR):
        with pytest.raises(PolicyViolation):
            svc.act(other, referred_case.id, "register_fir", note="basis")
    svc.act(OFFICER, referred_case.id, "register_fir", note="provisions assessed")
    assert referred_case.stage == Stage.FIR_REGISTERED.value


def test_decisions_need_a_written_reason(svc, social_case):
    for action in ("no_action", "request_context"):
        with pytest.raises(PolicyViolation) as exc:
            svc.act(REVIEWER, social_case.id, action, note="   ")
        assert code(exc) == "note_required"


def test_workflow_order_is_enforced(svc, social_case):
    with pytest.raises(PolicyViolation) as exc:
        svc.act(OFFICER, social_case.id, "register_fir", note="skip ahead")
    assert code(exc) == "role_not_permitted" or code(exc) == "invalid_transition"
    with pytest.raises(PolicyViolation) as exc:
        svc.act(REVIEWER, social_case.id, "refer", note="skip assignment")
    assert code(exc) == "invalid_transition"


def test_only_a_judicial_authority_can_close_a_registered_fir(svc, fir_case):
    for other in (REVIEWER, OFFICER, SUPERVISOR, CITIZEN):
        with pytest.raises(PolicyViolation):
            svc.act(other, fir_case.id, "court_close", note="close it")
    svc.act(JUDGE, fir_case.id, "court_close", note="response material accepted; no case to answer")
    assert fir_case.stage == Stage.CLOSED_BY_COURT.value


def test_the_accused_cannot_cancel_their_own_fir_by_uploading(svc, fir_case):
    svc.submit_response(CITIZEN, fir_case.id, label="alibi video", sha256=HASH2)
    assert fir_case.stage == Stage.FIR_REGISTERED.value  # a response informs humans; it decides nothing


# ----------------------------------------------- right to respond and the window

def test_window_starts_only_when_notice_is_recorded_as_served(svc, fir_case, clock):
    assert fir_case.window_closes_at is None
    svc.act(OFFICER, fir_case.id, "serve_notice")
    assert fir_case.window_closes_at.startswith("2026-10-20")
    with pytest.raises(PolicyViolation) as exc:
        svc.act(OFFICER, fir_case.id, "serve_notice")
    assert code(exc) == "already_served"


def test_expiry_never_changes_a_case_and_only_asks_a_human_to_follow_up(svc, fir_case, clock):
    svc.act(OFFICER, fir_case.id, "serve_notice")
    assert svc.window_elapsed_cases() == []
    clock.advance(days=11)
    elapsed = svc.window_elapsed_cases()
    assert [c.id for c in elapsed] == [fir_case.id]
    assert fir_case.stage == Stage.FIR_REGISTERED.value  # no adverse inference, no automatic escalation


def test_a_late_response_is_accepted_and_marked_late_not_refused(svc, fir_case, clock):
    svc.act(OFFICER, fir_case.id, "serve_notice")
    clock.advance(days=14)
    item = svc.submit_response(CITIZEN, fir_case.id, label="CCTV from my shop", sha256=HASH2)
    assert item.late is True and fir_case.response_received is True
    assert svc.window_elapsed_cases() == []


def test_only_a_party_can_respond_and_not_after_closure(svc, fir_case):
    with pytest.raises(PolicyViolation) as exc:
        svc.submit_response(actor(Role.CITIZEN, "stranger"), fir_case.id, label="x")
    assert code(exc) == "not_a_party"
    svc.act(JUDGE, fir_case.id, "court_close", note="closed")
    with pytest.raises(PolicyViolation) as exc:
        svc.submit_response(CITIZEN, fir_case.id, label="too late")
    assert code(exc) == "case_closed"


def test_appeal_stays_open_to_the_affected_party_and_is_resolved_by_a_court(svc, fir_case):
    with pytest.raises(PolicyViolation):
        svc.act(actor(Role.CITIZEN, "stranger"), fir_case.id, "appeal", note="not mine")
    svc.act(CITIZEN, fir_case.id, "appeal", note="the video was misread")
    assert fir_case.appeal_open
    svc.act(JUDGE, fir_case.id, "resolve_appeal", note="heard; matter to proceed")
    assert not fir_case.appeal_open


def test_resolving_without_an_appeal_is_refused(svc, fir_case):
    with pytest.raises(PolicyViolation) as exc:
        svc.act(JUDGE, fir_case.id, "resolve_appeal", note="n/a")
    assert code(exc) == "no_open_appeal"


# --------------------------------------------------------- conduct complaints

@pytest.fixture
def complaint(svc):
    return svc.file_complaint(
        CITIZEN, title="Abusive language at counter", summary="Recording attached",
        subject_ids=["emp-77"], evidence=[{"label": "recording", "sha256": HASH}],
    )


def test_conduct_complaints_route_to_a_supervisory_authority_not_the_force(svc, complaint):
    svc.act(REVIEWER, complaint.id, "assign")
    svc.act(REVIEWER, complaint.id, "refer", note="ready for supervisory review")
    assert complaint.referred_to_role == Role.SUPERVISORY_AUTHORITY.value
    with pytest.raises(PolicyViolation) as exc:
        svc.act(OFFICER, complaint.id, "open_inquiry", note="I'll take it")
    assert code(exc) in ("wrong_handler", "role_not_permitted")
    svc.act(SUPERVISOR, complaint.id, "open_inquiry", note="inquiry opened")
    assert complaint.stage == Stage.INQUIRY.value


def test_a_named_subject_can_never_act_on_their_own_case(svc, complaint):
    subject_reviewer = actor(Role.REVIEWER, "emp-77")
    with pytest.raises(PolicyViolation) as exc:
        svc.act(subject_reviewer, complaint.id, "assign")
    assert code(exc) == "conflict_of_interest"


def test_conduct_complaint_cannot_jump_straight_to_an_fir(svc, complaint):
    svc.act(REVIEWER, complaint.id, "assign")
    svc.act(REVIEWER, complaint.id, "refer", note="ready")
    with pytest.raises(PolicyViolation) as exc:
        svc.act(OFFICER, complaint.id, "register_fir", note="basis")
    assert code(exc) == "inquiry_first"


# ---------------------------------------------------- confession-video alerts

@pytest.fixture
def confession(svc):
    return new_alert(
        svc, category=Category.SELF_CONFESSION_VIDEO, title="Self-uploaded confession video",
        summary="Public video in which the poster says they committed an offence", confidence=0.7,
        behaviors=["self_admission"], priority="routine",
    )


def test_confession_video_needs_human_wellbeing_and_authenticity_checks_before_referral(svc, confession):
    svc.act(REVIEWER, confession.id, "assign")
    complete_context(svc, confession)
    with pytest.raises(PolicyViolation) as exc:
        svc.act(REVIEWER, confession.id, "refer", note="looks real")
    assert code(exc) == "checks_incomplete"
    svc.act(REVIEWER, confession.id, "record_check", check="wellbeing")
    with pytest.raises(PolicyViolation):
        svc.act(REVIEWER, confession.id, "refer", note="still missing authenticity")
    svc.act(REVIEWER, confession.id, "record_check", check="authenticity")
    svc.act(REVIEWER, confession.id, "refer", note="both checks done")
    assert confession.stage == Stage.REFERRED.value


def test_unknown_checks_are_rejected(svc, confession):
    with pytest.raises(PolicyViolation) as exc:
        svc.act(REVIEWER, confession.id, "record_check", check="vibes")
    assert code(exc) == "unknown_check"


# ------------------------------------------- no counter ever restricts the courts

def test_no_flag_or_strike_state_exists_that_could_block_judicial_relief(svc, fir_case):
    from app import domain, models

    for module in (domain, models):
        names = " ".join(dir(module)).lower()
        assert "strike" not in names and "lock" not in names and "permanent" not in names
    # Many alerts and cases against the same person change nothing about what a court can do.
    for _ in range(8):
        new_alert(svc)
    svc.act(JUDGE, fir_case.id, "court_close", note="court retains full power regardless of how many alerts exist")
    assert fir_case.stage == Stage.CLOSED_BY_COURT.value


def test_no_action_closes_and_is_recorded(svc, social_case):
    svc.act(REVIEWER, social_case.id, "no_action", note="satire; protected expression")
    assert social_case.stage == Stage.CLOSED_NO_ACTION.value


def test_hash_validation_and_text_validation(svc):
    with pytest.raises(PolicyViolation) as exc:
        svc.create_alert(AI, **alert_kwargs(evidence=[{"label": "x", "sha256": "nope"}]))
    assert code(exc) == "bad_hash"
    with pytest.raises(PolicyViolation):
        svc.create_alert(AI, **alert_kwargs(title=" "))
    with pytest.raises(PolicyViolation):
        svc.create_alert(AI, **alert_kwargs(confidence=1.5))
