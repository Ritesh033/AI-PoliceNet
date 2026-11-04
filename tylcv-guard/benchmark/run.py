"""Benchmark: previous approaches vs TYLCV-Guard v1 vs calibrated v2 (synthetic ground truth).

Run:  python benchmark/run.py     (needs numpy, matplotlib, scikit-learn; the app itself needs none)
"""
import json
import math
import os
import random
import sys
import time

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score, roc_curve

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import calibrate, risk, rotation, seqtools, stacking  # noqa: E402
from benchmark import simulate as sim  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(OUT, exist_ok=True)
SEED = 2026
OUTBREAK = 0.30
C = {"Temp-only": "#9a9a9a", "Whitefly-threshold": "#6b8fb5", "Env-only (T×WF)": "#4a6fa5",
     "v1 (heuristic)": "#e08a1e", "v2 (calibrated)": "#2a9d5c", "Truth": "#222222"}
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 130})
FIGS = []
METRICS = {}


def save(fig, name):
    path = os.path.join(OUT, name)
    fig.savefig(path, bbox_inches="tight")
    FIGS.append(fig)
    return path


# ------------------------------------------------------------------ models
def s_temp(r):
    return risk.temp_factor(r["temp_c"])


def s_wf(r):
    return r["whitefly_per_leaf"]


def s_env(r):
    return risk.temp_factor(r["temp_c"]) * risk.vector_factor(r["whitefly_per_leaf"])


def s_v1(r):
    prot = stacking.plan(r["loci"], r["temp_c"], r["recombinant_pressure"])["protection"]
    return risk.risk_index(r["temp_c"], r["whitefly_per_leaf"], r["stage"], prot, r["exclusion"])["index"] / 100


BASELINES = {"Temp-only": s_temp, "Whitefly-threshold": s_wf, "Env-only (T×WF)": s_env, "v1 (heuristic)": s_v1}


def fit_uni(x, n, k, iters=40):
    """Univariate binomial logistic recalibration of a raw score -> incidence."""
    X = np.column_stack([np.ones_like(x), x])
    w = np.zeros(2)
    for _ in range(iters):
        p = 1 / (1 + np.exp(-X @ w))
        g = X.T @ (k - n * p) - 1e-3 * np.r_[0, w[1]]
        H = (X * (n * p * (1 - p) + 1e-9)[:, None]).T @ X + 1e-3 * np.diag([0, 1])
        w = w + np.linalg.solve(H, g)
    return w


def predict_models(train, test):
    """Return {model: predicted incidence on test}; every model is fitted on the same training data."""
    out = {}
    n = np.array([r["plants"] for r in train], float)
    k = np.array([r["infected"] for r in train], float)
    for name, fn in BASELINES.items():
        xs = np.array([fn(r) for r in train])
        mu, sd = xs.mean(), xs.std() + 1e-9
        w = fit_uni((xs - mu) / sd, n, k)
        xt = (np.array([fn(r) for r in test]) - mu) / sd
        out[name] = 1 / (1 + np.exp(-(w[0] + w[1] * xt)))
    m = calibrate.fit(train, ridge=1.0)
    out["v2 (calibrated)"] = np.array([calibrate.predict(m, r) for r in test])
    return out, m


def metrics(pred, test):
    y = np.array([r["incidence"] >= OUTBREAK for r in test])
    inc = np.array([r["incidence"] for r in test])
    ece = 0.0
    bins = np.quantile(pred, np.linspace(0, 1, 11))
    for a, b in zip(bins[:-1], bins[1:]):
        m = (pred >= a) & (pred <= b)
        if m.any():
            ece += m.mean() * abs(pred[m].mean() - inc[m].mean())
    return {"auc": float(roc_auc_score(y, pred)), "ap": float(average_precision_score(y, pred)),
            "mae": float(np.mean(np.abs(pred - inc))), "rmse": float(np.sqrt(np.mean((pred - inc) ** 2))),
            "ece": float(ece), "r2": float(1 - np.sum((pred - inc) ** 2) / np.sum((inc - inc.mean()) ** 2))}


