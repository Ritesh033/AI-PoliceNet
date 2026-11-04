"""Sequence surveillance utilities (gap: surveillance of strains and recombinants).

Alignment-free k-mer comparison against a reference panel that the USER supplies
(strain names and sequences), plus a sliding-window recombination screen. This is a
screening aid, not a substitute for phylogenetic analysis (e.g. RDP/IQ-TREE).
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

K = 12
GENOME_RANGE = (2500, 3000)  # typical monopartite begomovirus genome size (nt)
VALID = set("ACGT")


class ValidationError(ValueError):
    pass


def parse_fasta(text: str) -> List[Tuple[str, str]]:
    records, name, buf = [], None, []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if name is not None:
                records.append((name, "".join(buf)))
            name, buf = line[1:].strip() or "unnamed", []
        else:
            if name is None:
                raise ValidationError("FASTA must start with a '>' header line")
            buf.append(line)
    if name is not None:
        records.append((name, "".join(buf)))
    if not records:
        raise ValidationError("no FASTA records found")
    return [(n, clean(s)) for n, s in records]


def clean(seq: str) -> str:
    seq = re.sub(r"\s+", "", seq).upper().replace("U", "T")
    bad = set(seq) - VALID - set("N")
    if bad:
        raise ValidationError(f"invalid characters in sequence: {sorted(bad)}")
    return seq


def kmers(seq: str, k: int = K) -> set:
    return {seq[i:i + k] for i in range(len(seq) - k + 1) if "N" not in seq[i:i + k]}


def circular_kmers(seq: str, k: int = K) -> set:
    return kmers(seq + seq[:k - 1], k) if len(seq) >= k else set()


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a or b) else 0.0


def containment(query: set, ref: set) -> float:
    return len(query & ref) / len(query) if query else 0.0


def stats(seq: str) -> Dict:
    gc = (seq.count("G") + seq.count("C")) / max(1, len(seq) - seq.count("N"))
    lo, hi = GENOME_RANGE
    warn = [] if lo <= len(seq) <= hi else [f"length {len(seq)} nt outside typical {lo}-{hi} nt range"]
    return {"length": len(seq), "gc": round(gc, 4), "ambiguous": seq.count("N"), "warnings": warn}


def classify(query: str, refs: Dict[str, str], threshold: float = 0.5) -> Dict:
    """Best-matching reference by k-mer containment (circular genomes)."""
    if not refs:
        raise ValidationError("reference panel is empty; add reference sequences first")
    q = circular_kmers(query)
    if not q:
        raise ValidationError("query too short for k-mer analysis")
    scores = sorted(((containment(q, circular_kmers(s)), n) for n, s in refs.items()), reverse=True)
    best_score, best = scores[0]
    return {"best_match": best if best_score >= threshold else None, "score": round(best_score, 4),
            "ranking": [{"name": n, "score": round(s, 4)} for s, n in scores[:5]],
            "status": "classified" if best_score >= threshold else "unclassified (possible novel lineage)"}


def recombination_screen(query: str, refs: Dict[str, str], window: int = 200, step: int = 50,
                         min_windows: int = 3) -> Dict:
    """Flag queries whose windows are best explained by different references."""
    if len(refs) < 2:
        return {"flag": False, "reason": "need at least 2 references", "segments": []}
    if len(query) < window * 2:
        return {"flag": False, "reason": "query too short for window screen", "segments": []}
    ref_k = {n: circular_kmers(s) for n, s in refs.items()}
    best_per_window = []
    for start in range(0, len(query) - window + 1, step):
        wk = kmers(query[start:start + window])
        if not wk:
            best_per_window.append((start, None))
            continue
        scored = sorted(((containment(wk, rk), n) for n, rk in ref_k.items()), reverse=True)
        (s1, n1), (s2, _n2) = scored[0], scored[1]
        best_per_window.append((start, n1 if s1 > s2 + 0.02 else None))  # ignore ties
    segments, cur = [], None
    for start, name in best_per_window:
        if name is None:
            continue
        if cur and cur["ref"] == name:
            cur["end"], cur["windows"] = start + window, cur["windows"] + 1
        else:
            cur = {"ref": name, "start": start, "end": start + window, "windows": 1}
            segments.append(cur)
    solid = [s for s in segments if s["windows"] >= min_windows]
    distinct = {s["ref"] for s in solid}
    flag = len(distinct) >= 2
    return {"flag": flag, "segments": solid,
            "reason": "windows best match different references" if flag else "single dominant reference",
            "note": "Screening only; confirm with RDP/phylogenetic recombination analysis."}
