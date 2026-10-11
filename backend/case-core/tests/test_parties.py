"""Who is the suspect, the notice a suspect receives, and responding with no login."""

import hashlib
import re
from pathlib import Path

import pytest

from app import models, service
from app.domain import Category, PolicyViolation, Stage
from app.ledger import Ledger
from app.models import Base, CaseItem

from .conftest import (
    AI, CITIZEN, HASH, HASH2, JUDGE, OFFICER, REVIEWER, SUPERVISOR, FINDINGS, complete_context, headers, new_alert,
)


def code(exc: pytest.ExceptionInfo) -> str:
    return exc.value.code


def referred_scenario_case(svc, scenario, behaviors, parties, category=Category.NCII):
    case = new_alert(svc, scenario=scenario, behaviors=behaviors, category=category, priority="high")
    svc.propose_parties(AI, case.id, parties)
    svc.act(REVIEWER, case.id, "assign")
    complete_context(svc, case)
    svc.act(REVIEWER, case.id, "refer", note="context reviewed")
    return case


@pytest.fixture
def intimate(svc):
    """Intimate imagery shared without consent: two people depicted, an uploader, someone who reshared it."""
    return referred_scenario_case(
        svc, "intimate_imagery_without_consent", ["non_consensual_imagery"],
        [
            {"ref": "acct:depicted-1", "role": "depicted_person", "rationale": "appears in the clip"},
            {"ref": "acct:depicted-2", "role": "depicted_person", "rationale": "appears in the clip"},
            {"ref": "acct:uploader-1", "role": "uploader", "rationale": "first account to post the clip"},
            {"ref": "acct:sharer-1", "role": "sharer", "rationale": "reposted it to a large group"},
        ],
    )


def determine(svc, case, ref, role, determination, note="decided on the facts", who=OFFICER):
    return svc.act(who, case.id, "determine_party", note=note, party_ref=ref, party_role=role, determination=determination)


# ------------------------------------------- the victim is never the suspect

def test_people_depicted_in_intimate_imagery_shared_without_consent_are_never_subjects(svc, intimate):
    for ref in ("acct:depicted-1", "acct:depicted-2"):
        with pytest.raises(PolicyViolation) as exc:
            determine(svc, intimate, ref, "depicted_person", "subject")
        assert code(exc) == "not_a_subject_role" and "victim" in exc.value.message
        determine(svc, intimate, ref, "depicted_person", "victim")
    # The person who uploaded it, and the person who reposted it, can be.
    determine(svc, intimate, "acct:uploader-1", "uploader", "subject")
    determine(svc, intimate, "acct:sharer-1", "sharer", "subject")
    by_ref = {(p.ref, p.role): p.determination for p in intimate.parties}
    assert by_ref[("acct:uploader-1", "uploader")] == "subject"
    assert by_ref[("acct:depicted-1", "depicted_person")] == "victim"


def test_two_adults_in_a_private_video_are_victims_of_the_person_who_leaked_it(svc, intimate):
    """The product rule in one test: the people in the video are not criminals, the uploader is the suspect."""
    for ref in ("acct:depicted-1", "acct:depicted-2"):
        determine(svc, intimate, ref, "depicted_person", "victim")
    determine(svc, intimate, "acct:uploader-1", "uploader", "subject")
    svc.act(OFFICER, intimate.id, "register_fir", note="Provisions assessed against the uploader (sample)")
    assert intimate.stage == Stage.FIR_REGISTERED.value
    subjects = {p.ref for p in intimate.parties if p.determination == "subject"}
    assert subjects == {"acct:uploader-1"}


# ---------------------------------- a public indecent act: the performer, not the recorder

@pytest.fixture
def public_act(svc):
    return referred_scenario_case(
        svc, "public_indecent_act", ["sexual_content"],
        [
            {"ref": "acct:performer-1", "role": "performer_in_public_act", "rationale": "performs in the live public clip"},
            {"ref": "acct:recorder-1", "role": "recorder", "rationale": "bystander who filmed it"},
            {"ref": "acct:uploader-1", "role": "uploader", "rationale": "posted the clip"},
        ],
        category=Category.SCAM,
    )


