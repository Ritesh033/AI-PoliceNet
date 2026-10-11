import os
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.db import make_session_factory
from app.demo_seed import seed
from app.domain import ACTIONS
from app.ledger import Ledger
from app.main import create_app
from app.models import Case
from app.service import CaseService

from .conftest import AUDITOR, CITIZEN, REVIEWER, headers


def test_seed_builds_every_guardrail_scenario_and_the_ledger_verifies(session, clock):
    ids = seed(session, clock)
    assert len(ids) == 7
    cases = {c.id: c for c in session.query(Case)}
    stages = {c.title: c.stage for c in cases.values()}
    assert stages["Reported threat of violence in a public video"] == "received"
    assert stages["Quoted line mistaken for a call to violence"] == "fir_registered"
    assert any(c.dismissal_recommended for c in cases.values())
    ncii = next(c for c in cases.values() if c.category == "ncii")
    assert ncii.items[0].preview_withheld and ncii.items[0].sha256
    assert sum(1 for e in Ledger(session).entries(limit=500) if e.action == "triage.no_flag") == 1
    svc = CaseService(session, clock)
    assert Ledger(session).verify().ok and svc.verify_projection() == []
    # Nothing was decided by a machine: every stage change after creation was made by a human actor.
    for e in Ledger(session).entries(limit=500):
        if e.action.startswith("case.") and e.action != "case.created":
            assert e.actor_kind == "human"


def test_seed_cli_refuses_outside_demo_mode(tmp_path):
    env = {**os.environ, "APN_ENV": "", "DATABASE_URL": f"sqlite:///{tmp_path}/x.db"}
    root = Path(__file__).resolve().parents[1]
    proc = subprocess.run([sys.executable, "-m", "app.demo_seed"], cwd=root, env=env, capture_output=True, text=True)
    assert proc.returncode == 2 and "Refusing to seed" in proc.stderr
    assert not (tmp_path / "x.db").exists()


def test_meta_actions_mirror_the_enforced_rules(client):
    meta = client.get("/meta/actions", headers=headers(REVIEWER)).json()
    assert set(meta["actions"]) == set(ACTIONS)
    reg = meta["actions"]["register_fir"]
    assert reg["roles"] == ["authorized_officer"] and reg["note_required"] is True
    assert meta["actions"]["record_check"]["params"] == ["check"]
    assert meta["actions"]["link_supplementary"]["params"] == ["link_to"]
    assert "context" in meta["checks"]
    assert client.get("/meta/actions").status_code == 401


def test_cors_allows_only_the_configured_origin(engine, monkeypatch):
    monkeypatch.setenv("APN_ENV", "demo")
    monkeypatch.setenv("APN_CORS_ORIGINS", "http://localhost:3100")
    client = TestClient(create_app(make_session_factory(engine)))
    ok = client.options("/cases", headers={
        "Origin": "http://localhost:3100", "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "x-actor-id,x-actor-role",
    })
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3100"
    bad = client.options("/cases", headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in bad.headers


def test_no_cors_headers_unless_configured(client):
    r = client.get("/health", headers={"Origin": "http://localhost:3100"})
    assert "access-control-allow-origin" not in r.headers
