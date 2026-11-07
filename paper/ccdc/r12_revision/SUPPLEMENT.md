# R12 Supplementary Method and Reproduction Notes

## S1. Conditional mathematical explanations

The synchronized relative segment r(α)=r₀+αd has squared norm ||r₀||²+2αr₀ᵀd+α²||d||². For d≠0 its unconstrained minimizer is −r₀ᵀd/||d||²; projection to [0,1] yields the evaluator's minimum. For d=0, the segment is constant. Code avoids division when dᵀd≤10⁻¹². This is the exact minimum of a specified linear relative segment, not a continuous hull guarantee.

The wind objective substitutes an endpoint-midpoint evaluation under a trial constant wind for an observed step's average derivative. The residual combines local-constant-wind error, midpoint approximation, numerical integration and other model discrepancies. No independent Gaussian-noise assumption or inverse-covariance interpretation is used. Finite bounded nonlinear least squares returns a local numerical estimate. Multiple starting points do not prove uniqueness or global optimality.

The supervisor is nominal-first. Write F(ρ) for valid predictions meeting the guard. If nominal is in F, it returns before costs are compared. If nominal is not in F and F is nonempty, every member of F receives the same 20 m offset, so removing that constant only in this branch leaves ordering unchanged. The statement does not hold globally. For a hypothetical tied-margin fallback with nominal and continuation both at 10 m clearance, their terminal distances 100/90 m become costs 100/110 m under the original rule. Removing 20 globally would change the winner. This example explains algebra; it is not a navigation result. No scientific code was changed to remove the offset.

For a common time domain, obstacle identity set and exclusion radii, the reverse triangle inequality gives | ||p−q||−||p̂−q̂|| |≤||p−p̂||+||q−q̂||. If the latter is bounded by E uniformly on that common domain, taking minima gives |m−m̂|≤E. Static centers contribute no target-position error. For synchronized piecewise-linear representations, endpoint error bounds extend to interpolated positions by convexity. A safety conclusion additionally requires an available bound E<ρ; the present finite observed errors do not provide such a bound. Shared execution protocols are required to interpret the discrepancy as prediction quality rather than later policy changes. The bare inequality does not itself prove that the predictor is accurate.

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
