# Benchmark: previous approaches vs TYLCV-Guard v1 vs calibrated v2

```bash
pip install numpy matplotlib scikit-learn scipy      # benchmark only; the app needs none
python benchmark/run.py                              # ~12 s, writes benchmark/results/
```

**Read this first.** The ground truth is *simulated* (`simulate.py`) with functional forms different from the app's
heuristics, but it was written by the same author as v1/v2, so its qualitative rules (heat weakens Ty-1/Ty-3,
recombinants break Ty-1/Ty-3, stacking different mechanisms helps) match what v1/v2 encode. Results therefore show how
the components behave *if the review's findings are right*; they are not evidence of real-world accuracy. Replace the
simulator with real trial data (Field Trials tab → CSV) to get a real benchmark.

## What is compared

| Module | Previous approach | v1 (heuristic) | v2 (improved) |
|---|---|---|---|
| Outbreak/incidence prediction | Temperature-only, whitefly-threshold, temperature×whitefly (each recalibrated on the same training data) | Heuristic risk index + stacking protection | Binomial logistic model learned from trials (`app/calibrate.py`) |
| Locus stacking | Count of resistance loci | `stacking.plan` | Same planner, scored from the calibrated model |
| Recombinant detection | Best-match classification (cannot flag recombinants) | Sliding-window k-mer screen | Discriminative-k-mer screen (`recombination_screen_v2`, window 150 nt) |
| Insecticide rotation | Same group repeated | Rotation + failure exclusion | Efficacy-adaptive planner with staleness-aware estimates |

## Headline results (see `results/REPORT.md`, `results/metrics.json`, `results/benchmark_report.pdf`)

- **Risk prediction:** AUC 0.64–0.76 for the previous approaches, 0.93 for v1, 0.98 for v2; MAE 0.117–0.126 → 0.074 → 0.038.
  Most of the gain comes from including resistance and crop stage, not from model complexity.
- **Learning curve:** v2 matches v1 with about 30 trials and clearly exceeds it from about 60; gains flatten after ~500.
- **Recombinant screen:** mean sensitivity 0.67 (v1) → 0.80 (v2) at ~1% false positives in a hard regime (0.5–16% parent
  divergence, 100–600 nt fragments, 1.5% query noise). Both fail at 0.5% divergence and ≤100 nt fragments.
- **Stacking:** locus count picks the wrong best-next-locus ~62–69% of the time under heat/recombinants; v1 and v2 pick correctly
  in all tested cases (expected, since the simulator shares their assumptions).
- **Rotation (toy population-genetics model):** every rotation strategy beats repeating one group (efficacy ≈0.04 → ≈0.33–0.40),
  but **the planners do not beat a fixed round-robin** in either scenario; with five groups and strong selection every strategy
  loses efficacy within ~20 sprays. Lesson: rotation alone is insufficient; reduce spray frequency (thresholds, exclusion,
  resistant cultivars).

## Known weaknesses of this benchmark

- Synthetic data; same-author assumptions (above). The "unseen hot region" test is mild extrapolation only.
- The "previous approaches" for risk ignore resistance by construction, so the comparison favours v1/v2.
- Recombination tests use random-substitution parents, which is easier than real genomes (hotspots, indels, >2 parents).
- Rotation dynamics (selection 0.8, reversion 0.93 per spray) are illustrative, not measured.
