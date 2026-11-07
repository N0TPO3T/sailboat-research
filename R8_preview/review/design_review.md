# R8 bounded design review

Status: same-family / provisional. No score, no scientific certification.
Review date: 2026-10-05. Read-only source review; no experiments were launched.
Scope: proposed candidate-waypoint GVO adaptation, causal independent physics predictor, finite hold and rolling reassessment. Reviewed server main at db9336dab91284044908f829b9b23f53148db693; context documents already had R8 edits. R8 implementation/results were not yet reviewed.

## Decision

Proceed with the small executable predictor/branch check. The proposed direction addresses the missing mechanism: different executable references should produce different predicted own-ship trajectories. Its scientific value remains unverified until the predictor ranks real maneuver outcomes and full tasks reduce underway incursions. Do not infer this from endpoint recovery or a nominally collision-free rollout.

The primary source is Wilkie et al. (2009), GVO equations (2), (3), (10), with finite-horizon sampling. This is an adaptation to closed-loop waypoint policies, not the paper's car-model reproduction or a safety guarantee. Source mapping is in source_notes.md.

## Findings that affect implementation

1. **Actuator targets are latent in raw14 but reconstructible from commands.** In third_party/senior/sailboat_s14.py:216-248 the persistent target sail/rudder angles accumulate scaled, floor-quantized increments, while raw14[8:10] contains actual angles approaching those targets under rate limits. Initializing target angles from current actual angles can change the next transition. Reconstruct targets from the known reset value and all causal issued commands, preserving per-step clipping, float scaling and negative floor division. Maintain these targets incrementally thereafter. Use a separate model instance; do not copy real environment globals, wind state or RNG. Evidence: reset target values at lines 773-774; Action_adapter at third_party/senior/utils_lstm.py:477-479; real scaling at continuous.py:167-170.

2. **First-step timing and memory are part of each candidate.** scripts/run_r7.py:38-67 computes a_t before planning, executes that old-reference command, then installs the selected reference at t+1. Thus every candidate has the same first physical step. Reconstruct the new frame using the predicted t+1 position, append a_t and the predicted observation, and rebuild policy memory before producing a_(t+1). Reusing the old-frame hidden state or taking two policy steps at t changes the controller. frames.py:80-124 and r7_dynamic.py:47-59 replay actual past commands and each historical target observation. Model predictions must never enter live history. A copied controller state is causal; a copied true environment is not an online predictor.

3. **The inverse wind estimate is delayed and may be non-identifiable.** A fit of (x_(t-1), a_(t-1), x_t) estimates the forcing during the previous transition. navigation.py:40-48 updates the real wind at the new boundary; that new sample is unavailable to the estimator. Call the estimate an inferred recent disturbance with its timestamp, then state the assumed extrapolation. Multiple wind vectors can fit weakly excited motion; a small residual alone does not establish correct candidate forecasts. Fit body velocities/roll/yaw with scaled residuals and actuator reconstruction, and inspect counterfactual prediction rather than only wind-angle error. This is a hypothesis requiring checks, not an observed failure of an unimplemented estimator.

4. **“Normal navigation” must retain its feedback.** A fixed current waypoint for the entire horizon is not the ordinary Relay policy. The R4 documented adverse case had six subsequent ordinary target replacements within 60 s (docs/R4_RESEARCH_REPORT.md:150). Model its actual replanning rules, manager state and target application delay when comparing against normal navigation. Define avoidance hold, continuation and rejoin as explicit candidate policies. If all candidates instead share a fixed-hold protocol, label and evaluate that altered baseline separately; do not credit gains against an inaccurately predicted nominal policy. A horizon longer than the committed hold is only a conditional forecast unless its continuation is defined.

5. **Safety screening must use synchronized motion and an explicit no-feasible case.** Check relative own/target segments at identical times, including the unavoidable first step, and static clearance throughout rollout; endpoint or reference-line clearance is insufficient. Target prediction uses current ID/timestamp/position/ground velocity, advanced from its observation timestamp. Do not expose target specs/turn tables. Separate 85 m evaluation geometry from planning guard and empirical error allowance. Mask predicted-unsafe candidates before optimizing progress/change cost. If every candidate is unsafe, log this and apply a stated best-effort response; neither a high score nor “keep current” makes the result feasible. Finite horizon and sampling do not establish recursive safety or feasibility.

6. **A hold requires updated danger handling and a defined exit.** A finite hold can prevent immediate cancellation, but stale forecasts can become wrong after a target turn. Explicitly state whether danger is checked during hold and what can cancel it. Compare normal, current avoidance and rejoin on the same current state and destination at renewal. Otherwise a short hold can repeatedly renew an unnecessary maneuver, recreating the 740 s failure without a long single lock. Include terminal progress and remaining task behavior, while permitting necessary temporary negative progress such as tacking.

