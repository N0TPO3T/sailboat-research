# Supplementary Method and Reproduction Notes

## S1. Conditional mathematical explanations

The synchronized relative segment r(α)=r₀+αd has squared norm ||r₀||²+2αr₀ᵀd+α²||d||². For d≠0 its unconstrained minimizer is −r₀ᵀd/||d||²; projection to [0,1] yields the evaluator's minimum. For d=0, the segment is constant. Code avoids division when dᵀd≤10⁻¹². This is the exact minimum of a specified linear relative segment, not a continuous hull guarantee.

The wind objective substitutes an endpoint-midpoint evaluation under a trial constant wind for an observed step's average derivative. The residual combines local-constant-wind error, midpoint approximation, numerical integration and other model discrepancies. No independent Gaussian-noise assumption or inverse-covariance interpretation is used. Finite bounded nonlinear least squares returns a local numerical estimate. Multiple starting points do not prove uniqueness or global optimality.

The supervisor is nominal-first. Write F(ρ) for valid predictions meeting the guard. If nominal is in F, it returns before costs are compared. If nominal is not in F and F is nonempty, every member of F receives the same 20 m offset, so removing that constant only in this branch leaves ordering unchanged. The statement does not hold globally. For a hypothetical tied-margin fallback with nominal and continuation both at 10 m clearance, their terminal distances 100/90 m become costs 100/110 m under the original rule. Removing 20 globally would change the winner. This example explains algebra; it is not a navigation result. No scientific code was changed to remove the offset.

For a common time domain, obstacle identity set and exclusion radii, the reverse triangle inequality gives | ||p−q||−||p̂−q̂|| |≤||p−p̂||+||q−q̂||. If the latter is bounded by E uniformly on that common domain, taking minima on the same protocol/time/obstacle domain gives |M−M̂|≤E, with M=m_real(γ;T,O) and M̂=m̂(γ;T,O). This is not a bound on the unrestricted whole-task metric. Static centers contribute no target-position error. For synchronized piecewise-linear representations, endpoint error bounds extend to interpolated positions by convexity. A safety conclusion additionally requires an available bound E<ρ; the present finite observed errors do not provide such a bound. Shared execution protocols are required to interpret the discrepancy as prediction quality rather than later policy changes. The bare inequality does not itself prove that the predictor is accurate.

At one frozen decision, increasing ρ shrinks F. It does not imply monotone closed-loop safety, navigation time or path length: a changed selection modifies later states and decisions. All four prespecified guards must therefore be shown, including adverse or nonmonotone results.

## S2. Exact reconstruction and timing

Reference selection at t follows computation of the old-reference action. That action drives t→t+1. A changed reference applies at t+1, and can first affect t+1→t+2. Hold/review timers start at selection t. For period P, holding short-circuits while t'<t+P; at equality the nominal manager is called with incumbent cleared. The resulting release reference applies at t+P+1. For H=P=60 the 60-step prediction contains no post-release tail.

Actuator targets are reconstructed by accumulating the complete actual commands from their zero initial values. Policy memory is reconstructed through the current frame from true historical state/obstacle observations and issued commands. Equality of the current action is asserted, not equality of every hidden tensor. A clone of the nominal manager AFTER its actual current call is supplied independently to each candidate. The prediction tail executes that nominal manager, not another future candidate-search loop.

Predicted policy/relay observations retain the 1000 m cutoff. Clearance evaluation retains every target valid in the initial prediction observation list even if its extrapolated position later leaves that range. No new unobserved arrivals are synthesized. The experimental tasks contain one target; paired error analysis uses that common observed target and the same static map.


### Input ordering and replay contract

The unnormalized 18-element policy input, in zero-based index order, is:

