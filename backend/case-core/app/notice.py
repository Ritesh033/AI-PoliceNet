"""The notice a subject receives. Deterministic text built from case facts, so every word served is on the record.

The platform never sends it. An authorized officer delivers it through a lawful channel and records that they did.
"""

from .models import Case

BEHAVIOR_TEXT = {
    "threat": "a threat",
    "extortion": "extortion or blackmail",
    "fraud": "fraud",
    "impersonation": "impersonation",
    "sexual_content": "sexually explicit material",
    "sexual_harassment": "sexual harassment",
    "non_consensual_imagery": "intimate imagery shared without consent",
    "child_involved": "content involving a child",
    "incitement_to_violence": "incitement to violence",
    "targeted_hate": "abuse aimed at a person or group for caste, religion or another protected trait",
    "self_admission": "a statement admitting an offence",
    "aggressive_abuse": "aggressive abuse",
    "physical_assault": "physical violence",
    "bribe_demand": "a demand for an illegal payment or favour by a public servant",
    "obstructive_parking": "parking that blocks a road",
    "public_spitting": "spitting in a public place",
    "public_urination": "urinating on a public wall or in a public place",
    "waste_dumping_in_water": "dumping waste in a river or other water body",
    "abuse_of_official_power": "use of official power without the papers or inquiry that the rules require",
    "private_agents_in_official_acts": "private persons acting alongside an official in official work",
    "official_misbehavior": "improper conduct by a person acting in an official capacity",
}

OUTCOME_TEXT = {
    "supports_flag": "points towards the flag",
    "undermines_flag": "points away from the flag",
    "inconclusive": "was inconclusive",
}

CHECK_TEXT = {
    "media_source": "Whether the clip comes from a film, show or skit",
    "edit_detection": "Whether the clip has been edited or cut",
    "full_context": "What the full original shows",
    "cross_platform_copies": "Where else the clip appears",
}


def _meaning(track: str) -> tuple[str, str]:
    """The decision that was taken and what it means for the person, by track."""
    if track == "civic":
        return (
            "An authorized officer decided to consider a challan (a fine). A machine did not make that decision.",
            "This is not a criminal matter and no FIR will be registered for it. A challan is a fine issued by an "
            "authorized officer and you can contest it. You may send the full video or any other material first.",
        )
    if track == "departmental":
        return (
            "A competent authority is considering whether any action is needed. A machine did not make that decision.",
            "This is a departmental or contractual matter, not a criminal case. A warning, fine, suspension or other "
            "sanction can be recorded only by the competent authority, only after it has read your response, and you "
            "can challenge it before a court.",
        )
    return (
        "A human reviewer checked it, and an authorized officer decided to register an FIR. A machine did not make that decision.",
        "An FIR starts an investigation. It is not a finding that you did anything wrong. You are presumed innocent, "
        "and only a court can decide guilt.",
    )


def build_notice(case: Case, response_link: str, window_days: int) -> str:
    what = ", ".join(BEHAVIOR_TEXT.get(b, b.replace("_", " ")) for b in case.behaviors) or "a possible offence"
    clip = (case.content_fingerprint or "")[:12]
    latest: dict[str, tuple[str, str]] = {}
    for item in case.items:
        if item.kind == "context_finding" and item.label in CHECK_TEXT:
            latest[item.label] = (item.outcome or "inconclusive", item.description)
    checks = "\n".join(
        f"  - {CHECK_TEXT[key]}: {OUTCOME_TEXT.get(outcome, outcome)}. {summary}"
        for key, (outcome, summary) in latest.items()
    )
    track = getattr(case, "track", "criminal") or "criminal"
    decision, means = _meaning(track)
    lines = [
        f"NOTICE ABOUT A CLIP (case {case.id})",
        "",
        "Why you are receiving this",
        f"A short video clip (reference {clip}) was flagged because it appeared to involve {what}. "
        f"An automated system only raised the flag. {decision}",
    ]
    if checks:
        heading = "What was checked before the officer decided" if track == "criminal" else "What was checked first"
        lines += ["", heading, checks]
    lines += [
        "",
        "What this means",
        means,
        "",
        "How to respond (you do not need to log in)",
        "You can send the full, unedited video of the incident, or any other material, from any account or device. "
        "You do not have to say who you are in order to upload. Use this private link, which belongs to this case only:",
        f"  {response_link}",
        "A human reads the material you send. Automated checks may also compare it with the flagged clip, and a court "
        "can review the case at any time.",
        "",
        "Time",
        f"Please respond within {window_days} days if you can. If that time passes, nothing happens to you "
        "automatically, and you can still respond.",
        "",
        "What this system will never ask for",
        "Money, bank details, OTPs, passwords or identity documents. A message that asks for these is not from this system.",
        "",
        "You may speak to a lawyer at any time.",
    ]
    return "\n".join(lines)
