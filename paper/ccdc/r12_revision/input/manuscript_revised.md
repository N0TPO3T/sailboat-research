# Reference-Conditioned Closed-Loop Prediction for Dynamic Obstacle Avoidance of an Autonomous Sailboat

Authors and affiliations to be confirmed

<!-- Content revision based on the uploaded R11 manuscript. No new navigation experiments or training are reported. The original figure files and official Word template are not included in this revision package. -->

## Abstract

A position reference does not uniquely determine the motion of a recurrent sailing controller: its trajectory also depends on controller memory, actuator state, and reference-management rules. We adapt the control-induced-motion principle of generalized velocity obstacles to finite position-reference protocols. A predictor initialized from causal observations runs the inherited controller and sailing dynamics under a locally fitted wind estimate. It evaluates nominal navigation, incumbent-reference continuation, and lateral references together with their holding and feedback-restoration rules. A nominal-first supervisor retains ordinary feedback when its predicted clearance meets an empirical guard and otherwise selects an alternative. In a historical 30-instance evaluation, both search configurations completed all tasks safely, compared with 28 for a reactive relay; the two gains were avoidance of moving-vessel safety-buffer incursions. Same-state comparisons further show that reference search can avoid failures of a specified prediction-triggered hold rule. In a separate 12-instance confirmation, search and the reactive relay both completed all tasks safely, while search added 27.08 s on average and up to 271 s. These results support the conditional value of reference selection while identifying conservative intervention as its main navigation tradeoff. The study concerns ideal-compute closed-loop simulation rather than real-time deployment.

Keywords: autonomous sailing; reference-conditioned prediction; dynamic obstacle avoidance; recurrent control; closed-loop simulation

## I. Introduction and Related Work

A waypoint specifies where a sailing controller should go, not the trajectory that it will execute. Wind-dependent propulsion, finite turning response, actuator dynamics, and recurrent state can produce turning or tacking motion that differs from the waypoint chord. During a moving-vessel encounter, a geometrically clear reference can therefore induce a safety-buffer incursion. The supervisory problem is to select a reference that the existing controller can use effectively, accounting for how long that reference will be maintained and how ordinary navigation will resume.

High-level sailing planners can generate routes and waypoints using environmental information; Silva Junior et al., for example, use Q-learning for sailboat path planning [1]. We address the execution interface beneath such planning: how should a supervisor compare the motion induced by different references supplied to an existing sail-and-rudder policy? We consider a known static map, no direct wind measurement, and current observations of one low-speed target vessel. The local policy is reused rather than retrained.

Generalized velocity obstacles (GVO) formulate collision avoidance in terms of control-induced motion instead of assuming that a desired velocity is immediately achieved [2]. Reference governors likewise modify commands supplied to an existing closed loop [3]. These perspectives motivate treating each candidate as a reference-execution protocol rather than a straight line. In maritime avoidance, branching-course model predictive control evaluates dynamically feasible candidate maneuvers and executes an initial part before replanning [6]. Feedback motion prediction provides a related approach: İşleyen et al. bound motion under a specified unicycle controller and use those predictions for reference regulation [7]. Here, the controller-specific motion envelopes and guarantees of those systems are not transplanted to a sailboat. Instead, finite protocols are evaluated by simulating the inherited recurrent policy and sailing dynamics.

The absence of direct wind measurements introduces a prediction uncertainty. Motion-based wind estimation, including MoWe [4], motivates extracting relevant information from vessel motion. Our predictor uses a small bounded inverse-dynamics fit to obtain a constant local wind approximation. This auxiliary fit is neither a reproduction of MoWe nor a new wind-estimation method.

The contribution is a protocol-conditioned prediction interface and an empirical assessment of its reference-selection effects. The interface explicitly restores controller and actuator state, preserves reference-delivery timing, and predicts feedback after a finite hold. The evaluation separates the effect of selecting an alternative from the value of initiating intervention, using reactive and holding comparators, shared-state evidence, and adverse cases. Planning computation does not advance the physical simulation clock. Under this abstraction, the boat still evolves through sailboat dynamics and feedback control; neither instantaneous heading tracking nor future environmental information is supplied.

## II. Navigation Problem and Controller Interface

### A. State and information

At one-second boundary t, the physical state contains world position p, roll and heading, body surge and sway velocities, roll and yaw rates, and actual sail and rudder angles. The final mission destination is G, while g is the currently active position reference. The supervisor receives the current state, previously observed states and issued commands, the static circular-obstacle map, and target-vessel observations with identity, position, ground velocity, timestamp and validity. Target observations are available within 1000 m. The evaluator uses the actual target trajectory even when it is outside this observation range.