def test_in_a_public_indecent_act_the_performer_is_the_subject_not_whoever_recorded_or_posted_it(svc, public_act):
    determine(svc, public_act, "acct:performer-1", "performer_in_public_act", "subject")
    for ref, role in (("acct:recorder-1", "recorder"), ("acct:uploader-1", "uploader")):
        with pytest.raises(PolicyViolation) as exc:
            determine(svc, public_act, ref, role, "subject")
        assert code(exc) == "not_a_subject_role" and "performing" in exc.value.message
        determine(svc, public_act, ref, role, "not_involved")


def test_an_uploader_in_a_public_act_case_can_be_a_subject_only_for_their_own_separate_wrongdoing(svc):
    case = referred_scenario_case(
        svc, "public_indecent_act", ["sexual_content", "extortion"],
        [{"ref": "acct:uploader-9", "role": "uploader", "rationale": "demanded money to delete the clip"}],
        category=Category.SCAM,
    )
    determine(svc, case, "acct:uploader-9", "uploader", "subject", note="extortion, flagged on its own behaviour")


def test_a_depicted_person_who_also_published_the_material_is_judged_in_each_role_separately(svc):
    case = referred_scenario_case(
        svc, "explicit_content_published", ["sexual_content"],
        [
            {"ref": "acct:creator-1", "role": "depicted_person", "rationale": "appears in the video"},
            {"ref": "acct:creator-1", "role": "uploader", "rationale": "posted it from their own account"},
        ],
        category=Category.SCAM,
    )
    with pytest.raises(PolicyViolation):
        determine(svc, case, "acct:creator-1", "depicted_person", "subject")
    determine(svc, case, "acct:creator-1", "uploader", "subject", note="published the material")


# ----------------------------------------------------------- humans decide

def test_only_an_authorized_officer_determines_parties_and_only_among_proposed_parties(svc, intimate):
    for who in (REVIEWER, SUPERVISOR, JUDGE, CITIZEN):
        with pytest.raises(PolicyViolation) as exc:
            determine(svc, intimate, "acct:uploader-1", "uploader", "subject", who=who)
        assert code(exc) in ("role_not_permitted",)
    with pytest.raises(PolicyViolation) as exc:
        determine(svc, intimate, "acct:made-up", "uploader", "subject")
    assert code(exc) == "unknown_party"
    with pytest.raises(PolicyViolation) as exc:
        determine(svc, intimate, "acct:uploader-1", "sharer", "subject")  # right ref, role never proposed
    assert code(exc) == "unknown_party"
    with pytest.raises(PolicyViolation) as exc:
        determine(svc, intimate, "acct:uploader-1", "uploader", "guilty")
    assert code(exc) == "bad_determination"
    with pytest.raises(PolicyViolation) as exc:
        svc.act(OFFICER, intimate.id, "determine_party", note="x", party_ref="acct:uploader-1")
    assert code(exc) == "party_params_required"
    with pytest.raises(PolicyViolation) as exc:
        svc.act(OFFICER, intimate.id, "determine_party", party_ref="acct:uploader-1", party_role="uploader", determination="subject")
    assert code(exc) == "note_required"


def test_the_ai_proposes_parties_but_cannot_decide_anyone_s_status(svc, social_case):
    with pytest.raises(PolicyViolation):
        svc.propose_parties(REVIEWER, social_case.id, [{"ref": "acct:x1", "role": "uploader"}])
    created = svc.propose_parties(AI, social_case.id, [{"ref": "acct:x1", "role": "uploader", "rationale": "posted it"}])
    assert created[0].determination is None  # a proposal decides nothing
    again = svc.propose_parties(AI, social_case.id, [{"ref": "acct:x1", "role": "uploader"}])
    assert again == []  # idempotent


@pytest.mark.parametrize("ref", ["person@example.com", "9876543210", "+91 98765 43210", "", "x" * 65])
def test_a_party_reference_can_never_be_an_email_or_phone_number(svc, social_case, ref):
    with pytest.raises(PolicyViolation) as exc:
        svc.propose_parties(AI, social_case.id, [{"ref": ref, "role": "uploader"}])
    assert code(exc) in ("ref_must_be_pseudonymous", "bad_ref")


def test_unknown_roles_are_rejected(svc, social_case):
    with pytest.raises(PolicyViolation) as exc:
        svc.propose_parties(AI, social_case.id, [{"ref": "acct:x1", "role": "criminal"}])
    assert code(exc) == "bad_role"