| Index | Quantity | Unit / frame |
| --- | --- | --- |
| 0, 1 | x, y | m, active reference frame |
| 2 | Roll | rad |
| 3 | Wrapped heading minus frame angle | rad, active reference frame |
| 4, 5 | Surge, sway | m/s, body frame |
| 6, 7 | Roll rate, yaw rate | rad/s |
| 8, 9 | Actual sail angle, actual rudder angle | rad |
| 10 | Previous minus current distance to the active reference | m; zero at the initial state |
| 11 | Previous minus current absolute x-distance to local x=500 | m; zero at the initial state |
| 12, 13 | Active reference coordinates | (500,0) m |
| 14, 15 | First encoded obstacle distance, relative bearing | m, rad relative to actual vessel heading |
| 16, 17 | Second encoded obstacle distance, relative bearing | m, rad relative to actual vessel heading |

Obstacle pairs are sorted lexicographically by encoded distance then relative bearing. Encoded distance is max(0, center distance minus exclusion radius plus 40 m). Only values at most 150 m enter the policy; missing pairs are (0,0). Static obstacles and moving-obstacle observations at the historical state's own time are combined before sorting. Body velocities and angular rates are not rotated. The frozen normalization is (input-mean)/(sqrt(variance)+10^-6), applied to current and previous state inputs; preceding normalized Actor commands are used directly.

At boundary t, recorded states contain s_0 through s_t and commands contain a_0 through a_(t-1). Reset clears the recurrent and attention dictionaries; the Actor initializes zero hidden/cell state and a zero-padded ten-slot output history. Reencode every state in the frame active at reconstruction. Replay exactly t Actor calls using (encoded s_i, encoded s_(i-1), a_(i-1)); at i=0, repeat encoded s_0 and use the zero command. Discard replay action outputs. The subsequent current call uses encoded s_t, encoded s_(t-1), and a_(t-1). This rebuilds memory conditional on recorded actions, not a counterfactual past trajectory under the new reference.

Actuator setpoints are computed separately from the command prefix: scale each two-element command by 10 degrees, floor signed increments to integer degrees, add to the preceding setpoint and clip sail/rudder targets to ±90/±30 degrees. Initial setpoints are zero. Actual actuator angles come from the current physical state. Independent branches share the reconstructed initial state and pending action, then advance separate simulated histories. A new reference triggers the same frame-reencoding procedure after delivery.

Verified implementation locations in the recovery archive: src/sailboat_routing/frames.py (LocalFrame.encode, reencode_controller); r6_controller.py (ObstacleFrame.encode); r7_dynamic.py (HistoricalFrame); r8_model.py (initialize, rollout); obstacle_candidate.py (ObstacleController.act); third_party/obstacle_candidate/utils_lstm_att_normal.py (Actor).

### Nominal route-manager geometry and wind convention

The temporary-endpoint manager evaluates the static chart plus circular exclusions centered at the currently observed target positions. A point is clear only if it is finite, inside the inclusive map bounds, and strictly farther than each exclusion radius from its circle center. A segment is clear only if both endpoints are clear and its closest-point distance to every circle center is strictly greater than that circle's exclusion radius; tangency is rejected. A zero-length segment reduces to the point test. Static exclusion radii equal entity radius plus 60 m; the target exclusion radius is 85 m.

The goal is occupied when it fails the point-clear test. While occupied, an incumbent is retained only if it is more than 100 m from the boat and both the incumbent point and boat-to-incumbent segment are clear. Otherwise eight candidates are placed at angles k*pi/4 on a 305 m goal-centered ring. Each candidate must be at least 200 m from the boat, have a clear boat-to-candidate segment, and have at least 120 m residual clearance from all chart exclusion boundaries. Ranking uses boat-to-candidate Euclidean distance in metres plus (80 m/rad) times the absolute wrapped turn from current heading to candidate bearing, in radians. Goal availability clears the temporary incumbent and restores the nominal route. These predicates document the evaluated implementation; they do not add a safety guarantee.