The physical environment and the predictor are separate instances of the inherited dynamics. This separation isolates state and hidden information; it does not imply independently identified physical models. The latter accepts causal state and command history, not the actual wind field, environment random generator, scenario seed, or target's future maneuver schedule. Target velocity is extrapolated inside a prediction. Actual environmental evolution can differ from that extrapolation. Static-map knowledge is complete, and the evaluated observations have no added sensor noise.

### B. Inherited local policy and continuous references

The local controller is an inherited 18-input recurrent soft actor-critic (SAC) policy with temporal attention, a fixed normalizer, and deterministic tanh evaluation actions [5]. No policy training is performed in this study. Both physical and prediction instances use the research group's sailing-dynamics implementation. Its upstream description identifies the four-degree-of-freedom model of Xiao and Jouffroy [8] as the modeling basis; this lineage does not establish that every optional mechanism or parameter of [8] is used here.

<!-- AUTHOR ACTION BEFORE SUBMISSION: supply the formal source of the inherited controller and weights, confirm the implemented dynamics and parameter table against the frozen code, and state permitted reproduction materials. The thesis draft establishes model lineage, not publication status or code-level equivalence. A generic SAC citation does not replace this attribution. -->

A rigid local frame places the active reference at (500, 0) m without rescaling lengths. At reference application, its angle is the boat-to-reference bearing θ and its origin is g − 500[cos θ, sin θ]. Body velocities u and v remain in body coordinates. The two progress differences are previous minus current distance to the reference, and previous minus current |500 − x_local|; both start at zero. The first 14 inputs comprise local position, roll and local heading, body velocities, angular rates, actual sail/rudder angles, two progress differences, and the local reference coordinates. The final four inputs are distance/bearing pairs for up to two selected static or observed dynamic obstacles. Their encoded distance is max(0, d − R + 40 m), where d is center distance and R is the obstacle's exclusion radius. Pairs within 150 m in that encoding are sorted by distance and bearing; missing pairs are zero-filled. This inherited boundary-input adapter is shared by the dynamic methods.

On a reference change, the adapter reconstructs recurrent state by reencoding the real state history in the new frame and replaying the actual past commands. Each historical dynamic-obstacle input uses its observation from that time. Predicted histories are never inserted into the real controller history. The ten-slot attention history is distinct from the persistent recurrent state; it is not a ten-step memory reset.

Each normalized action component is scaled by 10 degrees, floor-quantized in one-degree increments, and accumulated into an actuator setpoint. Signed floor is used also for negative increments. Sail and rudder setpoints are clipped to ±90 and ±30 degrees respectively. Actual angles approach them at at most 10 degrees per second. An adaptive Dormand–Prince integrator advances the inherited dynamics over each one-second control step. Thus reference direction alone does not determine the executed motion.

### C. Timing and evaluation

At t, the policy first computes an action using the active reference. The supervisor then selects a proposed reference. The already computed action advances the real dynamics to t+1, after which a changed reference is applied and memory is reencoded. Consequently, a selection at t can first affect the physical transition from t+1 to t+2. Planning wall time is recorded but does not advance this physical clock in the main experiments.

Static exclusion radii equal entity radius plus 60 m. The dynamic radius is 85 m: a combined 25 m entity radius, comprising a 10 m own-boat and 15 m target proxy, plus a 60 m buffer. Safety is measured on every one-second segment. For dynamic motion, define r₀ = pₜ − qₜ and Δr = (pₜ₊₁ − qₜ₊₁) − r₀. The segment clearance is

\[
c_t=\|r_0+\alpha^*\Delta r\|-85\,\mathrm m,\qquad
\alpha^*=
\begin{cases}
\operatorname{clip}_{[0,1]}
\!\left(-\dfrac{r_0^\mathsf T\Delta r}{\|\Delta r\|^2}\right),&
\|\Delta r\|^2>0,\\
0,&\Delta r=0.
\end{cases} \tag{1}
\]

Equation (1) follows by differentiating the convex quadratic
\(\|r_0+\alpha\Delta r\|^2\) and projecting its unconstrained minimizer onto
\([0,1]\). It is exact for the specified linearly interpolated relative segment.