def test_an_fir_in_a_scenario_case_needs_the_parties_decided_first(svc, intimate):
    with pytest.raises(PolicyViolation) as exc:
        svc.act(OFFICER, intimate.id, "register_fir", note="basis")
    assert code(exc) == "parties_undetermined"
    determine(svc, intimate, "acct:depicted-1", "depicted_person", "victim")
    svc.act(OFFICER, intimate.id, "register_fir", note="basis")
    assert intimate.stage == Stage.FIR_REGISTERED.value


# ------------------------------------------- the notice, with no auto-messaging

@pytest.fixture
def fir_intimate(svc, intimate):
    determine(svc, intimate, "acct:depicted-1", "depicted_person", "victim")
    determine(svc, intimate, "acct:uploader-1", "uploader", "subject")
    svc.act(OFFICER, intimate.id, "register_fir", note="Provisions assessed (sample)")
    return intimate


def test_a_notice_goes_only_to_a_determined_subject_never_to_a_victim(svc, fir_intimate):
    with pytest.raises(PolicyViolation) as exc:
        svc.act(OFFICER, fir_intimate.id, "serve_notice")
    assert code(exc) == "party_ref_required"
    for ref in ("acct:depicted-1", "acct:depicted-2", "acct:sharer-1"):  # victim, undetermined, undetermined
        with pytest.raises(PolicyViolation) as exc:
            svc.act(OFFICER, fir_intimate.id, "serve_notice", party_ref=ref)
        assert code(exc) == "notice_only_to_subjects"
    with pytest.raises(PolicyViolation) as exc:
        svc.act(OFFICER, fir_intimate.id, "serve_notice", party_ref="acct:nobody")
    assert code(exc) == "unknown_party"
    svc.act(OFFICER, fir_intimate.id, "serve_notice", party_ref="acct:uploader-1")
    with pytest.raises(PolicyViolation) as exc:
        svc.act(OFFICER, fir_intimate.id, "serve_notice", party_ref="acct:uploader-1")
    assert code(exc) == "already_served"


def test_the_notice_explains_why_what_it_means_and_how_to_respond_without_logging_in(svc, session, fir_intimate):
    case = svc.act(OFFICER, fir_intimate.id, "serve_notice", party_ref="acct:uploader-1")
    text = case.issued_notice_text
    assert case.issued_response_token and f"/public/responses/{case.issued_response_token}" in text
    lowered = text.lower()
    for phrase in (
        "intimate imagery shared without consent",   # why
        "an automated system only raised the flag",  # a machine did not decide
        "authorized officer decided",                # a human did
        "not a finding that you did anything wrong", # presumption of innocence
        "full, unedited video",                      # how to save themselves
        "from any account or device",
        "do not need to log in",
        "do not have to say who you are",
        "nothing happens to you automatically",      # no adverse inference
        "never ask for",                             # anti-scam
        "money, bank details, otps",
        "lawyer",
    ):
        assert phrase in lowered, phrase
    assert "a human reads the material you send" in lowered
    assert "may also compare it" in lowered  # promises no automatic matching the platform does not yet do
    assert "what was checked before the officer decided" in lowered
    assert "from a film, show or skit" in lowered


def test_the_response_link_is_shown_once_and_only_its_hash_is_stored(svc, session, fir_intimate):
    case = svc.act(OFFICER, fir_intimate.id, "serve_notice", party_ref="acct:uploader-1")
    token = case.issued_response_token
    notice = session.query(CaseItem).filter_by(kind="notice").one()
    assert token not in notice.description and token not in (notice.label or "")
    assert notice.sha256 == hashlib.sha256(token.encode()).hexdigest()
    entry = [e for e in Ledger(session).entries(limit=500) if e.action == "case.serve_notice"][0]
    assert token not in str(entry.payload) and entry.payload["notice_sha256"]
    assert entry.payload["party_ref"] == "acct:uploader-1"


# ---------------------------------------------------- respond with no login

def serve(svc, fir_intimate):
    return svc.act(OFFICER, fir_intimate.id, "serve_notice", party_ref="acct:uploader-1").issued_response_token


