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


# --- Who is the suspect ------------------------------------------------------------------------------------------
# The platform looks for the person who committed the offence, not for whoever appears in or hosts a video.
# A scenario says what kind of event the clip shows; each scenario fixes which party roles can ever be a subject.
#   * Intimate imagery shared without consent: the people depicted are victims and are never subjects. The uploader,
#     the sharer or the person who secretly recorded it can be.
#   * A public indecent act (for example nudity at a live show or in a public place): the person performing the act is
#     the subject. The person who recorded or uploaded it is not, unless that person did something else wrong, such as
#     extortion or harassment, which is flagged separately.
#   * Explicit content published by the people who made or share it: the person who published it can be a subject.
# Parties are pseudonymous references from the platform feed. The AI proposes roles; only a human officer decides.
SCENARIOS = frozenset(
    {"other", "intimate_imagery_without_consent", "public_indecent_act", "explicit_content_published"}
)
PARTY_ROLES = frozenset(
    {"depicted_person", "uploader", "sharer", "recorder", "performer_in_public_act", "viewer_or_commenter"}
)
DETERMINATIONS = frozenset({"subject", "victim", "witness", "not_involved"})
SUBJECT_CAPABLE_ROLES: dict[str, frozenset[str]] = {
    "intimate_imagery_without_consent": frozenset({"uploader", "sharer", "recorder"}),
    "public_indecent_act": frozenset({"performer_in_public_act"}),
    "explicit_content_published": frozenset({"uploader", "sharer"}),
}
# Behaviours that are the wrongdoing of whoever recorded or shared a clip, independent of what the clip shows.
UPLOADER_SIDE_BEHAVIORS = frozenset({"extortion", "sexual_harassment", "targeted_hate", "incitement_to_violence", "child_involved"})


def explain_subject_rule(scenario: str, role: str, behaviors: "set[str] | list[str]") -> str | None:
    """None when this role can be a subject in this scenario; otherwise the reason it cannot."""
    capable = SUBJECT_CAPABLE_ROLES.get(scenario)
    if capable is None:
        return None  # no scenario rule: a human decides on the facts
    if role in capable:
        return None
    if scenario == "public_indecent_act" and role in {"uploader", "sharer", "recorder"} and set(behaviors) & UPLOADER_SIDE_BEHAVIORS:
        return None  # separate wrongdoing by the uploader, flagged on its own behaviours
    if role == "depicted_person" and scenario in ("intimate_imagery_without_consent", "explicit_content_published"):
        return (
            "The person depicted is a victim in this kind of case and is never a subject. "
            f"Subjects can be: {sorted(capable)}. If this person also published the material, record that as a separate 'uploader' role."
        )
    if scenario == "public_indecent_act":
        return (
            "In a public indecent act the subject is the person performing it, not the person who recorded or shared it. "
            "An uploader or recorder becomes a subject only for separate wrongdoing such as extortion or harassment, which must be flagged as its own behaviour."
        )
    return f"In '{scenario}' cases subjects can only be: {sorted(capable)}"


# Context the AI must have examined before any human can refer a social-media case: is the clip from a film, show
# or skit; has it been edited or cut; what is the full original; where else does it appear.
REQUIRED_CONTEXT_FINDINGS = frozenset({"media_source", "edit_detection", "full_context", "cross_platform_copies"})
# Recorded by the AI when material is uploaded in response to a notice: does it match the flagged clip, is it the full
# original. Informs humans; never part of the referral gate.
OPTIONAL_FINDINGS = frozenset({"response_match"})
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
    # Only a human officer decides who is a subject, a victim or a witness, within the scenario rules above.
    "determine_party": _spec(
        {_R.AUTHORIZED_OFFICER}, {_S.REFERRED, _S.INQUIRY, _S.FIR_REGISTERED}, None, True
    ),
    # Identifying a person behind an account is a legal-process step by an officer, recorded here with its legal basis.
    # The platform itself never looks up, stores or messages anyone's contact details.
    "request_identification": _spec(
        {_R.AUTHORIZED_OFFICER}, {_S.REFERRED, _S.INQUIRY, _S.FIR_REGISTERED}, None, True
    ),
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
ACTION_PARAMS: dict[str, list[str]] = {
    "record_check": ["check"],
    "link_supplementary": ["link_to"],
    "determine_party": ["party_ref", "party_role", "determination"],
    "request_identification": ["party_ref", "legal_basis"],
    "serve_notice": ["party_ref"],
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
