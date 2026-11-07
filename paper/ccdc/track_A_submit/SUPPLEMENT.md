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

## S3. Low-order comparator specification

State: planar position p, course χ, course rate r. Causal initialization uses the last displacement for speed/course and the median of the last three course increments for r. Its heading input to the unchanged nominal manager is predicted course plus the current observed heading-minus-course offset. The manager's velocity input uses the same ten-transition position window.

For each one-second prediction step after the common candidate-independent first step, desired course rate is clip(κ·wrap(bearing(g−p)−χ),−r_max,r_max). Rate approaches this value with multiplier 1−exp(−1/τ). Course advances by the new rate; position advances at fixed causal speed along the midpoint course. References apply after the step, and nominal feedback resumes at the same hold boundary as detailed prediction. Forecast target visibility, clearance radii, predicted-arrival stopping, candidate generation, ranking and fallback remain shared.

Calibration grid: τ∈{1,3,8,20}s, κ∈{.025,.05,.1,.2}s⁻¹ and r_max∈{.04,.08,.16}rad/s. Selection minimizes the mean over source tasks of their mean 15-second position error. Seven training and five validation source scenes, 136/87 unchanged-reference windows, are all old development data. The selected parameters are (8,.1,.16). The upper-bound rate cap and limited calibration support are reported rather than treated as physical identification. The model does not use the old_action argument, wind fitting, recurrent policy or actuator state. Its zero wind field in inherited logging is a placeholder and means N/A. Differences cannot be attributed solely to numerical dynamics order.

## S4. Numerical and computation protocols

Fixed-protocol branches replay real past commands through the original physical simulator and external field, preserving command application and controller history. Prefix states must match exactly. The selected branch's first 15 seconds must also match its source. Real branches alone query actual external evolution; online predictors never receive the field, seed or future target schedule. Fixed protocols release to the cloned nominal manager and suppress new search for their 60-second assessment. Any earlier real or predicted stop limits the common domain.

Numerical safety checks add an observation-only hook at accepted custom Dormand–Prince substeps. They retain original commands, tolerances and endpoints. Relative segment minima use target positions at the corresponding fractional absolute times. Maximum accepted step is 0.1 s. These finer linear segments are stronger local numerical evidence than the one-second chord, but are not dense analytic interpolation, a changed closed-loop result or a formal continuous-safety proof.

The representative planning profile reuses three real decision inputs, each three times for each predictor. It includes causal estimation and candidate rollout/selection with nominal early return; it excludes model loading, initial nominal/candidate setup and real feedback execution. The pressure state evaluates six detailed candidates versus one low-order nominal; the endpoint state evaluates six each; the non-conflict state evaluates one each. This is the operational estimation/rollout/selection core, not an equal-work per-candidate speed ratio. Stage restore inputs and hardware/thread limits are fixed. Measurements remain empirical timings on a shared host, not hard deadlines. Episode CPU includes all actual execution and setup and must not be substituted for a planning deadline.

## S5. Reproduction and source boundaries

The authoritative project is `/home/ot/Students/hs/sailboat-routing-v0`; R12 evidence is `runs/r12_revision_20261006/`. `plan.json`, `freeze.json`, `calibration.json` and the development/guard/confirmation manifests define scope and identity. `original_hashes.json` protects old scientific files and R11. `CODE_FORMULA_AUDIT.md` records actual source positions and mathematical alignment. No R8/R10/R11 results, model weights or upstream assets are overwritten.

Scripts: `prepare_r12.py`, `run_r12.py`, `prepare_r12_confirmation.py`, `analyze_r12_prefix.py`, `check_r12_branches.py`, `profile_r12.py`, `analyze_r12.py`, and the final plotting script. The only new online model is `src/sailboat_routing/r12_model.py`; the original supervisor and physical worker are imported unchanged. Raw traces retain each actual trajectory, target observations, commands, changes, predictions and failures. The preview is not a substitute for all weights/raw traces; exact source/asset hashes and existing recovery archives are indexed separately.

R12 confirms a finite set of claims only. Future model improvement, retraining, target maneuvers, multi-vessel rules or real-time delivery require separate evidence and are not automatically initiated by this revision.


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


