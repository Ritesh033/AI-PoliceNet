"""Calibrated infection model v2 (learns from field-trial data).

Pure-Python binomial logistic regression (Newton/IRLS with ridge) over features that
encode the review's gaps: temperature (G4), vector density, crop stage, individual Ty
loci and their interactions with heat and recombinant pressure (G1), mechanism
diversity (G1) and exclusion. Unlike the v1 heuristics, coefficients are *learned* from
observed incidence, so it gets better as real trial data accumulates (G5).
"""
from __future__ import annotations

import json
import math
from typing import Dict, List, Sequence

from . import risk, stacking

LOCI = list(stacking.LOCI)
STAGES = ["seedling", "flowering", "fruiting"]  # "vegetative" is the baseline
FEATURES = (["bias", "tf", "tf2", "log_wf"] + [f"stage_{s}" for s in STAGES] +
            [f"locus_{l}" for l in LOCI] +
            ["exclusion", "recomb", "ty13_hot", "ty13_recomb", "multi_mech"])


def features(x: Dict) -> List[float]:
    """x: temp_c, whitefly_per_leaf, stage, loci(list), exclusion(bool), recombinant_pressure(bool)."""
    t = float(x["temp_c"])
    tf = risk.temp_factor(t)
    loci = set(x.get("loci") or [])
    ty13 = 1.0 if "Ty-1/Ty-3" in loci else 0.0
    hot = max(0.0, t - 30.0) / 5.0
    recomb = 1.0 if x.get("recombinant_pressure") else 0.0
    mechs = {stacking.LOCI[n]["mechanism"] for n in loci if n in stacking.LOCI and stacking.LOCI[n]["weight"] >= 0.2}
    stage = x.get("stage", "vegetative")
    return ([1.0, tf, tf * tf, math.log1p(max(0.0, float(x.get("whitefly_per_leaf", 0))))] +
            [1.0 if stage == s else 0.0 for s in STAGES] +
            [1.0 if l in loci else 0.0 for l in LOCI] +
            [1.0 if x.get("exclusion") else 0.0, recomb, ty13 * hot, ty13 * recomb,
             1.0 if len(mechs) >= 2 else 0.0])


def _solve(a: List[List[float]], b: List[float]) -> List[float]:
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(m[r][c]))
        m[c], m[p] = m[p], m[c]
        piv = m[c][c]
        if abs(piv) < 1e-12:
            raise ValueError("singular system")
        for j in range(c, n + 1):
            m[c][j] /= piv
        for r in range(n):
            if r != c and m[r][c]:
                f = m[r][c]
                for j in range(c, n + 1):
                    m[r][j] -= f * m[c][j]
    return [m[i][n] for i in range(n)]


def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def fit(rows: Sequence[Dict], ridge: float = 1.0, iters: int = 30) -> Dict:
    """rows: dicts with the feature inputs plus plants, infected. Returns a model dict."""
    if len(rows) < 30:
        raise ValueError("need at least 30 trial rows to calibrate")
    X = [features(r) for r in rows]
    n = [float(r["plants"]) for r in rows]
    k = [float(r["infected"]) for r in rows]
    d = len(FEATURES)
    w = [0.0] * d
    for _ in range(iters):
        grad = [0.0] * d
        hess = [[0.0] * d for _ in range(d)]
        for xi, ni, ki in zip(X, n, k):
            p = _sigmoid(sum(a * b for a, b in zip(w, xi)))
            r = ki - ni * p
            v = ni * p * (1 - p) + 1e-9
            for i in range(d):
                if xi[i]:
                    grad[i] += r * xi[i]
                    for j in range(d):
                        if xi[j]:
                            hess[i][j] += v * xi[i] * xi[j]
        for i in range(1, d):  # do not penalise the bias
            grad[i] -= ridge * w[i]
            hess[i][i] += ridge
        step = _solve(hess, grad)
        w = [a + b for a, b in zip(w, step)]
        if max(abs(s) for s in step) < 1e-6:
            break
    return {"features": FEATURES, "weights": w, "n_rows": len(rows), "ridge": ridge}


def predict(model: Dict, x: Dict) -> float:
    return _sigmoid(sum(a * b for a, b in zip(model["weights"], features(x))))


def save(model: Dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(model, f)


def load(path: str) -> Dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)
