"""Leaf-image screening via a Roboflow workflow (optional integration).

Configuration comes ONLY from environment variables (never commit keys):
    ROBOFLOW_API_KEY        required
    ROBOFLOW_WORKSPACE      required
    ROBOFLOW_WORKFLOW_ID    required
    ROBOFLOW_API_URL        optional, default https://serverless.roboflow.com
    ROBOFLOW_CLASSES        optional, default "Tomato - Yellow Leaf Curl Virus"

The model is an image classifier/detector trained on the public Roboflow Universe dataset
"Tomato - Yellow Leaf Curl Virus" (Thesis, 2022). It recognises SYMPTOMS, not the virus:
similar-looking disorders (other begomoviruses, herbicide injury, nutrient deficiency) can
be misclassified, so a positive screen must be confirmed by PCR/qPCR. Its accuracy has not
been verified here.
"""
from __future__ import annotations

import base64
import binascii
import os
import tempfile
from typing import Any, Dict, List, Optional

MAX_IMAGE_BYTES = 5 * 1024 * 1024
DEFAULT_URL = "https://serverless.roboflow.com"
DATASET_CITATION = ("Thesis, “Tomato - Yellow Leaf Curl Virus Dataset,” Roboflow Universe, Roboflow, Dec. 2022. "
                    "[Online]. Available: https://universe.roboflow.com/thesis-okplj/tomato-yellow-leaf-curl-virus")


class VisionError(ValueError):
    pass


def config() -> Dict[str, Optional[str]]:
    return {"api_key": os.environ.get("ROBOFLOW_API_KEY"), "workspace": os.environ.get("ROBOFLOW_WORKSPACE"),
            "workflow_id": os.environ.get("ROBOFLOW_WORKFLOW_ID"),
            "api_url": os.environ.get("ROBOFLOW_API_URL", DEFAULT_URL),
            "classes": os.environ.get("ROBOFLOW_CLASSES", "Tomato - Yellow Leaf Curl Virus")}


def status() -> Dict[str, Any]:
    c = config()
    missing = [k for k in ("api_key", "workspace", "workflow_id") if not c[k]]
    return {"configured": not missing, "missing": [m.upper() for m in missing],
            "dataset": DATASET_CITATION}


def decode_image(b64: str) -> tuple:
    """Return (bytes, extension) after validating size and magic bytes."""
    if not b64:
        raise VisionError("image required")
    if "," in b64[:100]:  # strip data-URL prefix
        b64 = b64.split(",", 1)[1]
    try:
        raw = base64.b64decode(b64, validate=False)
    except (binascii.Error, ValueError):
        raise VisionError("image is not valid base64")
    if len(raw) > MAX_IMAGE_BYTES:
        raise VisionError(f"image larger than {MAX_IMAGE_BYTES // (1024 * 1024)} MB")
    if raw[:3] == b"\xff\xd8\xff":
        return raw, ".jpg"
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        return raw, ".png"
    raise VisionError("only JPEG and PNG images are supported")


def extract_detections(node: Any) -> List[Dict[str, Any]]:
    """Walk an arbitrary workflow result and collect {class, confidence} items.

    Workflow outputs differ by how the workflow was built (detections, classification top-k,
    nested outputs), so this is deliberately tolerant.
    """
    found: List[Dict[str, Any]] = []

    def walk(n):
        if isinstance(n, dict):
            cls = n.get("class") or n.get("class_name") or n.get("top")
            conf = n.get("confidence")
            if isinstance(cls, str) and isinstance(conf, (int, float)):
                found.append({"class": cls, "confidence": float(conf)})
            for k, v in n.items():
                if k in ("predictions", "outputs") or isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(n, list):
            for x in n:
                walk(x)

    walk(node)
    return found


def summarize(dets: List[Dict[str, Any]], target_class: str, threshold: float = 0.5) -> Dict[str, Any]:
    target = target_class.lower()
    pos = [d for d in dets if target in d["class"].lower() or "yellow leaf curl" in d["class"].lower()]
    best = max(pos, key=lambda d: d["confidence"], default=None)
    if best and best["confidence"] >= threshold:
        verdict = "symptoms consistent with TYLCV"
    elif dets:
        verdict = "no TYLCV-like symptoms detected above threshold"
    else:
        verdict = "no detections returned"
    return {"verdict": verdict, "tylcv_confidence": best["confidence"] if best else 0.0,
            "n_detections": len(dets), "detections": sorted(dets, key=lambda d: -d["confidence"])[:10],
            "threshold": threshold,
            "advice": ["Screening aid only: confirm suspected TYLCV by PCR/qPCR before taking action.",
                       "Photograph young symptomatic leaves in good light; also check for whitefly on leaf undersides."]}


def make_client():
    """Build the Roboflow client lazily so the app runs without the optional dependency."""
    c = config()
    try:
        from inference_sdk import InferenceConfiguration, InferenceHTTPClient
    except ImportError:
        raise VisionError("inference-sdk is not installed: pip install inference-sdk")
    return InferenceHTTPClient(api_url=c["api_url"], api_key=c["api_key"]).configure(
        InferenceConfiguration(api_key_transport="header"))


def diagnose(image_b64: str, threshold: float = 0.5, client: Any = None) -> Dict[str, Any]:
    st = status()
    if not st["configured"]:
        raise VisionError("vision not configured; set " + ", ".join(st["missing"]))
    if not 0.0 <= threshold <= 1.0:
        raise VisionError("threshold must be between 0 and 1")
    raw, ext = decode_image(image_b64)
    c = config()
    client = client or make_client()
    fd, path = tempfile.mkstemp(suffix=ext)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
        try:
            result = client.run_workflow(workspace_name=c["workspace"], workflow_id=c["workflow_id"],
                                         images={"image": path}, parameters={"classes": c["classes"]},
                                         use_cache=True)
        except Exception as e:  # noqa: BLE001  (network/auth errors from the SDK)
            raise VisionError(f"inference request failed: {type(e).__name__}")
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
    return summarize(extract_detections(result), c["classes"], threshold)