Static clearance is the analogous distance from a boat segment to an obstacle center minus its exclusion radius. Safe completion requires arrival within 10 m of G before the task limit and strictly positive static and dynamic clearance throughout. The time limits are 1800, 5400 and 9000 s for 1, 3 and 5 km tasks. An incursion remains a failure even if arrival subsequently occurs. NoRouteError is an exit label, not the safety measurement. Circular proxies and linear interpolation between recorded states define the evaluation; they are not exact swept-hull guarantees.

## III. Reference-Conditioned Execution Prediction

### A. Nominal feedback, eligibility, and execution state

The nominal supervisor is a geometric route relay with local obstacle response and shared temporary-endpoint handling. Its settings are 120 m planning allowance, 500 m lookahead, 100 m handoff distance, and 80 m geometric-clearance trigger. It uses current observed vessel positions in its circle map. The supervisor first predicts this nominal feedback and retains it when its predicted margin meets an additional planning guard.

Prediction becomes eligible at \(t=10\) s when a valid observed target is strictly within 600 m and the review timer is due. An existing non-nominal hold takes precedence until its deadline. The representative configuration uses a 60 s horizon \(H\) and a 15 s holding/update period \(P\), selected during development.

A reproducible branch needs more than the physical state. Denote the execution snapshot by
\[
\Xi_t=(s_t,b_t,\mu_t,\ell_t,\mathcal H_t,a_t^{\mathrm{pending}}), \tag{2}
\]
where \(b_t\) contains actuator setpoints, \(\mu_t\) recurrent and attention state, and \(\ell_t\) the local frame, active reference, relay/endpoint state, and timers. The archive \(\mathcal H_t\) contains the actual history required by subsequent reencoding. The pending action has already been computed before supervisory selection. Equation (2) specifies the information needed to reproduce execution; it does not assert that the hidden environmental process is observable or that the archive can be discarded.

![Fig. 1. Reference-conditioned prediction and physical execution. Each branch restores the execution snapshot and evaluates a reference together with its protocol. Only actual observations and issued commands update the real history.](figures/figure1_interface.png)

### B. Local wind approximation

Let \(z=(u,v,\omega_\phi,\omega_\psi)\), and let \(f_z\) return its time derivative from the inherited dynamics. Over an observed step,
\[
\frac{z_{i+1}-z_i}{\Delta t}
=\frac{1}{\Delta t}\int_{i\Delta t}^{(i+1)\Delta t}
 f_z(s(\tau),w(\tau))\,d\tau
\approx f_z(\bar s_i,w),\qquad \Delta t=1\,\mathrm s. \tag{3}
\]
The equality describes the continuous dynamics; the approximation replaces the step's effective wind by a constant trial vector and its average response by a midpoint evaluation. The stored midpoint is arithmetic except for shortest-angle heading interpolation. It uses actual midpoint sail/rudder angles and zero within-step angle increments for this derivative evaluation. Numerical integration and interpolation introduce additional approximation.

The numerical residual objective is
\[
\mathcal L_t(w)=
\sum_{i\in\mathcal I_t}
\left\|D\left[
f_z(\bar s_i,w)-\frac{z_{i+1}-z_i}{\Delta t}
\right]\right\|_2^2,
\quad
\mathcal I_t=\{t-6,t-4,t-2\},\quad D=\operatorname{diag}(1,1,5,5). \tag{4}
\]
The components are evaluated in their stored units; \(D\) is an empirical numerical scaling, not an estimated inverse noise covariance. The latest fitted transition ends at \(t-1\), not at \(t\). The fit searches the componentwise box \([-16,16]^2\,\mathrm{m/s}\), which is not a bound on wind-vector norm.

The returned \(\hat w_t\) is a bounded local least-squares estimate with a finite evaluation budget, not a guaranteed global minimizer of (4). The prior is \((0,8)\) m/s. The first fit tests that prior and six magnitude-8 m/s initializations separated by \(60^\circ\), retaining the lowest residual. Later fits warm-start from the preceding estimate. Each start uses `max_nfev=35` and finite-difference step \(10^{-3}\); this is not a 35-call total limit. With fewer than three usable transitions, the prior is retained. The fitted wind remains constant throughout each branch. A low residual measures consistency with the selected past transitions, not certainty about future wind.

### C. Candidate protocols and closed-loop rollout