# ------------------------------------------------------------------ 1. risk prediction
def exp_risk():
    data = sim.generate(3600, SEED)
    r = random.Random(SEED)
    r.shuffle(data)
    train, test = data[:2400], data[2400:]
    preds, model = predict_models(train, test)
    METRICS["risk_id"] = {k: metrics(v, test) for k, v in preds.items()}
    # out-of-distribution: train on cool+warm, test on hot
    ood_train = sim.generate(2400, SEED + 1, regions=("cool", "warm"))
    ood_test = sim.generate(1200, SEED + 2, regions=("hot",))
    preds_o, _ = predict_models(ood_train, ood_test)
    METRICS["risk_ood"] = {k: metrics(v, ood_test) for k, v in preds_o.items()}
    return train, test, preds, preds_o, ood_test, model


def fig_roc_pr(test, preds, tag, title):
    y = np.array([r["incidence"] >= OUTBREAK for r in test])
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.8))
    for name, p in preds.items():
        fpr, tpr, _ = roc_curve(y, p)
        ax[0].plot(fpr, tpr, color=C[name], lw=2 if "v" in name[:2] else 1.4,
                   label=f"{name} (AUC {roc_auc_score(y, p):.3f})")
        pr, rc, _ = precision_recall_curve(y, p)
        ax[1].plot(rc, pr, color=C[name], lw=2 if "v" in name[:2] else 1.4)
    ax[0].plot([0, 1], [0, 1], ":", color="#bbb")
    ax[0].set(xlabel="False positive rate", ylabel="True positive rate", title="ROC curve")
    ax[1].set(xlabel="Recall", ylabel="Precision", title="Precision–recall curve")
    ax[0].legend(fontsize=7, loc="lower right")
    fig.suptitle(title, y=1.02)
    return save(fig, f"01_roc_pr_{tag}.png")


def fig_bars():
    fig, axes = plt.subplots(1, 4, figsize=(12, 3.3))
    for ax, (key, lab, better) in zip(axes, [("auc", "ROC-AUC", "↑"), ("ap", "Avg precision", "↑"),
                                             ("mae", "MAE (incidence)", "↓"), ("ece", "Calibration error", "↓")]):
        names = list(METRICS["risk_id"])
        x = np.arange(len(names))
        ax.bar(x - 0.2, [METRICS["risk_id"][n][key] for n in names], 0.4, color=[C[n] for n in names], label="In-distribution")
        ax.bar(x + 0.2, [METRICS["risk_ood"][n][key] for n in names], 0.4, color=[C[n] for n in names], alpha=0.45,
               hatch="//", label="Shifted (hot region)")
        ax.set_xticks(x); ax.set_xticklabels([n.split(" (")[0] for n in names], rotation=35, ha="right")
        ax.set_title(f"{lab} {better}")
    axes[0].legend(fontsize=7)
    fig.suptitle("Risk models: in-distribution vs unseen hot region (grouped bars)")
    fig.tight_layout()
    return save(fig, "02_metric_bars.png")


def fig_calibration(test, preds):
    inc = np.array([r["incidence"] for r in test])
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.8))
    ax[0].plot([0, 1], [0, 1], ":", color="#999")
    for name in ["Env-only (T×WF)", "v1 (heuristic)", "v2 (calibrated)"]:
        p = preds[name]
        edges = np.quantile(p, np.linspace(0, 1, 9))
        xs, ys = [], []
        for a, b in zip(edges[:-1], edges[1:]):
            m = (p >= a) & (p <= b)
            if m.any():
                xs.append(p[m].mean()); ys.append(inc[m].mean())
        ax[0].plot(xs, ys, "o-", color=C[name], label=name)
    ax[0].set(xlabel="Predicted incidence", ylabel="Observed incidence", title="Reliability diagram")
    ax[0].legend(fontsize=7)
    for name in ["v1 (heuristic)", "v2 (calibrated)"]:
        ax[1].scatter(preds[name], inc, s=4, alpha=0.25, color=C[name], label=name)
    ax[1].plot([0, 1], [0, 1], ":", color="#999")
    ax[1].set(xlabel="Predicted incidence", ylabel="Observed incidence", title="Predicted vs observed (scatter)")
    ax[1].legend(fontsize=7, markerscale=3)
    fig.tight_layout()
    return save(fig, "03_calibration.png")