R8: detailed predictor original closed-loop study. R10: same main ideal-compute method with new confirmation and overlapping mechanism cases. R12: same frozen detailed method plus calibrated L; 24 frozen tasks. R13: textual/figure revision and log reanalysis; no changed algorithm or new main-task outcomes. R9 delayed execution is a different protocol, not pooled.

## S7. Grouped fixed-protocol diagnostics

| Snapshot | Source / time | Circle protocol | Triangle protocol | Common time |
| --- | --- | --- | --- | --- |
| 1 | r8new_mixed_pressure_2 / 149 s | turn-90 | nominal | 60/60 s |
| 2 | r8new_mixed_pressure_4 / 228 s | continue | nominal | 60/60 s |
| 3 | r10new_endpoint_0 / 247 s | turn45 | nominal | 58/58 s |
| 4 | r8new_endpoint_1 / 341 s | nominal | continue | 60/60 s |
| 5 | r8new_nonconflict_0 / 56 s | nominal | continue | 60/60 s |
| 6 | r10new_mixed_pressure_0 / 157 s | turn-90 | nominal | 60/60 s |

Two protocols share one source state; snapshot 4 even duplicates the paths. Branch/window counts are diagnostic workload, not independent sample sizes.

## S8. Unique confirmation difference

`evidence/decision_260.csv` contains all evaluated candidates at the same physical/history state at 260 s in `runs/r12_revision_20261006/confirmation/r12new_mixed_pressure_1__{sampled,simple}/trace.json`. `evidence/case_analysis.json` records the prefix equality check and complete-task minima. No unexecuted L alternative is invented after its nominal early return. The matched state validates a decision contrast, not a claim that this single intervention caused the whole-voyage rescue.

## S9. Reproduction assets and limitations

`evidence/ASSET_HASHES.json`, `dynamics_parameters.json`, and `INHERITED_SOURCE_CHECK.json` specify the exact inherited files. Yang et al. [9] is the formal related research source; Chao Yang supplied the inherited dynamics implementation, 18D Actor and matching normalizer. On 2026-10-07 the user explicitly confirmed the provider's permission for this study and provision of complete source/model/reproduction materials to editors and reviewers. The confirmation is a user-reported statement, not a fabricated license file or signed correspondence. Exact asset identities and archive locations are checked in evidence/asset_resume_check.json. With this permission, the source, weights, matching normalizer, configurations and records can be provided upon request. No public release of the exact 18D assets or new open-source license is claimed. Original training-run linkage remains unknown; the journal's 14D benchmark is not reproduced or used as an identical checkpoint baseline.


## S10. Primary confirmation scene envelope

All24 tasks: start(0,0), goal(1000,0)m, one constant-velocity target. Random generation seed202610612, physical seed2026106120+i. Each family alternates stable/fast wind (total12/12). No outcome filtering or new R13 sampling.

| Family (n) | Initial target position (m) and velocity (m/s) | Base wind (degrees) | Static context |
| --- | --- | --- | --- |
| Pressure (8) | q=(x,sT), x∈[620,710], T∈[185,230]s, s∈[.65,.95]; v=(0,−s) | [115,135] | Circle center(850,300), entity radius45m |
| Crossing (4) | q=(x,−sT), x∈[420,540], T∈[140,220]s; v=(0,s), s∈[.65,.95] | [45,80] | None |
| Overtaking (4) | q=(x,y), x∈[230,300], y∈[−15,15]; v=(s,0), s∈[.65,.95] | [45,80] | None |
| Endpoint (4) | q=(x,y), x∈[610,650], y∈[−15,15]; v=(s,0), s∈[.8,1.0] | [45,80] | None |
| Non-conflict (4) | q=(x,±y), x∈[500,600], y∈[340,390]; v=(s,0), s∈[.65,.95] | [45,80] | None |

All draws use the exact ordering in code/scripts/prepare_r12_confirmation.py; the manifest lists realized values. “Pressure” changes several factors jointly. Paired method contrasts remain matched within each scene, but this study does not assign the gains to one of those factors alone. These are newly generated supervisor tests, not verified holdouts from unknown inherited policy training.

## S11. R13 recovery and numerical checks

