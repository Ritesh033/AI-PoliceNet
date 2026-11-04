"""Insecticide mode-of-action rotation planner (gap: insecticide resistance).

Generates a spray plan that never repeats the same mode-of-action (MoA) group
consecutively and balances group usage. It does not recommend products or doses:
the user supplies the MoA groups available to them, and local labels/extension
advice always take precedence.
"""
from __future__ import annotations

from collections import Counter
from typing import Dict, List


class ValidationError(ValueError):
    pass


def plan(available_groups: List[str], history: List[str] = None, sprays: int = 6,
         failed_groups: List[str] = None) -> Dict:
    history = [g.strip() for g in (history or []) if g and g.strip()]
    failed = {g.strip() for g in (failed_groups or []) if g and g.strip()}
    groups = [g.strip() for g in available_groups if g and g.strip()]
    groups = list(dict.fromkeys(groups))  # unique, order-preserving
    if not 1 <= sprays <= 30:
        raise ValidationError("sprays must be between 1 and 30")
    usable = [g for g in groups if g not in failed]
    warnings = []
    if failed:
        warnings.append(f"Excluded groups with reported control failure: {sorted(failed & set(groups))}")
    if not usable:
        raise ValidationError("no usable groups (all excluded or none supplied)")
    if len(usable) < 3:
        warnings.append("Fewer than 3 usable groups: resistance risk is high; add non-chemical measures and more groups.")
    sequence: List[str] = []
    prev = history[-1] if history else None
    counts = Counter(history[-3:])
    for _ in range(sprays):
        candidates = [g for g in usable if g != prev] or usable
        if candidates == usable and len(usable) == 1:
            warnings.append("Only one usable group: consecutive repeats are unavoidable.")
        choice = min(candidates, key=lambda g: (counts[g], usable.index(g)))
        sequence.append(choice)
        counts[choice] += 1
        prev = choice
    warnings = list(dict.fromkeys(warnings))
    return {"plan": [{"spray": i + 1, "moa_group": g} for i, g in enumerate(sequence)],
            "usage": dict(Counter(sequence)), "warnings": warnings,
            "disclaimer": "Advisory only. Follow product labels, local regulations and resistance-management guidance."}
