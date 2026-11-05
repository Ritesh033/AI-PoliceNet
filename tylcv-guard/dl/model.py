"""Model factory (transfer learning) and Grad-CAM explainability."""
from __future__ import annotations

import warnings

import torch
import torch.nn as nn

ARCHS = ("mobilenet_v3_small", "resnet18", "efficientnet_b0")


def build_model(arch: str = "mobilenet_v3_small", pretrained: bool = True, weights_path: str = None):
    """Return (model, info). Pretrained ImageNet weights are used when reachable; otherwise random init
    (with a loud warning) unless `weights_path` points to a local ImageNet state_dict."""
    import torchvision.models as M
    if arch not in ARCHS:
        raise ValueError(f"arch must be one of {ARCHS}")
    info = {"arch": arch, "pretrained": False}
    kw = {}
    if pretrained and not weights_path:
        try:
            kw["weights"] = "DEFAULT"
            model = getattr(M, arch)(**kw)
            info["pretrained"] = True
        except Exception as e:  # noqa: BLE001  (offline: weights download failed)
            warnings.warn(f"could not load pretrained weights ({type(e).__name__}); using RANDOM init. "
                          "Accuracy will be far worse: supply --weights or train with network access.")
            model = getattr(M, arch)(weights=None)
    else:
        model = getattr(M, arch)(weights=None)
        if weights_path:
            model.load_state_dict(torch.load(weights_path, map_location="cpu"))
            info["pretrained"] = True
    if arch == "mobilenet_v3_small":
        model.classifier[-1] = nn.Linear(model.classifier[-1].in_features, 2)
        info["target_layer"] = "features.12"
    elif arch == "resnet18":
        model.fc = nn.Linear(model.fc.in_features, 2)
        info["target_layer"] = "layer4"
    else:
        model.classifier[-1] = nn.Linear(model.classifier[-1].in_features, 2)
        info["target_layer"] = "features.8"
    return model, info


def get_layer(model, dotted: str):
    m = model
    for part in dotted.split("."):
        m = m[int(part)] if part.isdigit() else getattr(m, part)
    return m


def set_backbone_trainable(model, arch: str, trainable: bool):
    head = {"mobilenet_v3_small": "classifier", "resnet18": "fc", "efficientnet_b0": "classifier"}[arch]
    for name, p in model.named_parameters():
        p.requires_grad = trainable or name.startswith(head)


class GradCAM:
    """Grad-CAM heatmap for the predicted (or a given) class: shows which leaf regions drove the decision."""

    def __init__(self, model, layer):
        self.model, self.acts, self.grads = model, None, None
        layer.register_forward_hook(lambda m, i, o: setattr(self, "acts", o.detach()))
        layer.register_full_backward_hook(lambda m, gi, go: setattr(self, "grads", go[0].detach()))

    def __call__(self, x, cls=None):
        self.model.eval()
        x = x.requires_grad_(True)
        out = self.model(x)
        cls = int(out.argmax(1)) if cls is None else cls
        self.model.zero_grad()
        out[0, cls].backward()
        w = self.grads.mean(dim=(2, 3), keepdim=True)
        cam = torch.relu((w * self.acts).sum(1, keepdim=True))
        cam = torch.nn.functional.interpolate(cam, size=x.shape[-2:], mode="bilinear", align_corners=False)[0, 0]
        cam = cam - cam.min()
        return (cam / (cam.max() + 1e-8)).numpy(), cls