7. **Do not mix information parity with environment identity.** World velocity depends on roll through J @ nu (senior/sailboat_s14.py:403-410); a simple heading rotation omits this. Known dynamics reuse is allowed, but estimated wind and approximate integration remain model assumptions. Each candidate needs its own model globals and recurrent memory. Candidate order must not affect predictions or the next real action. Real paired trajectories share an exogenous spatial/time field; after divergence they need not receive identical local wind. Runtime must report prediction/replay latency; a frozen simulation clock does not validate a 1 Hz deployment deadline.

## Minimal discriminative checks

These are recommended small checks, not a new audit platform or mandatory approval process.

| Check | Minimal comparison | Decision-relevant result |
|---|---|---|
| Transition identity | Isolated model against a controlled constant-wind diagnostic with identical known state and command; include negative sub-degree command, saturation and delayed actuator tracking | Distinguishes dynamics/quantization errors from wind-estimation error. Any privileged diagnostic wind stays outside the main method. |
| Causality/isolation | Freeze observed prefix; vary inaccessible future target/field data and candidate order; compare selected reference, live history and next real action | All online outputs must be invariant to inaccessible data and model sampling order. |
| Prefix/protocol parity | Same-state ordinary continuation versus actual branch; first candidate step common, then nominal/avoid/rejoin with declared hold and feedback | Distinguishes forecast error from a different policy or off-by-one target installation. |
| Useful candidate prediction | One confirmation85 underway incursion prefix, one normal success, one endpoint recovery and final_overtaking_1; compare nominal, avoidance and rejoin predictions with actual branches | Report error at closest approach, predicted/actual minimum margin, false-safe outcomes and ranking. Branches from one prefix are not independent samples. |
| Actual task benefit | Full paired tasks with common endpoint fallback; one candidate-independent prediction or geometry-only ablation, plus a truly activated target-turn/delay case | Underway collision/incursion changes, endpoint recovery and false-intervention tail costs remain separate. An offline best branch is not online success. |

Start with few candidates and a short horizon that covers meaningful controller response. Expand only if observed margin/ranking errors permit useful discrimination. If even controlled parity fails, fix the model/interface. If parity passes but inferred forcing cannot predict useful ordering, change identification/interface or controller within R8 authorization rather than hide failure with a larger buffer. If forecasts rank branches but full tasks do not improve, investigate rolling decisions and candidate coverage; do not declare a model breakthrough.

## Memory update

Retain in reviewer memory; no project memory file was edited:

- R7 final 30/32 to 32/32 was endpoint NoRouteError recovery, with zero collision/incursion in every final group; not collision reduction.
- R7 confirmation85 underway incursions and collisions remain unresolved by those final endpoint results.
- R4 feedback and R6 actuator quantization show that reference differences are not necessarily executed maneuver differences; compare whole candidate policies and effective commands.
- New source-level lesson: raw14 omits actuator target accumulators, but the current deterministic interface makes them reconstructible from causal commands; the newest transition-derived wind estimate has a one-interval information lag.

Limit: no new runs, implementation tests, trained models or performance numbers were produced by this review. Same-family / provisional status must accompany downstream use.

## Implementation follow-up — 2026-10-05

Status remains same-family / provisional; source review only, no score. No experiment or test was launched by the reviewer. Read the three new implementation files, check_r8_model.py, existing smoke_parity.json, saved provenance, and selected existing JSON fields. Initial development was interrupted by the owner; its interrupted.json explicitly excludes it from efficacy use. The owner restarted development2 after fixes. This review did not control any process.

### Verified information boundary and execution structure

- CausalModel constructs fresh SeniorModules, ContinuousPhysics and ObstacleController. SeniorModules owns separate mutable globals. initialize() copies observed raw state and reconstructs actuator target angles from commands starting from zero, using the inherited scaling, floor quantization and clipping. It accepts no real environment, field, scene seed or future target schedule. The internal reset seed is a fixed initialization constant, not the evaluation seed.
- estimate(history) uses observed raw-state midpoints, observed velocity/rate differences and the inherited force derivative. No hidden real wind enters this fit. Its midpoint approximation and fitted constant wind remain model assumptions. At six available intervals, pairs[::2] uses t-6→t-5, t-4→t-3 and t-2→t-1; it excludes the latest t-1→t interval. Report these actual intervals rather than describing an instantaneous wind measurement.
- rollout resets its own policy by replay, verifies the reproduced current command, and uses the supplied old_action at k=0. h/acts/oh are separate lists; appended simulated observations/actions are internal. Existing historical arrays and dictionaries are read by encoding, not overwritten. Each navigator is a deepcopy of AvailabilityRelay after the current nominal decision. Source inspection found no path from candidate rollouts back into live history or manager state.
- Nominal rollout calls AvailabilityRelay after each simulated step. Avoidance rollout holds the reference, skips nominal calls during the hold, and resumes AvailabilityRelay with current=None at k=hold. Online selection performs the same hold and incumbent reset. For hold=15, the first action is still old-reference, and the action already computed at t+15 is executed before a new decision takes effect at t+16. Subsequent model rejoin is a conditional tail: online reassessment may choose another avoidance. Do not call that entire tail a committed execution.
- The existing smoke_parity receipt reports equal 40 s raw prefixes and passed command-replay/environment-continuity assertions for its source version. These assertions are useful but do not establish candidate physical prediction accuracy, live-history isolation by test, or long-horizon safety. Updated-source tests were not rerun by this reviewer.

