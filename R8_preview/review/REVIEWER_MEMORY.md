# R8 reviewer memory

Same-family / provisional; reviews are bounded debugging/evidence checks, not certification. Shared budget: 24 h, four single-thread experimental CPU workers; no assigned GPU. Reviewer writes are limited to review-stage artifacts.

## Evidence identity

- R7 final 30/32→32/32 gains were temporary endpoint NoRouteError recovery, not collision reduction. Its confirmation85 incursions were not resolved by that final endpoint evaluation.
- R8 development2 now supplies separate evidence: reactive 4/6 versus sampled 6/6 on known scenes, including mixed_3 and mixed_7 buffer-incursion rescues; final_overtaking_1 retains 382 s. These are selected development cases, not unseen generalization.
- Primary mechanism is a GVO-inspired search over executable reference/feedback programs using observed history and independent known dynamics with inferred recent wind. No true environment clone or target/field future is permitted online.

## Implementation lessons

- Reconstruct actuator target accumulators from actual issued commands; actual raw sail/rudder angles are not target accumulators.
- Use live current_frame.goal_world for model continuation. raw14 goal fields can lag boundary installation and lose precision.
- Keep candidate-local rollout failure distinct from real episode failure. Rank complete valid forecasts before incomplete best-effort fallbacks.
- Model nominal Relay feedback, old-action first step, reference queue ordering, and hold/rejoin protocol. Simulated history remains separate.
- Wind inversion uses selected past intervals, not instantaneous true wind. The initial fixed-target predictor_witness mixed policy changes into its error; do not reuse those errors as wind-model bounds.

## Latest verified witnesses and limits

- pre_freeze_review.md records direct read-only recalculation: all four t=115 branches share observed complete prefix and old-action transition; nominal full 0–175 s trace is identical. Selected turn90 predicts 52.939700 m margin versus actual 52.956139 m. Continue tail still has 10.349735 m 60 s position error. All four are one source-state witness.
- Activated turn: enter115/apply116, target turns15 degrees at122, recheck130/rejoin131; sampled safe. Shared3 s reference delivery: sampled enters145/applies148; sampled safe and reactive invades the buffer. These two perturbations share one known source scene; not broad robustness or collision-rate evidence.
- Queue timing now matches modeled goal_delay. Sensor observation delay remains unsupported. Planning latency exceeds real-time periods; modeled3 s delivery does not validate arbitrary computation delays.
- hold60 jointly changes reassessment cadence and commitment. Preserve that interpretation in the fresh reactive/sample15/hold60 comparison.
- Historical interrupted implementation-defect batches remain preserved and excluded from efficacy claims. Fixed confirmation/long/static results are now complete and reviewed below; keep their separate scenario counts and limitations.

Evidence: design_review.md; pre_freeze_review.md; ../branch_validation.json; ../branches/; ../development2/; ../active_sensitivity/; current source hashes in pre_freeze_review.md.

## Completed-source evidence checks after freeze 29124b8

- final_evidence_checks.md verifies mixed_6: R7 current and R8 reactive full trajectories are equal, safe at293 s/+20.0524 m margin. R7 CPA variants share the failing prefix (buffer margin -19.5414 m, no entity collision). R8 sampled adds13.2577 m margin but costs43 s/118.2293 m. Do not count it as another reactive rescue.
- prediction_execution's error_15 can be shorter; nine of225 audited completed-development records are. Prefix error is own xy only, predicted minimum combines static/dynamic while actual field is dynamic-only, and forecast_valid is not feasible.
- Six development, two derived sensitivity and four paired hold episodes supplied225 correlated selected windows. All selected forecasts were feasible and source episodes safe; no false-safe incursion was observed. This is not225 independent safety tests or an error bound.
- Longer horizon_error can compare different future control programs. mixed_6 exit at176 has9.970 m prefix discrepancy but181.264 m horizon discrepancy after later online avoidance; do not assign the whole difference to wind/model error.
- Queue application deltas checked across all12 completed method episodes:1 s normally,3 s for the shared delay; no pending-overlap violations. Use changes records, since trajectory target fields are logged before boundary installation.
- The earlier development-stage check did not summarize running confirmation/long/static. The completed extension below supersedes that pending status.

Method-note spot check: use max_nfev=35 per start (first fit7 starts; numerical-Jacobian calls excluded), and allow predicted-arrival termination before60 s. See final_evidence_checks.md. No frozen-method change requested.

## Frozen evaluation extension — durable boundaries

- Evidence: final_evidence_checks.md, confirmation90 and long12/static12 raw traces; scientific freeze29124b8. Paired scenes/initial states/target traces and reconstructed actual safety agree. Confirmation gains are exactly pressure_2/4: genuine underway buffer incursions avoided, with positive entity margins and no endpoint events. Do not convert this to entity-collision reduction or a natural-traffic rate.
- The paired common-safe travel cost is material: sampled mean+15.285714 s, endpoint_5 maximum+267 s/+1008.844 m. That adverse episode combines intervention and later endpoint occupancy, not just hold duration. hold60 gets the same30/30 safety count at lower CPU cost;15 s superiority is unsupported.
- All922 confirmation selected common prefixes were recomputed, with no observed false-safe incursion. One confirmation plus two long selections use the flagged all-infeasible best-effort branch below30 m; these are not feasible solutions. Never generalize development fallback0 to the final set or call all selected forecasts guard-satisfying.
- Diagnostic coverage uses min(period,prediction length,actual remaining).53 confirmation windows are short; hold60 crossing_2 t310 predicts28 of55 actual remaining steps. No observed failure does not certify the uncovered tail. Own-position errors are not full-state/target errors or a calibrated safety bound.
- endpoint_1 t341 ordinary error reaches30.506 m over15 s and134.947 m over60 s without any avoidance in the actual episode. This discrepancy cannot be assigned to later policy switching. Fitted wind differs across15/60 cadence because the estimator carries previous fits; same raw state is not identical predictor state.
- The completed long planning peak is43.4595 s; physics-paused simulation and3 s modeled reference delivery do not establish15 s real-time execution. Preserve this limitation in final claims.

Delivery correction: error_15 is now named error_at_prefix_end, with prefix_steps retained. Reporting corrections include the3 fallbacks,53 truncated windows and estimator-history distinction. Delivery commit f75130d leaves reviewed scientific core unchanged from29124b8.