def fig_error_box(test, preds, preds_o, ood_test):
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
    for a, (t, p, title) in zip(ax, [(test, preds, "Mixed regions (held-out)"), (ood_test, preds_o, "Hot region (unseen at training)")]):
        inc = np.array([r["incidence"] for r in t])
        names = list(p)
        data = [np.abs(p[n] - inc) for n in names]
        bp = a.boxplot(data, patch_artist=True, showfliers=False, tick_labels=[n.split(" (")[0] for n in names])
        for patch, n in zip(bp["boxes"], names):
            patch.set_facecolor(C[n]); patch.set_alpha(0.8)
        a.set(title=title, ylabel="Absolute error in incidence")
        a.tick_params(axis="x", rotation=30)
    fig.suptitle("Error distributions (box plots)")
    fig.tight_layout()
    return save(fig, "04_error_boxplots.png")


def fig_surface(model):
    Ts = np.linspace(12, 40, 57)
    Ws = np.linspace(0, 10, 51)
    def grid(fn):
        return np.array([[fn(T, w) for T in Ts] for w in Ws])
    truth = grid(lambda T, w: sim.sigmoid(sim.true_logit(T, w, "vegetative", [], False, False)))
    v1 = grid(lambda T, w: risk.risk_index(T, w, "vegetative")["index"] / 100)
    v2 = grid(lambda T, w: calibrate.predict(model, {"temp_c": T, "whitefly_per_leaf": w, "stage": "vegetative",
                                                    "loci": [], "exclusion": False, "recombinant_pressure": False}))
    fig, ax = plt.subplots(1, 3, figsize=(12, 3.6), sharey=True)
    for a, g, t in zip(ax, [truth, v1, v2], ["Ground truth (simulated)", "v1 heuristic index", "v2 calibrated"]):
        im = a.imshow(g, origin="lower", aspect="auto", extent=[Ts[0], Ts[-1], Ws[0], Ws[-1]], cmap="YlOrRd", vmin=0, vmax=1)
        a.set(title=t, xlabel="Temperature (°C)")
    ax[0].set_ylabel("Whitefly adults / leaf")
    fig.colorbar(im, ax=ax, shrink=0.85, label="Risk / incidence")
    fig.suptitle("Risk surfaces (heatmaps), susceptible cultivar, vegetative stage")
    return save(fig, "05_risk_surfaces.png")


def fig_learning_curve(test):
    sizes = [30, 60, 120, 250, 500, 1000, 2000]
    pool = sim.generate(2000, SEED + 7)
    res = {"auc": [], "mae": []}
    y = np.array([r["incidence"] >= OUTBREAK for r in test])
    inc = np.array([r["incidence"] for r in test])
    for n in sizes:
        m = calibrate.fit(pool[:n], ridge=max(1.0, 60.0 / n * 5))
        p = np.array([calibrate.predict(m, r) for r in test])
        res["auc"].append(roc_auc_score(y, p)); res["mae"].append(np.mean(np.abs(p - inc)))
    v1 = METRICS["risk_id"]["v1 (heuristic)"]
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.5))
    ax[0].plot(sizes, res["auc"], "o-", color=C["v2 (calibrated)"], label="v2 (calibrated)")
    ax[0].axhline(v1["auc"], color=C["v1 (heuristic)"], ls="--", label="v1 (heuristic, trained on 2400)")
    ax[1].plot(sizes, res["mae"], "o-", color=C["v2 (calibrated)"])
    ax[1].axhline(v1["mae"], color=C["v1 (heuristic)"], ls="--")
    for a, t in zip(ax, ["ROC-AUC ↑", "MAE ↓"]):
        a.set(xscale="log", xlabel="Number of field trials used for calibration", title=t)
    ax[0].legend(fontsize=7)
    fig.suptitle("Learning curve: v2 improves as field-trial data accumulate (gap G5)")
    fig.tight_layout()
    METRICS["learning_curve"] = {"sizes": sizes, **{k: [float(x) for x in v] for k, v in res.items()}}
    return save(fig, "06_learning_curve.png")


