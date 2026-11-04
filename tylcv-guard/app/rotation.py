"""Insecticide mode-of-action rotation planner (gap: insecticide resistance).

Generates a spray plan that never repeats the same mode-of-action (MoA) group
consecutively and balances group usage. It does not recommend products or doses:
the user supplies the MoA groups available to them, and local labels/extension
advice always take precedence.
"""
from __future__ import annotations

from collections import Counter
from typing import Dict, List


PRIOR_EFFICACY = 0.8   # assumed efficacy of an untested / fully susceptible group
REVERSION = 0.95       # per-spray recovery of efficacy in a group that is not being used


class ValidationError(ValueError):
    pass


def plan(available_groups: List[str], history: List[str] = None, sprays: int = 6,
         failed_groups: List[str] = None, efficacy: Dict[str, float] = None) -> Dict:
    history = [g.strip() for g in (history or []) if g and g.strip()]
    failed = {g.strip() for g in (failed_groups or []) if g and g.strip()}
    efficacy = dict(efficacy or {})
    eff_failed = set()
    for g, e in efficacy.items():
        if not 0.0 <= float(e) <= 1.0:
            raise ValidationError("efficacy values must be between 0 and 1")
        if float(e) < 0.5:  # observed field efficacy below 50% counts as a control failure
            eff_failed.add(g.strip())
    failed |= eff_failed
    groups = [g.strip() for g in available_groups if g and g.strip()]
    groups = list(dict.fromkeys(groups))  # unique, order-preserving
    if not 1 <= sprays <= 30:
        raise ValidationError("sprays must be between 1 and 30")
    usable = [g for g in groups if g not in failed]
    warnings = []
    if failed:
        warnings.append(f"Excluded groups with reported control failure: {sorted(failed & set(groups))}")
    if not usable and eff_failed and not ((failed - eff_failed) & set(groups)):
        # every group is failing on observed efficacy: fall back to the least-bad groups and say so
        usable = list(groups)
        warnings.append("All groups show observed efficacy below 50%: rely on non-chemical measures (exclusion, "
                        "sanitation, resistant cultivars) and re-assess efficacy before spraying.")
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
        if efficacy:  # prefer the best *estimated* efficacy; observations go stale as resistance reverts
            seq_all = history + sequence

            def estimate(g):
                if g not in efficacy:
                    return PRIOR_EFFICACY
                age = next((i for i, x in enumerate(reversed(seq_all)) if x == g), len(seq_all))
                return PRIOR_EFFICACY - (PRIOR_EFFICACY - float(efficacy[g])) * REVERSION ** age
            choice = max(candidates, key=lambda g: (estimate(g) - 0.1 * counts[g], -usable.index(g)))
        else:
            choice = min(candidates, key=lambda g: (counts[g], usable.index(g)))
        sequence.append(choice)
        counts[choice] += 1
        prev = choice
    warnings = list(dict.fromkeys(warnings))
    return {"plan": [{"spray": i + 1, "moa_group": g} for i, g in enumerate(sequence)],
            "usage": dict(Counter(sequence)), "warnings": warnings,
            "disclaimer": "Advisory only. Follow product labels, local regulations and resistance-management guidance."}
