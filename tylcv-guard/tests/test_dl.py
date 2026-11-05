"""Pipeline tests for dl/ using SYNTHETIC images. They prove the code runs end to end and that the
split logic prevents leakage; they say nothing about accuracy on real leaves."""
import json
import os
import random
import tempfile
import unittest

try:
    import torch  # noqa: F401
    import torchvision  # noqa: F401
    from PIL import Image, ImageDraw
    HAVE = True
except ImportError:  # optional dependency
    HAVE = False


def make_leaf(path, yellow, seed, size=96):
    r = random.Random(seed)
    base = (r.randint(150, 200), r.randint(200, 235), r.randint(40, 90)) if yellow else (r.randint(20, 60), r.randint(110, 160), r.randint(20, 60))
    im = Image.new("RGB", (size, size), (120, 110, 100))
    d = ImageDraw.Draw(im)
    d.ellipse((10, 10, size - 10, size - 10), fill=base)
    for _ in range(6):  # veins / texture
        x = r.randint(20, size - 20)
        d.line((x, 12, x + r.randint(-10, 10), size - 12), fill=(base[0] - 20, base[1] - 30, base[2]), width=2)
    im.save(path, quality=92)


@unittest.skipUnless(HAVE, "torch/torchvision not installed")
class DL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.mkdtemp()
        for name, yellow in (("Tomato___healthy", False), ("Tomato___Tomato_Yellow_Leaf_Curl_Virus", True)):
            os.makedirs(os.path.join(cls.root, name))
            for i in range(30):
                make_leaf(os.path.join(cls.root, name, f"{i}.jpg"), yellow, i + (100 if yellow else 0))
        # a resized duplicate of one image: must land in the same split as its original
        src = os.path.join(cls.root, "Tomato___healthy", "0.jpg")
        Image.open(src).resize((48, 48)).save(os.path.join(cls.root, "Tomato___healthy", "0_small.jpg"))

    def test_labels_and_split_without_leakage(self):
        from dl import data as D
        items = D.scan_folder(self.root)
        self.assertEqual(sum(l for _p, l, _c in items), 30)
        split = D.group_split(items, seed=1)
        where = {os.path.basename(p): k for k, v in split.items() for p, _l, _c in v}
        self.assertEqual(where["0.jpg"], where["0_small.jpg"])
        self.assertEqual(sum(len(v) for v in split.values()), 61)
        for k, v in split.items():
            self.assertTrue({l for _p, l, _c in v} == {0, 1}, k)

    def test_train_eval_infer_gradcam(self):
        from dl import infer, train
        out = tempfile.mkdtemp()
        res = train.main(["--data", self.root, "--out", out, "--epochs", "3", "--freeze-epochs", "1", "--size", "96",
                          "--batch", "8", "--workers", "0", "--no-pretrained", "--seed", "0"])
        for f in ("model.pt", "metrics.json", "evaluation.png", "MODEL_CARD.md"):
            self.assertTrue(os.path.exists(os.path.join(out, f)), f)
        t = res["test"]
        self.assertEqual(sum(sum(r) for r in t["confusion_matrix"]), t["n"])
        cam = os.path.join(out, "cam.png")
        pred = infer.predict(os.path.join(self.root, "Tomato___Tomato_Yellow_Leaf_Curl_Virus", "1.jpg"),
                             os.path.join(out, "model.pt"), cam)
        self.assertTrue(0.0 <= pred["probability_tylcv"] <= 1.0)
        self.assertIn(pred["label"], ("tylcv", "not_tylcv"))
        self.assertTrue(os.path.exists(cam))

    def test_refuses_single_class(self):
        from dl import train
        only = tempfile.mkdtemp()
        os.makedirs(os.path.join(only, "Tomato_Yellow_Leaf_Curl_Virus"))
        for i in range(12):
            make_leaf(os.path.join(only, "Tomato_Yellow_Leaf_Curl_Virus", f"{i}.jpg"), True, i)
        with self.assertRaises(SystemExit) as cm:
            train.main(["--data", only, "--out", tempfile.mkdtemp(), "--workers", "0", "--no-pretrained"])
        self.assertIn("negatives", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
