"""Dataset utilities: folder scan, binary labelling, duplicate-aware (group) splitting, transforms."""
from __future__ import annotations

import os
import random
import re
from typing import Dict, List, Sequence, Tuple

import numpy as np
from PIL import Image

EXTS = (".jpg", ".jpeg", ".png")
POSITIVE_PATTERN = re.compile(r"yellow.?leaf.?curl|ylcv|tylcv", re.I)
IMAGENET_MEAN, IMAGENET_STD = (0.485, 0.456, 0.406), (0.229, 0.224, 0.225)
CLASS_NAMES = ["not_tylcv", "tylcv"]


def scan_folder(root: str, positive: Sequence[str] = ()) -> List[Tuple[str, int, str]]:
    """Return (path, label, source_class). Sub-folders are classes; a class is positive if its name
    matches `positive` (exact names) or the TYLCV pattern. Everything else is label 0."""
    items = []
    for cls in sorted(os.listdir(root)):
        d = os.path.join(root, cls)
        if not os.path.isdir(d):
            continue
        label = int(cls in positive or (not positive and POSITIVE_PATTERN.search(cls) is not None))
        for dirpath, _dirs, files in os.walk(d):
            for f in sorted(files):
                if f.lower().endswith(EXTS):
                    items.append((os.path.join(dirpath, f), label, cls))
    if not items:
        raise ValueError(f"no images found under {root}")
    return items


def ahash256(path: str) -> np.ndarray:
    """16x16 average hash packed into 32 bytes (coarser hashes merge unrelated leaves on plain backdrops)."""
    im = Image.open(path).convert("L").resize((16, 16))
    a = np.asarray(im, dtype=float)
    return np.packbits((a > a.mean()).flatten())


_POP = np.array([bin(i).count("1") for i in range(256)], dtype=np.int64)


def duplicate_groups(paths: Sequence[str], max_hamming: int = 12) -> List[int]:
    """Group ids such that near-duplicate images (same photo, resized/recompressed) share a group.
    Threshold 12 of 256 bits matched the true duplicate pairs found when auditing the Kaggle TYLCV folder."""
    hashes = np.stack([ahash256(p) for p in paths])
    n = len(paths)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n - 1):
        d = _POP[hashes[i] ^ hashes[i + 1:]].sum(axis=1)
        for j in np.nonzero(d <= max_hamming)[0]:
            a, b = find(i), find(i + 1 + int(j))
            if a != b:
                parent[b] = a
    return [find(i) for i in range(n)]


def group_split(items: List[Tuple[str, int, str]], fractions=(0.7, 0.15, 0.15), seed: int = 0,
                max_hamming: int = 12) -> Dict[str, List[Tuple[str, int, str]]]:
    """Stratified split by duplicate group, so no near-duplicate crosses train/val/test."""
    groups = duplicate_groups([p for p, _l, _c in items], max_hamming)
    by_group: Dict[int, List[int]] = {}
    for idx, g in enumerate(groups):
        by_group.setdefault(g, []).append(idx)
    rng = random.Random(seed)
    out = {"train": [], "val": [], "test": []}
    for label in (0, 1):
        gl = [g for g, idxs in by_group.items()
              if round(sum(items[i][1] for i in idxs) / len(idxs)) == label]
        rng.shuffle(gl)
        total = sum(len(by_group[g]) for g in gl)
        targets = [fractions[0] * total, (fractions[0] + fractions[1]) * total]
        seen = 0
        for g in gl:
            split = "train" if seen < targets[0] else ("val" if seen < targets[1] else "test")
            out[split].extend(items[i] for i in by_group[g])
            seen += len(by_group[g])
    return out


def make_transforms(size: int = 224, train: bool = False):
    from torchvision import transforms as T
    norm = T.Normalize(IMAGENET_MEAN, IMAGENET_STD)
    if train:
        return T.Compose([T.RandomResizedCrop(size, scale=(0.6, 1.0)), T.RandomHorizontalFlip(),
                          T.RandomVerticalFlip(), T.RandomRotation(25),
                          # colour is diagnostic (yellowing): keep hue jitter small
                          T.ColorJitter(brightness=0.25, contrast=0.25, saturation=0.2, hue=0.03),
                          T.ToTensor(), norm])
    return T.Compose([T.Resize(int(size * 1.14)), T.CenterCrop(size), T.ToTensor(), norm])


class LeafDataset:
    def __init__(self, items, size=224, train=False):
        self.items, self.tf = list(items), make_transforms(size, train)

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        path, label, _cls = self.items[i]
        return self.tf(Image.open(path).convert("RGB")), label
