"""Roles, stages and the rules for who may do what.

This module is the single source of truth for the platform's decision boundaries:

* AI actors can raise alerts and attach advisory notes. They can never move a case.
* Only a human authorized officer can register an FIR.
* Only a judicial authority can close a registered FIR.
* Nobody can act on a case in which they are named as the subject.
* Time passing never changes a person's legal position.
* There is no counter of flags, strikes or alerts that restricts access to any court.
"""

from dataclasses import dataclass
from enum import Enum


class Role(str, Enum):
    AI_SERVICE = "ai_service"
    REVIEWER = "reviewer"
    AUTHORIZED_OFFICER = "authorized_officer"
    SUPERVISORY_AUTHORITY = "supervisory_authority"
    JUDICIAL_AUTHORITY = "judicial_authority"
    CITIZEN = "citizen"
    AUDITOR = "auditor"


class Kind(str, Enum):
    AI = "ai"
    HUMAN = "human"


class Stage(str, Enum):
    RECEIVED = "received"
    IN_REVIEW = "in_review"
    REFERRED = "referred"
    INQUIRY = "inquiry"
    FIR_REGISTERED = "fir_registered"
    CLOSED_NO_ACTION = "closed_no_action"
    CLOSED_BY_COURT = "closed_by_court"


class CaseKind(str, Enum):
    SOCIAL = "social"
    CONDUCT = "conduct"


class Category(str, Enum):
    THREAT = "threat"
    SCAM = "scam"
    NCII = "ncii"
    HATE = "hate"
    MANIPULATED = "manipulated"
    SELF_CONFESSION_VIDEO = "self_confession_video"
    CONDUCT = "conduct"


# Categories whose media must never be previewed, only hashed.
SENSITIVE_CATEGORIES = frozenset({Category.NCII})

# Checks a human must record before a self-uploaded confession video can go further.
CONFESSION_REQUIRED_CHECKS = frozenset({"wellbeing", "authenticity"})
KNOWN_CHECKS = frozenset({"wellbeing", "authenticity", "real_world_match", "context"})


@dataclass(frozen=True)
class Actor:
    id: str
    role: Role

    @property
    def kind(self) -> Kind:
        return Kind.AI if self.role is Role.AI_SERVICE else Kind.HUMAN

    @property
    def is_staff(self) -> bool:
        return self.role in STAFF_ROLES


STAFF_ROLES = frozenset(
    {
        Role.REVIEWER,
        Role.AUTHORIZED_OFFICER,
        Role.SUPERVISORY_AUTHORITY,
        Role.JUDICIAL_AUTHORITY,
        Role.AUDITOR,
    }
)


@dataclass(frozen=True)
class ActionSpec:
    roles: frozenset[Role]
    from_stages: frozenset[Stage]
    to_stage: Stage | None
    note_required: bool


def _spec(roles: set[Role], from_stages: set[Stage], to_stage: Stage | None, note_required: bool) -> ActionSpec:
    return ActionSpec(frozenset(roles), frozenset(from_stages), to_stage, note_required)


_S = Stage
_R = Role

ACTIONS: dict[str, ActionSpec] = {
    "assign": _spec({_R.REVIEWER}, {_S.RECEIVED}, _S.IN_REVIEW, False),
    "record_check": _spec({_R.REVIEWER}, {_S.RECEIVED, _S.IN_REVIEW}, None, False),
    "request_context": _spec({_R.REVIEWER}, {_S.RECEIVED, _S.IN_REVIEW}, None, True),
    "no_action": _spec({_R.REVIEWER}, {_S.RECEIVED, _S.IN_REVIEW}, _S.CLOSED_NO_ACTION, True),
    "refer": _spec({_R.REVIEWER}, {_S.IN_REVIEW}, _S.REFERRED, True),
    "open_inquiry": _spec({_R.AUTHORIZED_OFFICER, _R.SUPERVISORY_AUTHORITY}, {_S.REFERRED}, _S.INQUIRY, True),
    "decline": _spec(
        {_R.AUTHORIZED_OFFICER, _R.SUPERVISORY_AUTHORITY},
        {_S.REFERRED, _S.INQUIRY},
        _S.CLOSED_NO_ACTION,
        True,
    ),
    "register_fir": _spec({_R.AUTHORIZED_OFFICER}, {_S.REFERRED, _S.INQUIRY}, _S.FIR_REGISTERED, True),
    "serve_notice": _spec({_R.AUTHORIZED_OFFICER}, {_S.FIR_REGISTERED}, None, False),
    "court_proceed": _spec({_R.JUDICIAL_AUTHORITY}, {_S.FIR_REGISTERED}, None, True),
    "court_close": _spec({_R.JUDICIAL_AUTHORITY}, {_S.FIR_REGISTERED}, _S.CLOSED_BY_COURT, True),
    "appeal": _spec(
        {_R.CITIZEN},
        {_S.FIR_REGISTERED, _S.CLOSED_NO_ACTION, _S.CLOSED_BY_COURT},
        None,
        True,
    ),
    "resolve_appeal": _spec(
        {_R.JUDICIAL_AUTHORITY, _R.SUPERVISORY_AUTHORITY},
        set(Stage),
        None,
        True,
    ),
}

# Who handles a referred case, by case kind. Conduct complaints never go to the force being complained about.
REFERRAL_TARGET: dict[CaseKind, Role] = {
    CaseKind.SOCIAL: Role.AUTHORIZED_OFFICER,
    CaseKind.CONDUCT: Role.SUPERVISORY_AUTHORITY,
}

# Actions a reviewer cannot skip past for confession videos.
CONFESSION_GATED_ACTIONS = frozenset({"refer", "register_fir"})


class PolicyViolation(Exception):
    """Raised when an action breaks a decision-boundary rule. Maps to HTTP 403 or 409."""

    def __init__(self, code: str, message: str, status: int = 403):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
