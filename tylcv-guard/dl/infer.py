"""Inference + Grad-CAM for a trained checkpoint.

CLI: python -m dl.infer --ckpt runs/exp1/model.pt --image leaf.jpg [--cam out.png]
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import torch
from PIL import Image

from . import data as D
from . import model as MD

_CACHE = {}


def load(ckpt_path):
    if ckpt_path not in _CACHE:
        ck = torch.load(ckpt_path, map_location="cpu", weights_only=False)
        model, _ = MD.build_model(ck["arch"], pretrained=False)
        model.load_state_dict(ck["state_dict"]); model.eval()
        _CACHE[ckpt_path] = (model, ck)
    return _CACHE[ckpt_path]


def predict(image, ckpt_path, cam_path=None):
    model, ck = load(ckpt_path)
    im = image if isinstance(image, Image.Image) else Image.open(image)
    im = im.convert("RGB")
    x = D.make_transforms(ck["size"])(im).unsqueeze(0)
    with torch.no_grad():
        p = float(torch.softmax(model(x) / ck["temperature"], 1)[0, 1])
    out = {"probability_tylcv": round(p, 4), "threshold": ck["threshold"],
           "label": ck["class_names"][int(p >= ck["threshold"])],
           "note": "Screening aid; confirm suspected TYLCV by PCR/qPCR."}
    if cam_path:
        cam, _ = MD.GradCAM(model, MD.get_layer(model, ck["target_layer"]))(x.clone(), cls=1)
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.cm as cm
        base = np.asarray(im.resize((ck["size"], ck["size"])), dtype=float) / 255
        heat = cm.jet(cam)[..., :3]
        Image.fromarray((0.55 * base + 0.45 * heat).clip(0, 1).__mul__(255).astype("uint8")).save(cam_path)
        out["gradcam"] = cam_path
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--ckpt", required=True); ap.add_argument("--image", required=True)
    ap.add_argument("--cam"); a = ap.parse_args()
    print(json.dumps(predict(a.image, a.ckpt, a.cam), indent=1))