The fitted wind has world-frame Cartesian components (w_x,w_y) in m/s. The dynamics receive speed norm(w) and direction atan2(w_y,w_x), wrapped to [-pi,pi). Direction is blowing toward, not the meteorological blowing-from convention. The fit uses physical world states; it does not rotate wind into the active reference frame. Code locators: planner.py (StaticMap.point_clear, segment_clear), r8_planner.py (AvailabilityRelay.plan), r8_model.py (set_wind), and wind_fields.py (sample).

## S3. Low-order comparator specification

State: planar position p, course χ, course rate r. Causal initialization uses the last displacement for speed/course and the median of the last three course increments for r. Its heading input to the unchanged nominal manager is predicted course plus the current observed heading-minus-course offset. The manager's velocity input uses the same ten-transition position window.

For each one-second prediction step after the common candidate-independent first step, desired course rate is clip(κ·wrap(bearing(g−p)−χ),−r_max,r_max). Rate approaches this value with multiplier 1−exp(−1/τ). Course advances by the new rate; position advances at fixed causal speed along the midpoint course. References apply after the step, and nominal feedback resumes at the same hold boundary as detailed prediction. Forecast target visibility, clearance radii, predicted-arrival stopping, candidate generation, ranking and fallback remain shared.

Calibration grid: τ∈{1,3,8,20}s, κ∈{.025,.05,.1,.2}s⁻¹ and r_max∈{.04,.08,.16}rad/s. Selection minimizes the mean over source tasks of their mean 15-second position error. Seven training and five validation source scenes, 136/87 unchanged-reference windows, are all old development data. The selected parameters are (8,.1,.16). The upper-bound rate cap and limited calibration support are reported rather than treated as physical identification. The model does not use the old_action argument, wind fitting, recurrent policy or actuator state. Its zero wind field in inherited logging is a placeholder and means N/A. Differences cannot be attributed solely to numerical dynamics order.

## S4. Numerical and computation protocols

Fixed-protocol branches replay real past commands through the original physical simulator and external field, preserving command application and controller history. Prefix states must match exactly. The selected branch's first 15 seconds must also match its source. Real branches alone query actual external evolution; online predictors never receive the field, seed or future target schedule. Fixed protocols release to the cloned nominal manager and suppress new search for their 60-second assessment. Any earlier real or predicted stop limits the common domain.

Numerical safety checks add an observation-only hook at accepted custom Dormand–Prince substeps. They retain original commands, tolerances and endpoints. Relative segment minima use target positions at the corresponding fractional absolute times. Maximum accepted step is 0.1 s. These finer linear segments are stronger local numerical evidence than the one-second chord, but are not dense analytic interpolation, a changed closed-loop result or a formal continuous-safety proof.

The representative planning profile reuses three real decision inputs, each three times for each predictor. It includes causal estimation and candidate rollout/selection with nominal early return; it excludes model loading, initial nominal/candidate setup and real feedback execution. The pressure state evaluates six detailed candidates versus one low-order nominal; the endpoint state evaluates six each; the non-conflict state evaluates one each. This is the operational estimation/rollout/selection core, not an equal-work per-candidate speed ratio. Stage restore inputs and hardware/thread limits are fixed. Measurements remain empirical timings on a shared host, not hard deadlines. Episode CPU includes all actual execution and setup and must not be substituted for a planning deadline.

## S5. Reproduction records

The recovery archive identifies the evaluated code, inherited assets and frozen configuration. Its plan.json, freeze.json, calibration.json and development/guard/confirmation manifests specify the experiment identities. The primary dataset is the 24-task confirmation with all three methods and all failures retained. Raw traces contain scene definitions, actual states, commands, target observations, reference changes, candidate predictions and failure reasons.

The low-order model is src/sailboat_routing/r12_model.py. Detailed prediction and supervision are r8_model.py and r8_planner.py; scripts/run_r12.py imports the unchanged physical worker. Scripts prepare_r12.py, prepare_r12_confirmation.py, analyze_r12_prefix.py, check_r12_branches.py, profile_r12.py and analyze_r12.py define calibration, task generation and diagnostics. The evidence index locates the complete archive; the lightweight manuscript package alone does not contain all model weights and raw traces.


