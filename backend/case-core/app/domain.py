"""Roles, stages and the rules for who may do what.

This module is the single source of truth for the platform's decision boundaries:

* AI actors can raise alerts and attach advisory notes. They can never move a case.
* Only a human authorized officer can register an FIR.
* Only a judicial authority can close a registered FIR.
* Nobody can act on a case in which they are named as the subject.
* Time passing never changes a person's legal position.
* There is no counter of flags, strikes or alerts that restricts access to any court.
* Only a human authority issues a challan or records a sanction. A count of recorded sanctions against a public
  servant can ask a human authority to review; it never suspends, removes or fines anyone by itself.
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
    PENALTY_RECORDED = "penalty_recorded"  # a human issued a challan or recorded a departmental sanction


class Track(str, Enum):
    """What kind of consequence a case can lead to. A case is on exactly one track and cannot change it."""

    CRIMINAL = "criminal"  # an offence: an authorized officer may register an FIR
    CIVIC = "civic"  # a civic violation: a human may issue a challan; never an FIR, never a flag
    DEPARTMENTAL = "departmental"  # official misconduct short of an offence: a competent authority may record a sanction


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
    CIVIC = "civic"  # a civic violation; leads to a challan, never an FIR
    OFFICIAL_MISCONDUCT = "official_misconduct"  # departmental matter about an official; not an offence in itself


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
        "physical_assault",  # beating or torture, by anyone; whether force was lawful is for the human who reviews the facts
        "bribe_demand",  # a public servant asking for an illegal payment or favour
    }
)
# Civic violations are not crimes. They lead to a fine (challan) issued by a human, never to an FIR, and they are not
# a flag: nothing counts them.
CIVIC_BEHAVIORS = frozenset({"obstructive_parking", "public_spitting", "public_urination", "waste_dumping_in_water"})
# Official misconduct that is not itself an offence. Flagged only when the clip shows a person acting in an official
# capacity, and then only for a competent authority to consider.
DEPARTMENTAL_BEHAVIORS = frozenset(
    {"abuse_of_official_power", "private_agents_in_official_acts", "official_misbehavior"}
)
KNOWN_BEHAVIORS = (
    CASUAL_OR_PROTECTED | CONDITIONAL_BEHAVIORS | HARD_ACTIONABLE | CIVIC_BEHAVIORS | DEPARTMENTAL_BEHAVIORS
)

BENIGN_SITUATIONS = frozenset(
    {"friendly_banter", "casual_talk", "quoted_or_fictional", "satire", "political_commentary", "public_debate"}
)
AGGRAVATING_SITUATIONS = frozenset(
    {"repeated_targeting", "coordinated_campaign", "power_imbalance", "target_is_minor", "private_individual_target"}
)
PUBLIC_OFFICIAL_TARGET = "public_official_target"
# The clip shows a person acting in an official capacity (as opposed to an official being the target of abuse).
ACTING_IN_OFFICIAL_CAPACITY = "acting_in_official_capacity"
KNOWN_SITUATIONS = BENIGN_SITUATIONS | AGGRAVATING_SITUATIONS | {PUBLIC_OFFICIAL_TARGET, ACTING_IN_OFFICIAL_CAPACITY}


@dataclass(frozen=True)
class FlagDecision:
    flag: bool
    reason: str
    track: str = Track.CRIMINAL.value


def behavior_tracks(behaviors: "set[str] | frozenset[str] | list[str]") -> set[str]:
    """The tracks the behaviours point to. Casual speech behaviours point to none and can accompany any alert."""
    b = set(behaviors)
    tracks: set[str] = set()
    if b & (HARD_ACTIONABLE | CONDITIONAL_BEHAVIORS):
        tracks.add(Track.CRIMINAL.value)
    if b & CIVIC_BEHAVIORS:
        tracks.add(Track.CIVIC.value)
    if b & DEPARTMENTAL_BEHAVIORS:
        tracks.add(Track.DEPARTMENTAL.value)
    return tracks


def decide_flag(behaviors: "set[str] | frozenset[str] | list[str]", situation: "set[str] | frozenset[str] | list[str]" = ()) -> FlagDecision:
    b = set(behaviors)
    s = set(situation)
    hard = b & HARD_ACTIONABLE
    if hard:
        return FlagDecision(True, f"Actionable behaviour detected: {sorted(hard)}. Temporary flag on the clip for human review.")
    departmental = b & DEPARTMENTAL_BEHAVIORS
    if departmental:
        dep = Track.DEPARTMENTAL.value
        if ACTING_IN_OFFICIAL_CAPACITY not in s:
            return FlagDecision(
                False,
                f"{sorted(departmental)} is considered only when the clip shows a person acting in an official capacity. "
                "Nothing here shows that, so it is not flagged.",
                dep,
            )
        if "quoted_or_fictional" in s:
            return FlagDecision(False, "The clip is quoted or fictional (for example a film scene). Not flagged.", dep)
        return FlagDecision(
            True,
            f"Possible official misconduct {sorted(departmental)}. Opened for a competent authority to consider. "
            "This is not a crime, so no FIR can be registered on it.",
            dep,
        )
    civic = b & CIVIC_BEHAVIORS
    if civic:
        cv = Track.CIVIC.value
        if "quoted_or_fictional" in s:
            return FlagDecision(False, "The clip is quoted or fictional (for example a film scene). Not flagged.", cv)
        return FlagDecision(
            True,
            f"Civic violation {sorted(civic)}. Opened for a human to consider a challan. This is not a crime, no FIR can "
            "be registered on it, and it is not counted as a flag.",
            cv,
        )
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
#   * A civic violation (parking that blocks a road, spitting, urinating on a public wall, dumping waste in a river):
#     the person who did it, or the registered owner of the vehicle, can be a subject. Whoever filmed or posted it is not.
#   * Official conduct (for example stopping and fining people without papers or inquiry, or keeping private persons
#     alongside to do official work): the public servant, a private person acting for them, or a contractor or licensee
#     can be a subject. Whoever filmed or posted it, and anyone treated that way, is not.
SCENARIOS = frozenset(
    {
        "other", "intimate_imagery_without_consent", "public_indecent_act", "explicit_content_published",
        "civic_violation", "official_conduct",
    }
)
PARTY_ROLES = frozenset(
    {
        "depicted_person", "uploader", "sharer", "recorder", "performer_in_public_act", "viewer_or_commenter",
        "vehicle_owner", "public_servant", "private_agent_of_official", "contractor_or_licensee",
    }
)
DETERMINATIONS = frozenset({"subject", "victim", "witness", "not_involved"})
SUBJECT_CAPABLE_ROLES: dict[str, frozenset[str]] = {
    "intimate_imagery_without_consent": frozenset({"uploader", "sharer", "recorder"}),
    "public_indecent_act": frozenset({"performer_in_public_act"}),
    "explicit_content_published": frozenset({"uploader", "sharer"}),
    "civic_violation": frozenset({"performer_in_public_act", "vehicle_owner"}),
    "official_conduct": frozenset({"public_servant", "private_agent_of_official", "contractor_or_licensee"}),
}
# The scenario that a track's cases use when the alert does not say.
TRACK_SCENARIO = {Track.CIVIC.value: "civic_violation", Track.DEPARTMENTAL.value: "official_conduct"}
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
    # For a criminal case a notice follows an FIR. For a civic or departmental case it can be served once the case is
    # referred (see CaseService._authorize_notice).
    "serve_notice": _spec(
        {_R.AUTHORIZED_OFFICER}, {_S.REFERRED, _S.INQUIRY, _S.FIR_REGISTERED, _S.PENALTY_RECORDED}, None, False
    ),
    "court_proceed": _spec({_R.JUDICIAL_AUTHORITY}, {_S.FIR_REGISTERED}, None, True),
    "court_close": _spec({_R.JUDICIAL_AUTHORITY}, {_S.FIR_REGISTERED}, _S.CLOSED_BY_COURT, True),
    # Only a human officer decides who is a subject, a victim or a witness, within the scenario rules above.
    "determine_party": _spec(
        {_R.AUTHORIZED_OFFICER}, {_S.REFERRED, _S.INQUIRY, _S.FIR_REGISTERED, _S.PENALTY_RECORDED}, None, True
    ),
    # Identifying a person behind an account is a legal-process step by an officer, recorded here with its legal basis.
    # The platform itself never looks up, stores or messages anyone's contact details.
    "request_identification": _spec(
        {_R.AUTHORIZED_OFFICER}, {_S.REFERRED, _S.INQUIRY, _S.FIR_REGISTERED, _S.PENALTY_RECORDED}, None, True
    ),
    # New information about the same clip or issue is added to the existing case; it never opens a second FIR.
    "link_supplementary": _spec({_R.REVIEWER}, {_S.RECEIVED, _S.IN_REVIEW}, _S.LINKED, True),
    # A court may allow a fresh registration on the same clip (for example when the full original surfaces later).
    "permit_fresh_registration": _spec({_R.JUDICIAL_AUTHORITY}, {_S.CLOSED_BY_COURT}, None, True),
    # Civic violations: a human issues a challan to each person determined to be a subject. No FIR, no flag.
    "issue_challan": _spec(
        {_R.AUTHORIZED_OFFICER}, {_S.REFERRED, _S.INQUIRY, _S.PENALTY_RECORDED}, _S.PENALTY_RECORDED, True
    ),
    # Official misconduct: the competent disciplinary or procuring authority records a sanction against each person
    # determined to be a subject, after notice. The platform never imposes one.
    "impose_sanction": _spec(
        {_R.SUPERVISORY_AUTHORITY}, {_S.REFERRED, _S.INQUIRY, _S.PENALTY_RECORDED}, _S.PENALTY_RECORDED, True
    ),
    # A challan or sanction can be withdrawn by the authority above the issuer or by a court. Withdrawal lowers the count.
    "revoke_penalty": _spec(
        {_R.JUDICIAL_AUTHORITY, _R.SUPERVISORY_AUTHORITY}, {_S.PENALTY_RECORDED}, None, True
    ),
    # A review that a count of sanctions asked for is answered in writing by a human authority.
    "resolve_review": _spec({_R.SUPERVISORY_AUTHORITY}, {_S.PENALTY_RECORDED}, None, True),
    "appeal": _spec(
        {_R.CITIZEN},
        {_S.FIR_REGISTERED, _S.PENALTY_RECORDED, _S.CLOSED_NO_ACTION, _S.CLOSED_BY_COURT},
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
    "issue_challan": ["party_ref", "amount_inr", "legal_basis"],
    "impose_sanction": ["party_ref", "sanction_kind", "amount_inr", "legal_basis"],
    "revoke_penalty": ["penalty_id"],
    "resolve_review": ["party_ref"],
}

# --- Penalties and the review a count can ask for ------------------------------------------------------------------
# Challans and sanctions are recorded by a named human authority. The amounts are set by the law or schedule that
# applies, not by this platform; the floors below are configurable policy settings (see config.py) and a deployment
# must replace them with figures that a statute or rule supports.
SANCTION_KINDS = frozenset({"warning", "fine", "suspension", "licence_cancellation", "removal_order"})
# Sanctions that need the person to have been heard (a response on file, or the response window elapsed) before they
# are recorded. A warning and a suspension need a notice but not the full window: a suspension is an interim measure.
HEARING_REQUIRED_SANCTIONS = frozenset({"fine", "licence_cancellation", "removal_order"})
# Which party roles each sanction can be recorded against.
SANCTION_ROLES: dict[str, frozenset[str]] = {
    "warning": frozenset({"public_servant", "private_agent_of_official"}),
    "fine": frozenset({"public_servant", "private_agent_of_official", "contractor_or_licensee"}),
    "suspension": frozenset({"public_servant"}),
    "licence_cancellation": frozenset({"contractor_or_licensee"}),
    "removal_order": frozenset({"public_servant"}),
}
# A removal order follows an inquiry; it is never recorded straight from a referral.
INQUIRY_REQUIRED_SANCTIONS = frozenset({"removal_order"})
# Sanctions that count toward a public servant's review thresholds. Suspensions and removals are what a review may
# decide, so they are not counted themselves.
COUNTED_SANCTIONS = frozenset({"warning", "fine"})
# Counts at which a human authority is asked to review. Reaching one records a request and nothing else.
REVIEW_THRESHOLDS: dict[int, str] = {3: "interim_suspension_review", 7: "removal_inquiry_review"}

# Who handles a referred case, by case kind. Conduct complaints never go to the force being complained about.
REFERRAL_TARGET: dict[CaseKind, Role] = {
    CaseKind.SOCIAL: Role.AUTHORIZED_OFFICER,
    CaseKind.CONDUCT: Role.SUPERVISORY_AUTHORITY,
}
# A departmental case about an official goes to the supervisory authority, never to the force being filmed.
DEPARTMENTAL_REFERRAL_TARGET = Role.SUPERVISORY_AUTHORITY

# Actions a reviewer cannot skip past for confession videos.
CONFESSION_GATED_ACTIONS = frozenset({"refer", "register_fir"})


class PolicyViolation(Exception):
    """Raised when an action breaks a decision-boundary rule. Maps to HTTP 403 or 409."""

    def __init__(self, code: str, message: str, status: int = 403):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