R13_REPRODUCTION_internal.zip is a separate internal archive containing source dependencies, Actor/normalizer, requirements.lock, manifests and all72 confirmation traces. It is available for this project and, with the provider's permission confirmed by the user, can be provided to editors and reviewers upon request. It is not claimed to be publicly released and confers no additional open-source license. SHA256 index and verify_recovery.py are inside it. In a new directory with the existing project Python environment, the script verified every packaged hash, constructed/closed CausalModel with actual weights, imported run_r12.worker, and recomputed19/23/24 plus23common-safe S15−L mean7s and maximum308s. No new navigation trial was needed for this recovery check. evidence/recovery_check.json/log identify the real directory and outputs. Reproduction command after extraction: python verify_recovery.py. Dependencies remain those in requirements.lock; no new packages were installed.

Three observation-only accepted-substep replays of r12new_mixed_pressure_1 use unchanged original commands and tolerances. All1s endpoints match exactly. R/L/S15 minima at accepted-substep segments are−0.162187/−1.117383/42.094165m; corresponding original1s minima are−0.162187/−1.115322/42.095555m. Maximum substep0.1s. This supports numerical labels, not exact hull safety. Plan, script and evidence: NUMERIC_PLAN.md, check_case_substeps.py, evidence/new_case_substeps.json.

## S12. Source follow-up and access status

The supplied formal paper is Yang et al. [9], Applied Ocean Research 175 (2026) 105246, DOI 10.1016/j.apor.2026.105246. The actual supplied file is main.pdf (19 pages; SHA256 9bc5165d59141e64c32cea5f4fbc2f4464c6fe0f88b40334de85703b92d356b9), called main(1).pdf in the request. Page 1 verifies the bibliographic identity; Section 2.3, equation (27), page 6 specifies a 14-dimensional wind-input-free observation. Our actual asset is an 18-input attention variant from the related codebase, identified independently by code, input ordering, normalization and checkpoint hashes. We do not claim that the journal reports this exact variant's training or benchmark performance. Page 19 credits Chao Yang with Software and Methodology, while other authors also have Software roles; sole authorship of all inherited files is not asserted.

The journal's page 18 reports a public v1.0.3 release at https://github.com/Sailboat-RL-4DOF-Control/sailboat2026/releases/tag/v1.0.3 . This is the paper's availability statement; exact membership of our actor10800/normalizer in that release has not been checked and is not claimed. No released asset was downloaded to replace the evaluated files. The previously inspected local thesis draft remains an unpublished local document, not proof of an awarded thesis or this checkpoint's original training run.

The original author's software page https://www.mathworks.com/matlabcentral/fileexchange/47981-sailingyachtmodel-zip identifies Jerome Jouffroy's 2014-10-02 release and credits Xiao/Jouffroy [8]. Its existing notice/disclaimer conditions are preserved; equivalence of our Python port to the original source is not established. The journal's CC BY article license is not assigned to the Python code or weights. The user confirmation now resolves the previously missing provider attribution and research/reviewer-provision permission. It does not supply unknown training records, public-release status or this paper's author order, affiliations and funding. SOURCE_FOLLOWUP.md records the exact basis and scope.

[9] C. Yang, B. Guo, Y. Zhang, Y. Gu, Y. Li, S. Huang, H. Huang, J. Dong, and P. Li, “Learning to sail without wind information: reinforcement learning-based control for unmanned sailing vessels under partial observability,” Applied Ocean Research, vol. 175, Art. no. 105246, 2026, doi: 10.1016/j.apor.2026.105246.


## S13. Editorial consolidation and implementation edge cases

The submission-track manuscript reorganizes R13 without changing methods, configurations, weights, numerical results or plots. Table II stratifies the same 24 confirmation tasks: pressure 3/7/8 for R/L/S15; each remaining four-task family is 4/4/4. The R12 24-task confirmation is the primary comparison; R8/R10 are historical/development evidence. The detailed-versus-L comparison replaces recurrent policy, actuator, wind and speed dynamics together and is not an isolated model-order ablation. L calibration covers 15-second unchanged-reference windows; it does not establish 60-second, side-reference or hold/release prediction fidelity.