def fig_coefs(model):
    pairs = list(zip(model["features"], model["weights"]))[1:]
    pairs.sort(key=lambda t: t[1])
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.barh([p[0] for p in pairs], [p[1] for p in pairs], color=["#2a9d5c" if p[1] < 0 else "#d1495b" for p in pairs])
    ax.axvline(0, color="#444", lw=0.8)
    ax.set(xlabel="Logit coefficient (negative = protective)", title="v2 learned effects (feature importance)")
    return save(fig, "07_v2_coefficients.png")


# ------------------------------------------------------------------ 2. stacking planner
def exp_stacking(model):
    envs = [("Cool, no recombinants", 24, False), ("Hot, no recombinants", 34, False), ("Hot + recombinants", 34, True)]
    combos = list(sim.all_combos())
    rows, rho = [], {}
    from scipy.stats import spearmanr
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.7), sharey=True)
    for ax, (lab, T, rec) in zip(axes, envs):
        truth = np.array([sim.true_protection(c, T, recomb=rec) for c in combos])
        v1 = np.array([stacking.plan(c, T, rec)["protection"] for c in combos])
        cnt = np.array([len(c) / 5 for c in combos])
        base = lambda c: {"temp_c": T, "whitefly_per_leaf": 3.0, "stage": "vegetative", "loci": c,
                          "exclusion": False, "recombinant_pressure": rec}
        p0 = calibrate.predict(model, base([]))
        v2 = np.array([1 - calibrate.predict(model, base(c)) / p0 for c in combos])
        ax.scatter(truth, cnt, s=14, color=C["Temp-only"], alpha=0.7, label="Previous: locus count")
        ax.scatter(truth, v1, s=14, color=C["v1 (heuristic)"], alpha=0.8, label="v1 planner")
        ax.scatter(truth, v2, s=14, color=C["v2 (calibrated)"], alpha=0.8, label="v2 calibrated")
        ax.set(title=lab, xlabel="True protection")
        for name, v in [("count", cnt), ("v1", v1), ("v2", v2)]:
            rho[f"{lab}|{name}"] = float(spearmanr(truth, v)[0])
        # top-pick accuracy: best next locus
        hits = {"count": 0, "v1": 0, "v2": 0}; tot = 0
        for i, c in enumerate(combos):
            if len(c) >= 3:
                continue
            nxt = [(j, d) for j, d in enumerate(combos) if len(d) == len(c) + 1 and set(c) < set(d)]
            best = lambda arr: max(nxt, key=lambda t: arr[t[0]])[1]
            tb = best(truth)
            tot += 1
            hits["count"] += (sorted(best(cnt)) == sorted(tb))  # ties -> first
            hits["v1"] += (sorted(best(v1)) == sorted(tb))
            hits["v2"] += (sorted(best(v2)) == sorted(tb))
        for k_ in hits:
            rho[f"{lab}|top1_{k_}"] = hits[k_] / tot
    axes[0].set_ylabel("Predicted protection")
    axes[0].plot([0, 1], [0, 1], ":", color="#999")
    axes[2].legend(fontsize=7, loc="lower right")
    fig.suptitle("Stacking planner vs truth, all 32 locus combinations (scatter)")
    fig.tight_layout()
    METRICS["stacking"] = rho
    save(fig, "08_stacking_scatter.png")
    fig, ax = plt.subplots(1, 2, figsize=(9.5, 3.4))
    labs = [e[0] for e in envs]
    x = np.arange(len(labs))
    for off, (k_, col, nm) in zip([-0.27, 0, 0.27], [("count", C["Temp-only"], "Locus count (previous)"),
                                                     ("v1", C["v1 (heuristic)"], "v1"), ("v2", C["v2 (calibrated)"], "v2")]):
        ax[0].bar(x + off, [rho[f"{l}|{k_}"] for l in labs], 0.27, color=col, label=nm)
        ax[1].bar(x + off, [rho[f"{l}|top1_{k_}"] for l in labs], 0.27, color=col)
    for a, t in zip(ax, ["Rank correlation with truth (Spearman) ↑", "Correct best-next-locus pick ↑"]):
        a.set_xticks(x); a.set_xticklabels(labs, rotation=15); a.set_title(t)
    ax[0].legend(fontsize=7)
    fig.tight_layout()
    save(fig, "09_stacking_bars.png")


