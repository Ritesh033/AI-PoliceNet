"""Descriptive analysis of an image folder (no labels needed): source groups, colour/sharpness statistics, PCA, hash distances,
sample photo grids. Usage: python -I experiments/data_analysis.py <image_dir> <out_dir>
Reads image files only; never executes anything from the folder."""
import json, os, re, sys
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

d, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 140})
files = sorted(f for f in os.listdir(d) if f.lower().endswith((".jpg", ".jpeg", ".png")))

def source(name):
    if re.search(r"YLCV", name, re.I): return "Lab-style (PlantVillage-type)"
    if re.match(r"IMG\d{8}", name): return "Phone photo"
    return "Field photo"
COL = {"Lab-style (PlantVillage-type)": "#8a8a8a", "Phone photo": "#2a9d5c", "Field photo": "#e08a1e"}

def feats(path):
    im = Image.open(path).convert("RGB"); W, H = im.size
    sm = im.resize((128, 128)); a = np.asarray(sm, float) / 255
    hsv = np.asarray(sm.convert("HSV"), float) / 255
    g = np.asarray(sm.convert("L"), float)
    lap = g[1:-1, 1:-1] * 4 - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:]
    ring = np.ones((128, 128), bool); ring[16:-16, 16:-16] = False
    leaf = hsv[..., 1] > 0.30                       # saturated pixels ~ leaf tissue
    cov = float(leaf.mean())
    yel = float(((a[..., 0] + a[..., 1]) / 2 - a[..., 2])[leaf].mean()) if leaf.any() else 0.0
    return {"w": W, "h": H, "mean_r": a[..., 0].mean(), "mean_g": a[..., 1].mean(), "mean_b": a[..., 2].mean(),
            "sat": hsv[..., 1].mean(), "val": hsv[..., 2].mean(), "border_val": float(hsv[..., 2][ring].mean()),
            "border_sat": float(hsv[..., 1][ring].mean()), "coverage": cov, "yellowness": yel,
            "sharp": float(lap.var()), "kb": os.path.getsize(path) / 1024}, sm

rows, thumbs = [], []
for f in files:
    r, sm = feats(os.path.join(d, f)); r["file"] = f; r["source"] = source(f); rows.append(r); thumbs.append(sm)
src = np.array([r["source"] for r in rows])
summary = {s: {k: float(np.mean([r[k] for r in rows if r["source"] == s])) for k in ["w", "h", "sat", "border_val", "coverage", "yellowness", "sharp", "kb"]}
           | {"n": int((src == s).sum())} for s in COL}
json.dump(summary, open(os.path.join(out, "source_summary.json"), "w"), indent=1)

# Fig A: sample photo grid per source
def grid(names, title, fn, cols=6):
    n = len(names); rws = (n + cols - 1) // cols
    fig, ax = plt.subplots(rws, cols, figsize=(cols * 1.7, rws * 1.9))
    ax = np.atleast_2d(ax)
    for a in ax.ravel(): a.axis("off")
    for i, nm in enumerate(names):
        k = files.index(nm); a = ax.ravel()[i]; a.imshow(thumbs[k]); a.set_title(f"{rows[k]['w']}×{rows[k]['h']}", fontsize=7)
    fig.suptitle(title, fontsize=10); fig.tight_layout(); fig.savefig(os.path.join(out, fn)); plt.close(fig)
lab = [r["file"] for r in rows if r["source"].startswith("Lab")]
ph = [r["file"] for r in rows if r["source"] == "Phone photo"]
fd = [r["file"] for r in rows if r["source"] == "Field photo"]
grid(lab[:12], "Lab-style images (256×256, plain background)", "photos_lab.png")
grid(ph + fd, "Phone photos (7) and field photos (2)", "photos_phone_field.png", cols=5)

# Fig B: colour / sharpness distributions by source
fig, ax = plt.subplots(2, 3, figsize=(10, 5.6))
for a, (k, t) in zip(ax.ravel(), [("yellowness", "Leaf yellowness index"), ("coverage", "Leaf coverage fraction"), ("sharp", "Sharpness (Laplacian variance)"),
                                  ("border_val", "Background brightness (border ring)"), ("sat", "Mean saturation"), ("kb", "File size (KB)")]):
    data = [[r[k] for r in rows if r["source"] == s] for s in COL]
    bp = a.boxplot(data, patch_artist=True, tick_labels=["Lab", "Phone", "Field"], showfliers=True)
    for p, s in zip(bp["boxes"], COL): p.set_facecolor(COL[s]); p.set_alpha(0.7)
    for i, (dd, s) in enumerate(zip(data, COL)): a.scatter(np.full(len(dd), i + 1) + np.random.RandomState(1).uniform(-.12, .12, len(dd)), dd, s=8, color="#222", alpha=.5, zorder=3)
    a.set_title(t, fontsize=9)