## S6. Separate historical evidence and version map

### A. Historical gains and intervention costs

Table I preserves the original evidence groups. The 13 seen mechanism instances overlap R8 and cannot be added to it. R8 S15 rescues two short and one long reactive failures. R10 new confirmation has no additional safe completions over R; ten of its twelve R/S15 trajectories are identical. Its mean common-safe S15−R time is +27.08 s, with an endpoint case at 584 versus 313 s (+271 s). Holding without comparing alternatives is not a sufficient substitute: NH succeeds on 9/13 seen and 11/12 new tasks. S60 remains competitive; on the twelve new tasks S15 is 9.25 s faster on average than S60 but uses 777.05 versus 328.77 s total episode CPU. These historical comparisons do not determine the new predictor comparison.

Table I. Historical safe completions, reported separately. *Overlaps R8; no pooled total.

| Evidence group | n | R | S15 | S60 | NH |
| --- | --- | --- | --- | --- | --- |
| R8 short | 30 | 28 | 30 | 30 | — |
| R8 long | 4 | 3 | 4 | 4 | — |
| R10 seen* | 13 | 11 | 13 | 13 | 9 |
| R10 new | 12 | 12 | 12 | 12 | 11 |


R8: detailed predictor original closed-loop study. R10: same main ideal-compute method with new confirmation and overlapping mechanism cases. R12: same frozen detailed method plus calibrated L; 24 frozen tasks. R13: textual/figure revision and log reanalysis; no changed algorithm or new main-task outcomes. 

## S7. Grouped fixed-protocol diagnostics

| Snapshot | Source / time | Circle protocol | Triangle protocol | Common time |
| --- | --- | --- | --- | --- |
| 1 | r8new_mixed_pressure_2 / 149 s | turn-90 | nominal | 60/60 s |
| 2 | r8new_mixed_pressure_4 / 228 s | continue | nominal | 60/60 s |
| 3 | r10new_endpoint_0 / 247 s | turn45 | nominal | 58/58 s |
| 4 | r8new_endpoint_1 / 341 s | nominal | continue | 60/60 s |
| 5 | r8new_nonconflict_0 / 56 s | nominal | continue | 60/60 s |
| 6 | r10new_mixed_pressure_0 / 157 s | turn-90 | nominal | 60/60 s |

The six source tasks were explicitly listed in scripts/check_r12_branches.py, rather than sampled randomly. Snapshots 2, 3 and 6 use the first recorded non-nominal entry in their chosen task; snapshot 5 uses the first prediction. Snapshots 1 and 4 use fixed times 149 s and 341 s. The code establishes these rules but does not document a prospective statistical selection criterion for the two fixed times. Each state compares the selected protocol with nominal, or continuation when nominal was selected. Consequently the twelve-branch median is a descriptive diagnostic of selected development states, some of which overlap low-order calibration data.

Two protocols share one source state; snapshot 4 even duplicates the paths. Branch/window counts are diagnostic workload, not independent sample sizes.

## S8. Unique confirmation difference

`evidence/decision_260.csv` contains all evaluated candidates at the same physical/history state at 260 s in `runs/r12_revision_20261006/confirmation/r12new_mixed_pressure_1__{sampled,simple}/trace.json`. `evidence/case_analysis.json` records the prefix equality check and complete-task minima. No unexecuted L alternative is invented after its nominal early return. The matched state validates a decision contrast, not a claim that this single intervention caused the whole-voyage rescue.

## S9. Reproduction assets and model provenance

The supplied dynamics implementation, 18-input Actor and matching normalizer come from the codebase associated with Yang et al. [8] and were provided by Chao Yang. Permission covers research use and provision of reproduction materials to editors and reviewers upon request. Public release of these exact assets is not established. The original training-run linkage remains undocumented; the 14-input policy described in the journal article is not used as an identical checkpoint baseline.

