"""Run every image in a folder through the Roboflow Leaf Scan and report the detection rate.

Usage: python -I tools/batch_scan.py <image_dir> [threshold]   (env vars as in app/vision.py)
If the folder contains ONLY TYLCV-positive images this measures sensitivity (recall) only: it
cannot measure false-positive rate. Add healthy/other-disease leaves in a separate folder and run
again to estimate specificity.
"""
import base64, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from app import vision  # noqa: E402


def main(d, th=0.5):
    files = sorted(f for f in os.listdir(d) if f.lower().endswith((".jpg", ".jpeg", ".png")))
    hit = err = 0
    client = vision.make_client()
    for f in files:
        raw = open(os.path.join(d, f), "rb").read()
        if len(raw) > vision.MAX_IMAGE_BYTES:
            print("skip (too large):", f); continue
        try:
            r = vision.diagnose(base64.b64encode(raw).decode(), th, client=client)
            hit += r["tylcv_confidence"] >= th
        except vision.VisionError as e:
            err += 1; print("error:", f, e)
    n = len(files) - err
    print(f"{hit}/{n} flagged as TYLCV-like at threshold {th} ({err} errors)")


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 0.5)