def test_anyone_holding_the_link_can_respond_from_any_account_without_identifying_themselves(svc, session, fir_intimate):
    token = serve(svc, fir_intimate)
    item = svc.submit_response_by_token(token, label="Full original video", description="Uploaded from a friend's phone", sha256=HASH2)
    assert item.kind == "response" and item.added_by.startswith("link:") and item.late is False
    assert fir_intimate.response_received and fir_intimate.stage == Stage.FIR_REGISTERED.value  # informs, never decides
    entry = [e for e in Ledger(session).entries(limit=500) if e.action == "response.submitted"][-1]
    assert entry.payload["via"] == "response_link" and entry.actor_id.startswith("link:")


def test_the_ai_can_record_that_a_response_matches_the_flagged_clip_but_it_decides_nothing(svc, fir_intimate):
    token = serve(svc, fir_intimate)
    svc.submit_response_by_token(token, label="Full original video", sha256=HASH2)
    svc.add_context_finding(AI, fir_intimate.id, key="response_match", outcome="undermines_flag",
                            summary="Uploaded material is the full original; the flagged clip is a cut of it")
    svc.add_advisory(AI, fir_intimate.id, recommendation="Recommend dismissal", kind="dismissal")
    assert fir_intimate.stage == Stage.FIR_REGISTERED.value
    assert [c.id for c in svc.dismissal_recommendations()] == [fir_intimate.id]


def test_response_links_are_validated_closed_with_the_case_and_limited(svc, fir_intimate, clock, monkeypatch):
    with pytest.raises(PolicyViolation) as exc:
        svc.submit_response_by_token("not-a-real-token", label="x")
    assert code(exc) == "unknown_link" and exc.value.status == 404
    token = serve(svc, fir_intimate)
    with pytest.raises(PolicyViolation) as exc:
        svc.submit_response_by_token(token, label="  ")
    assert code(exc) == "empty_text"
    with pytest.raises(PolicyViolation) as exc:
        svc.submit_response_by_token(token, label="x", sha256="nope")
    assert code(exc) == "bad_hash"
    clock.advance(days=12)
    assert svc.submit_response_by_token(token, label="late but accepted").late is True
    monkeypatch.setattr(service, "TOKEN_RESPONSE_LIMIT", 2)
    svc.submit_response_by_token(token, label="second")
    with pytest.raises(PolicyViolation) as exc:
        svc.submit_response_by_token(token, label="third")
    assert code(exc) == "too_many_responses" and exc.value.status == 429
    svc.act(JUDGE, fir_intimate.id, "court_close", note="closed")
    with pytest.raises(PolicyViolation) as exc:
        svc.submit_response_by_token(token, label="after closure")
    assert code(exc) == "case_closed"


# ---------------------- identifying a person is a recorded legal-process step by an officer

def test_identification_is_a_recorded_officer_step_with_a_legal_basis_and_never_for_a_victim(svc, session, fir_intimate):
    with pytest.raises(PolicyViolation) as exc:
        svc.act(REVIEWER, fir_intimate.id, "request_identification", note="x", party_ref="acct:uploader-1", legal_basis="ref 1")
    assert code(exc) == "role_not_permitted"
    with pytest.raises(PolicyViolation) as exc:
        svc.act(OFFICER, fir_intimate.id, "request_identification", note="x", party_ref="acct:uploader-1")
    assert code(exc) == "legal_basis_required"
    with pytest.raises(PolicyViolation) as exc:
        svc.act(OFFICER, fir_intimate.id, "request_identification", note="x", party_ref="acct:depicted-1", legal_basis="ref 1")
    assert code(exc) == "identification_not_allowed"
    with pytest.raises(PolicyViolation) as exc:
        svc.act(OFFICER, fir_intimate.id, "request_identification", note="x", party_ref="acct:ghost", legal_basis="ref 1")
    assert code(exc) == "unknown_party"
    svc.act(OFFICER, fir_intimate.id, "request_identification",
            note="Intermediary asked to disclose subscriber details", party_ref="acct:uploader-1",
            legal_basis="Notice under the applicable provision, ref SAMPLE/2026/114")
    entry = [e for e in Ledger(session).entries(limit=500) if e.action == "case.request_identification"][0]
    assert entry.payload["legal_basis"].startswith("Notice under") and entry.payload["party_ref"] == "acct:uploader-1"
    assert entry.actor_kind == "human"


