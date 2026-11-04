"""Resistance-stacking planner (gap: durability of resistance).

HEURISTIC. Effect sizes below are illustrative priors reflecting the review's
qualitative findings (Ty-1/Ty-3 weaken at high temperature and under recombinant
pressure; Ty-2 acts through an NB-LRR and is narrower in virus spectrum; stacking
loci with different mechanisms improves durability). They must be calibrated with
field-trial data before being used for real breeding decisions.
"""
from __future__ import annotations

from typing import Dict, List

LOCI: Dict[str, Dict] = {
    "Ty-1/Ty-3": {"mechanism": "RNA-dependent RNA polymerase (DNA methylation)", "weight": 0.45,
                  "note": "Broad geminivirus resistance; reported to weaken at high temperature and under recombinant pressure."},
    "Ty-2": {"mechanism": "NB-LRR immune receptor (TYNBS1)", "weight": 0.40,
             "note": "Effective against TYLCV but narrower against other begomoviruses."},
    "ty-5": {"mechanism": "Pelota loss of function (recessive)", "weight": 0.35,
             "note": "Susceptibility-gene mechanism; recessive, so both parents must carry it."},
    "Ty-6": {"mechanism": "DNA polymerase delta subunit 1 variant (POLD1)", "weight": 0.25,
             "note": "Partial resistance; best when combined with another locus."},
    "Ty-4": {"mechanism": "Minor-effect locus", "weight": 0.10,
             "note": "Small effect on its own."},
}

DURABILITY = {0: "None", 1: "Low (single mechanism)", 2: "Moderate", 3: "Higher"}


class ValidationError(ValueError):
    pass


def effective_weights(selected: List[str], mean_max_temp_c: float, recombinant_pressure: bool,
                      virus: str) -> Dict[str, float]:
    eff = {}
    for name in selected:
        w = LOCI[name]["weight"]
        if name == "Ty-1/Ty-3":
            if mean_max_temp_c > 30:
                w *= 0.7
            if recombinant_pressure:
                w *= 0.6
        if name == "Ty-2" and virus != "TYLCV":
            w *= 0.5
        eff[name] = round(w, 4)
    return eff


def combined(eff: Dict[str, float]) -> float:
    p = 1.0
    for w in eff.values():
        p *= 1.0 - w
    return round(min(0.95, 1.0 - p), 4)


def durability_tier(selected: List[str]) -> str:
    mechanisms = {LOCI[n]["mechanism"] for n in selected if LOCI[n]["weight"] >= 0.2}
    return DURABILITY[min(3, len(mechanisms))]


def plan(selected: List[str], mean_max_temp_c: float = 28.0, recombinant_pressure: bool = False,
         virus: str = "TYLCV") -> Dict:
    unknown = [s for s in selected if s not in LOCI]
    if unknown:
        raise ValidationError(f"unknown loci: {unknown}; valid: {sorted(LOCI)}")
    if len(set(selected)) != len(selected):
        raise ValidationError("duplicate loci")
    if not -10 <= mean_max_temp_c <= 55:
        raise ValidationError("mean_max_temp_c outside plausible range")
    eff = effective_weights(selected, mean_max_temp_c, recombinant_pressure, virus)
    score = combined(eff)
    recs = []
    for name in LOCI:
        if name in selected:
            continue
        e = effective_weights(selected + [name], mean_max_temp_c, recombinant_pressure, virus)
        recs.append({"locus": name, "gain": round(combined(e) - score, 4),
                     "new_durability": durability_tier(selected + [name]),
                     "mechanism": LOCI[name]["mechanism"], "note": LOCI[name]["note"]})
    recs.sort(key=lambda r: r["gain"], reverse=True)
    warnings = []
    if mean_max_temp_c > 30 and "Ty-1/Ty-3" in selected:
        warnings.append("Ty-1/Ty-3 effect reduced for hot-season production.")
    if recombinant_pressure and "Ty-1/Ty-3" in selected:
        warnings.append("Recombinant pressure: do not rely on Ty-1/Ty-3 alone.")
    if len(selected) == 1:
        warnings.append("Single-locus resistance is vulnerable to breakdown; add a locus with a different mechanism.")
    if virus != "TYLCV" and "Ty-2" in selected:
        warnings.append("Ty-2 has a narrower virus spectrum; effect reduced for non-TYLCV begomoviruses.")
    return {"selected": selected, "effective_weights": eff, "protection": score,
            "durability": durability_tier(selected), "recommendations": recs, "warnings": warnings,
            "disclaimer": "Heuristic priors, not field-calibrated. Calibrate with Field Trials data."}