# ------------------------------------------------------------------ 3. recombination screen
def mutate(seq, rate, rng):
    out = list(seq)
    for i in range(len(out)):
        if rng.random() < rate:
            out[i] = rng.choice([b for b in "ACGT" if b != out[i]])
    return "".join(out)


def exp_recomb():
    """Harder regime: low parent divergence, short recombinant fragments, 1.5% query noise."""
    rng = random.Random(SEED)
    A = "".join(rng.choice("ACGT") for _ in range(2780))
    divs = [0.005, 0.01, 0.02, 0.04, 0.08, 0.16]
    lens = [100, 150, 200, 300, 450, 600]
    reps = 8
    methods = {"Best-match only (previous)": None, "v1 window screen": seqtools.recombination_screen,
               "v2 discriminative k-mers": seqtools.recombination_screen_v2}
    sens = {m: np.zeros((len(divs), len(lens))) for m in methods}
    fpr = {m: [] for m in methods}
    for i, d in enumerate(divs):
        B = mutate(A, d, rng)
        refs = {"A": A, "B": B}
        for j, L in enumerate(lens):
            hit = {m: 0 for m in methods}
            for _ in range(reps):
                s0 = rng.randint(300, len(A) - L - 300)
                q = mutate(A[:s0] + B[s0:s0 + L] + A[s0 + L:], 0.015, rng)
                for m, fn in methods.items():
                    hit[m] += bool(fn and fn(q, refs)["flag"])
            for m in methods:
                sens[m][i, j] = hit[m] / reps
        fp = {m: 0 for m in methods}; nfp = 20
        for _ in range(nfp):  # negatives: noisy copies of one parent
            q = mutate(rng.choice([A, B]), 0.015, rng)
            for m, fn in methods.items():
                fp[m] += bool(fn and fn(q, refs)["flag"])
        for m in methods:
            fpr[m].append(fp[m] / nfp)
    METRICS["recomb"] = {"mean_sensitivity": {m: float(sens[m].mean()) for m in methods},
                         "mean_fpr": {m: float(np.mean(fpr[m])) for m in methods},
                         "sens_by_divergence": {m: sens[m].mean(1).tolist() for m in methods},
                         "sens_by_length": {m: sens[m].mean(0).tolist() for m in methods},
                         "divergences": divs, "fragment_lengths": lens}
    fig, ax = plt.subplots(1, 3, figsize=(12.5, 3.8), sharey=True)
    for a, m in zip(ax, methods):
        im = a.imshow(sens[m], vmin=0, vmax=1, cmap="Greens", aspect="auto", origin="lower")
        a.set_xticks(range(len(lens))); a.set_xticklabels(lens)
        a.set_yticks(range(len(divs))); a.set_yticklabels([f"{d * 100:g}%" for d in divs])
        a.set(title=m, xlabel="Recombinant fragment length (nt)")
        for (r_, c_), v in np.ndenumerate(sens[m]):
            a.text(c_, r_, f"{v:.2f}", ha="center", va="center", fontsize=6.5, color="white" if v > 0.6 else "#333")
    ax[0].set_ylabel("Parent divergence")
    fig.colorbar(im, ax=ax, shrink=0.85, label="Sensitivity")
    fig.suptitle("Recombinant detection sensitivity (heatmaps; 8 replicates per cell)")
    save(fig, "10_recomb_heatmaps.png")
    fig, ax = plt.subplots(1, 3, figsize=(12.5, 3.4))
    mc = {"Best-match only (previous)": C["Temp-only"], "v1 window screen": C["v1 (heuristic)"], "v2 discriminative k-mers": C["v2 (calibrated)"]}
    for m in methods:
        ax[0].plot(lens, sens[m].mean(0), "o-", color=mc[m], label=m)
        ax[1].plot([d * 100 for d in divs], sens[m].mean(1), "o-", color=mc[m])
        ax[2].plot([d * 100 for d in divs], fpr[m], "s-", color=mc[m])
    ax[0].set(xlabel="Fragment length (nt)", ylabel="Sensitivity", title="Sensitivity vs fragment length")
    ax[1].set(xlabel="Parent divergence (%)", xscale="log", title="Sensitivity vs divergence")
    ax[2].set(xlabel="Parent divergence (%)", xscale="log", ylabel="False-positive rate", title="False positives (non-recombinants)")
    ax[0].legend(fontsize=7)
    fig.tight_layout()
    save(fig, "11_recomb_lines.png")


