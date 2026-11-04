# TYLCV-Guard

A dependency-free (Python standard library + SQLite + vanilla JS) decision-support and data
platform built to close the research gaps identified in the accompanying review paper
(`../TYLCV_review_IEEE.pdf`). **It is a heuristic advisory and data-collection tool. Its models
are not validated against field data and it is not a substitute for expert or local guidance.**

## Run

```bash
cd tylcv-guard
python -m app.server --port 8080      # open http://127.0.0.1:8080
python -m unittest discover -s tests -t .   # 22 tests
```

Docker: `docker build -t tylcv-guard . && docker run -p 8080:8080 tylcv-guard`

## Gaps → features

| Gap (from the review) | Feature | Module |
|---|---|---|
| G1 Durability of stacked Ty resistance (heat, recombinants) | Resistance Stacking Planner: protection score, mechanism-diversity durability tier, best next locus, warnings | `app/stacking.py` |
| G2 Virus–vector interface poorly resolved | Evidence Library: the 40 reviewed papers tagged by gap | `data/evidence.json` |
| G3 Seed / non-vector transmission | Seed Lot Register: untested/positive/negative status, rule-of-three 95% prevalence bound | `app/db.py` |
| G4 Climate effects | Climate & Vector Risk Index (daily + season series) | `app/risk.py` |
| G5 Lack of field validation | Field Trial log: incidence by locus combination with Wilson 95% CI, CSV export (feeds calibration of G1/G4) | `app/db.py` |
| G6 Uneven recombinant surveillance | Sequence Surveillance: user-supplied reference panel, k-mer classification, sliding-window recombination screen, per-country summary | `app/seqtools.py` |
| G7 Whitefly insecticide resistance | IPM Rotation Planner: MoA rotation, no back-to-back repeats, excludes failed groups (no product or dose advice) | `app/rotation.py` |

## API (JSON)

`GET /api/health | gaps | loci | evidence | refseqs | trials | trials/summary | trials.csv | seedlots | surveillance/summary`
`POST /api/risk | risk/season | stacking | rotation | refseqs | classify | trials | seedlots`

## Limitations (read before use)

- Risk curves and Ty-locus effect sizes are illustrative priors derived from qualitative findings in the
  review. Calibrate them with the Field Trials data before any real decision.
- No reference genomes are bundled: add trusted sequences (e.g. from GenBank) to the panel.
  The k-mer recombination screen is a triage aid; confirm with RDP or phylogenetics.
- Citations in the Evidence Library are inherited from the review and are not yet verified against
  publisher records (see `../TYLCV_reference_verification.md`).
- No authentication; run on localhost or behind a trusted proxy. Do not expose publicly as-is.

## Roadmap

Weather-API ingestion; model calibration from trial data; map view; user accounts; GenBank import;
experiment-tracking module for vector-interface studies (G2).