### Reported bugs and source-level repair verification

| Finding | Evidence and consequence | Follow-up status |
|---|---|---|
| Candidate-local NoRoute escaped into the real runner | Original r8_model called navigator.plan without handling planning failure; run_r8 caught it as real episode NoRouteError, stopping before the pending real action | Fixed in development2 r8_model.py:75-77: valid=False and prediction_failure; remaining candidates can be considered |
| Current reference inferred from stale/rounded raw14 goal | The runner stores history before applying a boundary goal. Example from old confirm_mixed_3: t=52 raw goal was approximately (483.588,-122.955), while the applied goal was (400,-150). Even unchanged noninteger references can differ after float32 storage, triggering a spurious frame rebuild | Fixed in development2 r8_model.py:68: use current_frame.goal_world and synchronize only the independent model goal |
| Expired held state survived a no-nearby early return | Original held remained non-null, so later incumbent=None repeatedly forced fresh nominal replanning; this was behavioral, not merely a missing release log | Fixed in development2 r8_planner.py:43-46: release event and held=None |
| Nominal-safe early stop | Original selection always preferred nominal when feasible; evaluating other candidates could not change that choice | New r8_planner.py:61 is selection-equivalent under the intended independent rollout contract; it reduces available diagnostic candidate data |

The reviewed updated files exactly matched development2/provenance.json:
- r8_model.py: ff24c889b6f9e5a2712bda6799c6ab0515c1c3f972c4259fdcece431ad4b5451
- r8_planner.py: 9fdd30319e826dbe3e9b9a3230fe292f41bb10bd045258b42e14ecbd1a020680
- scripts/run_r8.py: 76e8baef064459732bb6a8ab7b3918e7f3a8b1995c544b2c349611c00c343164

“Fixed” here means the observed code implements the identified repair; it does not mean a new regression run was executed by this reviewer.

### Remaining limitations and the smallest useful checks

1. **Incomplete forecast ranking remains a concern.** r8_planner.py:66 ranks all candidates by min_margin when no candidate meets feasibility, including valid=False and integration_failed trajectories. A two-step or otherwise truncated positive margin is not comparable with a complete horizon minimum. Prefer complete, numerically valid trajectories for the maximum-margin best effort; if none exist, record a distinct no-valid-forecast fallback. The existing all_predicted_infeasible flag correctly avoids calling this safe. A small synthetic selector check with one invalid high-margin prefix and one valid lower-margin trajectory isolates this issue; do not infer a performance effect without an actual occurrence.

2. **The initial predictor witness does not isolate prediction error.** check_r8_model.py passes navigator=None, which holds its target. The existing witness windows contain 5, 1 and 6 actual target applications for mixed_3, mixed_7 and final_overtaking_1. Their final position errors (about 43.99, 18.75 and 18.38 m) therefore mix model error with a different feedback policy. Use an unchanged-target branch or the same AvailabilityRelay continuation before attributing error to wind estimation. This witness limitation does not imply that the online implementation also omits feedback; online rollout now supplies it.

3. **Only zero observation delay and the current one-step reference interface are modeled.** future_obs and relative clearance use q+k v without adding current time minus observation timestamp. The predictor also has no pending delayed-reference queue. These are known limitations, not a present delay-zero bug. The owner explicitly selected an activated target-turn sensitivity instead of an unsupported delay run. A future delayed case needs timestamp propagation and the same queued application protocol, or an explicit statement that delay is an unmodeled perturbation.

4. **Hold safety remains open loop for its duration.** t<until returns immediately without checking new danger. The chosen 15 s hold is explicit and bounded, but target turns can invalidate the initial forecast. The planned activated-turn case should report whether a turn occurs during hold, how soon it is observed, the next selection/application times, and the observed minimum margin. No need to build a general traffic predictor.

For a later narrow regression pass, prioritize: candidate exception containment; nominal continuation immediately after a reference change, including a noninteger unchanged reference; and one expired-hold/outside-range continuation. These three tests distinguish the repaired implementation errors from scientific model limitations. Do not redo a broad audit or stop development solely for a larger checklist.

### Memory update from this follow-up

Keep the previous R7/R4 evidence boundaries. Add that recorded raw-state goal fields can lag reference installation and are float32, whereas the live frame/reference is authoritative for controller continuation. Keep candidate-local simulation failure separate from real episode failure. Do not promote the fixed-target witness errors to a validated wind-model error bound.
