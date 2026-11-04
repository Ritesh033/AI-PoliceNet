"""Synthetic ground truth for benchmarking (NOT real data).

The generator deliberately uses functional forms different from the app's heuristics
(Gaussian temperature optimum, Hill function for vectors, additive logit effects,
region random effects, binomial sampling noise) so the heuristics are genuinely
mis-specified approximations rather than the data-generating process.
"""
import itertools
import math
import random

LOCI = ["Ty-1/Ty-3", "Ty-2", "ty-5", "Ty-6", "Ty-4"]
REGIONS = {"cool": 22.0, "warm": 27.0, "hot": 32.0}
STAGES = ["seedling", "vegetative", "flowering", "fruiting"]
STAGE_EFFECT = {"seedling": 0.9, "vegetative": 0.4, "flowering": -0.2, "fruiting": -0.8}
MECH = {"Ty-1/Ty-3": "rdr", "Ty-2": "nlr", "ty-5": "pelo", "Ty-6": "pold", "Ty-4": "minor"}


def true_logit(T, wf, stage, loci, excl, recomb, field_effect=0.0):
    hill = wf ** 1.6 / (1.5 ** 1.6 + wf ** 1.6) if wf > 0 else 0.0
    z = -3.0 + 2.4 * hill + 1.7 * math.exp(-((T - 27.0) / 6.0) ** 2) + STAGE_EFFECT[stage] + field_effect
    for l in loci:
        if l == "Ty-1/Ty-3":
            eff = 1.4
            if T > 30:
                eff -= 0.6 * min(1.0, (T - 30) / 4.0)
            if recomb:
                eff -= 0.5
            z -= max(0.2, eff)
        elif l == "Ty-2":
            z -= 1.3
        elif l == "ty-5":
            z -= 1.0
        elif l == "Ty-6":
            z -= 0.6
        else:
            z -= 0.2
    if len({MECH[l] for l in loci if l != "Ty-4"}) >= 2:
        z -= 0.4
    if excl:
        z -= 2.0
    return z


def sigmoid(z):
    return 1 / (1 + math.exp(-z))


def generate(n, seed, regions=("cool", "warm", "hot"), plants=100):
    r = random.Random(seed)
    rows = []
    for i in range(n):
        reg = r.choice(regions)
        T = r.gauss(REGIONS[reg], 3.0)
        wf = min(15.0, r.lognormvariate(0.3, 0.9))
        stage = r.choice(STAGES)
        loci = [l for l in LOCI if r.random() < 0.35]
        excl = r.random() < 0.15
        recomb = r.random() < (0.45 if reg == "hot" else 0.25)
        fe = r.gauss(0, 0.3)
        p = sigmoid(true_logit(T, wf, stage, loci, excl, recomb, fe))
        k = sum(r.random() < p for _ in range(plants))
        rows.append({"region": reg, "temp_c": T, "whitefly_per_leaf": wf, "stage": stage, "loci": loci,
                     "exclusion": excl, "recombinant_pressure": recomb, "plants": plants,
                     "infected": k, "p_true": p, "incidence": k / plants})
    return rows


def all_combos():
    for n in range(len(LOCI) + 1):
        for c in itertools.combinations(LOCI, n):
            yield list(c)


def true_protection(loci, T, wf=3.0, stage="vegetative", recomb=False):
    """True relative reduction of incidence vs no resistance, at fixed environment."""
    base = sigmoid(true_logit(T, wf, stage, [], False, recomb))
    with_ = sigmoid(true_logit(T, wf, stage, loci, False, recomb))
    return 1 - with_ / base
