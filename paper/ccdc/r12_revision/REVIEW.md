# R12 final internal evidence-consistency review

This completes the same separated author/simulated-review workflow begun in CODE_FORMULA_AUDIT.md and continued in REVIEW_EVIDENCE.md. It is not a CCDC review, acceptance prediction or score. Scope is scientific text, completed evidence and four new figure images. DOCX/PDF are not treated as final artifacts; their forthcoming compilation and page checks remain the author's responsibility.

## Finding

The current manuscript and Chinese report support the stated bounded conclusion: detailed prediction produced one additional safe completion over the specified calibrated low-order predictor in this 24-task confirmation, with substantial computation and a navigation-cost tail. No numerical or scientific-claim correction is required by the checks below. No further experiment or tuning is requested. One small figure annotation should be corrected before delivery.

## Independent final verification

I read manuscript.md, R12_REVISION_REPORT.md, verification.json, the prior method/supplement, analysis and plot source, and inspected PNG Figures 2–5. I read the original server confirmation traces and independently recomputed dynamic minima from their per-step records, safe labels, paired completion changes, time differences, activation counts and CPU sums. All 24 scene IDs have all three methods: 72 retained episodes. These are independent arithmetic/source checks, not independent physical reruns.

| Check | Independently recomputed |
|---|---|
| R / S15 / L safe completions | 19 / 24 / 23, each out of 24 |
| S15 vs L gain / loss | 1 / 0 |
| S15–L common-safe pairs | 23 |
| S15–L time mean / median / maximum | +7 / 0 / +308 s |
| S15–R common-safe n / mean / maximum | 19 / +25.157895 / +308 s |
| L–R common-safe n / mean / maximum | 19 / +6.631579 / +69 s |
| Total episode CPU, R / S15 / L | 270.677134 / 2133.232056 / 378.444523 s |
| Activated tasks, S15 / L | 11 / 11 |

The unique S15-over-L completion is r12new_mixed_pressure_1. L reaches the destination but incurs a -1.115321735 m dynamic buffer margin; counting it unsafe matches the specified evaluation. Five reactive failures are pressure_1/2/4/5/7 with margins -0.162187, -0.083002, -0.539992, -1.412341 and -0.311739 m. The largest common-safe S15 time cost is r12new_endpoint_3: S15 587 s versus L/R 279 s. Thus the 308 s adverse case is real and correctly included in the abstract/discussion/report and Figure 5.

Guard data were independently paired to the same 12 historical scene IDs and reactive records. Every guard gives 12/12 versus reactive 10/12. The common-safe denominator is 10 for all guards. Recomputed worst dynamic margins at rho=0/15/30/60 are 3.346823/24.879040/31.781188/61.767456 m; common-safe time maxima are 28/334/267/321 s, with median zero throughout. Tables and Figure 3 agree. The manuscript correctly retains the original 30 m identity and does not select an optimum from this sensitivity test.

The prior independent fixed-branch/window arithmetic remains applicable. Detailed/actual has 12 complete 60-second branches; three-way comparison has ten 60-second and two 58-second intervals because low-order prediction reaches arrival early. The three low-order guard-feasibility errors have positive actual margins 17.868/23.384/16.430 m and are correctly called guard shortfalls rather than incursions. The 106.064 m detailed error is retained and explicitly identified as one endpoint snapshot with duplicate nominal/continuation trajectories. The manuscript does not treat these alternatives or the 1083 windows as independent tasks.

## Figure and conclusion checks

- Figure 2 contains all 24 new tasks, includes every actual margin, and its caption explicitly explains crosses at zero as excluded failed pairs rather than zero time cost. Values agree with the paired traces. Small negative margins cluster near the zero line at full scale, but the table/text supply the exact failure interpretation.
- Figure 3 preserves the nonmonotone time-cost tail and unchanged safe counts; it does not imply a monotone general safety result.
- Figure 4 uses the three-way common horizons and visibly retains the large detailed error. Duplicate snapshot labels and sample unit are explained.
- Figure 5 is based on the prespecified historical pressure_2 and rule-selected largest new common-safe S15 time cost, not a favorable-only selection. Its trajectories and times agree with the original records.

The constant-speed/drift low-order comparator's simplifications, unused pending action, fixed development calibration, full predictor replacement and limited claims remain disclosed. The paper does not claim an ODE-order causal isolation or superiority over all low-order models. Ideal-compute timing is explicit; the core timing excludes initial nominal/candidate setup and loading, allows different candidate counts and is distinguished from whole-episode CPU. The large planning cost and historical S60 alternative remain visible.

Substep evidence correctly supports only the explicitly identified two historical reactive incursions and their paired S15 branches, preserving original one-second endpoints. It does not numerically certify all new failures, including the new L failure, or provide continuous safety. Current prose keeps that scope. No formal uniform error bound, swept-hull guarantee or real-time claim is made.

## Required presentation correction (one)

Figure 5 currently labels “All markers: 200s”, but the same axes also contain failed-termination crosses and mission-goal stars, which do not represent that common timestamp. Change this annotation to “Circle/square markers: 200s” (or equivalent) and retain the caption's separate explanation of crosses and goal stars. This is a timestamp-label clarification; it does not alter data or results.

Optional copy edit: “S15 gains 1 safe completions” should read “S15 gains one safe completion.” The full dynamics parameter dictionary exists in evidence/dynamics_parameters.json; directing readers explicitly to that file and evidence/ASSET_HASHES.json is clearer than saying only that the supplement lists them.

## Review boundary and remaining delivery checks

The scientific evidence review is complete with the stated figure clarification. Bibliographic ownership, inherited-controller training provenance, distribution permission, author identities and current venue requirements remain the listed author-confirmation items; this review does not resolve them. Final DOCX/PDF rendering, page-by-page layout, final package completeness and synchronization are not yet verified here. Those are delivery checks, not grounds to extend the prespecified experiments or change the conclusions.
