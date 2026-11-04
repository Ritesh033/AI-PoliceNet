"""SQLite storage: reference sequences, submissions, field trials, seed lots."""
from __future__ import annotations

import math
import os
import sqlite3
from typing import Dict, List

from . import seqtools

DB_PATH = os.environ.get("TYLCV_DB", os.path.join(os.path.dirname(__file__), "..", "data", "tylcv.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS refseqs(name TEXT PRIMARY KEY, lineage TEXT, sequence TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS submissions(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, country TEXT, collected TEXT,
  length INTEGER, best_match TEXT, score REAL, status TEXT, recombinant_flag INTEGER,
  created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS trials(
  id INTEGER PRIMARY KEY AUTOINCREMENT, site TEXT NOT NULL, country TEXT, season TEXT,
  cultivar TEXT, loci TEXT NOT NULL DEFAULT '', strain TEXT, mean_max_temp REAL,
  plants INTEGER NOT NULL, infected INTEGER NOT NULL, severity REAL, notes TEXT,
  created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS seedlots(
  id INTEGER PRIMARY KEY AUTOINCREMENT, lot TEXT NOT NULL, origin TEXT, method TEXT,
  tested INTEGER NOT NULL DEFAULT 0, positive INTEGER NOT NULL DEFAULT 0, sample_size INTEGER,
  date TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP);
"""


class ValidationError(ValueError):
    pass


def connect(path: str = None) -> sqlite3.Connection:
    path = path or DB_PATH
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def rows(cur) -> List[Dict]:
    return [dict(r) for r in cur.fetchall()]


# ---------- reference panel & surveillance ----------
def add_reference(conn, name: str, lineage: str, sequence: str) -> None:
    name = (name or "").strip()
    if not name:
        raise ValidationError("name required")
    seq = seqtools.clean(sequence)
    if len(seq) < 1000:
        raise ValidationError("reference sequence too short (<1000 nt)")
    conn.execute("INSERT OR REPLACE INTO refseqs(name,lineage,sequence) VALUES (?,?,?)", (name, lineage, seq))
    conn.commit()


def reference_map(conn) -> Dict[str, str]:
    return {r["name"]: r["sequence"] for r in conn.execute("SELECT name,sequence FROM refseqs")}


def list_references(conn) -> List[Dict]:
    return rows(conn.execute("SELECT name,lineage,length(sequence) AS length FROM refseqs ORDER BY name"))


def submit_sequences(conn, fasta: str, country: str = "", collected: str = "") -> List[Dict]:
    refs = reference_map(conn)
    results = []
    for name, seq in seqtools.parse_fasta(fasta):
        st = seqtools.stats(seq)
        cls = seqtools.classify(seq, refs)
        rec = seqtools.recombination_screen(seq, refs)
        conn.execute(
            "INSERT INTO submissions(name,country,collected,length,best_match,score,status,recombinant_flag)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (name, country, collected, st["length"], cls["best_match"], cls["score"], cls["status"], int(rec["flag"])))
        results.append({"name": name, **st, "classification": cls, "recombination": rec})
    conn.commit()
    return results


def surveillance_summary(conn) -> Dict:
    by_country = rows(conn.execute(
        "SELECT COALESCE(NULLIF(country,''),'unknown') AS country, COUNT(*) AS n,"
        " SUM(recombinant_flag) AS recombinant_flags FROM submissions GROUP BY 1 ORDER BY n DESC"))
    by_match = rows(conn.execute(
        "SELECT COALESCE(best_match,'unclassified') AS lineage, COUNT(*) AS n FROM submissions GROUP BY 1 ORDER BY n DESC"))
    return {"by_country": by_country, "by_lineage": by_match}


# ---------- field trials ----------
def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def add_trial(conn, d: Dict) -> int:
    site = (d.get("site") or "").strip()
    if not site:
        raise ValidationError("site required")
    try:
        plants, infected = int(d["plants"]), int(d["infected"])
    except (KeyError, TypeError, ValueError):
        raise ValidationError("plants and infected must be integers")
    if plants <= 0 or not 0 <= infected <= plants:
        raise ValidationError("need plants > 0 and 0 <= infected <= plants")
    loci = ",".join(sorted(x.strip() for x in (d.get("loci") or "").split(",") if x.strip()))
    sev = d.get("severity")
    if sev not in (None, ""):
        sev = float(sev)
        if not 0 <= sev <= 4:
            raise ValidationError("severity must be on a 0-4 scale")
    else:
        sev = None
    temp = d.get("mean_max_temp")
    temp = float(temp) if temp not in (None, "") else None
    cur = conn.execute(
        "INSERT INTO trials(site,country,season,cultivar,loci,strain,mean_max_temp,plants,infected,severity,notes)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (site, d.get("country", ""), d.get("season", ""), d.get("cultivar", ""), loci, d.get("strain", ""),
         temp, plants, infected, sev, d.get("notes", "")))
    conn.commit()
    return cur.lastrowid


def list_trials(conn) -> List[Dict]:
    return rows(conn.execute("SELECT * FROM trials ORDER BY id DESC"))


def trial_summary(conn) -> List[Dict]:
    out = []
    for r in conn.execute(
            "SELECT loci, COUNT(*) AS trials, SUM(plants) AS plants, SUM(infected) AS infected,"
            " AVG(severity) AS mean_severity FROM trials GROUP BY loci ORDER BY loci"):
        lo, hi = wilson(r["infected"], r["plants"])
        out.append({"loci": r["loci"] or "(none / susceptible)", "trials": r["trials"], "plants": r["plants"],
                    "infected": r["infected"], "incidence": round(r["infected"] / r["plants"], 4),
                    "ci95": [round(lo, 4), round(hi, 4)],
                    "mean_severity": None if r["mean_severity"] is None else round(r["mean_severity"], 2)})
    return out


def trials_csv(conn) -> str:
    cols = ["id", "site", "country", "season", "cultivar", "loci", "strain", "mean_max_temp",
            "plants", "infected", "severity", "notes"]
    lines = [",".join(cols)]
    for t in list_trials(conn):
        lines.append(",".join('"' + str(t[c] if t[c] is not None else "").replace('"', '""') + '"' for c in cols))
    return "\n".join(lines) + "\n"


# ---------- seed lots (gap: seed transmission) ----------
def add_seedlot(conn, d: Dict) -> int:
    lot = (d.get("lot") or "").strip()
    if not lot:
        raise ValidationError("lot required")
    try:
        tested = int(d.get("tested", 0))
        positive = int(d.get("positive", 0))
        size = int(d["sample_size"]) if d.get("sample_size") not in (None, "") else None
    except (TypeError, ValueError):
        raise ValidationError("tested, positive and sample_size must be integers")
    if tested not in (0, 1) or positive < 0:
        raise ValidationError("tested must be 0/1 and positive >= 0")
    if tested == 0 and positive:
        raise ValidationError("untested lot cannot have positives")
    cur = conn.execute("INSERT INTO seedlots(lot,origin,method,tested,positive,sample_size,date) VALUES (?,?,?,?,?,?,?)",
                       (lot, d.get("origin", ""), d.get("method", ""), tested, positive, size, d.get("date", "")))
    conn.commit()
    return cur.lastrowid


def list_seedlots(conn) -> List[Dict]:
    out = rows(conn.execute("SELECT * FROM seedlots ORDER BY id DESC"))
    for r in out:
        if not r["tested"]:
            r["status"] = "untested - hold until tested"
        elif r["positive"] > 0:
            r["status"] = "POSITIVE - quarantine/reject"
        else:
            r["status"] = "negative in tested sample"
            if r["sample_size"] is not None and r["sample_size"] > 0:
                # rule of three: 95% upper bound on prevalence when 0 positives found
                r["prevalence_upper95"] = round(min(1.0, 3.0 / r["sample_size"]), 4)
    return out