# ------------------------------------------------------------------ 4. resistance management
GROUPS = ("4A", "28", "7C", "23", "29")
KILL = 0.8  # susceptible mortality per spray; resistant individuals survive


def simulate_rotation(strategy, seed, scenario, sprays=60):
    rng = random.Random(seed)
    r = {g: rng.uniform(0.005, 0.05) for g in GROUPS}
    if scenario == "hetero":  # two groups already compromised in the field
        for g in rng.sample(GROUPS, 2):
            r[g] = rng.uniform(0.25, 0.6)
    hist, failed, rest, obs, eff_series, rr = [], set(), {}, {}, [], [dict(r)]
    for t in range(sprays):
        if strategy == "repeat":
            g = GROUPS[0]
        elif strategy == "random":
            g = rng.choice(GROUPS)
        elif strategy == "round-robin":
            g = GROUPS[t % len(GROUPS)]
        else:
            for gg in list(failed):
                rest[gg] = rest.get(gg, 0) + 1
                if rest[gg] >= 8:
                    failed.discard(gg); rest[gg] = 0
            if len(failed) >= len(GROUPS):
                failed.clear()
            kw = {"efficacy": dict(obs)} if strategy == "planner_v2" else {}
            g = rotation.plan(list(GROUPS), hist, 1, sorted(failed), **kw)["plan"][0]["moa_group"]
        eff = KILL * (1 - r[g])
        eff_series.append(eff)
        obs[g] = min(1.0, max(0.0, eff + rng.gauss(0, 0.04)))  # noisy field assessment
        if obs[g] < 0.5:
            failed.add(g)
        rg = r[g]
        r[g] = min(0.995, rg / (rg + (1 - rg) * (1 - KILL)))
        for gg in GROUPS:  # fitness cost: resistance in unsprayed groups reverts slowly
            if gg != g:
                r[gg] = max(0.005, r[gg] * 0.93)
        hist.append(g)
        rr.append(dict(r))
    return eff_series, rr


def exp_rotation():
    strategies = {"repeat": "Single group repeated (previous)", "random": "Random group", "round-robin": "Fixed round-robin",
                  "planner": "Planner v1 (failure-aware)", "planner_v2": "Planner v2 (efficacy-adaptive)"}
    cols = {"repeat": C["Temp-only"], "random": C["Whitefly-threshold"], "round-robin": C["Env-only (T×WF)"],
            "planner": C["v1 (heuristic)"], "planner_v2": C["v2 (calibrated)"]}
    scenarios = {"uniform": "Uniform low resistance", "hetero": "Two groups already compromised"}
    METRICS["rotation"] = {}
    fig, ax = plt.subplots(2, 2, figsize=(11, 6.4))
    for row, (sc, sc_lab) in enumerate(scenarios.items()):
        series = {s: [simulate_rotation(s, seed, sc)[0] for seed in range(100)] for s in strategies}
        METRICS["rotation"][sc] = {s: {"mean_efficacy": float(np.mean(series[s])),
                                       "sprays_below_50pct": float(np.mean(np.array(series[s]) < 0.5) * 60)} for s in strategies}
        for s, lab in strategies.items():
            arr = np.array(series[s])
            ax[row, 0].plot(arr.mean(0), color=cols[s], label=lab, lw=1.8)
            ax[row, 0].fill_between(range(60), np.percentile(arr, 10, 0), np.percentile(arr, 90, 0), color=cols[s], alpha=0.08)
        ax[row, 0].set(title=f"{sc_lab}: efficacy per spray (mean, 10–90% band)", xlabel="Spray number", ylabel="Efficacy", ylim=(0, 0.85))
        ax[row, 1].bar(range(5), [METRICS["rotation"][sc][s]["mean_efficacy"] for s in strategies], color=[cols[s] for s in strategies])
        ax[row, 1].set_xticks(range(5)); ax[row, 1].set_xticklabels(["Repeat", "Random", "Round-\nrobin", "Planner\nv1", "Planner\nv2"])
        ax[row, 1].set(title="Mean efficacy ↑", ylim=(0, 0.85))
    ax[0, 0].legend(fontsize=6.5)
    fig.tight_layout()
    save(fig, "12_rotation_efficacy.png")
    fig, ax = plt.subplots(1, 5, figsize=(15, 2.9), sharey=True)
    for a, s in zip(ax, strategies):
        _, rr = simulate_rotation(s, 3, "hetero")
        mat = np.array([[st[x] for st in rr] for x in GROUPS])
        im = a.imshow(mat, aspect="auto", cmap="magma_r", vmin=0, vmax=1)
        a.set_yticks(range(5)); a.set_yticklabels(GROUPS); a.set(title=strategies[s].split(" (")[0], xlabel="Spray")
    fig.colorbar(im, ax=ax, shrink=0.8, label="Resistance frequency")
    fig.suptitle("Resistance allele frequency by MoA group (heatmaps, one replicate, two groups pre-compromised)")
    save(fig, "13_rotation_heatmaps.png")


