from sqlalchemy import text

from .conftest import AI, AUDITOR, CITIZEN, HASH, HASH2, JUDGE, OFFICER, REVIEWER, headers

ALERT = {
    "category": "threat", "title": "Reported threat", "summary": "Spoken threat in a public video",
    "confidence": 0.87, "priority": "urgent", "signals": ["explicit harm"],
    "evidence": [{"label": "video", "sha256": HASH}], "affected_party_id": "cit-1",
}


def test_health_reports_demo_auth(client):
    assert client.get("/health").json() == {"status": "ok", "auth": "demo-stub"}


def test_auth_fails_closed_outside_demo_mode(client, monkeypatch):
    monkeypatch.setenv("APN_ENV", "production")
    r = client.get("/cases", headers=headers(REVIEWER))
    assert r.status_code == 503


def test_missing_or_unknown_identity_is_401(client):
    assert client.get("/cases").status_code == 401
    assert client.get("/cases", headers={"X-Actor-Id": "x", "X-Actor-Role": "emperor"}).status_code == 401


def test_full_flow_with_human_decisions_and_a_verifiable_ledger(client):
    r = client.post("/alerts", json=ALERT, headers=headers(AI))
    assert r.status_code == 201
    case = r.json()
    cid = case["id"]
    assert cid == "APN-1001" and "advisory" in case["ai_notice"]

    # The AI cannot decide anything, over HTTP either.
    r = client.post(f"/cases/{cid}/actions", json={"action": "register_fir", "note": "x"}, headers=headers(AI))
    assert r.status_code == 403 and r.json()["error"] == "ai_cannot_decide"

    def do(who, action, **extra):
        return client.post(f"/cases/{cid}/actions", json={"action": action, **extra}, headers=headers(who))

    assert do(REVIEWER, "assign").status_code == 200
    assert do(REVIEWER, "refer", note="verified context").status_code == 200
    assert do(OFFICER, "register_fir", note="provisions assessed").json()["stage"] == "fir_registered"
    assert do(OFFICER, "serve_notice").json()["window_closes_at"]

    r = client.post(f"/cases/{cid}/responses", json={"label": "alibi", "sha256": HASH2}, headers=headers(CITIZEN))
    assert r.status_code == 201
    assert client.get(f"/cases/{cid}", headers=headers(CITIZEN)).json()["stage"] == "fir_registered"

    assert do(JUDGE, "court_close", note="no case to answer").json()["stage"] == "closed_by_court"

    v = client.get("/ledger/verify", headers=headers(AUDITOR)).json()
    assert v["chain_valid"] and v["projection_consistent"] and v["entries_checked"] == 7  # created, assign, refer, FIR, notice, response, court close
    cp = client.get("/ledger/checkpoint", headers=headers(AUDITOR)).json()
    assert cp["chain_valid"] and len(cp["signature"]) == 64


def test_citizens_see_only_their_own_cases_and_never_model_signals(client):
    cid = client.post("/alerts", json=ALERT, headers=headers(AI)).json()["id"]
    own = client.get(f"/cases/{cid}", headers=headers(CITIZEN)).json()
    assert "signals" not in own
    stranger = {"X-Actor-Id": "stranger", "X-Actor-Role": "citizen"}
    assert client.get(f"/cases/{cid}", headers=stranger).status_code == 403
    assert client.get("/cases", headers=headers(CITIZEN)).status_code == 403
    staff = client.get(f"/cases/{cid}", headers=headers(REVIEWER)).json()
    assert staff["signals"] == ["explicit harm"]


def test_sensitive_items_never_carry_media_only_a_hash(client):
    body = {**ALERT, "category": "ncii", "title": "Suspected NCII"}
    case = client.post("/alerts", json=body, headers=headers(AI)).json()
    item = case["items"][0]
    assert item["preview_withheld"] is True and item["sha256"] == HASH
    assert set(item) == {"id", "kind", "label", "description", "sha256", "preview_withheld", "late", "added_by", "added_at"}


def test_ledger_is_for_oversight_roles_only(client):
    assert client.get("/ledger", headers=headers(REVIEWER)).status_code == 403
    assert client.get("/ledger", headers=headers(CITIZEN)).status_code == 403
    assert client.get("/ledger", headers=headers(AUDITOR)).status_code == 200
    assert client.get("/ledger", headers=headers(JUDGE)).status_code == 200


def test_api_reports_tampering(client, engine):
    client.post("/alerts", json=ALERT, headers=headers(AI))
    with engine.begin() as conn:
        conn.execute(text("DROP TRIGGER ledger_no_update"))
        conn.execute(text("UPDATE ledger SET actor_role='authorized_officer' WHERE seq=1"))
    v = client.get("/ledger/verify", headers=headers(AUDITOR)).json()
    assert v["chain_valid"] is False and v["first_bad_seq"] == 1


def test_complaint_endpoint_and_validation_errors(client):
    r = client.post("/complaints", json={"title": "t", "summary": "s", "subject_ids": []}, headers=headers(CITIZEN))
    assert r.status_code == 422 and r.json()["error"] == "subject_required"
    r = client.post("/alerts", json={**ALERT, "evidence": [{"label": "x", "sha256": "bad"}]}, headers=headers(AI))
    assert r.status_code == 422
