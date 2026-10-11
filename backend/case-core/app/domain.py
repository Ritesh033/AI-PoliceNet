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
    SYSTEM = "system"
    REVIEWER = "reviewer"
    AUTHORIZED_OFFICER = "authorized_officer"
    SUPERVISORY_AUTHORITY = "supervisory_authority"
    JUDICIAL_AUTHORITY = "judicial_authority"
    CITIZEN = "citizen"
    AUDITOR = "auditor"


class Kind(str, Enum):
    AI = "ai"
    SYSTEM = "system"
    HUMAN = "human"


class Stage(str, Enum):
    RECEIVED = "received"
    IN_REVIEW = "in_review"
    REFERRED = "referred"
    INQUIRY = "inquiry"
    FIR_REGISTERED = "fir_registered"
    CLOSED_NO_ACTION = "closed_no_action"
    CLOSED_BY_COURT = "closed_by_court"
    LINKED = "linked"  # merged into another case as supplementary information


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

# --- Flagging policy -------------------------------------------------------------------------------------------
# What the AI may flag is a *policy*, owned by legal experts, not an engineering decision. A flag is only a
# consequence-free request for human review of one clip; it is never an accusation.
#
# The model classifies by intent and situation, never by keywords: common profanity (including Hindi words with
# sexual references) is everyday speech between friends and must not be flagged just because the word appears.
#
# Default policy:
#   * Casual profanity, insults, criticism and false statements alone are never flagged.
#   * Aggressive abuse is flagged only when the situation shows an aggravator (repeated targeting of a private
#     person, a coordinated campaign against a private person, a power imbalance, or a minor target).
#   * Abuse of or criticism aimed at a public official or leader is never flagged on that basis, however crude.
#     Officials get no extra protection from criticism. Threats and the other hard behaviours below are flagged
#     for everyone alike, officials included.
# Legal review must confirm this list: some abuse IS an offence (for example caste-based abuse in public, words
# insulting a woman's modesty, threats, incitement against a community), which is why those are hard behaviours.
CASUAL_OR_PROTECTED = frozenset({"casual_profanity", "insult", "criticism", "false_statement"})
CONDITIONAL_BEHAVIORS = frozenset({"aggressive_abuse"})
HARD_ACTIONABLE = frozenset(
    {
        "threat",
        "extortion",
        "fraud",
        "impersonation",
        "sexual_content",  # sexually explicit material; NOT profanity that merely contains a sexual reference
        "sexual_harassment",  # sexual comments or threats directed at a person
        "non_consensual_imagery",
        "child_involved",
        "incitement_to_violence",
        "targeted_hate",  # abuse aimed at a person or group for caste, religion or another protected trait
        "self_admission",
    }
)
KNOWN_BEHAVIORS = CASUAL_OR_PROTECTED | CONDITIONAL_BEHAVIORS | HARD_ACTIONABLE

BENIGN_SITUATIONS = frozenset(
    {"friendly_banter", "casual_talk", "quoted_or_fictional", "satire", "political_commentary", "public_debate"}
)
AGGRAVATING_SITUATIONS = frozenset(
    {"repeated_targeting", "coordinated_campaign", "power_imbalance", "target_is_minor", "private_individual_target"}
)
PUBLIC_OFFICIAL_TARGET = "public_official_target"
KNOWN_SITUATIONS = BENIGN_SITUATIONS | AGGRAVATING_SITUATIONS | {PUBLIC_OFFICIAL_TARGET}


@dataclass(frozen=True)
class FlagDecision:
    flag: bool
    reason: str


def decide_flag(behaviors: "set[str] | frozenset[str] | list[str]", situation: "set[str] | frozenset[str] | list[str]" = ()) -> FlagDecision:
    b = set(behaviors)
    s = set(situation)
    hard = b & HARD_ACTIONABLE
    if hard:
        return FlagDecision(True, f"Actionable behaviour detected: {sorted(hard)}. Temporary flag on the clip for human review.")
    if "aggressive_abuse" in b:
        if PUBLIC_OFFICIAL_TARGET in s:
            return FlagDecision(
                False,
                "Abuse of or criticism aimed at a public official or leader is not flagged on that basis. "
                "Officials get no extra protection from criticism, however crude.",
            )
        aggravators = s & AGGRAVATING_SITUATIONS
        if aggravators:
            return FlagDecision(True, f"Aggressive abuse with aggravating context {sorted(aggravators)}. Temporary flag on the clip for human review.")
        return FlagDecision(False, "Aggressive language without aggravating context. Banter-style and general-talk abuse is not flagged.")
    return FlagDecision(False, "No actionable behaviour. Casual profanity, insults, criticism or false statements alone are not flagged.")


# Context the AI must have examined before any human can refer a social-media case: is the clip from a film, show
# or skit; has it been edited or cut; what is the full original; where else does it appear.
REQUIRED_CONTEXT_FINDINGS = frozenset({"media_source", "edit_detection", "full_context", "cross_platform_copies"})
FINDING_OUTCOMES = frozenset({"supports_flag", "undermines_flag", "inconclusive"})
CONTEXT_GATED_ACTIONS = frozenset({"refer", "register_fir"})

# Stages where a human has not yet taken the case to an authorized decision. The decision clock watches these.
UNDECIDED_STAGES = frozenset({Stage.RECEIVED, Stage.IN_REVIEW, Stage.REFERRED})

# Checks a human must record before a self-uploaded confession video can go further.
CONFESSION_REQUIRED_CHECKS = frozenset({"wellbeing", "authenticity"})
KNOWN_CHECKS = frozenset({"wellbeing", "authenticity", "real_world_match", "context"})


@dataclass(frozen=True)
class Actor:
    id: str
    role: Role

    @property
    def kind(self) -> Kind:
        if self.role is Role.AI_SERVICE:
            return Kind.AI
        if self.role is Role.SYSTEM:
            return Kind.SYSTEM
        return Kind.HUMAN

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
    # New information about the same clip or issue is added to the existing case; it never opens a second FIR.
    "link_supplementary": _spec({_R.REVIEWER}, {_S.RECEIVED, _S.IN_REVIEW}, _S.LINKED, True),
    # A court may allow a fresh registration on the same clip (for example when the full original surfaces later).
    "permit_fresh_registration": _spec({_R.JUDICIAL_AUTHORITY}, {_S.CLOSED_BY_COURT}, None, True),
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

# Extra inputs an action needs besides the written note. Exposed so a client can render the right form.
ACTION_PARAMS: dict[str, list[str]] = {"record_check": ["check"], "link_supplementary": ["link_to"]}

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