The ordered candidate set consists of nominal feedback, continuation of the current reference, and four lateral references. If \(\beta\) is the current bearing to the nominal reference, the lateral references are
\[
g_\alpha=p_t+
350
\begin{bmatrix}
\cos(\beta+\alpha)\\
\sin(\beta+\alpha)
\end{bmatrix}\mathrm m,\qquad
\alpha\in\{-90,-45,45,90\}^{\circ}. \tag{5}
\]
A candidate \(\gamma\) specifies both its reference-generation rule and its execution protocol. Nominal feedback keeps applying ordinary relay updates throughout the rollout. Every other candidate initially holds its reference for the configured period, then restores ordinary feedback and clears the incumbent on release. A nominal and continuation candidate can therefore start with the same coordinates while inducing different motion. The prediction tail assumes nominal feedback; it cannot anticipate later online decisions to intervene again.

Each branch restores \(\Xi_t\). Setpoints are reconstructed by accumulating the issued commands using the same scaling, signed-floor quantization, clipping, and actuator rules. The reproduced current policy action must equal the already computed real action elementwise. That common action advances the first interval; a candidate can affect the following interval only after the common next-step reference application.

For an observed target \(j\), prediction uses
\(\hat q_{j,t+k}=q_{j,t}+k\Delta t\,v_{j,t}\), retaining the 1000 m observation limit. Let \(\mathcal F_\gamma\) represent one complete policy–actuator–dynamics–reference update under protocol \(\gamma\). The branch evolves as
\[
\hat\Xi^\gamma_{t+k+1}
=\mathcal F_\gamma\!\left(
\hat\Xi^\gamma_{t+k},\hat w_t,\hat Q_{t+k:t+k+1}
\right),
\qquad \hat\Xi^\gamma_t=\Xi_t, \tag{6}
\]
where \(\hat Q\) is the extrapolated target-observation process. This is a compact definition of the implemented simulator, not a newly learned transition model. Predicted observations remain inside the branch.

A rollout ends at 60 s, predicted arrival at the original goal, or route/integration failure. An early predicted arrival is valid; a route or integration failure excludes the prediction from guarded selection. Static and synchronous dynamic clearances are evaluated using (1). Their minimum over the completed branch is denoted by \(\hat m_t(\gamma)\).

### D. Nominal-first selection and recovery

Let \(\mathcal V_t\) contain valid, integration-successful predictions and define
\[
\mathcal F_t(\rho)=
\{\gamma\in\mathcal V_t:\hat m_t(\gamma)\ge\rho\},
\qquad \rho=30\,\mathrm m. \tag{7}
\]
This planning guard is separate from the zero-margin task boundary. The nominal candidate \(n\) is evaluated first. If it is feasible, the call stops without evaluating alternatives. Otherwise valid alternatives are scored by the original terminal preference
\[
J_t(\gamma)=
\|\hat p^\gamma_{t+K_\gamma}-G\|
+20\,\mathrm m\,\mathbf1_{\gamma\ne n}
+10\,\mathrm m\,\mathbf1_{\gamma\in\mathcal C_{\mathrm{side}}},
\qquad K_\gamma\le60. \tag{8}
\]
This is a terminal-distance preference with candidate-type offsets, not a travel-time model. Let \(\iota(\gamma)\) denote fixed enumeration order. Conditional on an eligible planning call, the selection rule is
\[
\gamma_t^*=
\begin{cases}
n,& n\in\mathcal F_t(\rho),\\
\displaystyle\operatorname*{argmin}_{\gamma\in\mathcal F_t(\rho)}
 (J_t(\gamma),\iota(\gamma)),
 & n\notin\mathcal F_t(\rho),\ \mathcal F_t(\rho)\ne\varnothing,\\
\displaystyle\operatorname*{argmin}_{\gamma\in\mathcal V_t}
 (-\hat m_t(\gamma),J_t(\gamma),\iota(\gamma)),
 & \mathcal F_t(\rho)=\varnothing,\ \mathcal V_t\ne\varnothing,\\
\text{current reference, otherwise nominal},&\mathcal V_t=\varnothing .
\end{cases} \tag{9}
\]
The tuples are ordered lexicographically. Thus all-infeasible predictions are ranked by maximum margin, then minimum \(J_t\), then enumeration order. This is a best-effort fallback, not a certified safe backup. Failure of the base planner before candidate construction can still terminate the actual task.

An important property of (8)–(9) is that the 20 m non-nominal offset does not price the decision to intervene in the feasible-alternative branch. If nominal is feasible, it is returned before comparison. Otherwise every feasible alternative is non-nominal, so the 20 m term is constant. It can still affect score-based tie breaking in the all-infeasible fallback. Consequently, the nominal prediction and guard primarily determine when intervention is considered; the objective then ranks the alternatives. This distinction is relevant to the navigation costs reported below.

