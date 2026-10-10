import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.domain import Category
from app.ledger import Ledger, verify_checkpoint
from app.models import Case
from app.service import CaseService

from .conftest import AI, HASH, REVIEWER


def test_empty_ledger_is_valid(session):
    assert Ledger(session).verify().ok


def test_chain_links_and_verifies(svc, session, social_case):
    svc.act(REVIEWER, social_case.id, "assign")
    entries = Ledger(session).entries()
    assert [e.seq for e in entries] == [1, 2]
    assert entries[1].prev_hash == entries[0].hash
    assert Ledger(session).verify().ok


def test_database_rejects_update_and_delete(svc, session, social_case):
    with pytest.raises(DBAPIError, match="append-only"):
        session.execute(text("UPDATE ledger SET actor_id='someone-else' WHERE seq=1"))
    session.rollback()
    with pytest.raises(DBAPIError, match="append-only"):
        session.execute(text("DELETE FROM ledger WHERE seq=1"))
    session.rollback()


def test_edit_by_someone_with_schema_access_is_detected(svc, session, social_case):
    """Even if an administrator drops the triggers and rewrites history, verification fails."""
    svc.act(REVIEWER, social_case.id, "assign")
    session.execute(text("DROP TRIGGER ledger_no_update"))
    session.execute(text("UPDATE ledger SET actor_id='forged' WHERE seq=1"))
    session.commit()
    result = Ledger(session).verify()
    assert not result.ok
    assert result.first_bad_seq == 1
    assert "hash" in result.reason


def test_deleting_an_entry_is_detected(svc, session, social_case):
    svc.act(REVIEWER, social_case.id, "assign")
    svc.act(REVIEWER, social_case.id, "request_context", note="need the original upload")
    session.execute(text("DROP TRIGGER ledger_no_delete"))
    session.execute(text("DELETE FROM ledger WHERE seq=2"))
    session.commit()
    result = Ledger(session).verify()
    assert not result.ok and result.first_bad_seq == 3


def test_checkpoint_signs_the_head_and_detects_forgery(svc, session, social_case):
    cp = Ledger(session).checkpoint("test-key")
    assert cp["chain_valid"] and cp["entries"] == 1
    assert verify_checkpoint(cp, "test-key")
    assert not verify_checkpoint({**cp, "entries": 99}, "test-key")
    assert not verify_checkpoint(cp, "wrong-key")


def test_checkpoint_needs_a_configured_key(session):
    with pytest.raises(ValueError):
        Ledger(session).checkpoint("")


def test_projection_matches_ledger_and_detects_a_silent_state_edit(svc, session, social_case):
    svc.act(REVIEWER, social_case.id, "assign")
    assert svc.verify_projection() == []
    # Someone edits the cases table directly, bypassing the workflow and the ledger.
    session.execute(text("UPDATE cases SET stage='fir_registered' WHERE id=:i"), {"i": social_case.id})
    session.commit()
    problems = CaseService(session, settings=svc.settings).verify_projection()
    assert problems and social_case.id in problems[0]


def test_every_decision_is_attributed_to_a_human_and_ai_alerts_to_the_ai(svc, session, social_case):
    svc.act(REVIEWER, social_case.id, "assign")
    kinds = {(e.action, e.actor_kind) for e in Ledger(session).entries()}
    assert ("case.created", "ai") in kinds
    assert ("case.assign", "human") in kinds


def test_sensitive_evidence_stores_hash_only_and_marks_preview_withheld(svc):
    case = svc.create_alert(
        AI, category=Category.NCII, title="Suspected NCII", summary="Flagged by classifier", confidence=0.9,
        evidence=[{"label": "clip", "sha256": HASH}],
    )
    item = case.items[0]
    assert item.preview_withheld and item.sha256 == HASH
    assert not hasattr(item, "media") and not hasattr(item, "content")
    assert session_count(svc, Case) == 1


def session_count(svc, model):
    from sqlalchemy import func, select

    return svc.session.execute(select(func.count()).select_from(model)).scalar_one()
