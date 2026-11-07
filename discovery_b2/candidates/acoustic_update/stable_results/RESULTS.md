# Acoustic update pilot results

Decision: **STOP_BOTH_GATES**. Fixed deployable simple method chosen on 2020: `current_median`.

Primary: linear NASC reconstruction of held-out observed spatial groups. This is an offline retrospective finite-support analysis, not biomass, whole-sea total, routing, or energy saving.

| Year | Label block fraction | Simple NMAE | RK NMAE | Improvement | Simple abs bias | RK abs bias |
|---|---:|---:|---:|---:|---:|---:|
| 2021 | 15% | 0.8253 | 1.0030 | -0.1777 | 0.5930 | 0.2834 |
| 2021 | 35% | 0.8046 | 0.9430 | -0.1384 | 0.6455 | 0.2079 |
| 2022 | 15% | 0.8712 | 1.2589 | -0.3876 | 0.5975 | 0.2967 |
| 2022 | 35% | 0.8545 | 1.1233 | -0.2688 | 0.6789 | 0.1081 |
| 2023 | 15% | 0.6757 | 0.7651 | -0.0894 | 0.4068 | 0.2168 |
| 2023 | 35% | 0.6716 | 0.7342 | -0.0626 | 0.4330 | 0.0916 |

Separate application comparison: {"current": "current_median", "history_enabled": "history_median", "cells": [{"year": 2021, "budget": 0.15, "improvement": 0.004309961924868766, "bias_gate": true}, {"year": 2021, "budget": 0.35, "improvement": 0.0009299507763437243, "bias_gate": true}, {"year": 2022, "budget": 0.15, "improvement": -0.0002405204319573251, "bias_gate": true}, {"year": 2022, "budget": 0.35, "improvement": 0.0030761737175767356, "bias_gate": true}, {"year": 2023, "budget": 0.15, "improvement": 0.0058887314270708035, "bias_gate": true}, {"year": 2023, "budget": 0.35, "improvement": 0.005619224899666264, "bias_gate": true}]}
Application gate: STOP_HISTORY_UPDATE_SIGNAL
RK increment gate: STOP_RK_INCREMENT
Each target year is a separate sparse-current-year experiment with full prior-year data; this is not a multi-year sparse acquisition deployment.

Qualifying improvement cells: 0/6. All cells must be nonnegative and pass the bias gate; 4 must exceed 0.05.

Three mask replicates are correlated resampling sensitivity checks, not independent ocean missions. GREG/HT full-support index errors are separately saved in index_estimates.csv; they do not replace reconstruction evidence.

Cost is reported as visible groups AND actual 7-minute segments in scores.csv. Prior observations at the same spatial location are allowed for annual updating; this does not validate unseen-region extrapolation. Hindcasts are offline information. Uneven diel/month sampling remains a limitation.

Files: groups.csv (including source-row indices), splits.csv, predictions.csv, scores.csv, index_estimates.csv, development_choice.json, diagnostics.json, verdict.json, two PNGs, receipt.json.