The chosen non-nominal reference is retained until its timer expires. The next eligible call can continue, change, or release it. Side references have no separate geometric prefilter; predicted execution determines their guarded feasibility.

```text
Algorithm 1  Reference-conditioned selection at a control boundary
Input: current observations, actual execution snapshot, map, and timers
1  If a non-nominal hold is active, return its reference.
2  Obtain the nominal relay proposal and shared endpoint handling.
3  If t < 10 s, no valid target is strictly within 600 m,
   or the review timer is not due, return nominal.
4  Fit local wind and restore prediction state, including the pending action.
5  Predict nominal feedback. If valid with margin >= rho, select nominal.
6  Otherwise predict continuation and the four lateral-reference protocols.
7  Select according to (9).
8  Once this supervisory prediction call has completed, set the next
   review to t + P. A non-nominal choice has the same hold deadline;
   a nominal choice releases the hold.
9  Return the reference for application after the already computed action.
```

<!-- Check Algorithm 1 against the frozen implementation, especially the equality at the hold deadline and reference clearing. This is an editorial restatement, not permission to change the timing or stale-state behavior while retaining old results. -->

Temporary endpoint occupation is handled identically for all comparators. When the final goal is currently covered, the nominal relay retains a clear current reference more than 100 m away if possible. Otherwise it considers eight points on a 305 m ring around the goal, rejecting points closer than 200 m to the boat, blocked segments, or endpoint clearances below 120 m. It minimizes distance plus 80 times absolute heading turn in radians. When the goal becomes available, it clears the incumbent and reconnects to the original task. If no temporary reference exists, it reports `NoRouteError`. This mechanism neither stops the boat nor removes a vessel.

## IV. Experimental Setup and Results

### A. Comparators and evidence groups

All comparisons retain the same policy, normalizer, dynamics, static map, initial state, external wind-field parameters, target motion and task judgement within each instance. Different executed paths can encounter different local values of the same spatial wind field. No additional learning is performed. We compare the following methods, using ideal-compute timing for all main results.

**Reactive relay (R)** uses nominal feedback and the shared endpoint manager. It includes local obstacle response and sail/rudder feedback, but does not simulate future candidate execution. **Search15 (S15)** is the representative method with a 15 s hold/update period. **Search60 (S60)** searches the same candidate set over the same 60 s horizon, with a 60 s hold/update period. Changing this period also changes subsequent wind-estimation history. **Nominal-prediction hold (NH)** predicts only nominal feedback; if that prediction is invalid, fails integration, or has margin below 30 m, it holds the current reference for 15 s when available, otherwise returning nominal. It does not predict alternatives. Each method triggers from its own actual history, not from another method's future trigger times.

The historical short evaluation contains 30 instances, six each of crossing, overtaking, non-conflict, endpoint and designed high-pressure crossing. These instances were generated after the then-current method freeze, but were later inspected during method selection. A separate historical long group contains four tasks: crossing and overtaking at both 3 and 5 km. The seen mechanism group contains 13 of the historical short instances and is not an additional independent sample. Finally, the new confirmation contains 12 frozen 1 km instances: four pressure and two each of crossing, overtaking, endpoint and non-conflict. All generated instances are retained. These small designed strata are not a sample of natural maritime traffic frequency.

All main tasks contain one non-reacting target with constant world-frame velocity and no scheduled turn. Target speeds range from 0.575 to 1.231 m/s in the historical short group, are 0.9 or 1.0 m/s in the long group, and range from 0.657 to 0.913 m/s in new confirmation. Constant-velocity extrapolation is therefore matched to these observed targets; robustness to target maneuvers is not evaluated. The synthetic wind field has base speed 8 m/s. Historical short tasks contain 18 stable, six slow and six fast profiles; new confirmation contains six stable and six fast profiles. Stable wind is fixed. Slow/fast profiles add bounded spatial and temporal direction waves with amplitudes 25/45 degrees, directional perturbations up to 3/6 degrees, and speed modulation of 12/20 percent. Exact instance manifests and asset hashes accompany the draft; public redistribution of the inherited assets remains subject to permission.

Table I reports the groups separately. Safety completion is the primary endpoint. Navigation-time differences are computed only on pairs in which both methods safely complete, and early failure is not counted as fast arrival. A task, rather than a one-second state, prediction window or candidate, is the sampling unit.