The asset files are checkpoints/obstacle_candidate/saclstm_s14obst_noise_0204_actor10800.pth and its matching normalizer10800.pth. evidence/ASSET_HASHES.json and asset_resume_check.json record exact identities. evidence/dynamics_parameters.json records the inherited physical parameters; INHERITED_SOURCE_CHECK.json identifies source versions. Numerical details and the complete recovery procedure appear in S11 and S14.


## S10. Primary confirmation scene envelope

All 24 tasks: start(0,0), goal(1000,0)m, one constant-velocity target. Random generation seed 202610612, physical seed 2026106120+i. Each family alternates stable/fast wind (total 12/12). No outcome filtering or new R13 sampling.

| Family (n) | Initial target position (m) and velocity (m/s) | Base wind (degrees) | Static context |
| --- | --- | --- | --- |
| Pressure (8) | q=(x,sT), x∈[620,710], T∈[185,230]s, s∈[.65,.95]; v=(0,−s) | [115,135] | Circle center(850,300), entity radius45m |
| Crossing (4) | q=(x,−sT), x∈[420,540], T∈[140,220]s; v=(0,s), s∈[.65,.95] | [45,80] | None |
| Overtaking (4) | q=(x,y), x∈[230,300], y∈[−15,15]; v=(s,0), s∈[.65,.95] | [45,80] | None |
| Endpoint (4) | q=(x,y), x∈[610,650], y∈[−15,15]; v=(s,0), s∈[.8,1.0] | [45,80] | None |
| Non-conflict (4) | q=(x,±y), x∈[500,600], y∈[340,390]; v=(s,0), s∈[.65,.95] | [45,80] | None |

All draws use the exact ordering in code/scripts/prepare_r12_confirmation.py; the manifest lists realized values. “Pressure” changes several factors jointly. Paired method contrasts remain matched within each scene, but this study does not assign the gains to one of those factors alone. These are newly generated supervisor tests, not verified holdouts from unknown inherited policy training.

## S11. Recovery procedure and numerical checks

The separate R13_REPRODUCTION_internal.zip archive contains source dependencies, the Actor and normalizer, requirements.lock, manifests and all 72 primary confirmation traces. CONTENTS_SHA256.json and verify_recovery.py are included. Extract to a new directory, prepare the documented dependency environment, and run python verify_recovery.py. The stored recovery check verified all packaged hashes, constructed and closed CausalModel with the actual weights, imported the physical worker and recomputed the primary counts and common-safe time differences. evidence/recovery_check.json and recovery_check.log record that check; it was not a new navigation experiment.

Three observation-only accepted-substep replays of r12new_mixed_pressure_1 use unchanged original commands and tolerances. All one-second endpoints match exactly. R/L/S15 minima are −0.162187/−1.117383/42.094165 m on accepted-substep segments and −0.162187/−1.115322/42.095555 m on the original one-second segments. Maximum substep is 0.1 s. These replays support the numerical labels for the circular exclusion proxy. They do not establish exact swept-hull safety. evidence/new_case_substeps.json records the values.


## S12. Relation to the published sources

Yang et al. [8], Applied Ocean Research 175 (2026) 105246, describes a 14-dimensional wind-input-free observation in Section 2.3, equation (27). The present 18-input attention asset is identified independently by code, observation ordering, normalization and checkpoint hashes. The journal's reported benchmark performance is not assigned to this asset. The article reports a public v1.0.3 software release, but membership of the evaluated actor10800 and normalizer in that release has not been established; no released asset was substituted in these experiments.

The model lineage is Xiao and Jouffroy [10]. The original author's software page identifies the corresponding 2014 sailing-yacht model release. The supplied Python implementation retains its existing notices; exact equivalence to the original implementation is not established. An article license is not assumed to license separate code or weights. These source distinctions separate bibliographic attribution, numerical model identity and access to reproduction materials.


## S13. Implementation edge cases

A nonempty rollout with no obstacles has predicted minimum +infinity; a zero-step rollout uses −10^9 m and fails the guard. The prediction-local physical clock starts at zero, while nominal management uses absolute task time. Inherited dynamics parameters include mass 25,900 kg and sail/rudder/keel areas 170/1.17/8.7 square meters. These settings are implementation details, not additional contributions.