fig.suptitle("Low-level image statistics by source group (box plots with individual images)"); fig.tight_layout(); fig.savefig(os.path.join(out, "stats_boxplots.png")); plt.close(fig)

# Fig C: PCA of standardised features, coloured by source
keys = ["mean_r", "mean_g", "mean_b", "sat", "val", "border_val", "border_sat", "coverage", "yellowness", "sharp"]
X = StandardScaler().fit_transform(np.array([[r[k] for k in keys] for r in rows]))
pca = PCA(2).fit(X); Z = pca.transform(X)
fig, ax = plt.subplots(figsize=(5.2, 4.2))
for s in COL:
    m = src == s; ax.scatter(Z[m, 0], Z[m, 1], s=28, color=COL[s], label=f"{s} (n={m.sum()})", alpha=.85, edgecolor="#333", linewidth=.3)
ax.set(xlabel=f"PC1 ({pca.explained_variance_ratio_[0] * 100:.0f}%)", ylabel=f"PC2 ({pca.explained_variance_ratio_[1] * 100:.0f}%)", title="PCA of low-level image features")
ax.legend(fontsize=7); fig.tight_layout(); fig.savefig(os.path.join(out, "pca_sources.png")); plt.close(fig)

# Fig D: average-hash distance distribution + similarity heatmap
def ah(path):
    im = Image.open(path).convert("L").resize((16, 16)); a = np.asarray(im, float); return (a > a.mean()).flatten()
H = np.array([ah(os.path.join(d, f)) for f in files])
D = (H[:, None, :] != H[None, :, :]).sum(-1)
iu = np.triu_indices(len(files), 1); dist = D[iu]
fig, ax = plt.subplots(1, 2, figsize=(9.4, 3.8), gridspec_kw={"width_ratios": [1.1, 1]})
ax[0].hist(dist, bins=40, color="#4a6fa5"); ax[0].axvline(12, color="#c0392b", ls="--", label="duplicate threshold (12 bits)")
ax[0].set(xlabel="Hamming distance between 16×16 average hashes (bits)", ylabel="Image pairs", title="Pairwise hash distances"); ax[0].legend(fontsize=7)
order = np.argsort(src, kind="stable"); im = ax[1].imshow(D[np.ix_(order, order)], cmap="viridis_r"); ax[1].set_title("Hash-distance matrix (sorted by source)")
fig.colorbar(im, ax=ax[1], shrink=.8, label="bits"); fig.tight_layout(); fig.savefig(os.path.join(out, "hash_distances.png")); plt.close(fig)
pairs = [(files[i], files[j], int(D[i, j])) for i, j in zip(*iu) if D[i, j] <= 12]
json.dump({"pairs": pairs, "n_pairs_total": int(len(dist)), "min_nonduplicate": int(np.sort(dist[dist > 12])[0])}, open(os.path.join(out, "duplicates.json"), "w"), indent=1)
# Fig E: duplicate pairs side by side
if pairs:
    fig, ax = plt.subplots(len(pairs), 2, figsize=(4.4, 2.3 * len(pairs)))
    ax = np.atleast_2d(ax)
    for r_, (a, b, dd) in enumerate(pairs):
        for c_, nm in enumerate((a, b)):
            k = files.index(nm); ax[r_, c_].imshow(thumbs[k]); ax[r_, c_].axis("off"); ax[r_, c_].set_title(f"{rows[k]['w']}×{rows[k]['h']}", fontsize=7)
        ax[r_, 0].text(-0.1, 0.5, f"{dd} bits", transform=ax[r_, 0].transAxes, rotation=90, va="center", ha="right", fontsize=8)
    fig.suptitle("Near-duplicate pairs (same photograph, two resolutions)", fontsize=9); fig.tight_layout(); fig.savefig(os.path.join(out, "dup_pairs.png")); plt.close(fig)
json.dump(rows, open(os.path.join(out, "features.json"), "w"), indent=0, default=float)
print(json.dumps(summary, indent=1)[:900]); print("pairs", pairs)
