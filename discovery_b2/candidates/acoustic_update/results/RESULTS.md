# Acoustic update pilot results

Decision: **STOP_BOTH_GATES**. Fixed deployable simple method chosen on 2020: `current_median`.

Primary: linear NASC reconstruction of held-out observed spatial groups. This is an offline retrospective finite-support analysis, not biomass, whole-sea total, routing, or energy saving.

| Year | Label block fraction | Simple NMAE | RK NMAE | Improvement | Simple abs bias | RK abs bias |
|---|---:|---:|---:|---:|---:|---:|
| 2021 | 15% | 0.8253 | 7.6055 | -6.7802 | 0.5930 | 6.1152 |
| 2021 | 35% | 0.8046 | 2.9222 | -2.1176 | 0.6455 | 1.5356 |
| 2022 | 15% | 0.8712 | 1.1749 | -0.3037 | 0.5975 | 0.0872 |
| 2022 | 35% | 0.8545 | 1.2157 | -0.3612 | 0.6789 | 0.2024 |
| 2023 | 15% | 0.6757 | 6.7478 | -6.0721 | 0.4068 | 5.5666 |
| 2023 | 35% | 0.6716 | 6.6959 | -6.0243 | 0.4330 | 5.6716 |

Separate application comparison: {"current": "current_median", "history_enabled": "regression_kriging", "cells": [{"year": 2021, "budget": 0.15, "improvement": -6.780199788515196, "bias_gate": false}, {"year": 2021, "budget": 0.35, "improvement": -2.117593878191933, "bias_gate": false}, {"year": 2022, "budget": 0.15, "improvement": -0.3036720304657131, "bias_gate": true}, {"year": 2022, "budget": 0.35, "improvement": -0.3612210758618972, "bias_gate": true}, {"year": 2023, "budget": 0.15, "improvement": -6.072120766771794, "bias_gate": false}, {"year": 2023, "budget": 0.35, "improvement": -6.024291720096205, "bias_gate": false}]}
Application gate: STOP_HISTORY_UPDATE_SIGNAL
RK increment gate: STOP_RK_INCREMENT
Each target year is a separate sparse-current-year experiment with full prior-year data; this is not a multi-year sparse acquisition deployment.

Qualifying improvement cells: 0/6. All cells must be nonnegative and pass the bias gate; 4 must exceed 0.05.

Three mask replicates are correlated resampling sensitivity checks, not independent ocean missions. GREG/HT full-support index errors are separately saved in index_estimates.csv; they do not replace reconstruction evidence.

Cost is reported as visible groups AND actual 7-minute segments in scores.csv. Prior observations at the same spatial location are allowed for annual updating; this does not validate unseen-region extrapolation. Hindcasts are offline information. Uneven diel/month sampling remains a limitation.

Files: groups.csv (including source-row indices), splits.csv, predictions.csv, scores.csv, index_estimates.csv, development_choice.json, diagnostics.json, verdict.json, two PNGs, receipt.json.