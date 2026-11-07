"""Extra analyses on the SIMULATED benchmark: bootstrap CIs, observation-noise and training-size sensitivity, cost-based thresholds.
Usage (from tylcv-guard/): python -m experiments.sensitivity"""
import json, os, random, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from benchmark import run as R, simulate as sim
from app import calibrate

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures"); RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
os.makedirs(OUT, exist_ok=True); os.makedirs(RES, exist_ok=True)
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 140})
C = R.C; out = {}
def outbreak(rows): return np.array([r["incidence"] >= R.OUTBREAK for r in rows])

# ---- 1. bootstrap CI of AUC and of the v2-v1 difference
data = sim.generate(3600, 2026); random.Random(2026).shuffle(data); train, test = data[:2400], data[2400:]
preds, model = R.predict_models(train, test); y = outbreak(test); rng = np.random.RandomState(0)
names = ["Temp-only", "Whitefly-threshold", "Env-only (T×WF)", "v1 (heuristic)", "v2 (calibrated)"]
boot = {n: [] for n in names}; diff = []
for _ in range(1000):
    i = rng.randint(0, len(y), len(y))
    if len(set(y[i])) < 2: continue
    for n in names: boot[n].append(roc_auc_score(y[i], preds[n][i]))
    diff.append(boot["v2 (calibrated)"][-1] - boot["v1 (heuristic)"][-1])
ci = {n: [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5)), float(np.mean(b))] for n, b in boot.items()}
out["auc_ci"] = ci; out["v2_minus_v1_auc"] = [float(np.percentile(diff, 2.5)), float(np.percentile(diff, 97.5)), float(np.mean(diff))]
fig, ax = plt.subplots(figsize=(6.2, 3.4))
for k, n in enumerate(names):
    lo, hi, m = ci[n]; ax.errorbar(m, k, xerr=[[m - lo], [hi - m]], fmt="o", color=C[n], capsize=4)
ax.set_yticks(range(len(names))); ax.set_yticklabels(names); ax.set(xlabel="ROC-AUC (bootstrap mean and 95% interval, 1000 resamples)", title="Uncertainty of the AUC estimates"); ax.invert_yaxis()
fig.tight_layout(); fig.savefig(os.path.join(OUT, "s1_auc_ci.png")); plt.close(fig)

# ---- 2. observation noise: plants scored per field
ns = [10, 25, 50, 100, 200]; res = {n: {k: [] for k in ["Env-only (T×WF)", "v1 (heuristic)", "v2 (calibrated)"]} for n in ns}
for plants in ns:
    for seed in range(3):
        d = sim.generate(1800, 700 + seed, plants=plants); random.Random(seed).shuffle(d); tr, te = d[:1200], d[1200:]
        p, _m = R.predict_models(tr, te); yy = outbreak(te)
        for k in res[plants]:
            if len(set(yy)) == 2: res[plants][k].append(roc_auc_score(yy, p[k]))
out["noise"] = {str(n): {k: [float(np.mean(v)), float(np.std(v))] for k, v in res[n].items()} for n in ns}
fig, ax = plt.subplots(figsize=(5.6, 3.5))
for k in ["Env-only (T×WF)", "v1 (heuristic)", "v2 (calibrated)"]:
    m = np.array([np.mean(res[n][k]) for n in ns]); s = np.array([np.std(res[n][k]) for n in ns])
    ax.plot(ns, m, "o-", color=C[k], label=k); ax.fill_between(ns, m - s, m + s, color=C[k], alpha=.15)
ax.set(xscale="log", xlabel="Plants scored per field (observation noise falls →)", ylabel="ROC-AUC", title="Sensitivity to observation noise (3 seeds)"); ax.legend(fontsize=7)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "s2_noise.png")); plt.close(fig)

# ---- 3. training size, 5 seeds, AUC and ECE
sizes = [30, 60, 120, 250, 500, 1000]; auc = {s: [] for s in sizes}; ece = {s: [] for s in sizes}
for seed in range(5):
    pool = sim.generate(1000, 900 + seed); tt = sim.generate(800, 950 + seed); yy = outbreak(tt); inc = np.array([r["incidence"] for r in tt])
    for s in sizes:
        m = calibrate.fit(pool[:s], ridge=max(1.0, 300.0 / s)); p = np.array([calibrate.predict(m, r) for r in tt])
        auc[s].append(roc_auc_score(yy, p)); ece[s].append(R.metrics(p, tt)["ece"])
out["train_size"] = {str(s): {"auc": [float(np.mean(auc[s])), float(np.std(auc[s]))], "ece": [float(np.mean(ece[s])), float(np.std(ece[s]))]} for s in sizes}
fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
for a, (d_, t_, yl) in zip(ax, [(auc, "ROC-AUC", "AUC"), (ece, "Calibration error", "ECE")]):
    m = np.array([np.mean(d_[s]) for s in sizes]); sd = np.array([np.std(d_[s]) for s in sizes])
    a.errorbar(sizes, m, yerr=sd, fmt="o-", color=C["v2 (calibrated)"], capsize=3); a.set(xscale="log", xlabel="Training fields", ylabel=yl, title=t_ + " of v2 vs training size (5 seeds)")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "s3_train_size.png")); plt.close(fig)

# ---- 4. cost-weighted threshold analysis on v2
p = preds["v2 (calibrated)"]; thr = np.linspace(0.02, 0.9, 89); costs = {}
fig, ax = plt.subplots(1, 2, figsize=(9.2, 3.5))
for cfn in [1, 3, 10]:
    ec = [(cfn * np.sum((p < t) & y) + np.sum((p >= t) & ~y)) / len(y) for t in thr]; costs[cfn] = (float(thr[int(np.argmin(ec))]), float(np.min(ec)))
    ax[0].plot(thr, ec, label=f"FN cost = {cfn}× FP cost"); ax[0].plot(thr[int(np.argmin(ec))], np.min(ec), "ko", ms=4)
ax[0].set(xlabel="Decision threshold on predicted incidence", ylabel="Expected cost per field", title="Cost-based threshold choice (v2)"); ax[0].legend(fontsize=7)
sens = [np.mean(p[y] >= t) for t in thr]; spec = [np.mean(p[~y] < t) for t in thr]
ax[1].plot(thr, sens, color="#c0392b", label="Sensitivity"); ax[1].plot(thr, spec, color="#2a9d5c", label="Specificity"); ax[1].set(xlabel="Threshold", title="Sensitivity and specificity vs threshold"); ax[1].legend(fontsize=7)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "s4_threshold.png")); plt.close(fig)
out["cost_thresholds"] = {str(k): v for k, v in costs.items()}
json.dump(out, open(os.path.join(RES, "sensitivity.json"), "w"), indent=1); print(json.dumps(out, indent=1)[:1500])
