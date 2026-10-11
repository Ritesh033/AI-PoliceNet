from sqlalchemy import text

from .conftest import AI, AUDITOR, CITIZEN, FINDINGS, HASH, HASH2, JUDGE, OFFICER, REVIEWER, SYSTEM, headers

ALERT = {
    "category": "threat", "title": "Reported threat", "summary": "Spoken threat in a public video",
    "confidence": 0.87, "priority": "urgent", "signals": ["explicit harm"],
    "content_fingerprint": "fp-api-0001", "behaviors": ["threat"], "situation": [],
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
    assert cid == "APN-1001" and "advisory" in case["ai_notice"] and case["outcome"] == "flagged"
    assert case["decision_due_at"] and set(case["context_missing"]) == set(FINDINGS)

    # The AI cannot decide anything, over HTTP either.
    r = client.post(f"/cases/{cid}/actions", json={"action": "register_fir", "note": "x"}, headers=headers(AI))
    assert r.status_code == 403 and r.json()["error"] == "ai_cannot_decide"

    def do(who, action, **extra):
        return client.post(f"/cases/{cid}/actions", json={"action": action, **extra}, headers=headers(who))

    assert do(REVIEWER, "assign").status_code == 200
    # Referral is blocked until the AI's full-context research is in and a human has acknowledged it.
    blocked = do(REVIEWER, "refer", note="too early")
    assert blocked.status_code == 409 and blocked.json()["error"] == "context_incomplete"
    for key in FINDINGS:
        r = client.post(f"/cases/{cid}/context-findings", headers=headers(AI),
                        json={"key": key, "outcome": "supports_flag", "summary": f"{key} examined"})
        assert r.status_code == 201
    assert do(REVIEWER, "record_check", check="context").status_code == 200
    assert do(REVIEWER, "refer", note="verified context").status_code == 200
    assert do(OFFICER, "register_fir", note="provisions assessed").json()["stage"] == "fir_registered"
    assert do(OFFICER, "serve_notice").json()["window_closes_at"]

    r = client.post(f"/cases/{cid}/responses", json={"label": "alibi", "sha256": HASH2}, headers=headers(CITIZEN))
    assert r.status_code == 201
    assert client.get(f"/cases/{cid}", headers=headers(CITIZEN)).json()["stage"] == "fir_registered"

    assert do(JUDGE, "court_close", note="no case to answer").json()["stage"] == "closed_by_court"

    v = client.get("/ledger/verify", headers=headers(AUDITOR)).json()
    assert v["chain_valid"] and v["projection_consistent"] and v["entries_checked"] == 12  # created, assign, 4 findings, context check, refer, FIR, notice, response, court close
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
    body = {**ALERT, "category": "ncii", "title": "Suspected NCII", "behaviors": ["non_consensual_imagery"],
            "content_fingerprint": "fp-api-0002"}
    case = client.post("/alerts", json=body, headers=headers(AI)).json()
    item = case["items"][0]
    assert item["preview_withheld"] is True and item["sha256"] == HASH
    assert set(item) == {"id", "kind", "label", "outcome", "description", "sha256", "preview_withheld", "late", "added_by", "added_at"}


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


def test_policy_drops_everyday_abuse_without_opening_a_case(client):
    body = {**ALERT, "behaviors": ["casual_profanity", "insult"], "situation": ["friendly_banter"], "content_fingerprint": "fp-api-0003"}
    r = client.post("/alerts", json=body, headers=headers(AI))
    assert r.status_code == 200 and r.json()["outcome"] == "no_flag" and "id" not in r.json()
    assert client.get("/cases", headers=headers(REVIEWER)).json() == []
    entries = client.get("/ledger", headers=headers(AUDITOR)).json()
    assert [e["action"] for e in entries] == ["triage.no_flag"] and entries[0]["case_id"] is None


def test_abuse_of_a_public_official_is_not_flagged_but_a_threat_against_them_is(client):
    abuse = {**ALERT, "behaviors": ["aggressive_abuse"], "situation": ["political_commentary", "public_official_target"],
             "content_fingerprint": "fp-api-0004"}
    assert client.post("/alerts", json=abuse, headers=headers(AI)).json()["outcome"] == "no_flag"
    threat = {**ALERT, "behaviors": ["threat"], "situation": ["public_official_target"], "content_fingerprint": "fp-api-0005"}
    r = client.post("/alerts", json=threat, headers=headers(AI))
    assert r.status_code == 201 and r.json()["outcome"] == "flagged"


def test_a_repeat_alert_on_the_same_clip_is_attached_not_duplicated(client):
    first = client.post("/alerts", json=ALERT, headers=headers(AI))
    again = client.post("/alerts", json=ALERT, headers=headers(AI))
    assert first.status_code == 201 and again.status_code == 200
    assert again.json()["outcome"] == "duplicate" and again.json()["id"] == first.json()["id"]
    assert len(client.get("/cases", headers=headers(REVIEWER)).json()) == 1


def test_deadline_sweep_is_for_the_scheduler_only_and_overdue_list_is_for_staff(client):
    assert client.post("/attention/sweep", headers=headers(REVIEWER)).status_code == 403
    assert client.post("/attention/sweep", headers=headers(AI)).status_code == 403
    assert client.post("/attention/sweep", headers=headers(SYSTEM)).json() == {"newly_breached": []}
    assert client.get("/attention/overdue-decisions", headers=headers(REVIEWER)).status_code == 200
    assert client.get("/attention/overdue-decisions", headers=headers(CITIZEN)).status_code == 403


def test_dismissal_recommendations_are_visible_to_courts_and_auditors_only(client):
    assert client.get("/attention/dismissal-recommendations", headers=headers(JUDGE)).status_code == 200
    assert client.get("/attention/dismissal-recommendations", headers=headers(AUDITOR)).status_code == 200
    assert client.get("/attention/dismissal-recommendations", headers=headers(OFFICER)).status_code == 403