# ------------------------------------------------------------------ 5. seed-lot rule of three
def exp_seed():
    prev = np.logspace(-3.5, -1.3, 80)
    fig, ax = plt.subplots(figsize=(6, 3.6))
    for n, col in zip([100, 300, 1000], ["#6b8fb5", "#e08a1e", "#2a9d5c"]):
        ax.plot(prev * 100, (1 - prev) ** n, color=col, label=f"n={n} (bound {300 / n:.2f}%)")
        ax.axvline(300 / n, color=col, ls=":", lw=0.8)
    ax.axhline(0.05, color="#444", ls="--", lw=0.8)
    ax.set(xscale="log", xlabel="True seed prevalence (%)", ylabel="P(no positives in sample)",
           title="Rule of three: false-assurance risk (analytic)")
    ax.legend(fontsize=7)
    METRICS["seed_rule_of_three"] = {str(n): float((1 - 3 / n) ** n) for n in [100, 300, 1000]}
    save(fig, "14_seed_rule_of_three.png")


# ------------------------------------------------------------------ 6. summary radar + table
def fig_summary():
    prev_risk = METRICS["risk_id"]["Temp-only"]
    v1 = METRICS["risk_id"]["v1 (heuristic)"]; v2 = METRICS["risk_id"]["v2 (calibrated)"]
    ood = METRICS["risk_ood"]
    st = METRICS["stacking"]; rc = METRICS["recomb"]; ro = METRICS["rotation"]
    avg = lambda key: float(np.mean([st[f"{e}|{key}"] for e in ["Cool, no recombinants", "Hot, no recombinants", "Hot + recombinants"]]))
    axes = ["Outbreak AUC", "Calibration\n(1−ECE×5)", "Shift robustness\n(AUC hot region)", "Stacking\nrank corr.",
            "Recombinant\nsensitivity", "Resistance-mgmt\nefficacy (rel. to max)"]
    prev = [prev_risk["auc"], 1 - 5 * prev_risk["ece"], ood["Temp-only"]["auc"], max(0, avg("count")),
            rc["mean_sensitivity"]["Best-match only (previous)"], ro["hetero"]["repeat"]["mean_efficacy"] / 0.8]
    m1 = [v1["auc"], 1 - 5 * v1["ece"], ood["v1 (heuristic)"]["auc"], avg("v1"),
          rc["mean_sensitivity"]["v1 window screen"], ro["hetero"]["planner"]["mean_efficacy"] / 0.8]
    m2 = [v2["auc"], 1 - 5 * v2["ece"], ood["v2 (calibrated)"]["auc"], avg("v2"),
          rc["mean_sensitivity"]["v2 discriminative k-mers"], ro["hetero"]["planner_v2"]["mean_efficacy"] / 0.8]
    ang = np.linspace(0, 2 * np.pi, len(axes), endpoint=False).tolist(); ang += ang[:1]
    fig = plt.figure(figsize=(6.2, 6))
    ax = plt.subplot(111, polar=True)
    for vals, col, lab in [(prev, C["Temp-only"], "Previous (baselines)"), (m1, C["v1 (heuristic)"], "Current v1"), (m2, C["v2 (calibrated)"], "Improved v2")]:
        v = [max(0, min(1, x)) for x in vals] + [max(0, min(1, vals[0]))]
        ax.plot(ang, v, color=col, lw=2, label=lab); ax.fill(ang, v, color=col, alpha=0.1)
    ax.set_xticks(ang[:-1]); ax.set_xticklabels(axes, fontsize=8); ax.set_ylim(0, 1)
    ax.set_title("Overall comparison (radar chart, higher is better)", y=1.1)
    ax.legend(loc="lower right", bbox_to_anchor=(1.25, -0.05), fontsize=8)
    METRICS["radar"] = {"axes": axes, "previous": prev, "v1": m1, "v2": m2}
    save(fig, "15_summary_radar.png")


