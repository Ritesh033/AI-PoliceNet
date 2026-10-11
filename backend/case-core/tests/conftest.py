import itertools
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.db import init_db, make_engine, make_session_factory
from app.domain import Actor, Category, Role
from app.main import create_app
from app.service import CaseService

HASH = "a" * 64
HASH2 = "b" * 64


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kwargs: float) -> None:
        self.now += timedelta(**kwargs)


_counter = itertools.count(1)
FINDINGS = ("media_source", "edit_detection", "full_context", "cross_platform_copies")


def fingerprint() -> str:
    return f"fp-{next(_counter):08d}"


def alert_kwargs(**overrides) -> dict:
    params = dict(
        category=Category.THREAT, title="Reported threat", summary="Spoken threat in a public video",
        confidence=0.87, content_fingerprint=fingerprint(), behaviors=["threat"], priority="urgent",
        signals=["explicit reference to harm"], evidence=[{"label": "video", "sha256": HASH}],
        affected_party_id="cit-1",
    )
    params.update(overrides)
    return params


def actor(role: Role, ident: str | None = None) -> Actor:
    return Actor(id=ident or role.value, role=role)


AI = actor(Role.AI_SERVICE, "model-v1")
SYSTEM = actor(Role.SYSTEM, "scheduler")
REVIEWER = actor(Role.REVIEWER, "rev-1")
OFFICER = actor(Role.AUTHORIZED_OFFICER, "off-1")
SUPERVISOR = actor(Role.SUPERVISORY_AUTHORITY, "sup-1")
JUDGE = actor(Role.JUDICIAL_AUTHORITY, "judge-1")
AUDITOR = actor(Role.AUDITOR, "aud-1")
CITIZEN = actor(Role.CITIZEN, "cit-1")


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def engine():
    eng = make_engine("sqlite://")
    init_db(eng)
    return eng


@pytest.fixture
def session(engine):
    factory = make_session_factory(engine)
    with factory() as s:
        yield s


@pytest.fixture
def svc(session, clock) -> CaseService:
    settings = Settings(env="demo", database_url="sqlite://", response_window_days=10, decision_sla_hours=24, checkpoint_key="test-key")
    return CaseService(session, clock, settings)


def new_alert(svc, **overrides):
    """Raise an alert that passes the flagging policy and return the new case."""
    result = svc.create_alert(AI, **alert_kwargs(**overrides))
    assert result.case is not None and result.outcome == "flagged", result
    return result.case


def complete_context(svc, case, outcome: str = "supports_flag") -> None:
    """The AI finishes its full-context research and a human acknowledges it."""
    for key in FINDINGS:
        svc.add_context_finding(AI, case.id, key=key, outcome=outcome, summary=f"{key} examined")
    svc.act(REVIEWER, case.id, "record_check", check="context")


@pytest.fixture
def social_case(svc):
    return new_alert(svc)


@pytest.fixture
def referred_case(svc, social_case):
    svc.act(REVIEWER, social_case.id, "assign")
    complete_context(svc, social_case)
    svc.act(REVIEWER, social_case.id, "refer", note="context verified")
    return social_case


@pytest.fixture
def fir_case(svc, referred_case):
    svc.act(OFFICER, referred_case.id, "register_fir", note="assessed provisions; cognizable offence made out")
    return referred_case


@pytest.fixture
def client(engine, monkeypatch):
    monkeypatch.setenv("APN_ENV", "demo")
    monkeypatch.setenv("APN_CHECKPOINT_KEY", "test-key")
    return TestClient(create_app(make_session_factory(engine)))


def headers(a: Actor) -> dict:
    return {"X-Actor-Id": a.id, "X-Actor-Role": a.role.value}
