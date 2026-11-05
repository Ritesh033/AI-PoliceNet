# TYLCV-Guard

A dependency-free (Python standard library + SQLite + vanilla JS) decision-support and data
platform built to close the research gaps identified in the accompanying review paper
(`../TYLCV_review_IEEE.pdf`). **It is a heuristic advisory and data-collection tool. Its models
are not validated against field data and it is not a substitute for expert or local guidance.**

## Run

```bash
cd tylcv-guard
python -m app.server --port 8080      # open http://127.0.0.1:8080
python -m unittest discover -s tests -t .   # 31 tests
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

## Benchmark and v2 improvements

`benchmark/` compares previous approaches, v1 and the calibrated v2 on simulated ground truth, with 15 figures (ROC/PR,
reliability diagrams, heatmaps, box plots, learning curve, radar, ...). See `benchmark/README.md` for results **and** caveats.
v2 additions: `app/calibrate.py` (model learned from logged trials; endpoints `/api/model`, `/api/model/train`,
`/api/model/predict`), `recombination_screen_v2`, and an efficacy-adaptive `rotation.plan(..., efficacy={...})`.

## Leaf scan (optional Roboflow integration)

Photo screening through a Roboflow workflow built on the public dataset
*Tomato - Yellow Leaf Curl Virus* (Thesis, Roboflow Universe, 2022):
<https://universe.roboflow.com/thesis-okplj/tomato-yellow-leaf-curl-virus>. Check the dataset's licence on that page before
any redistribution or commercial use.

```bash
pip install inference-sdk
export ROBOFLOW_API_KEY=...            # never commit this; it is read only from the environment
export ROBOFLOW_WORKSPACE=<your-workspace>
export ROBOFLOW_WORKFLOW_ID=<your-workflow-id>
python -m app.server
```

`POST /api/diagnose {image: <base64 or data-URL>, threshold: 0.5}` → verdict, TYLCV confidence, detections. Images are
validated (JPEG/PNG, ≤5 MB), written to a temp file for the SDK call, then deleted; SDK errors are sanitised so keys never
leak. **Caveats:** it recognises symptoms, not the virus (confirm by PCR); the model's accuracy has not been evaluated here;
the integration was tested only against a mocked client because the build environment could not reach Roboflow, so run one
real image through it before relying on it.

## API (JSON)

`GET /api/vision/status`  ·  `POST /api/diagnose`  ·  `GET /api/health | gaps | loci | evidence | refseqs | trials | trials/summary | trials.csv | seedlots | surveillance/summary`
`POST /api/risk | risk/season | stacking | rotation | refseqs | classify | trials | seedlots | model/train | model/predict`  ·  `GET /api/model`

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