Table I. Safe completions by evidence group. The seen mechanism row overlaps the historical short row and must not be pooled with it.

| Evidence group | Tasks | R | S15 | S60 | NH |
|---|---:|---:|---:|---:|---:|
| Historical short | 30 | 28 | 30 | 30 | — |
| Historical long | 4 | 3 | 4 | 4 | — |
| Seen mechanism | 13 | 11 | 13 | 13 | 9 |
| New confirmation | 12 | 12 | 12 | 12 | 11 |

Table II. S15 navigation-time difference from the reactive relay on common-safe pairs. Median difference is zero in each group.

| Evidence group | Pairs | Mean (s) | Maximum (s) |
|---|---:|---:|---:|
| Historical short | 28 | +15.29 | +267 |
| Historical long | 3 | +8.67 | +26 |
| Seen mechanism | 11 | +38.91 | +267 |
| New confirmation | 12 | +27.08 | +271 |

### B. Avoided incursions and same-state selection

In the historical short group, both search protocols safely complete all 30 tasks, whereas the reactive relay incurs the dynamic buffer in two pressure tasks. Its margins are −1.225 and −0.872 m before NoRouteError termination; S15 completes the corresponding tasks with margins 43.589 and 38.455 m. No entity collision is observed in those failed reactive trajectories, so the measured gain is prevention of buffer incursion and recovery of safe task completion. The remaining 24 non-pressure tasks are safe for all three methods. S15 and the reactive relay have identical complete trajectories in 22 of 30 tasks.

The seen mechanism group tests whether predicting nominal risk and simply retaining the incumbent reference can reproduce search's effect. S15 and S60 complete all 13 tasks, while NH completes nine. The four NH failures include both historical reactive-incursion cases. Three first-decision differences have identical preceding physical states, commands, vessel observations and complete nominal predictions. This controls the information and initial execution conditions for those decisions without assuming later trajectories remain identical.

Fig. 2 illustrates the first difference at 149 s in one pressure case. Nominal feedback predicts 17.706 m minimum margin and continuation predicts 22.110 m; both are positive but below the 30 m guard. The −90-degree reference at (238.784, −324.617) m predicts 94.815 m margin and has score 521.172 m, below the other feasible side scores. It is selected at 149 s and applied at 150 s; the first physical-state difference occurs at 151 s. S15 safely completes at 444 s with 43.589 m actual margin. NH terminates at 224 s with −0.649 m margin. This establishes a difference between the defined online selection rules, not proof that the first turn alone determines the final outcome or that every side candidate is necessary.

![Fig. 2. Common-state decision at 149 s. Solid lines show actual motion after the shared state; dashed lines show candidate predictions over the first 15 s. Actual simultaneous clearance distinguishes search from nominal-prediction hold.](figures/figure2_mechanism.png)

The selected prediction has maximum position error 0.00684 m over the first 15 s after that decision, including the first old-action step. The corresponding reference-execution interval gives the same maximum. This is a favorable local case. Historical ordinary-feedback windows include an error of 30.506 m over 15 s. Prediction tails also mix model error with later decisions that may differ from the assumed return to nominal feedback. A local agreement therefore does not turn the planning guard into an error bound.

In the four long tasks, both search protocols complete four and the reactive relay completes three. The 3 km crossing is completed by S15 in 929 s and S60 in 877 s; the reactive trajectory ends after incursion at 512 s. All methods complete the 5 km crossing, with times 1306, 1332 and 1516 s for R, S15 and S60. The two overtaking tasks have identical trajectories and no search intervention.

### C. New confirmation and intervention cost

The new confirmation gives 12 safe completions for R, S15 and S60, and 11 for NH. S15 does not improve safe completion over R in this group. Ten of the twelve complete trajectories are identical between S15 and R. Intervention occurs in only a pressure instance and an endpoint instance, adding 54 and 271 s respectively. Their mean over all twelve common-safe pairs is 27.08 s. These unchanged tasks should not be counted as evidence of successful activated avoidance.

In the new pressure instance, R completes in 299 s with 6.512 m margin; S15 takes 353 s with 37.337 m; S60 takes 443 s with 17.993 m. NH instead incurs the buffer, reaching −20.580 m before termination at 292 s. This demonstrates that the tested hold response can harm an otherwise safe closed loop. Search avoids that outcome, but the case does not establish that intervention was necessary compared with continued reactive feedback.

