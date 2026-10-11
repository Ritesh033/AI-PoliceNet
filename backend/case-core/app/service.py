import hashlib
import re
import secrets
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import Settings, get_settings
from .domain import (
    ACTIONS,
    CONFESSION_GATED_ACTIONS,
    CONFESSION_REQUIRED_CHECKS,
    CONTEXT_GATED_ACTIONS,
    DETERMINATIONS,
    FINDING_OUTCOMES,
    KNOWN_BEHAVIORS,
    KNOWN_SITUATIONS,
    OPTIONAL_FINDINGS,
    PARTY_ROLES,
    SCENARIOS,
    explain_subject_rule,
    KNOWN_CHECKS,
    REFERRAL_TARGET,
    REQUIRED_CONTEXT_FINDINGS,
    SENSITIVE_CATEGORIES,
    UNDECIDED_STAGES,
    Actor,
    Category,
    CaseKind,
    Kind,
    PolicyViolation,
    PUBLIC_OFFICIAL_TARGET,
    Role,
    Stage,
    decide_flag,
)
from .ledger import Ledger, iso, utcnow
from .models import Case, CaseItem, CaseParty
from .notice import build_notice

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
TOKEN_RESPONSE_LIMIT = 50
CLOSED_STAGES = {Stage.CLOSED_NO_ACTION.value, Stage.CLOSED_BY_COURT.value}
FROZEN_STAGES = CLOSED_STAGES | {Stage.LINKED.value}
UNDECIDED = {s.value for s in UNDECIDED_STAGES}
PRIORITIES = {"urgent", "high", "routine"}


