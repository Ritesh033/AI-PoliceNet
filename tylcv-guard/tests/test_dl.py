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
    """Synthetic 'leaf' with random shape, position, background and veins (varied enough that the
    duplicate hash does not merge unrelated images)."""
    r = random.Random(seed)
    base = (r.randint(150, 200), r.randint(200, 235), r.randint(40, 90)) if yellow else (r.randint(20, 60), r.randint(110, 160), r.randint(20, 60))
    bg = tuple(r.randint(60, 200) for _ in range(3))
    im = Image.new("RGB", (size, size), bg)
    d = ImageDraw.Draw(im)
    x0, y0 = r.randint(0, 25), r.randint(0, 25)
    x1, y1 = size - r.randint(0, 25), size - r.randint(0, 25)
    d.ellipse((x0, y0, x1, y1), fill=base)
    for _ in range(r.randint(3, 9)):
        xa, ya = r.randint(x0, x1), r.randint(y0, y1)
        d.line((xa, ya, r.randint(x0, x1), r.randint(y0, y1)), fill=(max(0, base[0] - 40), max(0, base[1] - 50), base[2]), width=r.randint(1, 3))
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
        where = {p: k for k, v in split.items() for p, _l, _c in v}
        h = os.path.join(self.root, "Tomato___healthy")
        self.assertEqual(where[os.path.join(h, "0.jpg")], where[os.path.join(h, "0_small.jpg")])
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
        # app integration: local backend through vision.diagnose
        import base64
        from app import vision
        os.environ["TYLCV_LOCAL_MODEL"] = os.path.join(out, "model.pt")
        try:
            raw = open(os.path.join(self.root, "Tomato___healthy", "1.jpg"), "rb").read()
            r = vision.diagnose(base64.b64encode(raw).decode())
            self.assertIn("verdict", r)
            self.assertEqual(vision.status()["backend"], "local")
        finally:
            del os.environ["TYLCV_LOCAL_MODEL"]

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
