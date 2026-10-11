"""Sample cases for the demo console. Demo only: refuses to run unless APN_ENV=demo.

    APN_ENV=demo python -m app.demo_seed

Everything here is invented. Evidence hashes are digests of placeholder strings, not real media.
"""

import hashlib
import sys
from collections.abc import Callable
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import get_settings
from .db import init_db, make_engine, make_session_factory
from .domain import Actor, Category, Role
from .ledger import utcnow
from .models import Case
from .service import CaseService

AI = Actor("model-v1", Role.AI_SERVICE)
REVIEWER = Actor("rev-demo", Role.REVIEWER)
OFFICER = Actor("off-demo", Role.AUTHORIZED_OFFICER)
CITIZEN = Actor("cit-demo", Role.CITIZEN)


def digest(label: str) -> str:
    return hashlib.sha256(f"demo-placeholder:{label}".encode()).hexdigest()


def seed(session: Session, clock: Callable[[], datetime] = utcnow) -> list[str]:
    """Create sample cases covering each stage and each guardrail. Returns the new case ids."""
    svc = CaseService(session, clock)
    ids: list[str] = []

    def alert(**kw) -> Case:
        base = dict(priority="routine", signals=[], evidence=[], affected_party_id="cit-demo", situation=[])
        base.update(kw)
        result = svc.create_alert(AI, **base)
        assert result.case is not None
        ids.append(result.case.id)
        return result.case

    def finding(case: Case, key: str, outcome: str, summary: str) -> None:
        svc.add_context_finding(AI, case.id, key=key, outcome=outcome, summary=summary)

    # 1. Urgent threat, context research still running.
    threat = alert(
        category=Category.THREAT, title="Reported threat of violence in a public video", confidence=0.87,
        summary="Spoken statements in a public video appear to threaten violence against an identifiable person.",
        content_fingerprint="fp-demo-0001", behaviors=["threat"], priority="urgent",
        signals=["Speech-to-text flagged an explicit reference to physical harm", "Target identifiable from the caption"],
        evidence=[{"label": "video (sample)", "sha256": digest("threat-video")}],
    )
    finding(threat, "media_source", "supports_flag", "No match to a known film, show or skit")
    finding(threat, "edit_detection", "inconclusive", "Container metadata stripped; cut points unclear")

    # 2. Suspected non-consensual imagery: hash only, preview withheld.
    ncii = alert(
        category=Category.NCII, title="Suspected non-consensual intimate content", confidence=0.91,
        summary="Classifier flagged a public post as possibly sharing intimate imagery without consent.",
        content_fingerprint="fp-demo-0002", behaviors=["non_consensual_imagery"], priority="high",
        signals=["Visual classifier: possible intimate content (flag only)", "Caption suggests no consent"],
        evidence=[{"label": "clip (sample)", "sha256": digest("ncii-clip")}],
    )
    finding(ncii, "media_source", "supports_flag", "No match to a known film or show")

    # 3. Miracle-cure donation appeal: all four findings in, awaiting human acknowledgement.
    scam = alert(
        category=Category.SCAM, title="Donation appeal built on a miracle-cure claim", confidence=0.74,
        summary="A promotional video claims to cure a serious illness through a ritual and asks viewers to donate.",
        content_fingerprint="fp-demo-0003", behaviors=["fraud"],
        signals=["Claim of curing a serious illness with no evidence", "Donation link in the description"],
        evidence=[{"label": "video (sample)", "sha256": digest("scam-video")}],
    )
    for key, outcome, text in [
        ("media_source", "supports_flag", "Original upload, not from a film or show"),
        ("edit_detection", "supports_flag", "No edits detected"),
        ("full_context", "supports_flag", "Full 12-minute video reviewed; claim repeated twice"),
        ("cross_platform_copies", "supports_flag", "3 public copies found; same uploader"),
    ]:
        finding(scam, key, outcome, text)

    # 4. A clip from a TV drama: the AI's own research undermines the flag and recommends no action.
    film = alert(
        category=Category.THREAT, title="Threatening line in a viral clip", confidence=0.66,
        summary="A clip contains a spoken threat. Context research suggests it is dialogue from a drama.",
        content_fingerprint="fp-demo-0004", behaviors=["threat"],
        evidence=[{"label": "clip (sample)", "sha256": digest("film-clip")}],
    )
    finding(film, "media_source", "undermines_flag", "Matches a scene from a streaming drama (confidence 0.96)")
    svc.add_advisory(AI, film.id, recommendation="Likely fiction clip; recommend no action", kind="info")

    # 5. Self-uploaded confession video: needs human wellbeing and authenticity checks before it can go further.
    alert(
        category=Category.SELF_CONFESSION_VIDEO, title="Self-uploaded confession video", confidence=0.7,
        summary="A public video in which the poster says they committed an offence. Skit, clout or crisis possible.",
        content_fingerprint="fp-demo-0005", behaviors=["self_admission"],
        evidence=[{"label": "video (sample)", "sha256": digest("confession")}],
    )

    # 6. A conduct complaint against an official, routed to a supervisory authority.
    complaint = svc.file_complaint(
        CITIZEN, title="Abusive language at a service counter",
        summary="Complainant submitted a recording alleging abusive language during document verification.",
        subject_ids=["emp-77"], evidence=[{"label": "recording (sample)", "sha256": digest("recording")}],
    )
    ids.append(complaint.id)

    # 7. An FIR registered by a human officer, with notice served and the AI's research recommending dismissal.
    fir = alert(
        category=Category.HATE, title="Quoted line mistaken for a call to violence", confidence=0.61,
        summary="A post repeats a slogan that the classifier read as incitement. Later research found the source.",
        content_fingerprint="fp-demo-0007", behaviors=["incitement_to_violence"], priority="high",
        evidence=[{"label": "post (sample)", "sha256": digest("slogan-post")}],
    )
    for key in ("media_source", "edit_detection", "full_context", "cross_platform_copies"):
        finding(fir, key, "supports_flag", f"{key} examined")
    svc.act(REVIEWER, fir.id, "assign")
    svc.act(REVIEWER, fir.id, "record_check", check="context")
    svc.act(REVIEWER, fir.id, "refer", note="Context reviewed; referring for an authorized decision")
    svc.act(OFFICER, fir.id, "register_fir", note="Provisions assessed by the authorized officer (sample)")
    svc.act(OFFICER, fir.id, "serve_notice")
    finding(fir, "full_context", "undermines_flag", "Original source shows the line is a quotation in a news report")
    svc.add_advisory(
        AI, fir.id, recommendation="Recommend dismissal", kind="dismissal",
        rationale="Continuing research found the original context; the court should review.",
    )

    def refer(case: Case) -> None:
        for key in ("media_source", "edit_detection", "full_context", "cross_platform_copies"):
            finding(case, key, "supports_flag", f"{key} examined")
        svc.act(REVIEWER, case.id, "assign")
        svc.act(REVIEWER, case.id, "record_check", check="context")
        svc.act(REVIEWER, case.id, "refer", note="Context reviewed; referring for an authorized decision")

    # 8. Intimate imagery shared without consent. The people in the video are victims; the uploader is the candidate
    #    subject. Parties are pseudonymous references. An officer decides; the rules refuse naming a victim a subject.
    intimate = alert(
        category=Category.NCII, title="Private video shared without consent", confidence=0.93, priority="high",
        summary="A private video of two adults was posted publicly by an account that is not either of them.",
        content_fingerprint="fp-demo-0009", behaviors=["non_consensual_imagery"],
        scenario="intimate_imagery_without_consent",
        evidence=[{"label": "clip (sample)", "sha256": digest("private-video")}],
    )
    svc.propose_parties(AI, intimate.id, [
        {"ref": "acct:person-a", "role": "depicted_person", "rationale": "appears in the video"},
        {"ref": "acct:person-b", "role": "depicted_person", "rationale": "appears in the video"},
        {"ref": "acct:poster-7", "role": "uploader", "rationale": "first account to post it; not in the video"},
    ])
    refer(intimate)

    # 9. A public indecent act at a live event. The person performing it is the candidate subject; the person who
    #    filmed and the account that posted it are not, unless they did something else wrong.
    public_act = alert(
        category=Category.NCII, title="Nudity during a live public event", confidence=0.88,
        summary="A bystander's recording shows a person performing a nude act in a public place during a live show.",
        content_fingerprint="fp-demo-0010", behaviors=["sexual_content"], scenario="public_indecent_act",
        evidence=[{"label": "clip (sample)", "sha256": digest("public-act")}],
    )
    svc.propose_parties(AI, public_act.id, [
        {"ref": "acct:performer-3", "role": "performer_in_public_act", "rationale": "performs the act in the clip"},
        {"ref": "acct:bystander-5", "role": "recorder", "rationale": "filmed it from the audience"},
        {"ref": "acct:poster-8", "role": "uploader", "rationale": "reposted the clip"},
    ])
    refer(public_act)

    # 10. An alert dropped by policy: casual profanity between friends. Recorded without any person.
    svc.create_alert(
        AI, category=Category.HATE, title="Friends joking", summary="Banter", confidence=0.5,
        content_fingerprint="fp-demo-0008", behaviors=["casual_profanity"], situation=["friendly_banter"],
    )
    return ids


def main() -> int:
    settings = get_settings()
    if settings.env != "demo":
        print("Refusing to seed: set APN_ENV=demo. This command creates invented sample data.", file=sys.stderr)
        return 2
    engine = make_engine(settings.database_url)
    init_db(engine)
    with make_session_factory(engine)() as session:
        if session.execute(select(func.count()).select_from(Case)).scalar_one():
            print("Database already has cases; not seeding.", file=sys.stderr)
            return 1
        ids = seed(session)
    print(f"Seeded {len(ids)} sample cases: {', '.join(ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
