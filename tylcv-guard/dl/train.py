"""Train and evaluate a TYLCV leaf-image classifier (binary: tylcv vs not_tylcv).

Example:
  python -m dl.train --data /path/to/plantvillage_tomato --arch mobilenet_v3_small --epochs 12 --out runs/exp1 \
         --external "/path/to/field_photos" --external-label 1
Data layout: one sub-folder per class (e.g. Tomato___healthy, Tomato___Tomato_Yellow_Leaf_Curl_Virus, ...).
Folders whose name matches yellow-leaf-curl/YLCV are positives; every other folder is a negative.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import random
import time

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import (average_precision_score, confusion_matrix, f1_score, precision_score,
                             recall_score, roc_auc_score, roc_curve, precision_recall_curve)
from torch.utils.data import DataLoader

from . import data as D
from . import model as MD


def seed_all(s):
    random.seed(s); np.random.seed(s); torch.manual_seed(s)


@torch.no_grad()
def logits_of(model, loader, device):
    model.eval()
    out, ys = [], []
    for x, y in loader:
        out.append(model(x.to(device)).cpu()); ys.append(y)
    return torch.cat(out), torch.cat(ys)


def fit_temperature(logits, y):
    """Single-parameter temperature scaling on validation logits."""
    t = torch.ones(1, requires_grad=True)
    opt = torch.optim.LBFGS([t], lr=0.1, max_iter=50)
    ce = nn.CrossEntropyLoss()

    def closure():
        opt.zero_grad(); loss = ce(logits / t.clamp(min=0.05), y); loss.backward(); return loss
    opt.step(closure)
    return float(t.clamp(min=0.05))


def probs(logits, temp):
    return torch.softmax(logits / temp, 1)[:, 1].numpy()


def best_threshold(p, y):
    cands = np.linspace(0.05, 0.95, 91)
    f1s = [f1_score(y, p >= c, zero_division=0) for c in cands]
    return float(cands[int(np.argmax(f1s))])


def metrics_at(p, y, thr):
    pred = p >= thr
    m = {"n": int(len(y)), "positives": int(np.sum(y)), "threshold": float(thr),
         "accuracy": float(np.mean(pred == y)),
         "precision": float(precision_score(y, pred, zero_division=0)),
         "recall_sensitivity": float(recall_score(y, pred, zero_division=0)),
         "specificity": float(np.mean(~pred[y == 0])) if (y == 0).any() else None,
         "f1": float(f1_score(y, pred, zero_division=0)),
         "confusion_matrix": confusion_matrix(y, pred, labels=[0, 1]).tolist()}
    if len(set(y)) == 2:
        m["roc_auc"] = float(roc_auc_score(y, p)); m["pr_auc"] = float(average_precision_score(y, p))
    return m


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True); ap.add_argument("--out", default="runs/exp")
    ap.add_argument("--arch", default="mobilenet_v3_small", choices=MD.ARCHS)
    ap.add_argument("--epochs", type=int, default=12); ap.add_argument("--freeze-epochs", type=int, default=2)
    ap.add_argument("--batch", type=int, default=32); ap.add_argument("--size", type=int, default=224)
    ap.add_argument("--lr", type=float, default=1e-3); ap.add_argument("--patience", type=int, default=4)
    ap.add_argument("--seed", type=int, default=0); ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--no-pretrained", action="store_true"); ap.add_argument("--weights", default=None)
    ap.add_argument("--positive", nargs="*", default=[]); ap.add_argument("--external", default=None)
    ap.add_argument("--external-label", type=int, default=None, choices=[0, 1])
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True); seed_all(a.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"

    items = D.scan_folder(a.data, a.positive)
    split = D.group_split(items, seed=a.seed)
    counts = {k: {"n": len(v), "positives": sum(l for _p, l, _c in v)} for k, v in split.items()}
    print("split (duplicate-aware):", counts)
    for k, v in counts.items():
        if v["n"] == 0 or v["positives"] in (0, v["n"]):
            raise SystemExit(f"split '{k}' lacks one of the classes {v}: need both tylcv and not_tylcv images "
                             "(negatives such as healthy leaves are required to train a diagnostic model)")
    mk = lambda it, tr: DataLoader(D.LeafDataset(it, a.size, tr), batch_size=a.batch, shuffle=tr,
                                   num_workers=a.workers)
    tr_dl, va_dl, te_dl = mk(split["train"], True), mk(split["val"], False), mk(split["test"], False)
    ytr = np.array([l for _p, l, _c in split["train"]])
    w = torch.tensor(len(ytr) / (2 * np.bincount(ytr, minlength=2)), dtype=torch.float32)

    model, info = MD.build_model(a.arch, not a.no_pretrained, a.weights)
    model.to(device)
    crit = nn.CrossEntropyLoss(weight=w.to(device))
    best, best_state, bad, hist = -1.0, None, 0, []
    for ep in range(a.epochs):
        frozen = ep < a.freeze_epochs
        MD.set_backbone_trainable(model, a.arch, not frozen)
        lr = a.lr if frozen else a.lr * 0.1
        opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=lr, weight_decay=1e-4)
        model.train(); tl = n = 0; t0 = time.time()
        for x, y in tr_dl:
            x, y = x.to(device), y.to(device)
            opt.zero_grad(); loss = crit(model(x), y); loss.backward(); opt.step()
            tl += loss.item() * len(y); n += len(y)
        vl, vy = logits_of(model, va_dl, device)
        vp = probs(vl, 1.0)
        auc = roc_auc_score(vy.numpy(), vp) if len(set(vy.numpy())) == 2 else 0.0
        vloss = nn.functional.cross_entropy(vl, vy).item()
        hist.append({"epoch": ep + 1, "train_loss": tl / n, "val_loss": vloss, "val_auc": float(auc),
                     "frozen_backbone": frozen})
        print(f"epoch {ep + 1}/{a.epochs} train_loss {tl / n:.4f} val_loss {vloss:.4f} val_auc {auc:.4f} "
              f"({time.time() - t0:.0f}s)")
        if auc > best:
            best, best_state, bad = auc, copy.deepcopy(model.state_dict()), 0
        else:
            bad += 1
            if bad >= a.patience:
                print("early stop"); break
    model.load_state_dict(best_state)

    vl, vy = logits_of(model, va_dl, device)
    temp = fit_temperature(vl, vy)
    thr = best_threshold(probs(vl, temp), vy.numpy())
    tl_, ty = logits_of(model, te_dl, device)
    tp = probs(tl_, temp); ty = ty.numpy()
    result = {"arch": a.arch, "pretrained": info["pretrained"], "seed": a.seed, "split_counts": counts,
              "temperature": temp, "val_best_auc": float(best), "history": hist,
              "test": metrics_at(tp, ty, thr)}
    if a.external:
        ext = D.scan_folder(a.external)
        if a.external_label is not None:
            ext = [(p, a.external_label, c) for p, _l, c in ext]
        el, ey = logits_of(model, DataLoader(D.LeafDataset(ext, a.size), batch_size=a.batch), device)
        result["external"] = metrics_at(probs(el, temp), ey.numpy(), thr)
        result["external"]["note"] = ("single-class external set: only sensitivity is meaningful"
                                      if len(set(ey.numpy())) == 1 else "mixed external set")
    torch.save({"state_dict": model.state_dict(), "arch": a.arch, "size": a.size, "temperature": temp,
                "threshold": thr, "class_names": D.CLASS_NAMES, "target_layer": info["target_layer"]},
               os.path.join(a.out, "model.pt"))
    json.dump(result, open(os.path.join(a.out, "metrics.json"), "w"), indent=1)
    make_figures(a.out, hist, tp, ty, thr, result)
    write_card(a.out, result, a)
    print(json.dumps({k: v for k, v in result["test"].items() if k != "confusion_matrix"}, indent=1))
    return result


def make_figures(out, hist, p, y, thr, result):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 4, figsize=(16, 3.6))
    ax[0].plot([h["train_loss"] for h in hist], label="train"); ax[0].plot([h["val_loss"] for h in hist], label="val")
    ax[0].set(title="Loss", xlabel="epoch"); ax[0].legend()
    cm = np.array(result["test"]["confusion_matrix"])
    ax[1].imshow(cm, cmap="Blues")
    for (i, j), v in np.ndenumerate(cm):
        ax[1].text(j, i, int(v), ha="center", va="center", color="white" if v > cm.max() / 2 else "black")
    ax[1].set(title="Confusion matrix (test)", xticks=[0, 1], yticks=[0, 1], xticklabels=D.CLASS_NAMES,
              yticklabels=D.CLASS_NAMES, xlabel="predicted", ylabel="true")
    if len(set(y)) == 2:
        fpr, tpr, _ = roc_curve(y, p); ax[2].plot(fpr, tpr); ax[2].plot([0, 1], [0, 1], ":")
        ax[2].set(title=f"ROC (AUC {result['test']['roc_auc']:.3f})", xlabel="FPR", ylabel="TPR")
        pr, rc, _ = precision_recall_curve(y, p); ax[3].plot(rc, pr); ax[3].set(title="Precision-recall", xlabel="recall")
    fig.tight_layout(); fig.savefig(os.path.join(out, "evaluation.png"), dpi=130)


def write_card(out, r, a):
    t = r["test"]
    open(os.path.join(out, "MODEL_CARD.md"), "w").write(f"""# Model card: TYLCV leaf-image classifier

- Architecture: {r['arch']} ({'ImageNet-pretrained' if r['pretrained'] else 'RANDOM INIT - not pretrained'}), input {a.size}px
- Task: binary, tylcv vs not_tylcv. Splits are duplicate-aware (near-duplicate images never cross splits).
- Split counts: {json.dumps(r['split_counts'])}
- Test: acc {t['accuracy']:.3f}, sensitivity {t['recall_sensitivity']:.3f}, specificity {t['specificity']}, F1 {t['f1']:.3f}
  (threshold {t['threshold']:.2f} chosen on validation; temperature {r['temperature']:.2f})
- External set: {json.dumps(r.get('external', 'none'))}

## Intended use and limits
Screening aid for symptom photos; it does NOT confirm infection (PCR/qPCR does). Expect lower accuracy on field photos than
on lab-background images, on other begomoviruses or nutrient disorders, and on classes absent from training.
""")


if __name__ == "__main__":
    main()
