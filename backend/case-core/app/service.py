import re
from collections.abc import Callable, Sequence
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import Settings, get_settings
from .domain import (
    ACTIONS,
    CONFESSION_GATED_ACTIONS,
    CONFESSION_REQUIRED_CHECKS,
    KNOWN_CHECKS,
    REFERRAL_TARGET,
    SENSITIVE_CATEGORIES,
    Actor,
    Category,
    CaseKind,
    PolicyViolation,
    Role,
    Stage,
)
from .ledger import Ledger, iso, utcnow
from .models import Case, CaseItem

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
CLOSED_STAGES = {Stage.CLOSED_NO_ACTION.value, Stage.CLOSED_BY_COURT.value}
PRIORITIES = {"urgent", "high", "routine"}


class CaseService:
    """Owns the transaction: every public method validates first, then writes the case and its ledger entries together."""

    def __init__(self, session: Session, clock: Callable[[], datetime] = utcnow, settings: Settings | None = None):
        self.session = session
        self.clock = clock
        self.settings = settings or get_settings()
        self.ledger = Ledger(session, clock)

    # ------------------------------------------------------------------ intake

    def create_alert(
        self,
        actor: Actor,
        *,
        category: Category,
        title: str,
        summary: str,
        confidence: float,
        priority: str = "routine",
        signals: Sequence[str] = (),
        evidence: Sequence[dict] = (),
        affected_party_id: str | None = None,
    ) -> Case:
        if actor.role is not Role.AI_SERVICE:
            raise PolicyViolation("alert_source", "Only the AI detection service can raise alerts", 403)
        if category is Category.CONDUCT:
            raise PolicyViolation("bad_category", "Conduct complaints come from citizens, not AI alerts", 422)
        if priority not in PRIORITIES:
            raise PolicyViolation("bad_priority", f"priority must be one of {sorted(PRIORITIES)}", 422)
        if not 0.0 <= confidence <= 1.0:
            raise PolicyViolation("bad_confidence", "confidence must be between 0 and 1", 422)
        return self._new_case(
            actor, CaseKind.SOCIAL, category, title, summary, confidence, priority, signals, evidence,
            subject_ids=[], complainant_id=None, affected_party_id=affected_party_id,
        )

    def file_complaint(
        self,
        actor: Actor,
        *,
        title: str,
        summary: str,
        subject_ids: Sequence[str],
        evidence: Sequence[dict] = (),
    ) -> Case:
        if actor.role is not Role.CITIZEN:
            raise PolicyViolation("complaint_source", "Complaints are filed by citizens", 403)
        if not subject_ids:
            raise PolicyViolation("subject_required", "Name at least one official or office the complaint is about", 422)
        return self._new_case(
            actor, CaseKind.CONDUCT, Category.CONDUCT, title, summary, 0.0, "routine", (), evidence,
            subject_ids=list(subject_ids), complainant_id=actor.id, affected_party_id=actor.id,
        )

    def _new_case(
        self, actor: Actor, kind: CaseKind, category: Category, title: str, summary: str, confidence: float,
        priority: str, signals: Sequence[str], evidence: Sequence[dict], *, subject_ids: list[str],
        complainant_id: str | None, affected_party_id: str | None,
    ) -> Case:
        if not title.strip() or not summary.strip():
            raise PolicyViolation("empty_text", "title and summary are required", 422)
        for item in evidence:
            self._check_hash(item.get("sha256"))
        now = iso(self.clock())
        count = self.session.execute(select(func.count()).select_from(Case)).scalar_one()
        case = Case(
            id=f"APN-{1001 + count}", kind=kind.value, category=category.value, title=title.strip(),
            summary=summary.strip(), priority=priority, confidence=confidence, stage=Stage.RECEIVED.value,
            signals=list(signals), subject_ids=subject_ids, complainant_id=complainant_id,
            affected_party_id=affected_party_id, checks=[], created_at=now, updated_at=now,
        )
        self.session.add(case)
        self.session.flush()
        withheld = category in SENSITIVE_CATEGORIES
        for item in evidence:
            self.session.add(
                CaseItem(
                    case_id=case.id, kind="evidence", label=item.get("label", "Evidence"), sha256=item.get("sha256"),
                    description=item.get("description", ""), preview_withheld=withheld,
                    added_by=actor.id, added_at=now,
                )
            )
        self.ledger.append(
            case_id=case.id, actor=actor, action="case.created",
            payload={"to": Stage.RECEIVED.value, "kind": kind.value, "category": category.value,
                     "priority": priority, "confidence": confidence, "evidence_hashes": [e.get("sha256") for e in evidence]},
        )
        self.session.commit()
        return case

    # ---------------------------------------------------------------- decisions

    def act(self, actor: Actor, case_id: str, action: str, note: str | None = None, check: str | None = None) -> Case:
        case = self.get_case_unchecked(case_id)
        spec = ACTIONS.get(action)
        if spec is None:
            raise PolicyViolation("unknown_action", f"Unknown action '{action}'", 400)
        note = (note or "").strip()
        self._authorize(actor, case, action, note, check)

        payload: dict = {"note": note} if note else {}
        now = iso(self.clock())
        if action == "record_check":
            if check not in case.checks:
                case.checks = [*case.checks, check]
            payload["check"] = check
        elif action == "refer":
            case.referred_to_role = REFERRAL_TARGET[CaseKind(case.kind)].value
            payload["referred_to_role"] = case.referred_to_role
        elif action == "serve_notice":
            closes = self.clock() + timedelta(days=self.settings.response_window_days)
            case.notice_served_at = now
            case.window_closes_at = iso(closes)
            payload["window_closes_at"] = case.window_closes_at
        elif action == "court_proceed":
            case.court_reviewed = True
        elif action == "appeal":
            case.appeal_open = True
        elif action == "resolve_appeal":
            case.appeal_open = False

        if spec.to_stage is not None:
            payload["from"] = case.stage
            payload["to"] = spec.to_stage.value
            case.stage = spec.to_stage.value
        case.updated_at = now
        self.ledger.append(case_id=case.id, actor=actor, action=f"case.{action}", payload=payload)
        self.session.commit()
        return case

    def _authorize(self, actor: Actor, case: Case, action: str, note: str, check: str | None) -> None:
        spec = ACTIONS[action]
        if actor.kind.value == "ai":
            raise PolicyViolation(
                "ai_cannot_decide",
                "AI services can raise alerts and attach advisory notes only. Every decision is made by a human.",
                403,
            )
        if actor.role not in spec.roles:
            raise PolicyViolation("role_not_permitted", f"Role '{actor.role.value}' cannot perform '{action}'", 403)
        if actor.id in case.subject_ids:
            raise PolicyViolation("conflict_of_interest", "You are named in this case and cannot act on it", 403)
        if action == "resolve_appeal":
            if not case.appeal_open:
                raise PolicyViolation("no_open_appeal", "There is no open appeal on this case", 409)
            if actor.role is Role.SUPERVISORY_AUTHORITY and case.kind != CaseKind.CONDUCT.value:
                raise PolicyViolation("role_not_permitted", "Supervisory authorities resolve conduct cases only", 403)
        elif case.stage not in {s.value for s in spec.from_stages}:
            raise PolicyViolation("invalid_transition", f"Cannot '{action}' while the case is '{case.stage}'", 409)
        if action == "appeal" and actor.id not in (case.affected_party_id, case.complainant_id):
            raise PolicyViolation("not_a_party", "Only a party to the case can appeal", 403)
        if spec.note_required and not note:
            raise PolicyViolation("note_required", f"'{action}' needs a written reason, recorded in the audit trail", 422)

        # Handlers: the referred-to authority acts on a referred case, never a different arm of the system.
        if action in ("open_inquiry", "decline") and actor.role.value != case.referred_to_role:
            raise PolicyViolation(
                "wrong_handler", f"This case was referred to '{case.referred_to_role}'", 403
            )
        if action == "register_fir" and case.kind == CaseKind.CONDUCT.value and case.stage != Stage.INQUIRY.value:
            raise PolicyViolation(
                "inquiry_first", "Conduct complaints need a supervisory inquiry before an FIR decision", 409
            )
        if action == "record_check" and check not in KNOWN_CHECKS:
            raise PolicyViolation("unknown_check", f"check must be one of {sorted(KNOWN_CHECKS)}", 422)
        if action == "serve_notice" and case.notice_served_at:
            raise PolicyViolation("already_served", "Notice has already been recorded as served", 409)
        if case.category == Category.SELF_CONFESSION_VIDEO.value and action in CONFESSION_GATED_ACTIONS:
            missing = CONFESSION_REQUIRED_CHECKS - set(case.checks)
            if missing:
                raise PolicyViolation(
                    "checks_incomplete",
                    f"Self-uploaded confession videos need these human checks first: {sorted(missing)}",
                    409,
                )

    # ------------------------------------------------- AI advice and the right to respond

    def add_advisory(self, actor: Actor, case_id: str, *, recommendation: str, rationale: str = "") -> CaseItem:
        """AI recommendations are recorded for humans to weigh. They are never binding and never move a case."""
        if actor.role is not Role.AI_SERVICE:
            raise PolicyViolation("advisory_source", "Only the AI service attaches advisory notes", 403)
        case = self.get_case_unchecked(case_id)
        now = iso(self.clock())
        item = CaseItem(
            case_id=case.id, kind="advisory", label=recommendation.strip(), description=rationale,
            added_by=actor.id, added_at=now,
        )
        self.session.add(item)
        self.session.flush()
        self.ledger.append(
            case_id=case.id, actor=actor, action="advisory.added",
            payload={"item_id": item.id, "recommendation": recommendation.strip(), "binding": False},
        )
        self.session.commit()
        return item

    def submit_response(
        self, actor: Actor, case_id: str, *, label: str, description: str = "", sha256: str | None = None
    ) -> CaseItem:
        """A party's material is always accepted while the matter is open. A late response is marked late, never refused."""
        case = self.get_case_unchecked(case_id)
        if actor.role is not Role.CITIZEN or actor.id not in (case.affected_party_id, case.complainant_id):
            raise PolicyViolation("not_a_party", "Only a party to the case can submit a response", 403)
        if case.stage in CLOSED_STAGES:
            raise PolicyViolation("case_closed", "This case is closed. You can still appeal.", 409)
        if not label.strip():
            raise PolicyViolation("empty_text", "label is required", 422)
        if sha256 is not None:
            self._check_hash(sha256)
        now = self.clock()
        late = bool(case.window_closes_at and iso(now) > case.window_closes_at)
        item = CaseItem(
            case_id=case.id, kind="response", label=label.strip(), description=description, sha256=sha256,
            late=late, added_by=actor.id, added_at=iso(now),
        )
        self.session.add(item)
        case.response_received = True
        case.updated_at = iso(now)
        self.session.flush()
        self.ledger.append(
            case_id=case.id, actor=actor, action="response.submitted",
            payload={"item_id": item.id, "sha256": sha256, "late": late},
        )
        self.session.commit()
        return item

    # --------------------------------------------------------------------- reads

    def get_case_unchecked(self, case_id: str) -> Case:
        case = self.session.get(Case, case_id)
        if case is None:
            raise PolicyViolation("not_found", f"No case {case_id}", 404)
        return case

    def get_case(self, actor: Actor, case_id: str) -> Case:
        case = self.get_case_unchecked(case_id)
        if actor.is_staff or (actor.role is Role.CITIZEN and actor.id in (case.affected_party_id, case.complainant_id)):
            return case
        raise PolicyViolation("forbidden", "You cannot view this case", 403)

    def list_cases(self, actor: Actor, stage: str | None = None, kind: str | None = None) -> list[Case]:
        if not actor.is_staff:
            raise PolicyViolation("forbidden", "Case queues are for staff roles", 403)
        query = select(Case).order_by(Case.id)
        if stage:
            query = query.where(Case.stage == stage)
        if kind:
            query = query.where(Case.kind == kind)
        return list(self.session.execute(query).scalars())

    def window_elapsed_cases(self) -> list[Case]:
        """Cases whose response window has passed without a response. This only asks a human to follow up;
        it never changes anyone's legal position."""
        now = iso(self.clock())
        query = select(Case).where(
            Case.stage == Stage.FIR_REGISTERED.value,
            Case.window_closes_at.is_not(None),
            Case.window_closes_at < now,
            Case.response_received.is_(False),
        )
        return list(self.session.execute(query.order_by(Case.window_closes_at)).scalars())

    def verify_projection(self) -> list[str]:
        """Replay the ledger and compare with the cases table. Returns a list of mismatches (empty means consistent)."""
        replayed: dict[str, str] = {}
        for entry in self.ledger.all_entries():
            if entry.case_id and "to" in entry.payload:
                replayed[entry.case_id] = entry.payload["to"]
        problems = []
        # Read columns, not ORM objects: an integrity check must see the database, not the session's cached copy.
        table = dict(self.session.execute(select(Case.id, Case.stage)).all())
        for case_id, stage in table.items():
            if replayed.get(case_id) != stage:
                problems.append(f"{case_id}: table says '{stage}', ledger replay says '{replayed.get(case_id)}'")
        for case_id in replayed.keys() - table.keys():
            problems.append(f"{case_id}: in ledger but missing from cases table")
        return problems

    @staticmethod
    def _check_hash(value: str | None) -> None:
        if value is None or not SHA256_RE.match(value):
            raise PolicyViolation("bad_hash", "sha256 must be 64 lowercase hex characters", 422)
