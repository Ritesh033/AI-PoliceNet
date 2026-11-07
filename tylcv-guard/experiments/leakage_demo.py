"""Controlled leakage experiment on SYNTHETIC leaf images.

Each base image has several near-duplicate variants (brightness, shift, recompression, rescale). The same small CNN is trained with
(a) a random image-level split and (b) the duplicate-aware group split of dl.data. The gap in test accuracy shows how much a random
split can inflate results when near-duplicates exist. Synthetic data: this demonstrates the mechanism, not field accuracy.
Usage: python experiments/leakage_demo.py [--seeds 5]"""
import argparse, json, os, random, shutil, sys, tempfile, time
import numpy as np, torch, torch.nn as nn
from PIL import Image, ImageDraw, ImageEnhance
from sklearn.metrics import roc_auc_score
from torch.utils.data import DataLoader
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from dl import data as D, model as MD

SIZE = 64


def make_base(rng, cls, delta):
    bg = tuple(rng.randint(40, 200) for _ in range(3))
    im = Image.new("RGB", (SIZE, SIZE), bg); d = ImageDraw.Draw(im)
    for _ in range(rng.randint(3, 8)):          # background clutter
        x, y = rng.randint(0, SIZE), rng.randint(0, SIZE)
        d.ellipse((x, y, x + rng.randint(6, 22), y + rng.randint(6, 22)), fill=tuple(rng.randint(30, 210) for _ in range(3)))
    base = np.array([60, 130, 50]) + rng.gauss(0, 28) + (np.array([delta, delta * 0.8, 0]) if cls else 0)
    col = tuple(int(np.clip(v + rng.gauss(0, 16), 0, 255)) for v in base)
    x0, y0 = rng.randint(2, 14), rng.randint(2, 14); x1, y1 = SIZE - rng.randint(2, 14), SIZE - rng.randint(2, 14)
    d.ellipse((x0, y0, x1, y1), fill=col)
    for _ in range(rng.randint(2, 6)):
        d.line((rng.randint(x0, x1), rng.randint(y0, y1), rng.randint(x0, x1), rng.randint(y0, y1)), fill=tuple(max(0, c - 40) for c in col), width=1)
    return im


def variants(im, rng, n):
    out = [im]
    for _ in range(n - 1):
        v = ImageEnhance.Brightness(im).enhance(rng.uniform(0.93, 1.07))
        v = v.transform(v.size, Image.AFFINE, (1, 0, rng.randint(-1, 1), 0, 1, rng.randint(-1, 1)), fillcolor=(120, 120, 120))
        s = rng.choice([56, 72]); v = v.resize((s, s)).resize((SIZE, SIZE))
        out.append(v)
    return out


def build(root, n_base, n_var, delta, seed):
    rng = random.Random(seed)
    for cname, cls in (("Tomato___healthy", 0), ("Tomato___Tomato_Yellow_Leaf_Curl_Virus", 1)):
        os.makedirs(os.path.join(root, cname), exist_ok=True)
        for i in range(n_base):
            for j, v in enumerate(variants(make_base(rng, cls, delta), rng, n_var)):
                v.save(os.path.join(root, cname, f"{i:03d}_{j}.jpg"), quality=90)


def run(items_split, seed, epochs):
    torch.manual_seed(seed); np.random.seed(seed); random.seed(seed)
    mk = lambda it, tr: DataLoader(D.LeafDataset(it, SIZE, False), batch_size=16, shuffle=tr, num_workers=0)  # no augmentation: isolates the split effect
    tr, va, te = mk(items_split["train"], True), mk(items_split["val"], False), mk(items_split["test"], False)
    model, _ = MD.build_model("mobilenet_v3_small", pretrained=False)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=0); crit = nn.CrossEntropyLoss()
    best, state = -1, None
    def probs(dl):
        model.eval(); ps, ys = [], []
        with torch.no_grad():
            for x, y in dl: ps.append(torch.softmax(model(x), 1)[:, 1]); ys.append(y)
        return torch.cat(ps).numpy(), torch.cat(ys).numpy()
    for ep in range(epochs):
        model.train()
        for x, y in tr:
            opt.zero_grad(); crit(model(x), y).backward(); opt.step()
    # last-epoch weights: the network is trained to (near) convergence on the training split
    p, y = probs(te)
    return {"acc": float(np.mean((p >= 0.5) == y)), "auc": float(roc_auc_score(y, p)), "n_test": int(len(y))}


def pixels(items, n=16):
    X = np.array([np.asarray(Image.open(p).convert("RGB").resize((n, n)), dtype=float).ravel() / 255 for p, _l, _c in items]); y = np.array([l for _p, l, _c in items])
    return X, y


def run_classic(sp):
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.linear_model import LogisticRegression
    Xtr, ytr = pixels(sp["train"]); Xte, yte = pixels(sp["test"]); out = {}
    for name, clf in (("1-NN (pixels)", KNeighborsClassifier(1)), ("5-NN (pixels)", KNeighborsClassifier(5)), ("Logistic (pixels)", LogisticRegression(C=10, max_iter=2000))):
        out[name] = float(clf.fit(Xtr, ytr).score(Xte, yte))
    return out


def random_split(items, seed, fr=(0.7, 0.15, 0.15)):
    r = random.Random(seed); idx = list(range(len(items))); r.shuffle(idx)
    a, b = int(fr[0] * len(idx)), int((fr[0] + fr[1]) * len(idx))
    return {"train": [items[i] for i in idx[:a]], "val": [items[i] for i in idx[a:b]], "test": [items[i] for i in idx[b:]]}


def leak_fraction(sp):
    """Share of test images that have a near-duplicate (same base id) in the training set."""
    base = lambda p: (os.path.basename(os.path.dirname(p)), os.path.basename(p).split("_")[0])
    tr = {base(p) for p, _l, _c in sp["train"]}
    return float(np.mean([base(p) in tr for p, _l, _c in sp["test"]]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seeds", type=int, default=3); ap.add_argument("--epochs", type=int, default=50)
    ap.add_argument("--base", type=int, default=70); ap.add_argument("--var", type=int, default=4); ap.add_argument("--delta", type=float, default=16)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "leakage.json"))
    ap.add_argument("--classic-seeds", type=int, default=20)
    a = ap.parse_args(); res = {"cnn": [], "classic": []}
    for s in range(max(a.seeds, a.classic_seeds)):
        root = tempfile.mkdtemp(); t0 = time.time()
        build(root, a.base, a.var, a.delta, 100 + s)
        items = D.scan_folder(root)
        rs = random_split(items, s); gs = D.group_split(items, seed=s, max_hamming=20)
        if s < a.classic_seeds:
            res["classic"].append({"seed": s, "random": run_classic(rs), "group": run_classic(gs), "leak_random": leak_fraction(rs), "leak_group": leak_fraction(gs)})
            json.dump(res, open(a.out, "w"), indent=1)
        if s < a.seeds:
            r = {"seed": s, "random": run(rs, s, a.epochs), "group": run(gs, s, a.epochs), "leak_random": leak_fraction(rs), "leak_group": leak_fraction(gs), "n_images": len(items)}
            res["cnn"].append(r); print(json.dumps(r), f"{time.time() - t0:.0f}s", flush=True)
            json.dump(res, open(a.out, "w"), indent=1)
        shutil.rmtree(root)