Fig. 3 contrasts a historical rescue with the largest new navigation cost. In the new endpoint case, R is already safe at 313 s with 10.957 m margin. S15 completes at 584 s with 34.687 m margin. A larger margin comes with 271 s extra travel time; the evaluation defines no utility function that proves this exchange worthwhile. The historical endpoint case also has a 267 s cost, involving both the maneuver and subsequent endpoint availability. Neither case should be attributed solely to holding duration.

![Fig. 3. Actual encounter trajectories. Top: historical pressure case with reactive buffer incursion. Bottom: new endpoint case where both methods are safe and search adds 271 s. Own-boat and target positions have synchronized time labels; safety circles are snapshots, not swept regions.](figures/figure3_encounters.png)

Search60 remains a substantive competitor. In the new group it has the same safe-completion count as S15, using 328.77 s cumulative episode CPU time versus 777.05 s. S15 reduces common-safe navigation time by 9.25 s on average relative to S60, with median zero. NH uses 693.43 s CPU and R uses 130.83 s; these totals include complete episodes and their different durations. They are not planning deadlines. In the historical long group, one S15 planning call takes 43.459 s, longer than the 15 s update period. The main results rely on ideal computation timing and do not demonstrate that this update rate can be delivered online.

## V. Discussion

### A. What is established by reference selection?

The evidence distinguishes the response to a predicted concern from the need to intervene. Historical evaluations include two short-task and one long-task buffer-incursion recoveries relative to reactive navigation. The same-state comparisons and NH failures further show that retaining the incumbent reference is not interchangeable with searching the tested alternatives. These are effects of complete supervisory protocols, rather than evidence that the first selected turn alone determines the final outcome.

The latest confirmation supplies the complementary result. Reactive navigation is already safe in all twelve tasks, and the two active S15 cases increase navigation time. Search prevents the damage caused by NH in one of them, but neither case proves that continued reactive motion needed intervention. Equations (8)–(9) explain the design distinction: the nominal guard gates the search, whereas the subsequent cost ranks the available alternatives. The constant 20 m offset in the feasible-alternative branch cannot determine whether leaving nominal is worth its cost.

S60 remains competitive. Its lower computation cost and equal safe-completion count prevent claiming that a 15 s update is necessary. Its larger navigation-cost tail in the historical short group also prevents declaring slower review uniformly preferable. The present comparisons establish conditional effects of the implemented rules. They do not yet isolate the additional value of detailed controller-conditioned rollout over a well-calibrated, simplified candidate predictor.

### B. Interpreting the planning guard

The 30 m guard is an empirical design choice, not a certified bound on forecast error. Consider predicted and realized trajectories evaluated with the same reference protocol, obstacle set, radii, and common time interval \(\mathcal T\). Define
\[
E=\sup_{\tau\in\mathcal T,\,j}
\left(\|p(\tau)-\hat p(\tau)\|
      +\|q_j(\tau)-\hat q_j(\tau)\|\right).
\]
The reverse triangle inequality, followed by taking minima on the common domain, gives
\[
\big|m^{\mathrm{real}}-\hat m\big|\le E. \tag{10}
\]
For a known static obstacle, the second position error is zero. Thus \(\hat m\ge\rho>E\) would imply positive realized clearance on that interval. This is a conditional geometric implication, not a property demonstrated by the current predictor: a uniform \(E<30\) m is unavailable, and a finite sampled error maximum does not supply it. The same-protocol condition also ceases to describe prediction-model accuracy once online replanning departs from the predicted tail.

This distinction matters even under ideal computation. A low inverse-dynamics residual does not guarantee future trajectory accuracy. Accurate selected short windows coexist with a 30.506 m ordinary-feedback position error, and finite candidate infeasibility is handled by best effort. Increasing the guard shrinks the feasible set at a fixed decision state, but need not monotonically improve full-task safety or travel time, because it changes subsequent motion and decisions.

### C. Scope and reproducibility

The results rely on known dynamics, ideal current motion observations, a locally constant fitted wind, and constant-velocity target extrapolation. Main-test targets match the latter assumption, so maneuvering-target robustness is not established. The safety measure is a circular-proxy, one-second-polyline criterion, not an exact swept-hull test. Only one low-speed non-cooperative target is evaluated; the method is not a complete COLREGs supervisor.

