"""Plot results/leakage.json. Usage: python experiments/leakage_plot.py"""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
H = os.path.dirname(os.path.abspath(__file__)); R = json.load(open(os.path.join(H, "results", "leakage.json")))
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 140})
cl = R["classic"]; names = list(cl[0]["random"]); fig, ax = plt.subplots(1, 3, figsize=(11.5, 3.6), gridspec_kw={"width_ratios": [1.25, 1, 0.8]})
x = np.arange(len(names))
for off, key, col in [(-0.19, "random", "#c0392b"), (0.19, "group", "#2a9d5c")]:
    m = [np.mean([r[key][n] for r in cl]) for n in names]; s = [np.std([r[key][n] for r in cl]) for n in names]
    ax[0].bar(x + off, m, 0.36, yerr=s, color=col, capsize=3, label="Random split" if key == "random" else "Duplicate-aware split")
ax[0].axhline(0.5, color="#555", ls=":", lw=1); ax[0].set_xticks(x); ax[0].set_xticklabels(names, fontsize=8); ax[0].set(ylabel="Test accuracy", ylim=(0, 1.05), title=f"Classical learners ({len(cl)} seeds)"); ax[0].legend(fontsize=7)
cn = R["cnn"]
for i, r in enumerate(cn):
    ax[1].plot([0, 1], [r["random"]["acc"], r["group"]["acc"]], "o-", color="#4a6fa5", alpha=.8)
ax[1].axhline(0.5, color="#555", ls=":", lw=1); ax[1].set_xticks([0, 1]); ax[1].set_xticklabels(["Random split", "Duplicate-aware split"]); ax[1].set(ylim=(0, 1.05), xlim=(-0.3, 1.3), title=f"CNN, trained to convergence ({len(cn)} seeds)", ylabel="Test accuracy")
lk = [np.mean([r["leak_random"] for r in cl]), np.mean([r["leak_group"] for r in cl])]
ax[2].bar(["Random", "Group-aware"], lk, color=["#c0392b", "#2a9d5c"]); ax[2].set(ylim=(0, 1.05), title="Leak fraction", ylabel="Test images with a copy in training")
for i, v in enumerate(lk): ax[2].text(i, v + 0.02, f"{v:.2f}", ha="center", fontsize=8)
fig.suptitle("Effect of near-duplicate leakage on measured accuracy (synthetic images, chance = 0.5)")
fig.tight_layout(); fig.savefig(os.path.join(H, "figures", "leakage.png")); print("saved")