The low-order comparison replaces recurrent-policy, actuator, wind and speed dynamics together. Its calibration covers unchanged-reference 15-second windows and does not establish 60-second hold/release fidelity. Historical input-adapter checks and detailed-prediction experiments retain their own datasets; they are not pooled with the 24-task primary confirmation.


## S14. Detailed settings and diagnostic records

The midpoint s̄ uses endpoint averages, except shortest-angle heading interpolation. Sail/rudder inputs are averages of observed endpoint angles, with zero within-step increments for this derivative evaluation. D=diag(1,1,5,5) is empirical scaling in stored units, not an estimated noise covariance. A bounded local least-squares solver searches componentwise w∈[−16,16]² m/s. The initial prior (0,8) and six magnitude-8 initializations separated by 60 degrees are tried on the first fit; subsequent fits warm-start from the preceding estimate. Each start has max_nfev=35 and finite-difference step 10⁻³. Insufficient history retains the current estimate. Neither a global minimum nor wind identifiability is guaranteed.

Within each task, physical policy, normalizer, dynamics, initial conditions, map, external wind parameters, target motion, execution timing and evaluation are shared. Different paths may encounter different local wind. Reactive relay R uses nominal feedback without future candidate rollout. Search15 S15 is the detailed predictor with P=15; Search60 S60 retains the same candidates/H but uses P=60. Nominal-prediction hold NH predicts nominal and, if invalid, integration-failed or below guard, holds the current reference when available without evaluating alternatives. NH is not a no-prediction baseline; S60 is not a no-search method.

Existing detailed-prediction logs provide actual selected-protocol prefixes until the next review or earlier prediction/real termination. Complete 15-second windows and truncated windows are reported separately; post-replanning tails are excluded. Six development snapshots additionally execute two fixed protocols each, to 60 seconds or actual termination. All twelve branches must reproduce the original physical prefixes. The six actually selected branches must additionally reproduce the first 15 seconds of positions from their original continuations; the alternatives are not subject to that selected-continuation parity check. Predictors use only causal inputs; offline real branches alone advance the actual external field.

For two decisive meter-scale incursions and their safe S15 pairs, fixed issued commands are replayed with the original integrator while logging its accepted internal substeps. Endpoint parity must remain exact. Synchronized substep-segment clearance supplements, and does not replace, the original one-second metric. Hardware is an AMD EPYC 7V12 host with at most four one-thread CPU experiment workers and no GPU. Pure planning calls and complete-episode CPU are distinguished; no online deadline is claimed.

An additional same-command check of the unique new case preserves every one-second endpoint exactly and gives R/L/S15 substep minima −0.162/−1.117/42.094 m, retaining all three labels. This is a numerical replay, not three new tasks. Historical accepted-integrator-substep checks also preserve every one-second endpoint exactly. The two historical reactive incursions remain −1.225 and −0.872 m. Their S15 minimum margins change from 43.589/38.455 m under one-second segments to 43.597/38.425 m under accepted-substep segments (maximum substep 0.1 s). Thus these particular gain labels do not arise solely from a one-second chord sign error. This is still a numerical circular-proxy check, not swept-hull or formal continuous safety.

Nine measurements of the estimation/rollout/selection core per model at three fixed states give detailed median/p95/maximum wall times 17.009/17.662/17.685 s, compared with 0.067/0.136/0.136 s for L. The states include two risk decisions and ordinary feedback, each repeated three times. The timer excludes initial nominal/candidate setup and model loading. Nominal early return can evaluate different candidate counts, so this is not an equal-work per-candidate speed ratio. Complete new-confirmation episode CPU totals are 270.68, 2133.23 and 378.44 s for R, S15 and L. These measures include different work and are not interchangeable. Detailed calls can exceed the 15 s review period; physical time remains paused here. 