The exact implementation edge cases remain: a nonempty rollout with no obstacles has predicted minimum +infinity; a zero-step rollout uses −1e9 m and fails the guard. The prediction-local clock starts at zero while nominal management uses absolute task time. Dynamics parameters include mass 25,900 kg and sail/rudder/keel areas 170/1.17/8.7 square meters. Progress inputs are previous minus current goal distance and previous minus current |500−x_local|, initially zero. Body velocities remain in the body frame. These implementation details remain part of reproduction, rather than separate theoretical contributions.

The existing internal recovery archive is preserved byte-for-byte. Any older archived README statement that research or reviewer-provision permission was pending describes the historical snapshot; it is superseded by the user's 2026-10-07 confirmation in S9/S12 and the accompanying CURRENT_ASSET_STATUS.md. Public release and original training-run linkage remain distinct from that confirmed permission.


## S14. Detailed settings and diagnostic records

The midpoint s̄ uses endpoint averages, except shortest-angle heading interpolation. Sail/rudder inputs are averages of observed endpoint angles, with zero within-step increments for this derivative evaluation. D=diag(1,1,5,5) is empirical scaling in stored units, not an estimated noise covariance. A bounded local least-squares solver searches componentwise w∈[−16,16]² m/s. The initial prior (0,8) and six magnitude-8 initializations separated by 60 degrees are tried on the first fit; subsequent fits warm-start from the preceding estimate. Each start has max_nfev=35 and finite-difference step 10⁻³. Insufficient history retains the current estimate. Neither a global minimum nor wind identifiability is guaranteed.

Within each task, physical policy, normalizer, dynamics, initial conditions, map, external wind parameters, target motion, execution timing and evaluation are shared. Different paths may encounter different local wind. Reactive relay R uses nominal feedback without future candidate rollout. Search15 S15 is the detailed predictor with P=15; Search60 S60 retains the same candidates/H but uses P=60. Nominal-prediction hold NH predicts nominal and, if invalid, integration-failed or below guard, holds the current reference when available without evaluating alternatives. NH is not a no-prediction baseline; S60 is not a no-search method.

Existing detailed-prediction logs provide actual selected-protocol prefixes until the next review or earlier prediction/real termination. Complete 15-second windows and truncated windows are reported separately; post-replanning tails are excluded. Six development snapshots additionally execute two fixed protocols each, to 60 seconds or actual termination. Full physical prefixes and selected first 15 seconds must reproduce the original trajectory before their branch comparisons are accepted. Predictors use only causal inputs; offline real branches alone advance the actual external field.

For two decisive meter-scale incursions and their safe S15 pairs, fixed issued commands are replayed with the original integrator while logging its accepted internal substeps. Endpoint parity must remain exact. Synchronized substep-segment clearance supplements, and does not replace, the original one-second metric. Hardware is an AMD EPYC 7V12 host with at most four one-thread CPU experiment workers and no GPU. Pure planning calls and complete-episode CPU are distinguished; no online deadline is claimed.

An additional same-command check of the unique new case preserves every one-second endpoint exactly and gives R/L/S15 substep minima −0.162/−1.117/42.094 m, retaining all three labels. This is a numerical replay, not three new tasks. Historical accepted-integrator-substep checks also preserve every one-second endpoint exactly. The two historical reactive incursions remain −1.225 and −0.872 m. Their S15 minimum margins change from 43.589/38.455 m under one-second segments to 43.597/38.425 m under accepted-substep segments (maximum substep 0.1 s). Thus these particular gain labels do not arise solely from a one-second chord sign error. This is still a numerical circular-proxy check, not swept-hull or formal continuous safety.

Nine measurements of the estimation/rollout/selection core per model at three fixed states give detailed median/p95/maximum wall times 17.009/17.662/17.685 s, compared with 0.067/0.136/0.136 s for L. The states include two risk decisions and ordinary feedback, each repeated three times. The timer excludes initial nominal/candidate setup and model loading. Nominal early return can evaluate different candidate counts, so this is not an equal-work per-candidate speed ratio. Complete new-confirmation episode CPU totals are 270.68, 2133.23 and 378.44 s for R, S15 and L. These measures include different work and are not interchangeable. Detailed calls can exceed the 15 s review period; physical time remains paused here. Separate R9 delayed-execution failures are boundary evidence, not pooled main-method outcomes.
