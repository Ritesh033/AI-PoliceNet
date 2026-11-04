"""Climate- and vector-driven TYLCV infection-risk index (gap: climate effects).

HEURISTIC model. The shape of the curves encodes qualitative findings from the
review (warm temperatures favour whitefly activity and virus spread; early plant
stages are most vulnerable; exclusion and resistance lower risk). It has NOT been
validated against field data. Use the Field Trials module to collect data for
calibration.
"""
from __future__ import annotations

import math
from typing import Dict, Iterable, List

# (temperature in C, suitability 0..1) piecewise-linear control points
TEMP_POINTS = [(10.0, 0.0), (18.0, 0.6), (22.0, 1.0), (30.0, 1.0), (35.0, 0.6), (40.0, 0.2)]

STAGE_FACTOR = {"seedling": 1.0, "vegetative": 0.8, "flowering": 0.5, "fruiting": 0.3}

CATEGORIES = [(20.0, "Low"), (40.0, "Moderate"), (65.0, "High"), (101.0, "Very high")]


class ValidationError(ValueError):
    pass


def temp_factor(t: float) -> float:
    if t <= TEMP_POINTS[0][0]:
        return 0.0
    for (x0, y0), (x1, y1) in zip(TEMP_POINTS, TEMP_POINTS[1:]):
        if t <= x1:
            return y0 + (y1 - y0) * (t - x0) / (x1 - x0)
    return 0.1  # very hot: whitefly activity strongly reduced


def vector_factor(whitefly_per_leaf: float) -> float:
    """Saturating response to adult whitefly density (adults/leaf)."""
    if whitefly_per_leaf < 0:
        raise ValidationError("whitefly_per_leaf must be >= 0")
    return min(1.0, math.log1p(whitefly_per_leaf) / math.log1p(5.0))


def category(index: float) -> str:
    for limit, name in CATEGORIES:
        if index < limit:
            return name
    return CATEGORIES[-1][1]


def risk_index(temp_c: float, whitefly_per_leaf: float, stage: str = "vegetative",
               protection: float = 0.0, exclusion: bool = False) -> Dict:
    """Return a 0-100 risk index with its components and advice."""
    if stage not in STAGE_FACTOR:
        raise ValidationError(f"stage must be one of {sorted(STAGE_FACTOR)}")
    if not 0.0 <= protection <= 1.0:
        raise ValidationError("protection must be between 0 and 1")
    if not -20.0 <= temp_c <= 60.0:
        raise ValidationError("temp_c outside plausible range (-20..60)")
    tf = temp_factor(temp_c)
    vf = vector_factor(whitefly_per_leaf)
    sf = STAGE_FACTOR[stage]
    value = 100.0 * tf * vf * sf * (1.0 - 0.7 * protection)
    if exclusion:
        value *= 0.25
    value = round(value, 1)
    cat = category(value)
    return {
        "index": value,
        "category": cat,
        "components": {"temperature": round(tf, 3), "vector": round(vf, 3),
                       "stage": sf, "protection": protection, "exclusion": exclusion},
        "actions": advice(cat, stage, exclusion, whitefly_per_leaf),
    }


def advice(cat: str, stage: str, exclusion: bool, wf: float) -> List[str]:
    out: List[str] = []
    if cat in ("High", "Very high"):
        out.append("Scout every 2-3 days and remove symptomatic plants early.")
        out.append("Rotate insecticide modes of action (see IPM Rotation); do not repeat a group back-to-back.")
        if not exclusion:
            out.append("Use insect-proof netting or reflective mulch where practical.")
    elif cat == "Moderate":
        out.append("Scout weekly with yellow sticky traps; confirm vector density before spraying.")
    else:
        out.append("Maintain routine monitoring and weed control around the field.")
    if stage == "seedling":
        out.append("Seedlings are the most vulnerable stage: keep nurseries under insect-proof nets.")
    if wf >= 3:
        out.append("Whitefly density is high; verify symptoms by PCR if available.")
    out.append("Advisory only: follow local extension guidance and product labels.")
    return out


def season_risk(rows: Iterable[Dict], stage: str = "vegetative", protection: float = 0.0,
                exclusion: bool = False) -> Dict:
    """Compute daily risk for rows of {date, temp_c, whitefly_per_leaf}."""
    daily = []
    for i, r in enumerate(rows):
        try:
            res = risk_index(float(r["temp_c"]), float(r.get("whitefly_per_leaf", 0)),
                             r.get("stage", stage), protection, exclusion)
        except (KeyError, TypeError, ValueError) as e:
            raise ValidationError(f"row {i + 1}: {e}")
        daily.append({"date": r.get("date", str(i + 1)), "index": res["index"], "category": res["category"]})
    if not daily:
        raise ValidationError("no rows supplied")
    idx = [d["index"] for d in daily]
    high = [d for d in daily if d["category"] in ("High", "Very high")]
    return {
        "daily": daily,
        "summary": {"days": len(daily), "mean": round(sum(idx) / len(idx), 1), "max": max(idx),
                    "high_risk_days": len(high), "first_high_date": high[0]["date"] if high else None},
    }
