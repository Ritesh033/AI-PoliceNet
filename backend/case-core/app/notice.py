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
    lines = [
        f"NOTICE ABOUT A CLIP (case {case.id})",
        "",
        "Why you are receiving this",
        f"A short video clip (reference {clip}) was flagged because it appeared to involve {what}. "
        "An automated system only raised the flag. A human reviewer checked it, and an authorized officer decided to "
        "register an FIR. A machine did not make that decision.",
    ]
    if checks:
        lines += ["", "What was checked before the officer decided", checks]
    lines += [
        "",
        "What this means",
        "An FIR starts an investigation. It is not a finding that you did anything wrong. You are presumed innocent, "
        "and only a court can decide guilt.",
        "",
        "How to respond (you do not need to log in)",
        "You can send the full, unedited video of the incident, or any other material, from any account or device. "
        "You do not have to say who you are in order to upload. Use this private link, which belongs to this case only:",
        f"  {response_link}",
        "The material you send is matched to the flagged clip automatically. A human reads it, and a court can review "
        "the case at any time.",
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