def test_no_social_case_action_exists_that_looks_up_or_messages_a_person():
    from app.domain import ACTIONS

    for name in ACTIONS:
        assert not re.search(r"lookup|harvest|scrape|message|sms|whatsapp|email|dox", name), name


# ------------------ the two "never" guarantees: no contact details stored, nothing ever sent

def test_the_schema_has_no_place_to_store_a_name_phone_number_email_or_address():
    forbidden = ("phone", "email", "whatsapp", "mobile", "address", "contact", "aadhaar", "passport", "name")
    columns = [f"{t.name}.{c.name}" for t in Base.metadata.tables.values() for c in t.columns]
    offenders = [c for c in columns if any(word in c.split(".")[1].lower() for word in forbidden)]
    assert offenders == [], offenders


def test_the_service_never_sends_anything_or_calls_out():
    app_dir = Path(models.__file__).parent
    outbound = re.compile(r"^\s*(import|from)\s+(smtplib|aiosmtplib|requests|httpx|aiohttp|urllib\.request|twilio|telegram|socket)\b", re.M)
    for path in app_dir.glob("*.py"):
        assert not outbound.search(path.read_text()), f"{path.name} imports an outbound-network library"


# ------------------------------------------------------------------------ over HTTP

def test_over_http_the_no_login_response_flow_works_even_when_staff_auth_is_not_configured(client, monkeypatch):
    base = {"category": "ncii", "title": "Suspected NCII", "summary": "Flagged", "confidence": 0.9,
            "content_fingerprint": "fp-http-0001", "behaviors": ["non_consensual_imagery"],
            "scenario": "intimate_imagery_without_consent", "priority": "high",
            "evidence": [{"label": "clip", "sha256": HASH}]}
    assert client.post("/alerts", json=base, headers=headers(AI)).status_code == 201
    cid = "APN-1001"
    r = client.post(f"/cases/{cid}/parties", headers=headers(AI), json={"proposals": [
        {"ref": "acct:depicted-1", "role": "depicted_person"}, {"ref": "acct:uploader-1", "role": "uploader"}]})
    assert r.status_code == 201 and len(r.json()["created"]) == 2

    def act(who, action, **body):
        return client.post(f"/cases/{cid}/actions", headers=headers(who), json={"action": action, **body})

    assert act(REVIEWER, "assign").status_code == 200
    for key in FINDINGS:
        client.post(f"/cases/{cid}/context-findings", headers=headers(AI),
                    json={"key": key, "outcome": "supports_flag", "summary": "examined"})
    assert act(REVIEWER, "record_check", check="context").status_code == 200
    assert act(REVIEWER, "refer", note="reviewed").status_code == 200

    refused = act(OFFICER, "determine_party", note="x", party_ref="acct:depicted-1", party_role="depicted_person", determination="subject")
    assert refused.status_code == 409 and refused.json()["error"] == "not_a_subject_role"
    assert act(OFFICER, "determine_party", note="victim", party_ref="acct:depicted-1", party_role="depicted_person", determination="victim").status_code == 200
    assert act(OFFICER, "determine_party", note="posted it", party_ref="acct:uploader-1", party_role="uploader", determination="subject").status_code == 200
    assert act(OFFICER, "register_fir", note="basis").status_code == 200
    served = act(OFFICER, "serve_notice", party_ref="acct:uploader-1").json()
    token = served["issued_response_token"]
    assert token and "do not need to log in" in served["issued_notice_text"]
    # The link is shown once: reading the case again never returns it.
    again = client.get(f"/cases/{cid}", headers=headers(OFFICER)).json()
    assert "issued_response_token" not in again and "issued_notice_text" not in again
    # Citizens never see who is a victim or subject.
    assert "parties" not in client.get(f"/cases/{cid}", headers=headers(CITIZEN)).json()

    # No login: no identity headers, and staff authentication is not even configured.
    monkeypatch.setenv("APN_ENV", "production")
    assert client.get("/cases", headers=headers(REVIEWER)).status_code == 503
    ok = client.post(f"/public/responses/{token}", json={"label": "Full original video", "sha256": HASH2})
    assert ok.status_code == 201 and ok.json()["received"] is True
    assert "Nothing happens to you automatically" in ok.json()["next"]
    assert client.post("/public/responses/wrong-token", json={"label": "x"}).status_code == 404