def write_report():
    r = METRICS
    def row(n):
        a, b = r["risk_id"][n], r["risk_ood"][n]
        return f"| {n} | {a['auc']:.3f} | {a['ap']:.3f} | {a['mae']:.3f} | {a['ece']:.3f} | {b['auc']:.3f} | {b['mae']:.3f} |"
    lines = ["# TYLCV-Guard benchmark report", "",
             "**All results come from SYNTHETIC ground truth, not field data.** They show how the models behave under an assumed",
             "generating process, and which components are worth keeping; they do not prove real-world accuracy.", "",
             "## Risk prediction (outbreak = incidence ≥ 30%)", "",
             "| Model | AUC | Avg precision | MAE | ECE | AUC (hot, unseen) | MAE (hot, unseen) |", "|---|---|---|---|---|---|---|"]
    lines += [row(n) for n in r["risk_id"]]
    lines += ["", "## Stacking planner (Spearman vs true protection / best-next-locus accuracy)", ""]
    for env in ["Cool, no recombinants", "Hot, no recombinants", "Hot + recombinants"]:
        s = r["stacking"]
        lines.append(f"- {env}: count {s[env + '|count']:.2f}/{s[env + '|top1_count']:.2f}, v1 {s[env + '|v1']:.2f}/{s[env + '|top1_v1']:.2f}, v2 {s[env + '|v2']:.2f}/{s[env + '|top1_v2']:.2f}")
    rc = r["recomb"]
    lines += ["", "## Recombinant screen", "", "| Method | Mean sensitivity | Mean false-positive rate |", "|---|---|---|"]
    for m in rc["mean_sensitivity"]:
        lines.append(f"| {m} | {rc['mean_sensitivity'][m]:.2f} | {rc['mean_fpr'][m]:.2f} |")
    lines += ["", "## Resistance management (toy population-genetics model, 100 replicates x 60 sprays)", ""]
    for sc, d in r["rotation"].items():
        lines += [f"**Scenario: {sc}**", "", "| Strategy | Mean efficacy | Sprays below 50% efficacy (of 60) |", "|---|---|---|"]
        lines += [f"| {k} | {v['mean_efficacy']:.3f} | {v['sprays_below_50pct']:.1f} |" for k, v in d.items()]
        lines.append("")
    lines += ["", "Figures: see `results/*.png` and `results/benchmark_report.pdf`."]
    open(os.path.join(OUT, "REPORT.md"), "w").write("\n".join(lines) + "\n")


def main():
    t0 = time.time()
    train, test, preds, preds_o, ood_test, model = exp_risk()
    fig_roc_pr(test, preds, "id", "Outbreak classification: mixed regions (held-out 1,200 fields)")
    fig_roc_pr(ood_test, preds_o, "ood", "Outbreak classification: hot region unseen during training")
    fig_bars(); fig_calibration(test, preds); fig_error_box(test, preds, preds_o, ood_test)
    fig_surface(model); fig_learning_curve(test); fig_coefs(model)
    exp_stacking(model); exp_recomb(); exp_rotation(); exp_seed(); fig_summary()
    json.dump(METRICS, open(os.path.join(OUT, "metrics.json"), "w"), indent=1)
    write_report()
    with PdfPages(os.path.join(OUT, "benchmark_report.pdf")) as pdf:
        for f in FIGS:
            pdf.savefig(f, bbox_inches="tight")
    print("done in %.0fs" % (time.time() - t0))


if __name__ == "__main__":
    main()
