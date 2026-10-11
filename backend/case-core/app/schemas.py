from pydantic import BaseModel, Field

from .domain import Category


class EvidenceIn(BaseModel):
    label: str = Field(max_length=200)
    sha256: str
    description: str = ""


class AlertIn(BaseModel):
    category: Category
    title: str = Field(max_length=200)
    summary: str
    confidence: float
    # Opaque identifier of the specific clip (for example a perceptual hash). The flag attaches to this, not to a person.
    content_fingerprint: str
    # What the model detected, from a closed vocabulary. Insults, criticism or false statements alone are not flagged.
    behaviors: list[str]
    # The situation the model judged: banter, political commentary, repeated targeting, and so on. Closed vocabulary.
    situation: list[str] = []
    priority: str = "routine"
    signals: list[str] = []
    evidence: list[EvidenceIn] = []
    affected_party_id: str | None = None


class ComplaintIn(BaseModel):
    title: str = Field(max_length=200)
    summary: str
    subject_ids: list[str]
    evidence: list[EvidenceIn] = []


class ActionIn(BaseModel):
    action: str
    note: str | None = None
    check: str | None = None
    link_to: str | None = None


class AdvisoryIn(BaseModel):
    recommendation: str = Field(max_length=200)
    rationale: str = ""
    kind: str = "info"  # info | dismissal


class ContextFindingIn(BaseModel):
    key: str  # media_source | edit_detection | full_context | cross_platform_copies
    outcome: str  # supports_flag | undermines_flag | inconclusive
    summary: str
    sha256: str | None = None


class ResponseIn(BaseModel):
    label: str = Field(max_length=200)
    description: str = ""
    sha256: str | None = None
