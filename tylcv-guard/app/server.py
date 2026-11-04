"""Dependency-free HTTP server + JSON API for TYLCV-Guard.

Run:  python -m app.server [--port 8080]
"""
from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from . import calibrate, db, risk, rotation, seqtools, stacking

ROOT = os.path.join(os.path.dirname(__file__), "..")
STATIC = os.path.join(ROOT, "static")
EVIDENCE = os.path.join(ROOT, "data", "evidence.json")
MODEL_PATH = os.environ.get("TYLCV_MODEL", os.path.join(ROOT, "data", "model_v2.json"))
MAX_BODY = 5 * 1024 * 1024

GAPS = [
    {"id": "G1", "gap": "Durability of resistance (stacked Ty loci, temperature, recombinants)",
     "features": ["Resistance Stacking Planner", "Field Trials (calibration data)"]},
    {"id": "G2", "gap": "Virus-vector interface understanding",
     "features": ["Evidence Library (curated literature by gap)"]},
    {"id": "G3", "gap": "Seed and non-vector transmission",
     "features": ["Seed Lot Register with rule-of-three prevalence bound"]},
    {"id": "G4", "gap": "Climate effects on vector and virus",
     "features": ["Climate & Vector Risk Index (daily and season)"]},
    {"id": "G5", "gap": "Field validation of resistance, editing and RNA tools",
     "features": ["Field Trials with Wilson confidence intervals and CSV export"]},
    {"id": "G6", "gap": "Uneven recombinant surveillance",
     "features": ["Sequence Surveillance (k-mer classification, recombination screen, country summary)"]},
    {"id": "G7", "gap": "Insecticide resistance in whiteflies",
     "features": ["IPM Rotation Planner (MoA rotation, failed-group exclusion)"]},
]


class Handler(BaseHTTPRequestHandler):
    server_version = "TYLCVGuard/1.0"

    def log_message(self, fmt, *args):  # quieter logs
        pass

    # ---- helpers
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else (
            json.dumps(body).encode() if ctype == "application/json" else str(body).encode())
        self.send_response(code)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype != "application/json" else ""))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def _json_body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_BODY:
            raise ValueError("request body too large")
        raw = self.rfile.read(n) if n else b"{}"
        try:
            obj = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            raise ValueError("invalid JSON body")
        if not isinstance(obj, dict):
            raise ValueError("JSON body must be an object")
        return obj

    # ---- routing
    def do_GET(self):
        path = urlparse(self.path).path
        try:
            if path in ("/", "/index.html"):
                with open(os.path.join(STATIC, "index.html"), "rb") as f:
                    return self._send(200, f.read(), "text/html")
            if path == "/api/health":
                return self._send(200, {"status": "ok"})
            if path == "/api/gaps":
                return self._send(200, GAPS)
            if path == "/api/model":
                if not os.path.exists(MODEL_PATH):
                    return self._send(200, {"trained": False})
                m = calibrate.load(MODEL_PATH)
                return self._send(200, {"trained": True, "n_rows": m["n_rows"]})
            if path == "/api/loci":
                return self._send(200, stacking.LOCI)
            if path == "/api/evidence":
                with open(EVIDENCE, encoding="utf-8") as f:
                    return self._send(200, json.load(f))
            conn = db.connect()
            try:
                if path == "/api/refseqs":
                    return self._send(200, db.list_references(conn))
                if path == "/api/surveillance/summary":
                    return self._send(200, db.surveillance_summary(conn))
                if path == "/api/trials":
                    return self._send(200, db.list_trials(conn))
                if path == "/api/trials/summary":
                    return self._send(200, db.trial_summary(conn))
                if path == "/api/trials.csv":
                    return self._send(200, db.trials_csv(conn), "text/csv")
                if path == "/api/seedlots":
                    return self._send(200, db.list_seedlots(conn))
            finally:
                conn.close()
            return self._send(404, {"error": "not found"})
        except Exception as e:  # noqa: BLE001
            return self._send(500, {"error": f"server error: {type(e).__name__}"})

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            body = self._json_body()
            if path == "/api/risk":
                return self._send(200, risk.risk_index(
                    float(body["temp_c"]), float(body.get("whitefly_per_leaf", 0)),
                    body.get("stage", "vegetative"), float(body.get("protection", 0)),
                    bool(body.get("exclusion", False))))
            if path == "/api/risk/season":
                return self._send(200, risk.season_risk(
                    body.get("rows", []), body.get("stage", "vegetative"),
                    float(body.get("protection", 0)), bool(body.get("exclusion", False))))
            if path == "/api/stacking":
                return self._send(200, stacking.plan(
                    list(body.get("selected", [])), float(body.get("mean_max_temp_c", 28)),
                    bool(body.get("recombinant_pressure", False)), body.get("virus", "TYLCV")))
            if path == "/api/rotation":
                return self._send(200, rotation.plan(
                    list(body.get("available_groups", [])), list(body.get("history", [])),
                    int(body.get("sprays", 6)), list(body.get("failed_groups", [])),
                    dict(body.get("efficacy", {}))))
            if path == "/api/model/predict":
                if not os.path.exists(MODEL_PATH):
                    raise ValueError("model not trained yet: POST /api/model/train after logging 30+ trials")
                x = {"temp_c": float(body["temp_c"]), "whitefly_per_leaf": float(body.get("whitefly_per_leaf", 0)),
                     "stage": body.get("stage", "vegetative"), "loci": list(body.get("loci", [])),
                     "exclusion": bool(body.get("exclusion", False)),
                     "recombinant_pressure": bool(body.get("recombinant_pressure", False))}
                prot = stacking.plan(x["loci"], x["temp_c"], x["recombinant_pressure"])["protection"]
                v1 = risk.risk_index(x["temp_c"], x["whitefly_per_leaf"], x["stage"], prot, x["exclusion"])
                return self._send(200, {"v2_incidence": round(calibrate.predict(calibrate.load(MODEL_PATH), x), 4),
                                        "v1_index": v1["index"], "v1_category": v1["category"]})
            conn = db.connect()
            try:
                if path == "/api/model/train":
                    rows_ = db.training_rows(conn)
                    m = calibrate.fit(rows_)  # raises ValueError (HTTP 400) when < 30 usable trials
                    calibrate.save(m, MODEL_PATH)
                    return self._send(200, {"trained": True, "n_rows": m["n_rows"]})
                if path == "/api/refseqs":
                    db.add_reference(conn, body.get("name"), body.get("lineage", ""), body.get("sequence", ""))
                    return self._send(201, {"ok": True})
                if path == "/api/classify":
                    res = db.submit_sequences(conn, body.get("fasta", ""), body.get("country", ""),
                                              body.get("collected", ""))
                    return self._send(200, res)
                if path == "/api/trials":
                    return self._send(201, {"id": db.add_trial(conn, body)})
                if path == "/api/seedlots":
                    return self._send(201, {"id": db.add_seedlot(conn, body)})
            finally:
                conn.close()
            return self._send(404, {"error": "not found"})
        except (ValueError, KeyError, TypeError) as e:
            return self._send(400, {"error": str(e)})
        except Exception as e:  # noqa: BLE001
            return self._send(500, {"error": f"server error: {type(e).__name__}"})


def make_server(port: int = 8080, host: str = "127.0.0.1") -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), Handler)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args()
    srv = make_server(a.port, a.host)
    print(f"TYLCV-Guard on http://{a.host}:{srv.server_address[1]}")
    srv.serve_forever()
