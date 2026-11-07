# R12 separated review: completed evidence, before confirmation outcome

This is the same internal simulated-review pass as CODE_FORMULA_AUDIT.md. It is not an actual venue review or acceptance recommendation. Scope: completed supplementary records and current manuscript_base.md/SUPPLEMENT.md only. New confirmation is still running; manuscript.md/DOCX/PDF are explicitly unfinished layout probes and are not assessed as delivery. No experiment rerun, science edit or original-record change was made.

## Checks completed independently

Read server scripts check_r12_branches.py, compare_r12_predictors.py, analyze_r12_prefix.py and profile_r12.py, together with fixed_branches.json, matched_prediction_quality.json, prediction_summary.json, substep_safety.json, planning_profile.json and matched_decisions.json under runs/r12_revision_20261006. Independently recomputed all 12 matched common lengths, trajectory maximum errors and minimum margins from the stored path/margin arrays. Recomputed all 1083 short-prefix maximum position errors against original source trajectories. All recomputed quantities agreed with their records. This verifies the reported arithmetic and inspected evaluation logic; it is not an independent rerun of the physical simulator.

The simplified comparator remains an acceptable explicitly limited candidate-conditioned comparison, following the preceding source review. Current method prose correctly discloses fixed speed/drift, unused pending action, grouped omission of policy/actuator/wind dynamics, and 15-second calibration scope. No new fairness blocker is identified.

## Three conclusion-changing issues to preserve in the final text

### 1. Keep the three time domains and sample units separate

Detailed-versus-real fixed branches are **12 branches of 60 seconds**, from **six source snapshots**. All actual branches end with reason=horizon, all reconstructed physical-prefix errors are zero, and the six selected branches reproduce their source first 15 seconds exactly. These are results stored in fixed_branches.json, with assertions in check_r12_branches.py:59,62,96,100.

The **three-way comparison** adds the low-order predictor and becomes **10 common intervals of 60 seconds plus two of 58 seconds**. The two shortened comparisons are r10new_endpoint_0 at t=247, nominal and turn45. Low-order prediction reaches its arrival tolerance at step 58; actual and detailed branches continue to 60. compare_r12_predictors.py:15–16 correctly recomputes all three margins and position errors on the same shortened domain. Do not report these as two early real terminations or silently mix full-60 detailed margins with 58-second low-order margins.

The separate actual-online-prefix audit has 1083 windows from 46 source tasks: 1048 full 15-second windows and 35 shorter windows. All compared prediction starts had their one truth target observed, so no unmatched-target discrepancy was found in this collection. Event counts are enter=26, ordinary=1017, reevaluate=14 and release=26. Overlapping/within-scene windows, alternative candidates and repeated timings are not independent navigation trials. Fixed-branch diagnostic snapshots were selected from seen favorable/adverse/error cases and cannot estimate fresh-task prevalence or replace new closed-loop confirmation.

### 2. Three low-order guard overestimates are not three safety violations

The matched records contain exactly three cases where low-order predicted margin meets 30 m while actual common-domain margin is below 30 m:

| Source nominal protocol | Low-order margin (m) | Actual margin (m) | Detailed margin (m) |
|---|---:|---:|---:|
| r8new_mixed_pressure_2, t=149 | 75.748 | 17.868 | 17.706 |
| r8new_mixed_pressure_4, t=228 | 72.243 | 23.384 | 23.803 |
| r10new_mixed_pressure_0, t=157 | 56.887 | 16.430 | 15.302 |

Every actual margin is positive. Thus these establish overestimation relative to the **empirical planning guard**, not missed zero-boundary incursions. Both predictors have zero positive-prediction/nonpositive-real cases in these 12 fixed common intervals. A later full-episode incursion cannot be attributed to these intervals without its own trajectory evidence. The matched first snapshot changes the actual search choice from detailed turn-90 to low-order nominal, but the fixed nominal 60-second branch itself stays outside the safety boundary. Wording such as “three false-safe predictions” requires an explicit guard-threshold qualifier and is better replaced by “three false guard-feasible predictions.”

Short-prefix records likewise show zero observed zero-boundary false-safe cases, zero predicted-30/real-zero cases and zero guard shortfalls in the sampled selected prefixes. These zeros are finite observations, not proof that the empirical guard covers error. The new confirmation must decide the closed-loop performance comparison separately.

### 3. Preserve the large detailed error and the numerical safety limit

On the same matched domains, per-branch maximum position-error medians are detailed **1.104 m** and low-order **53.818 m**. That descriptive contrast supports improved fidelity on these selected protocols, not uniform accuracy. The detailed maximum is **106.064 m** at r8new_endpoint_1, t=341; nominal and continuation have identical trajectories there, so this is one source snapshot repeated under two protocol labels, not two independent large-error events. Detailed margin is 140.990 m versus actual 146.171 m. Large position error and a much smaller margin error coexist because the geometric risk measure differs from position tracking. Do not suppress this case, claim all detailed rollouts are accurate, or claim the 30 m guard bounds position error. Its error also cannot be assigned specifically to wind-estimation error without a discriminating test: the checked fixed protocol includes nominal feedback and state-dependent reference changes.

Substep results support the two historical buffer-incursion labels under a finer numerical representation:

| Source | One-second margin (m) | Accepted-substep margin (m) | Endpoint max error |
|---|---:|---:|---:|
| pressure_2 reactive | -1.225020 | -1.225020 | 0 |
| pressure_2 S15 | 43.589225 | 43.597334 | 0 |
| pressure_4 reactive | -0.872436 | -0.872436 | 0 |
| pressure_4 S15 | 38.454925 | 38.424701 | 0 |

The hook records original accepted Dormand–Prince endpoints, with max spacing 0.1 s; target positions are evaluated at synchronized fractional absolute times (check_r12_branches.py:38–59). Commands and original integration are replayed, and all recorded physical endpoints agree. This is sufficient to say the signs survive this substep-polyline check. It is not a new feedback run, new finer-tolerance integration, analytic dense-output minimum, swept-hull test or continuous-safety certificate. The current supplement states that boundary correctly.

## Timing and presentation notes

The profile contains three decision states, three repeats each, per predictor. Its pressure state evaluates six detailed candidates versus only one low-order nominal candidate; the endpoint state evaluates six for each; the non-conflict state evaluates one for each. Timing therefore measures the operational predictor/selection core with its nominal early return, not a per-candidate equal-work speed ratio. profile_r12.py:14 prepares options and reconstructs the nominal manager before the timer; lines20–28 include estimation, rollout and selection but exclude this setup, model loading and real execution. Describe it precisely as the “timed estimation/rollout/selection core.” Nine measurements per predictor are too few to claim a production tail distribution or guaranteed deadline, and shared-host wall times remain empirical. The current supplement's scope is broadly accurate; adding the excluded nominal/candidate setup makes it exact.

The current method and supplement incorporate the prior audit's key corrections. This review found no reason to halt the prespecified confirmation or demand a new platform. Final result claims, guard tradeoffs, evidence-group labels, manuscript figures and final artifacts still require the planned final consistency check after completion. No overall detailed-predictor superiority conclusion is issued at this stage.
