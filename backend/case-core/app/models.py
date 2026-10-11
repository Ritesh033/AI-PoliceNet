from typing import ClassVar

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Case(Base):
    """Current-state projection. The ledger is the record of truth; see `CaseService.verify_projection`."""

    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))
    category: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(16), default="routine")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    stage: Mapped[str] = mapped_column(String(24), default="received")
    signals: Mapped[list] = mapped_column(JSON, default=list)
    behaviors: Mapped[list] = mapped_column(JSON, default=list)
    scenario: Mapped[str] = mapped_column(String(48), default="other")
    situation: Mapped[list] = mapped_column(JSON, default=list)
    # The flag attaches to a specific piece of content (an opaque fingerprint from the AI service), never to a person.
    content_fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    # People. Subjects can never act on the case; parties can respond to it.
    subject_ids: Mapped[list] = mapped_column(JSON, default=list)
    complainant_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    affected_party_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    referred_to_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    checks: Mapped[list] = mapped_column(JSON, default=list)
    # Right to respond. The window starts only when a human records that notice was served.
    notice_served_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    window_closes_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    response_received: Mapped[bool] = mapped_column(Boolean, default=False)
    court_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    appeal_open: Mapped[bool] = mapped_column(Boolean, default=False)
    # Decision clock: a human must take the case to an authorized decision by this time, else it escalates.
    decision_due_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    sla_breached: Mapped[bool] = mapped_column(Boolean, default=False)
    fir_registered_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    linked_to: Mapped[str | None] = mapped_column(String(16), nullable=True)
    fresh_registration_permitted: Mapped[bool] = mapped_column(Boolean, default=False)
    dismissal_recommended: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[str] = mapped_column(String(40))
    updated_at: Mapped[str] = mapped_column(String(40))

    items: Mapped[list["CaseItem"]] = relationship(back_populates="case", order_by="CaseItem.id")
    parties: Mapped[list["CaseParty"]] = relationship(back_populates="case", order_by="CaseParty.id")

    # Not persisted: set only on the instance returned by the action that served notice, so the response token and
    # notice text reach the officer once and are never readable again.
    issued_response_token: ClassVar[str | None] = None
    issued_notice_text: ClassVar[str | None] = None


class CaseParty(Base):
    """A pseudonymous party in a case. No names, phone numbers, emails or addresses are ever stored here."""

    __tablename__ = "case_parties"
    __table_args__ = (UniqueConstraint("case_id", "ref", "role", name="uq_party_ref_role"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    ref: Mapped[str] = mapped_column(String(64))  # opaque reference from the platform feed, for example "acct:7f3a9c"
    role: Mapped[str] = mapped_column(String(32))
    rationale: Mapped[str] = mapped_column(Text, default="")
    proposed_by: Mapped[str] = mapped_column(String(64))
    determination: Mapped[str | None] = mapped_column(String(16), nullable=True)
    determined_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    determined_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    determined_at: Mapped[str | None] = mapped_column(String(40), nullable=True)

    case: Mapped[Case] = relationship(back_populates="parties")


class CaseItem(Base):
    """Evidence, responses and advisory notes attached to a case. Media itself is never stored here, only its hash."""

    __tablename__ = "case_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    kind: Mapped[str] = mapped_column(String(16))  # evidence | response | advisory | context_finding
    outcome: Mapped[str | None] = mapped_column(String(24), nullable=True)
    label: Mapped[str] = mapped_column(String(200))
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    preview_withheld: Mapped[bool] = mapped_column(Boolean, default=False)
    late: Mapped[bool] = mapped_column(Boolean, default=False)
    added_by: Mapped[str] = mapped_column(String(64))
    added_at: Mapped[str] = mapped_column(String(40))

    case: Mapped[Case] = relationship(back_populates="items")


class LedgerEntry(Base):
    """Append-only, hash-chained audit record. Never updated or deleted; corrections are new entries."""

    __tablename__ = "ledger"
    __table_args__ = (UniqueConstraint("seq", name="uq_ledger_seq"), UniqueConstraint("prev_hash", name="uq_ledger_prev"))

    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    ts: Mapped[str] = mapped_column(String(40))
    case_id: Mapped[str | None] = mapped_column(String(16), nullable=True)
    actor_id: Mapped[str] = mapped_column(String(64))
    actor_role: Mapped[str] = mapped_column(String(32))
    actor_kind: Mapped[str] = mapped_column(String(8))
    action: Mapped[str] = mapped_column(String(48))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64))
