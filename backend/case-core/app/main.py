from collections.abc import Iterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings
from .db import init_db, make_engine, make_session_factory
from .domain import Actor, PolicyViolation, Role
from .ledger import Ledger
from .models import Case, CaseItem, LedgerEntry
from .schemas import ActionIn, AdvisoryIn, AlertIn, ComplaintIn, ContextFindingIn, ResponseIn
from .service import CaseService


def create_app(session_factory: sessionmaker[Session] | None = None) -> FastAPI:
    holder: dict = {"factory": session_factory}

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if holder["factory"] is None:
            engine = make_engine(get_settings().database_url)
            init_db(engine)
            holder["factory"] = make_session_factory(engine)
        yield

    app = FastAPI(
        title="AI Policing Net: case core (DEMO auth)",
        description=(
            "Workflow with enforced human decisions and a tamper-evident ledger. "
            "Authentication here is a demo stub: run with APN_ENV=demo. Real identity, MFA and RBAC are not wired in yet."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    def db() -> Iterator[Session]:
        session = holder["factory"]()
        try:
            yield session
        finally:
            session.close()

    def current_actor(
        x_actor_id: str | None = Header(default=None), x_actor_role: str | None = Header(default=None)
    ) -> Actor:
        if get_settings().env != "demo":
            # Fail closed: the demo header scheme must never silently run in a real deployment.
            raise HTTPException(503, "Real authentication is not configured. Set APN_ENV=demo for the demo stub only.")
        if not x_actor_id or not x_actor_role:
            raise HTTPException(401, "X-Actor-Id and X-Actor-Role headers are required (demo auth)")
        try:
            return Actor(id=x_actor_id, role=Role(x_actor_role))
        except ValueError:
            raise HTTPException(401, f"Unknown role '{x_actor_role}'") from None

    def service(session: Session = Depends(db)) -> CaseService:
        return CaseService(session)

    @app.exception_handler(PolicyViolation)
    async def policy_handler(_: Request, exc: PolicyViolation) -> JSONResponse:
        return JSONResponse(status_code=exc.status, content={"error": exc.code, "detail": exc.message})

    # ---------------------------------------------------------------- serializers

    def item_out(i: CaseItem) -> dict:
        return {
            "id": i.id, "kind": i.kind, "label": i.label, "outcome": i.outcome, "description": i.description,
            "sha256": i.sha256, "preview_withheld": i.preview_withheld, "late": i.late,
            "added_by": i.added_by, "added_at": i.added_at,
        }

    def case_out(c: Case, actor: Actor) -> dict:
        findings = [i for i in c.items if i.kind == "context_finding"]
        out = {
            "id": c.id, "kind": c.kind, "category": c.category, "title": c.title, "summary": c.summary,
            "priority": c.priority, "confidence": c.confidence, "stage": c.stage, "signals": c.signals,
            "behaviors": c.behaviors, "content_fingerprint": c.content_fingerprint,
            "checks": c.checks, "referred_to_role": c.referred_to_role, "notice_served_at": c.notice_served_at,
            "window_closes_at": c.window_closes_at, "response_received": c.response_received,
            "court_reviewed": c.court_reviewed, "appeal_open": c.appeal_open,
            "decision_due_at": c.decision_due_at, "sla_breached": c.sla_breached,
            "linked_to": c.linked_to, "dismissal_recommended": c.dismissal_recommended,
            "fresh_registration_permitted": c.fresh_registration_permitted,
            "context_missing": CaseService.missing_context(c) if c.kind == "social" else [],
            "context_findings_undermining_flag": sum(1 for f in findings if f.outcome == "undermines_flag"),
            "created_at": c.created_at, "updated_at": c.updated_at,
            "items": [item_out(i) for i in c.items],
            # AI output is advisory and says so on every case.
            "ai_notice": "AI output is advisory. Registration, referral and closure are human decisions.",
        }
        if not actor.is_staff:
            out.pop("signals", None)  # internal model signals are for reviewers
        return out

    def ledger_out(e: LedgerEntry) -> dict:
        return {
            "seq": e.seq, "ts": e.ts, "case_id": e.case_id, "actor_id": e.actor_id, "actor_role": e.actor_role,
            "actor_kind": e.actor_kind, "action": e.action, "payload": e.payload,
            "prev_hash": e.prev_hash, "hash": e.hash,
        }

    # ------------------------------------------------------------------ routes

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "auth": "demo-stub" if get_settings().env == "demo" else "not-configured"}

    @app.post("/alerts")
    def create_alert(
        body: AlertIn, response: Response, actor: Actor = Depends(current_actor), svc: CaseService = Depends(service)
    ) -> dict:
        result = svc.create_alert(actor, **body.model_dump())
        # 201 only when a new case is opened. A policy drop or an attach to an existing case is a 200.
        response.status_code = 201 if result.outcome == "flagged" else 200
        out = case_out(result.case, actor) if result.case is not None else {}
        return {**out, "outcome": result.outcome, "reason": result.reason}

    @app.post("/complaints", status_code=201)
    def file_complaint(body: ComplaintIn, actor: Actor = Depends(current_actor), svc: CaseService = Depends(service)) -> dict:
        return case_out(svc.file_complaint(actor, **body.model_dump()), actor)

    @app.get("/cases")
    def list_cases(
        stage: str | None = None, kind: str | None = None,
        actor: Actor = Depends(current_actor), svc: CaseService = Depends(service),
    ) -> list[dict]:
        return [case_out(c, actor) for c in svc.list_cases(actor, stage, kind)]

    @app.get("/cases/{case_id}")
    def get_case(case_id: str, actor: Actor = Depends(current_actor), svc: CaseService = Depends(service)) -> dict:
        return case_out(svc.get_case(actor, case_id), actor)

    @app.post("/cases/{case_id}/actions")
    def act(case_id: str, body: ActionIn, actor: Actor = Depends(current_actor), svc: CaseService = Depends(service)) -> dict:
        return case_out(svc.act(actor, case_id, body.action, body.note, body.check, body.link_to), actor)

    @app.post("/cases/{case_id}/context-findings", status_code=201)
    def context_finding(
        case_id: str, body: ContextFindingIn, actor: Actor = Depends(current_actor), svc: CaseService = Depends(service)
    ) -> dict:
        return item_out(svc.add_context_finding(actor, case_id, **body.model_dump()))

    @app.post("/cases/{case_id}/advisory", status_code=201)
    def advisory(case_id: str, body: AdvisoryIn, actor: Actor = Depends(current_actor), svc: CaseService = Depends(service)) -> dict:
        return item_out(svc.add_advisory(actor, case_id, **body.model_dump()))

    @app.post("/cases/{case_id}/responses", status_code=201)
    def respond(case_id: str, body: ResponseIn, actor: Actor = Depends(current_actor), svc: CaseService = Depends(service)) -> dict:
        return item_out(svc.submit_response(actor, case_id, **body.model_dump()))

    @app.get("/attention/window-elapsed")
    def window_elapsed(actor: Actor = Depends(current_actor), svc: CaseService = Depends(service)) -> dict:
        if not actor.is_staff:
            raise PolicyViolation("forbidden", "Staff only", 403)
        return {
            "note": "A passed window never changes a case. These need a human to confirm notice was served and follow up.",
            "cases": [case_out(c, actor) for c in svc.window_elapsed_cases()],
        }

    @app.get("/attention/overdue-decisions")
    def overdue(actor: Actor = Depends(current_actor), svc: CaseService = Depends(service)) -> dict:
        if not actor.is_staff:
            raise PolicyViolation("forbidden", "Staff only", 403)
        return {
            "note": "These missed the human-decision deadline and go to a supervisory authority. Nothing is filed automatically.",
            "cases": [case_out(c, actor) for c in svc.overdue_decisions()],
        }

    @app.post("/attention/sweep")
    def sweep(actor: Actor = Depends(current_actor), svc: CaseService = Depends(service)) -> dict:
        breached = svc.sweep_deadlines(actor)
        return {"newly_breached": [c.id for c in breached]}

    @app.get("/attention/dismissal-recommendations")
    def dismissal_recommendations(actor: Actor = Depends(current_actor), svc: CaseService = Depends(service)) -> dict:
        if actor.role not in (Role.JUDICIAL_AUTHORITY, Role.AUDITOR):
            raise PolicyViolation("forbidden", "For judicial authorities and auditors", 403)
        return {
            "note": "The AI's continuing research recommends dismissal on these FIRs. Only a judicial authority can act.",
            "cases": [case_out(c, actor) for c in svc.dismissal_recommendations()],
        }

    def require_oversight(actor: Actor) -> None:
        if actor.role not in (Role.AUDITOR, Role.JUDICIAL_AUTHORITY):
            raise PolicyViolation("forbidden", "Ledger access is for auditors and judicial authorities", 403)

    @app.get("/ledger")
    def ledger(
        after_seq: int = 0, limit: int = 100, case_id: str | None = None,
        actor: Actor = Depends(current_actor), session: Session = Depends(db),
    ) -> list[dict]:
        require_oversight(actor)
        return [ledger_out(e) for e in Ledger(session).entries(after_seq, min(limit, 500), case_id)]

    @app.get("/ledger/verify")
    def verify(actor: Actor = Depends(current_actor), session: Session = Depends(db)) -> dict:
        require_oversight(actor)
        result = Ledger(session).verify()
        problems = CaseService(session).verify_projection()
        return {
            "chain_valid": result.ok, "entries_checked": result.checked, "head_hash": result.head_hash,
            "first_bad_seq": result.first_bad_seq, "reason": result.reason,
            "projection_consistent": not problems, "projection_problems": problems,
        }

    @app.get("/ledger/checkpoint")
    def checkpoint(actor: Actor = Depends(current_actor), session: Session = Depends(db)) -> dict:
        require_oversight(actor)
        try:
            return Ledger(session).checkpoint(get_settings().checkpoint_key)
        except ValueError as exc:
            raise HTTPException(503, str(exc)) from exc

    return app


app = create_app()