@dataclass(frozen=True)
class TriageResult:
    """What happened to an AI alert: flagged as a new case, dropped by policy, or attached to an existing case."""

    outcome: str  # flagged | no_flag | duplicate
    case: Case | None
    reason: str


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
        content_fingerprint: str,
        behaviors: Sequence[str],
        situation: Sequence[str] = (),
        scenario: str = "other",
        priority: str = "routine",
        signals: Sequence[str] = (),
        evidence: Sequence[dict] = (),
        affected_party_id: str | None = None,
    ) -> TriageResult:
        if actor.role is not Role.AI_SERVICE:
            raise PolicyViolation("alert_source", "Only the AI detection service can raise alerts", 403)
        if category is Category.CONDUCT:
            raise PolicyViolation("bad_category", "Conduct complaints come from citizens, not AI alerts", 422)
        if priority not in PRIORITIES:
            raise PolicyViolation("bad_priority", f"priority must be one of {sorted(PRIORITIES)}", 422)
        if not 0.0 <= confidence <= 1.0:
            raise PolicyViolation("bad_confidence", "confidence must be between 0 and 1", 422)
        if len(content_fingerprint.strip()) < 8:
            raise PolicyViolation("bad_fingerprint", "content_fingerprint identifies the specific clip", 422)
        if not behaviors:
            raise PolicyViolation("behaviors_required", "List the behaviours the model detected", 422)
        unknown = set(behaviors) - KNOWN_BEHAVIORS
        if unknown:
            raise PolicyViolation("unknown_behavior", f"Unknown behaviours {sorted(unknown)}; allowed: {sorted(KNOWN_BEHAVIORS)}", 422)
        if scenario not in SCENARIOS:
            raise PolicyViolation("unknown_scenario", f"scenario must be one of {sorted(SCENARIOS)}", 422)
        unknown_situation = set(situation) - KNOWN_SITUATIONS
        if unknown_situation:
            raise PolicyViolation(
                "unknown_situation", f"Unknown situation tags {sorted(unknown_situation)}; allowed: {sorted(KNOWN_SITUATIONS)}", 422
            )
        if PUBLIC_OFFICIAL_TARGET in situation and "private_individual_target" in situation:
            raise PolicyViolation("conflicting_situation", "A target cannot be both a public official and a private individual", 422)
        for item in evidence:
            self._check_hash(item.get("sha256"))

        # Policy gate (see domain.decide_flag): casual abuse and criticism, including crude abuse aimed at public
        # officials, are not flagged. The decision is still recorded (content fingerprint, behaviours and situation
        # only, no person) so auditors can see what the AI saw and dropped.
        decision = decide_flag(behaviors, situation)
        if not decision.flag:
            self.ledger.append(
                case_id=None, actor=actor, action="triage.no_flag",
                payload={"content_fingerprint": content_fingerprint, "behaviors": sorted(behaviors),
                         "situation": sorted(situation), "reason": decision.reason},
            )
            self.session.commit()
            return TriageResult("no_flag", None, decision.reason)

        # Same clip, same issue: add the information to the existing case. A second FIR is never opened.
        existing = self._existing_for_fingerprint(content_fingerprint)
        if existing is not None:
            self.ledger.append(
                case_id=existing.id, actor=actor, action="alert.duplicate",
                payload={"behaviors": sorted(behaviors), "confidence": confidence,
                         "evidence_hashes": [e.get("sha256") for e in evidence]},
            )
            self.session.commit()
            return TriageResult("duplicate", existing, f"This clip is already tracked as {existing.id}; information added there.")

        case = self._new_case(
            actor, CaseKind.SOCIAL, category, title, summary, confidence, priority, signals, evidence,
            subject_ids=[], complainant_id=None, affected_party_id=affected_party_id,
            behaviors=sorted(behaviors), situation=sorted(situation), scenario=scenario,
            content_fingerprint=content_fingerprint,
        )
        return TriageResult("flagged", case, decision.reason)

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

    def _existing_for_fingerprint(self, fingerprint: str) -> Case | None:
        """An open case or an FIR already tracks this clip. A case closed with no action does not block fresh review,
        and a court can lift the block for a clip with `permit_fresh_registration`."""
        query = (
            select(Case)
            .where(
                Case.content_fingerprint == fingerprint,
                Case.fresh_registration_permitted.is_(False),
                Case.stage != Stage.CLOSED_NO_ACTION.value,
            )
            .order_by(Case.id)
        )
        case = self.session.execute(query).scalars().first()
        seen: set[str] = set()
        while case is not None and case.linked_to and case.id not in seen:
            seen.add(case.id)
            case = self.session.get(Case, case.linked_to)
        return case

    def _new_case(
        self, actor: Actor, kind: CaseKind, category: Category, title: str, summary: str, confidence: float,
        priority: str, signals: Sequence[str], evidence: Sequence[dict], *, subject_ids: list[str],
        complainant_id: str | None, affected_party_id: str | None, behaviors: Sequence[str] = (),
        situation: Sequence[str] = (), scenario: str = "other", content_fingerprint: str | None = None,
    ) -> Case:
        if not title.strip() or not summary.strip():
            raise PolicyViolation("empty_text", "title and summary are required", 422)
        for item in evidence:
            self._check_hash(item.get("sha256"))
        now_dt = self.clock()
        now = iso(now_dt)
        count = self.session.execute(select(func.count()).select_from(Case)).scalar_one()
        due = iso(now_dt + timedelta(hours=self.settings.decision_sla_hours)) if kind is CaseKind.SOCIAL else None
        case = Case(
            id=f"APN-{1001 + count}", kind=kind.value, category=category.value, title=title.strip(),
            summary=summary.strip(), priority=priority, confidence=confidence, stage=Stage.RECEIVED.value,
            signals=list(signals), behaviors=list(behaviors), situation=list(situation), scenario=scenario,
            content_fingerprint=content_fingerprint,
            subject_ids=subject_ids, complainant_id=complainant_id, affected_party_id=affected_party_id,
            checks=[], decision_due_at=due, created_at=now, updated_at=now,
        )
        self.session.add(case)
        self.session.flush()
        withheld = category in SENSITIVE_CATEGORIES or "non_consensual_imagery" in behaviors
        for item in evidence:
            self.session.add(
                CaseItem(
                    case=case, kind="evidence", label=item.get("label", "Evidence"), sha256=item.get("sha256"),
                    description=item.get("description", ""), preview_withheld=withheld,
                    added_by=actor.id, added_at=now,
                )
            )
        self.ledger.append(
            case_id=case.id, actor=actor, action="case.created",
            payload={"to": Stage.RECEIVED.value, "kind": kind.value, "category": category.value,
                     "behaviors": list(behaviors), "situation": list(situation), "scenario": scenario, "priority": priority, "confidence": confidence,
                     "content_fingerprint": content_fingerprint, "decision_due_at": due,
                     "evidence_hashes": [e.get("sha256") for e in evidence]},
        )
        self.session.commit()
        return case

    # ---------------------------------------------------------------- decisions

    def act(
        self, actor: Actor, case_id: str, action: str, note: str | None = None, check: str | None = None,
        link_to: str | None = None,
        **params: str | None,
    ) -> Case:
        case = self.get_case_unchecked(case_id)
        spec = ACTIONS.get(action)
        if spec is None:
            raise PolicyViolation("unknown_action", f"Unknown action '{action}'", 400)
        note = (note or "").strip()
        unknown = set(params) - {"party_ref", "party_role", "determination", "legal_basis"}
        if unknown:
            raise PolicyViolation("unknown_param", f"Unknown parameters {sorted(unknown)}", 422)
        target = self._authorize(actor, case, action, note, check, link_to, params)

        payload: dict = {"note": note} if note else {}
        now = iso(self.clock())
        if action == "record_check":
            if check not in case.checks:
                case.checks = [*case.checks, check]
            payload["check"] = check
        elif action == "refer":
            case.referred_to_role = REFERRAL_TARGET[CaseKind(case.kind)].value
            payload["referred_to_role"] = case.referred_to_role
        elif action == "register_fir":
            case.fir_registered_at = now
        elif action == "serve_notice":
            party_ref = params.get("party_ref") or "*"
            if not case.notice_served_at:
                case.notice_served_at = now
                case.window_closes_at = iso(self.clock() + timedelta(days=self.settings.response_window_days))
            # The case's response link is a capability: whoever holds it can respond, with no login. Only its hash is
            # stored. The record keeps the notice text with the link left out; the officer receives the full text once.
            token = secrets.token_urlsafe(24)
            placeholder = "<private response link>"
            recorded = build_notice(case, placeholder, self.settings.response_window_days)
            self.session.add(
                CaseItem(
                    case=case, kind="notice", label=party_ref, sha256=hashlib.sha256(token.encode()).hexdigest(),
                    description=recorded, added_by=actor.id, added_at=now,
                )
            )
            case.issued_response_token = token
            case.issued_notice_text = recorded.replace(placeholder, f"/public/responses/{token}")
            payload.update(
                party_ref=party_ref, window_closes_at=case.window_closes_at,
                notice_sha256=hashlib.sha256(recorded.encode()).hexdigest(),
            )
        elif action == "determine_party":
            party = self._find_party(case, params["party_ref"], params["party_role"])
            party.determination = params["determination"]
            party.determined_by = actor.id
            party.determined_note = note
            party.determined_at = now
            payload.update(party_ref=party.ref, party_role=party.role, determination=party.determination)
        elif action == "request_identification":
            # Recorded for accountability only. The platform never looks up, stores or messages contact details.
            payload.update(party_ref=params["party_ref"], legal_basis=(params.get("legal_basis") or "").strip())
        elif action == "court_proceed":
            case.court_reviewed = True
        elif action == "appeal":
            case.appeal_open = True
        elif action == "resolve_appeal":
            case.appeal_open = False
        elif action == "permit_fresh_registration":
            case.fresh_registration_permitted = True
        elif action == "link_supplementary" and target is not None:
            case.linked_to = target.id
            payload["linked_to"] = target.id
            self.ledger.append(
                case_id=target.id, actor=actor, action="case.supplementary_info",
                payload={"from_case": case.id, "note": note, "behaviors": list(case.behaviors),
                         "evidence_hashes": [i.sha256 for i in case.items if i.kind == "evidence"]},
            )

        if spec.to_stage is not None:
            payload["from"] = case.stage
            payload["to"] = spec.to_stage.value
            case.stage = spec.to_stage.value
        case.updated_at = now
        self.ledger.append(case_id=case.id, actor=actor, action=f"case.{action}", payload=payload)
        self.session.commit()
        return case

    def _authorize(
        self, actor: Actor, case: Case, action: str, note: str, check: str | None, link_to: str | None,
        params: dict,
    ) -> Case | None:
        spec = ACTIONS[action]
        if actor.kind is not Kind.HUMAN:
            raise PolicyViolation(
                "ai_cannot_decide",
                "Automated actors (AI services and the scheduler) can raise alerts, attach advisory notes and "
                "record deadlines only. Every decision is made by a human.",
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
            raise PolicyViolation("wrong_handler", f"This case was referred to '{case.referred_to_role}'", 403)
        if action == "register_fir" and case.kind == CaseKind.CONDUCT.value and case.stage != Stage.INQUIRY.value:
            raise PolicyViolation("inquiry_first", "Conduct complaints need a supervisory inquiry before an FIR decision", 409)
        if action == "record_check" and check not in KNOWN_CHECKS:
            raise PolicyViolation("unknown_check", f"check must be one of {sorted(KNOWN_CHECKS)}", 422)
        if action == "serve_notice":
            self._authorize_notice(case, params.get("party_ref"))
        if action == "determine_party":
            self._authorize_determination(case, params)
        if action == "request_identification":
            self._authorize_identification(case, params)
        if action == "register_fir" and case.scenario != "other" and not any(p.determination for p in case.parties):
            raise PolicyViolation(
                "parties_undetermined",
                "Decide who is a subject, a victim or a witness (determine_party) before registering an FIR in this kind of case.",
                409,
            )

        if case.kind == CaseKind.SOCIAL.value and action in CONTEXT_GATED_ACTIONS:
            missing = self.missing_context(case)
            if missing:
                raise PolicyViolation(
                    "context_incomplete",
                    f"The full-context check is not finished. Missing AI findings: {missing}. "
                    "Check whether the clip is from a film, show or skit, whether it is edited or partial, "
                    "what the full original shows, and where else it appears.",
                    409,
                )
        if case.category == Category.SELF_CONFESSION_VIDEO.value and action in CONFESSION_GATED_ACTIONS:
            missing_checks = CONFESSION_REQUIRED_CHECKS - set(case.checks)
            if missing_checks:
                raise PolicyViolation(
                    "checks_incomplete",
                    f"Self-uploaded confession videos need these human checks first: {sorted(missing_checks)}",
                    409,
                )

        # One FIR per clip. Further information goes to the existing case.
        if action == "register_fir" and case.content_fingerprint:
            other = self.session.execute(
                select(Case.id).where(
                    Case.content_fingerprint == case.content_fingerprint,
                    Case.id != case.id,
                    Case.fir_registered_at.is_not(None),
                    Case.fresh_registration_permitted.is_(False),
                )
            ).first()
            if other:
                raise PolicyViolation(
                    "duplicate_fir",
                    f"An FIR already exists on this clip ({other[0]}). Add new information to that case instead.",
                    409,
                )

        target: Case | None = None
        if action == "link_supplementary":
            if not link_to:
                raise PolicyViolation("link_target_required", "Name the existing case to add this information to", 422)
            target = self.session.get(Case, link_to)
            if target is None or target.id == case.id or target.stage == Stage.LINKED.value:
                raise PolicyViolation("bad_link_target", "link_to must be a different, existing, unlinked case", 422)
        return target

    @staticmethod
    def _find_party(case: Case, ref: str | None, role: str | None = None) -> CaseParty | None:
        for p in case.parties:
            if p.ref == ref and (role is None or p.role == role):
                return p
        return None

    def _authorize_notice(self, case: Case, party_ref: str | None) -> None:
        if case.parties:
            if not party_ref:
                raise PolicyViolation("party_ref_required", "Name which subject this notice is for (party_ref)", 422)
            determinations = {p.determination for p in case.parties if p.ref == party_ref}
            if not determinations:
                raise PolicyViolation("unknown_party", f"No party '{party_ref}' on this case", 422)
            if "subject" not in determinations:
                raise PolicyViolation(
                    "notice_only_to_subjects",
                    "A notice goes only to a party an officer has determined to be a subject. Victims, witnesses and "
                    "undetermined parties never receive one.",
                    409,
                )
        label = party_ref or "*"
        if any(i.kind == "notice" and i.label == label for i in case.items):
            raise PolicyViolation("already_served", "Notice has already been recorded as served to this party", 409)

    def _authorize_determination(self, case: Case, params: dict) -> None:
        ref, role, determination = params.get("party_ref"), params.get("party_role"), params.get("determination")
        if not (ref and role and determination):
            raise PolicyViolation("party_params_required", "party_ref, party_role and determination are required", 422)
        if determination not in DETERMINATIONS:
            raise PolicyViolation("bad_determination", f"determination must be one of {sorted(DETERMINATIONS)}", 422)
        if self._find_party(case, ref, role) is None:
            raise PolicyViolation(
                "unknown_party", f"No proposed party '{ref}' in the role '{role}'. The AI proposes parties; an officer decides.", 422
            )
        if determination == "subject":
            reason = explain_subject_rule(case.scenario, role, case.behaviors)
            if reason:
                raise PolicyViolation("not_a_subject_role", reason, 409)

    def _authorize_identification(self, case: Case, params: dict) -> None:
        ref = params.get("party_ref")
        if not (params.get("legal_basis") or "").strip():
            raise PolicyViolation(
                "legal_basis_required", "State the legal basis for this identification request (for example the notice or order reference)", 422
            )
        entries = [p for p in case.parties if p.ref == ref]
        if not entries:
            raise PolicyViolation("unknown_party", f"No party '{ref}' on this case", 422)
        if all(p.determination in ("victim", "witness", "not_involved") for p in entries):
            raise PolicyViolation(
                "identification_not_allowed",
                "A victim, witness or uninvolved person is never identified through this step.",
                409,
            )

    # ------------------------------------- AI findings, advice and the right to respond

    def add_context_finding(
        self, actor: Actor, case_id: str, *, key: str, outcome: str, summary: str, sha256: str | None = None
    ) -> CaseItem:
        """The AI's full-context research: film or show match, edits, the full original, other copies of the clip."""
        if actor.role is not Role.AI_SERVICE:
            raise PolicyViolation("finding_source", "Only the AI service records context findings", 403)
        if key not in REQUIRED_CONTEXT_FINDINGS | OPTIONAL_FINDINGS:
            raise PolicyViolation(
                "unknown_finding", f"key must be one of {sorted(REQUIRED_CONTEXT_FINDINGS | OPTIONAL_FINDINGS)}", 422
            )
        if outcome not in FINDING_OUTCOMES:
            raise PolicyViolation("bad_outcome", f"outcome must be one of {sorted(FINDING_OUTCOMES)}", 422)
        if not summary.strip():
            raise PolicyViolation("empty_text", "summary is required", 422)
        if sha256 is not None:
            self._check_hash(sha256)
        case = self.get_case_unchecked(case_id)
        if case.stage in FROZEN_STAGES:
            raise PolicyViolation("case_closed", "This case is closed or merged", 409)
        item = CaseItem(
            case=case, kind="context_finding", label=key, outcome=outcome, description=summary.strip(),
            sha256=sha256, added_by=actor.id, added_at=iso(self.clock()),
        )
        self.session.add(item)
        self.session.flush()
        self.ledger.append(
            case_id=case.id, actor=actor, action="context.finding",
            payload={"item_id": item.id, "key": key, "outcome": outcome},
        )
        self.session.commit()
        return item

    @staticmethod
    def missing_context(case: Case) -> list[str]:
        have = {i.label for i in case.items if i.kind == "context_finding"}
        missing = REQUIRED_CONTEXT_FINDINGS - have
        if not missing and "context" not in case.checks:
            return ["human acknowledgement (record_check: context)"]
        return sorted(missing)

    def add_advisory(
        self, actor: Actor, case_id: str, *, recommendation: str, rationale: str = "", kind: str = "info"
    ) -> CaseItem:
        """AI recommendations are recorded for humans to weigh. They are never binding and never move a case.
        A 'dismissal' advisory puts an FIR in front of the court's queue, where only a judicial authority can act."""
        if actor.role is not Role.AI_SERVICE:
            raise PolicyViolation("advisory_source", "Only the AI service attaches advisory notes", 403)
        if kind not in ("info", "dismissal"):
            raise PolicyViolation("bad_advisory_kind", "kind must be 'info' or 'dismissal'", 422)
        case = self.get_case_unchecked(case_id)
        now = iso(self.clock())
        item = CaseItem(
            case=case, kind="advisory", label=recommendation.strip(), description=rationale,
            added_by=actor.id, added_at=now,
        )
        self.session.add(item)
        if kind == "dismissal":
            case.dismissal_recommended = True
        self.session.flush()
        self.ledger.append(
            case_id=case.id, actor=actor, action="advisory.added",
            payload={"item_id": item.id, "recommendation": recommendation.strip(), "kind": kind, "binding": False},
        )
        self.session.commit()
        return item

    def propose_parties(self, actor: Actor, case_id: str, proposals: Sequence[dict]) -> list[CaseParty]:
        """The AI proposes who appears in a case and in what role, using pseudonymous references only.
        It cannot decide anyone's status: an officer does that with determine_party."""
        if actor.role is not Role.AI_SERVICE:
            raise PolicyViolation("party_source", "Only the AI service proposes parties", 403)
        case = self.get_case_unchecked(case_id)
        if case.stage in FROZEN_STAGES:
            raise PolicyViolation("case_closed", "This case is closed or merged", 409)
        created: list[CaseParty] = []
        for p in proposals:
            ref, role = (p.get("ref") or "").strip(), p.get("role")
            if not ref or len(ref) > 64:
                raise PolicyViolation("bad_ref", "ref is required and at most 64 characters", 422)
            if "@" in ref or sum(c.isdigit() for c in ref) >= 8:
                raise PolicyViolation(
                    "ref_must_be_pseudonymous",
                    "A party reference must be an opaque account reference, never an email address or phone number.",
                    422,
                )
            if role not in PARTY_ROLES:
                raise PolicyViolation("bad_role", f"role must be one of {sorted(PARTY_ROLES)}", 422)
            if self._find_party(case, ref, role) is not None:
                continue
            party = CaseParty(
                case=case, ref=ref, role=role, rationale=p.get("rationale", ""), proposed_by=actor.id
            )
            self.session.add(party)
            created.append(party)
            self.session.flush()
            self.ledger.append(
                case_id=case.id, actor=actor, action="party.proposed",
                payload={"party_ref": ref, "party_role": role, "rationale": p.get("rationale", "")},
            )
        self.session.commit()
        return created

    def submit_response_by_token(
        self, token: str, *, label: str, description: str = "", sha256: str | None = None
    ) -> CaseItem:
        """Respond with no login. Holding the case's private link is the only credential, and the responder never has to
        say who they are. A human reads every response. Late responses are marked late, never refused."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        notice = self.session.execute(
            select(CaseItem).where(CaseItem.kind == "notice", CaseItem.sha256 == token_hash)
        ).scalar_one_or_none()
        if notice is None:
            raise PolicyViolation("unknown_link", "This response link is not valid.", 404)
        case = notice.case
        if case.stage in FROZEN_STAGES:
            raise PolicyViolation("case_closed", "This case is closed. You can still appeal.", 409)
        if not label.strip():
            raise PolicyViolation("empty_text", "label is required", 422)
        if sha256 is not None:
            self._check_hash(sha256)
        who = f"link:{token_hash[:8]}"
        used = sum(1 for i in case.items if i.kind == "response" and i.added_by == who)
        if used >= TOKEN_RESPONSE_LIMIT:
            raise PolicyViolation("too_many_responses", "This link has reached its response limit.", 429)
        now = self.clock()
        late = bool(case.window_closes_at and iso(now) > case.window_closes_at)
        item = CaseItem(
            case=case, kind="response", label=label.strip(), description=description, sha256=sha256, late=late,
            added_by=who, added_at=iso(now),
        )
        self.session.add(item)
        case.response_received = True
        case.updated_at = iso(now)
        self.session.flush()
        self.ledger.append(
            case_id=case.id, actor=Actor(id=who, role=Role.CITIZEN), action="response.submitted",
            payload={"item_id": item.id, "sha256": sha256, "late": late, "via": "response_link"},
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
        if case.stage in FROZEN_STAGES:
            raise PolicyViolation("case_closed", "This case is closed. You can still appeal.", 409)
        if not label.strip():
            raise PolicyViolation("empty_text", "label is required", 422)
        if sha256 is not None:
            self._check_hash(sha256)
        now = self.clock()
        late = bool(case.window_closes_at and iso(now) > case.window_closes_at)
        item = CaseItem(
            case=case, kind="response", label=label.strip(), description=description, sha256=sha256,
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

    # ----------------------------------------------------------- deadlines

    def sweep_deadlines(self, actor: Actor) -> list[Case]:
        """Record, once, that a case missed its decision deadline and must go to a supervisor.
        This never registers, refers or closes anything: a missed deadline escalates to a human."""
        if actor.role is not Role.SYSTEM:
            raise PolicyViolation("system_only", "Only the scheduler runs the deadline sweep", 403)
        now = iso(self.clock())
        query = select(Case).where(
            Case.decision_due_at.is_not(None),
            Case.decision_due_at < now,
            Case.sla_breached.is_(False),
            Case.stage.in_(UNDECIDED),
        )
        breached = list(self.session.execute(query.order_by(Case.decision_due_at)).scalars())
        for case in breached:
            case.sla_breached = True
            self.ledger.append(
                case_id=case.id, actor=actor, action="sla.breached",
                payload={"due_at": case.decision_due_at, "stage": case.stage,
                         "escalate_to": Role.SUPERVISORY_AUTHORITY.value},
            )
        self.session.commit()
        return breached

    def overdue_decisions(self) -> list[Case]:
        query = select(Case).where(Case.sla_breached.is_(True), Case.stage.in_(UNDECIDED))
        return list(self.session.execute(query.order_by(Case.decision_due_at)).scalars())

    def dismissal_recommendations(self) -> list[Case]:
        """FIRs where the AI's continuing research recommends dismissal. Only a judicial authority can act on them."""
        query = select(Case).where(
            Case.stage == Stage.FIR_REGISTERED.value,
            Case.dismissal_recommended.is_(True),
            Case.court_reviewed.is_(False),
        )
        return list(self.session.execute(query.order_by(Case.id)).scalars())

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