Computation is a separate execution boundary. A planning call can exceed the configured review period. A separate timing-aware project experiment, using a different delivery protocol, also contains a predicted-safe/realized-incursion counterexample. That experiment is not pooled with the ideal-compute results. Real-time use would require evaluating motion while computation proceeds, not merely adding CPU seconds to the final travel time. Within the current scope, however, conservative intervention remains a method-level issue rather than only a future implementation-speed problem.

Historical tasks were generated after their original method freeze but later informed selection; the seen mechanism set overlaps them. The latest confirmation contains only twelve designed instances, two with S15 intervention. Results are therefore reported by evidence group, with common-safe travel time separated from changes in completion. Overlapping prediction windows or additional candidates are not independent navigation tasks. A matched simpler predictor and a limited guard tradeoff study are natural targeted assessments; they have not been run for the present revision.

Reproduction requires the precise inherited controller, normalizer, dynamics parameters, and supervisory protocol. Their formal attribution and release terms remain author-verification items. Added supervisor code, configurations, scene manifests, and analysis should be identified separately from the inherited assets.

## VI. Conclusion

We developed a reference-conditioned execution-prediction supervisor for an existing recurrent sailboat controller. A candidate consists of a position reference together with its delivery, holding, and feedback-restoration protocol. An isolated instance of the inherited policy and dynamics predicts the corresponding motion under a causal local wind estimate, and a nominal-first guarded rule selects a reference for execution.

Under ideal-compute closed-loop simulation, this method avoids several historical moving-vessel buffer incursions and outperforms a specified prediction-triggered holding rule. The latest confirmation shows no additional safe completions over reactive navigation and reveals a substantial intervention-cost tail. The study thus provides a concrete adaptation of control-induced prediction to recurrent reference execution, with evidence of both useful selection and unnecessary conservatism. Establishing when intervention warrants its cost remains the principal method-level question; real-time delivery and broader uncertainty require separate validation.

## Acknowledgment and Author Actions

Author names, affiliations, funding, and formal attribution and release conditions for the inherited policy, weights, and simulator remain to be confirmed. AI tools assisted drafting and evidence-based internal review. Human authors are responsible for the submitted content, references, permissions, and applicable disclosure wording. No new training, physical experiment, or supplemental navigation experiment is reported in this revision.

## References

[1] A. G. da Silva Junior, D. H. dos Santos, A. P. F. de Negreiros, J. M. V. B. de Souza Silva, and L. M. G. Gonçalves, “High-level path planning for an autonomous sailboat robot using Q-learning,” Sensors, vol. 20, no. 6, Art. 1550, 2020, doi: 10.3390/s20061550.

[2] D. Wilkie, J. van den Berg, and D. Manocha, “Generalized velocity obstacles,” in Proc. IEEE/RSJ International Conference on Intelligent Robots and Systems, 2009, doi: 10.1109/IROS.2009.5354175.

[3] E. Garone, S. Di Cairano, and I. Kolmanovsky, “Reference and command governors for systems with constraints: A survey on theory and applications,” Automatica, vol. 75, pp. 306–328, 2017, doi: 10.1016/j.automatica.2016.08.013.

[4] Q. Sun, W. Qi, and H. Qian, “MoWe: Motion observation for wind estimation of sailing robots,” Journal of Field Robotics, vol. 42, no. 5, pp. 2355–2374, 2025, doi: 10.1002/rob.22512.

[5] T. Haarnoja, A. Zhou, P. Abbeel, and S. Levine, “Soft actor-critic: Off-policy maximum entropy deep reinforcement learning with a stochastic actor,” in Proc. 35th International Conference on Machine Learning, vol. 80, pp. 1861–1870, 2018.

[6] B.-O. H. Eriksen, M. Breivik, E. F. Wilthil, A. L. Flåten, and E. F. Brekke, “The branching-course model predictive control algorithm for maritime collision avoidance,” Journal of Field Robotics, vol. 36, no. 7, pp. 1222–1249, 2019, doi: 10.1002/rob.21900.

[7] A. İşleyen, N. van de Wouw, and Ö. Arslan, “Feedback motion prediction for safe unicycle robot navigation,” in Proc. IEEE/RSJ International Conference on Intelligent Robots and Systems, 2023, pp. 10511–10518, doi: 10.1109/IROS55552.2023.10341787.

[8] L. Xiao and J. Jouffroy, “Modeling and nonlinear heading control of sailing yachts,” IEEE Journal of Oceanic Engineering, vol. 39, no. 2, pp. 256–268, 2014, doi: 10.1109/JOE.2013.2247276.
