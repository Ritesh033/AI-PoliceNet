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


class AdvisoryIn(BaseModel):
    recommendation: str = Field(max_length=200)
    rationale: str = ""


class ResponseIn(BaseModel):
    label: str = Field(max_length=200)
    description: str = ""
    sha256: str | None = None
