# TYLCV-Guard benchmark report

**All results come from SYNTHETIC ground truth, not field data.** They show how the models behave under an assumed
generating process, and which components are worth keeping; they do not prove real-world accuracy.

## Risk prediction (outbreak = incidence ≥ 30%)

| Model | AUC | Avg precision | MAE | ECE | AUC (hot, unseen) | MAE (hot, unseen) |
|---|---|---|---|---|---|---|
| Temp-only | 0.635 | 0.222 | 0.126 | 0.069 | 0.666 | 0.106 |
| Whitefly-threshold | 0.736 | 0.314 | 0.125 | 0.041 | 0.732 | 0.114 |
| Env-only (T×WF) | 0.764 | 0.348 | 0.117 | 0.017 | 0.775 | 0.102 |
| v1 (heuristic) | 0.930 | 0.786 | 0.074 | 0.022 | 0.938 | 0.064 |
| v2 (calibrated) | 0.980 | 0.897 | 0.038 | 0.003 | 0.982 | 0.036 |

## Stacking planner (Spearman vs true protection / best-next-locus accuracy)

- Cool, no recombinants: count 0.89/1.00, v1 1.00/1.00, v2 1.00/1.00
- Hot, no recombinants: count 0.89/0.38, v1 1.00/1.00, v2 1.00/1.00
- Hot + recombinants: count 0.85/0.31, v1 0.99/1.00, v2 1.00/1.00

## Recombinant screen

| Method | Mean sensitivity | Mean false-positive rate |
|---|---|---|
| Best-match only (previous) | 0.00 | 0.00 |
| v1 window screen | 0.67 | 0.01 |
| v2 discriminative k-mers | 0.80 | 0.01 |

## Resistance management (toy population-genetics model, 100 replicates x 60 sprays)

**Scenario: uniform**

| Strategy | Mean efficacy | Sprays below 50% efficacy (of 60) |
|---|---|---|
| repeat | 0.041 | 57.5 |
| random | 0.370 | 41.3 |
| round-robin | 0.396 | 43.5 |
| planner | 0.393 | 44.3 |
| planner_v2 | 0.395 | 43.6 |

**Scenario: hetero**

| Strategy | Mean efficacy | Sprays below 50% efficacy (of 60) |
|---|---|---|
| repeat | 0.031 | 58.4 |
| random | 0.325 | 46.3 |
| round-robin | 0.351 | 49.1 |
| planner | 0.350 | 49.4 |
| planner_v2 | 0.351 | 48.6 |


Figures: see `results/*.png` and `results/benchmark_report.pdf`.
