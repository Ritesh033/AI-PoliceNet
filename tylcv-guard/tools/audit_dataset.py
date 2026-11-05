"""Audit an image folder: sizes, sources, exact/near duplicates (average hash), blur.

Usage: python -I tools/audit_dataset.py <image_dir> [report.json]
Needs Pillow and numpy. Never executes anything from the dataset; only reads image files.
"""
import collections, hashlib, json, os, re, sys
import numpy as np
from PIL import Image


def ahash(im, n=16):
    a = np.asarray(im.convert("L").resize((n, n)), dtype=float)
    return (a > a.mean()).flatten()


def blur_score(im):
    g = np.asarray(im.convert("L").resize((256, 256)), dtype=float)
    lap = g[1:-1, 1:-1] * 4 - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:]
    return float(lap.var())


def source_of(name, size):
    if re.search(r"YLCV", name, re.I):
        return "PlantVillage-style filename"
    if re.match(r"IMG\d{8}", name):
        return "phone camera (IMG<date>)"
    if re.match(r"\d{13}", name):
        return "timestamp filename (likely field photo)"
    return "other"


def main(d, out=None):
    files = sorted(f for f in os.listdir(d) if f.lower().endswith((".jpg", ".jpeg", ".png")))
    rows, md5, hashes = [], collections.defaultdict(list), {}
    for f in files:
        p = os.path.join(d, f)
        md5[hashlib.md5(open(p, "rb").read()).hexdigest()].append(f)
        im = Image.open(p); im.load()
        hashes[f] = ahash(im)
        rows.append({"file": f, "w": im.size[0], "h": im.size[1], "blur": blur_score(im), "source": source_of(f, im.size)})
    near = []
    names = list(hashes)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            dist = int((hashes[a] != hashes[b]).sum())
            if dist <= 12:  # of 256 bits
                near.append({"a": a, "b": b, "hamming": dist})
    blurs = np.array([r["blur"] for r in rows])
    rep = {"n_images": len(rows),
           "dimensions": {f"{w}x{h}": c for (w, h), c in collections.Counter((r["w"], r["h"]) for r in rows).items()},
           "sources": dict(collections.Counter(r["source"] for r in rows)),
           "exact_duplicates": [v for v in md5.values() if len(v) > 1],
           "near_duplicate_pairs": near,
           "blur_variance": {"median": float(np.median(blurs)), "p10": float(np.percentile(blurs, 10)),
                             "blurriest": [r["file"] for r in sorted(rows, key=lambda r: r["blur"])[:5]]},
           "labels_present": False,
           "notes": ["Folder has images only: no labels, no healthy/negative class, so accuracy cannot be computed.",
                     "256x256 PlantVillage-style files may overlap with public datasets used to train other models (leakage risk)."]}
    print(json.dumps(rep, indent=1))
    if out:
        json.dump(rep, open(out, "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
