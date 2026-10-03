# Empirical Route-Clearance Adaptation for a Frozen Sailing Controller without Direct Wind Measurements

**CCDC English content draft — R3.** Authors, affiliations and funding await human confirmation. The inherited controller/dynamics require formal author attribution and permission checks. The manuscript uses real closed-loop simulation records; camera-ready template layout and PDF verification remain pending.

## Abstract

A collision-free waypoint chord need not be safely executed by a sailing controller that turns and tacks autonomously. We study high-level waypoint management with a known static map, unobserved wind and one fixed recurrent sail-and-rudder policy. The main method is a simple geometric relay on an adaptively inflated map. It holds a visible route target until handoff or geometric risk requests replanning. Development on 72 previously seen instances selects a 160 m extra-clearance cap over smaller margins and additional own-clearance intervention rules. This cap is an empirical design choice, not an execution-error bound. A prospectively frozen evaluation compares the method, original scored waypoint selection, a tuned 120 m relay, a zero-extra-margin ablation and a fixed-clearance replanning comparator on 144 new paired 1/3/5 km scenarios. Relay160 safely completes 135/144 missions, compared with 129 for original R1, 133 for Relay120 and 88 without extra margin. Against Relay120 it gains seven successes but loses five, and is 52.9 s slower on their 128 common successes. Against R1 its mean time difference is −129.3 s on 125 common successes, but the median difference is +20 s; a general efficiency improvement is not supported. The study distinguishes complete safe arrival from travel time conditional on both methods succeeding, and documents intervention failures as well as favorable examples. It contributes a bounded application study of a fixed controller interface rather than a new reinforcement-learning algorithm or a formal safety guarantee.

## 1. Introduction and related work

A sailing waypoint is a reference supplied to a controller, not a command to follow its straight chord. Wind-dependent propulsion, finite turning response and autonomous tacking can bring an executed path toward an obstacle even when the target chord is clear. This matters when a local learned controller is reused over several kilometres. We consider the practical problem of selecting and maintaining position targets without retraining that controller or providing direct wind measurements.

The principal question is whether a small geometric allowance for execution is sufficient, or whether explicit near-obstacle intervention adds value. We compare scored waypoint selection with a simpler A* route relay, rather than assuming a large candidate library is necessary. Development selects the relay with a larger empirical clearance cap. The final comparison retains the frozen choice while testing its limits against the simpler alternatives. Neither map inflation nor A* nor target holding is claimed as a new algorithm; the application contribution being tested is their adaptation and controlled evaluation at a fixed learned-controller interface.

Several sailing planners use current wind information. Silva Junior et al. generate high-level waypoints using Q-learning with wind-dependent dead-zone restrictions [1]. Suda and Nikovski learn upwind sailing decisions [2]; an unknown stochastic wind process in their setting does not mean absent measurements, since current direction and strength enter the state. Wang et al. optimize the probability of arriving before a deadline [3], using wind direction as a feedback state in reduced, obstacle-free dynamics with instantaneous velocity-direction changes within a tack. These studies motivate hierarchical decisions but do not directly test our observation and controller contract.

Jambak et al. construct obstacle tangents, project wind-infeasible headings, commit to an avoidance side and use hysteresis [4]. Their supervisor receives wind, current and obstacle state. Our high level instead supplies position targets to an inherited recurrent controller and leaves sail and rudder decisions unchanged. Zhang et al. combine wind-aware logic virtual ship guidance with event-triggered actuation [5]; their actuator communication trigger is different from our waypoint interface. MoWe provides a motion-based alternative for estimating wind [6], which this study does not require.

Reference governors also modify references supplied to a pre-existing closed loop [7]. Their constraint guarantees require suitable admissibility models and assumptions. Predictive safety filters similarly use dynamics, uncertainty descriptions and a feasible backup construction [8]. Our empirical clearance and geometric trigger supply no such certificate. The relevant comparison is therefore an empirical one: complete safe missions and their navigation costs under the same fixed controller and information boundary.

## 2. Problem and common controller interface

At the one-second decision boundary t, let p_t denote world position, g_t the issued waypoint, and G the final destination. Obstacle i has known centre o_i, entity radius r_i and evaluation buffer b_i. Its safety radius R_i = r_i + b_i is identical for every method. Point clearance and minimum point clearance are

```text
c_i(p) = ||p - o_i|| - R_i,       c(p) = min_i c_i(p).
```

On an obstacle-free map c(p) is positive infinity. Evaluation uses the minimum circle clearance along every segment joining consecutive one-second recorded positions. This control-step polyline test is not a certificate over the adaptive integrator's continuous curve. A mission succeeds only if it reaches within 10 m of G within the fixed 1800/5400/9000 s limit for a 1/3/5 km task, without an entity collision or safety-buffer intrusion anywhere in the episode. Recovering after an intrusion does not restore success.

The inherited asset is a 14-observation-dimensional, no-wind SAC-LSTM (soft actor–critic with long short-term memory) actor and its matching fixed normalizer. Its internal asset identity is the fourth-chapter checkpoint 7200, not the separate final checkpoint at 9000. Evaluation uses deterministic tanh(mu) actions. Observation fields include position, roll/heading, body velocities, angular rates, actual sail/rudder angles, progress and the target. The inherited action quantization, saturation, rate limits and dynamics remain fixed. The continuous-navigation adapter adds no sensor or actuator noise. Original training provenance, formal asset authorship and an associated publication have not been established; the authors must settle attribution before submission or distribution. Exact source locations and asset hashes are recorded in the upstream manifest.

A common rigid local frame places the issued target at (500, 0) m. Its origin lies 500 m behind that target along the bearing from the measured position when the target is applied; heading is rotated, but physical distances are not rescaled. A shorter leg therefore starts closer to the local target. The frame remains fixed until a target change. Progress fields are recomputed from consecutive real positions. At a change, the adapter rebuilds recurrent state from the recorded physical observations and actual previous normalized commands in the new frame. It neither invents physical history nor resets mission time.

The planner receives the map, current position, heading, target, destination and clock; permitted history is used only by explicitly identified variants. Geometry-only methods receive no wind estimate. The actor also has no direct wind observation. All paired methods share initial conditions, the external wind-field function and the random-disturbance protocol. Different paths naturally encounter different local wind values.

Each episode initializes its first target and frame at t=0 before taking an action. During navigation, at boundary t the actor first chooses its action for g_t. The planner then proposes a target, and the already chosen action advances the physical state to t+1. A surviving episode applies the new target at that boundary. A proposal immediately preceding termination may never be applied. We distinguish risk detection, a planner call, a proposed change and an actually applied target change.

## 3. Frozen main method and comparators

### 3.1 Simple relay with empirical planning clearance

The frozen main is **Relay160** (`relay_m160`). When replanning is required, its additional margin is

```text
m_t = min(160 m, max(0, min(c(p_t), c(G)) - 5 m)).
```

The planner adds m_t to every obstacle's evaluation buffer for route and target feasibility checks, leaving the evaluation radii unchanged. It constructs an A* route on a 25 m grid. If no route exists on the inflated map, it retries the original safety map with zero additional margin. Thus 160 m is a cap, not a minimum maintained clearance or an error bound.

The relay walks up to 500 m of route arc length and selects the furthest encountered point visible from p_t on the planned map. Candidates are route vertices and the point at which the 500 m arc budget is exhausted; the relay does not cut an occluded turn or extend beyond G. It uses no radial library, weighted candidate score, learned predictor or explicit wind estimate.

Let d_seg(p_t,g_t) be the original-map safety clearance of the target chord. An incumbent is valid if it is within 550 m and the chord is clear. It is near handoff when it is nonfinal and within 100 m. The retained geometric risk rule is

```text
risk = d_seg(p_t,g_t) < min(80 m, max(0, c(p_t) - 5 m)).
```

A valid target is held while neither handoff nor risk is active. Otherwise a route target is recomputed. This original chord-risk rule can weaken as point clearance shrinks; it is not a predictive safety guarantee. No additional fixed own-clearance supervisor is used by the main method.

```text
At each physical decision boundary:
    read the available state and unchanged static map
    if current target is valid, not near handoff, and not at chord risk:
        keep current target
    else:
        cap extra margin by available start/goal clearance
        plan an inflated-map A* route; fall back to original map if needed
        choose the furthest visible route point within 500 m arc length
    submit target through the common t-to-t+1 interface
```

![Frozen interface schematic](../../runs/r3_ccdc_20261003T121146Z/figures/method_framework.png)

*Figure 1. Interface schematic only. It is not an experimental trajectory or safety certificate. The low-level controller and real-history processing are common to all groups.*

### 3.2 Strong controls and direct ablation

Original **R1** (`geom80`) uses an 80 m adaptive margin and a feasible candidate set containing route vertices, the incumbent and radial targets at 150/300/500 m with 15-degree spacing. Its cost combines remaining connected-route distance, 15 times the absolute heading change in radians, and 0.04 times target displacement. Wind and motion-bias terms are disabled. Ordinary planning has a 10 s period, 20 s hold and 15-point improvement threshold. Hold and improvement gates require a nonurgent incumbent that survives the inflated-map candidate filter; validity on the original safety map alone is insufficient.

**Relay120** is the strongest lower-margin simple development comparator and differs from Relay160 only in its margin cap. **Relay0** removes only the extra planning margin from the main; original safety radii and all relay settings remain fixed. This directly tests the retained spatial mechanism.

**Risk60** (`r1_replan60`) is the strongest developed fixed-own-clearance R1 comparator. If any current point clearance falls below 60 m and a 20 s attempt cooldown has elapsed, it requests a planning call while retaining R1's hold and score-improvement gates. It does not use an approach predictor. Every completed R1 planning call updates the planning timestamp, even if the target is held, so an extra request can postpone the next periodic call. This implemented rescheduling must not be described as uniformly earlier intervention.

| Frozen group | Planner | Extra margin cap | Additional own-clearance request |
|---|---|---:|---|
| R1 | scored route/radial targets | 80 m | none |
| Relay120 | route relay | 120 m | none |
| Relay160 (main) | route relay | 160 m | none |
| Relay0 (ablation) | same route relay | 0 m | none |
| Risk60 | original R1 with retained acceptance | 80 m | below 60 m; 20 s cooldown |

## 4. Experimental design

All previous seed271/371/1271 scenes are seen data. Initial screens use the first 36 seed1271 scenes. Surviving methods and both original baselines are then compared on the same 72 instances: those 36 scenes and 36 seed371 scenes. They cover four layouts (islands, channel, staggered, open water), three wind profiles and 1/3/5 km lengths. Preserved baseline episodes are reused only after relevant source/configuration checks; two full baseline replays also reproduce their physical/action traces and scientific outcomes exactly. Historical compute timings are not treated as a fresh speed benchmark.

The synthetic field has nominal speed 8 m/s. Stable wind is constant. Slow/fast profiles activate smoothly after 100 s and combine bounded spatial/temporal waves with precomputed perturbations. Slow wind uses 25-degree wave amplitude plus 3-degree perturbations, 12% speed variation, a primary 1800 s period and 2400 m wavelength. Fast wind uses 45 degrees plus 6 degrees, 20%, 480 s and 1200 m. Activation lasts 60/30 s respectively. Wind updates occur at physical decision boundaries for the next transition. Sampling the initialized field does not advance its private random generator, and no field object or future wind reaches the planner.

The method, parameters, analysis and case-selection rules were frozen at 3.116 hours of a shared 12-hour budget, before generating seed2271 and seed3271. Each new batch contains 72 paired scenes: two instances for each layout/wind/distance combination. All five groups run all 144 instances regardless of outcomes. The study uses at most four single-thread CPU experiment workers and no GPU or low-level training. Complete manifests and scientific source hashes identify the exact implementation; the frozen evaluation commit is `037fe1a`.

Safe arrival is primary. Buffer intrusions, timeouts and original program-stop reasons are reported separately. Paired wins/losses reveal changes hidden by equal totals. Time and path length use each pair's explicitly listed common-safe-success set, with mean, median, upper tail and descriptive scene-bootstrap intervals. Early failure never counts as a faster arrival. Wilson and paired intervals describe this finite synthetic experiment, not field reliability or safety equivalence. A margin-only relay comparison must leave open-map physical/action traces unchanged.

Normal 1/3/5 km figures use the three displayed methods (R1, Relay120, Relay160) and prefer their open/channel/staggered common successes closest to the within-pool median main-minus-R1 time difference. Favorable and adverse extremes are labelled posthoc. Development intervention examples are explicitly separated from the new evaluation.

## 5. Results

### 5.1 Development selection and discarded mechanisms

On matched 72 seen scenes, R1, Risk60, risk-replan100, Relay80, Relay120 and Relay160 safely complete 64, 65, 64, 65, 67 and 69 tasks. Relay160 gains seven safe arrivals and loses two relative to R1, but on their 62 common successes is 93.47 s slower on average (median 21.5 s; descriptive 95% interval [-23.29, 211.60] s). Seed blocks disagree: Relay160 is 36/36 on seed371 versus Relay120's 33/36, but 33/36 on seed1271 versus 34/36. We select Relay160 for the declared safety-first objective and retain this uncertainty; the three-cap sweep does not establish an optimum.

In the first 36-scene screen, bypassing R1's hold and score gates at 60 m gives 31 safe arrivals versus R1's 32. Restricting requests to net radial approach above 0.05 m/s over the past 10 s also gives 31; fewer attempts do not establish better navigation. Exposure and stopping times differ, and first-round attempt logs omit failed terminal calls although outcomes include all episodes. The later logger records these exceptions without changing behavior. Constant 200 m Relay reaches 26/36 with eight timeouts; 200 m lookahead only during risk requests reaches 30/36. A 20 s nominal R1 period reaches 32/36 with one gain and one loss. These branches are not retained.

The adverse development case s1271_032 is concrete. At 323 s the physical/action prefixes match. The fresh incumbent score is 4497.14098 and the best alternative is 4496.42062, only 0.72036 better. At that same state, the original-map chord clearance is 58.52 m for the incumbent and 57.76 m for the replacement; a small score improvement is not an increased geometric clearance. Bypass applies a new target at 324 s; its complete episode later violates the buffer at 1447 s while R1 safely arrives at 3945 s. This does not prove that the first replacement alone caused the eventual failure. Conversely, an apparent rescue in s1271_034 involves a retained target at a 364 s risk request, which shifts the planning clock: R1 changes at 372 s, the variant at 375 s. Its later success is not evidence of uniformly earlier risk intervention.

### 5.2 Prospectively frozen evaluation

All 720 episodes in the unchanged manifest completed. Saved-data checks cover paired inputs, frozen configurations and source identities, action/target timing, and recomputation of path length, clearance and tack counts from raw records. Table 2 gives every frozen group. Each distance contains 48 scenes; each seed block contains 72. There are no entity collisions or other outcome categories. All buffer failures stop with `NoRouteError`; timeouts stop with `task_limit`. The original error labels are retained rather than replacing unsafe episodes with successful replanning.

| Method | Safe / 144 | Buffer | Timeout | 1 km / 48 | 3 km / 48 | 5 km / 48 | Seed2271 / 72 | Seed3271 / 72 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| R1 | 129 | 6 | 9 | 46 | 41 | 42 | 66 | 63 |
| Risk60 | 131 | 4 | 9 | 46 | 42 | 43 | 67 | 64 |
| Relay0 | 88 | 55 | 1 | 36 | 28 | 24 | 44 | 44 |
| Relay120 | 133 | 9 | 2 | 46 | 45 | 42 | 66 | 67 |
| Relay160 | 135 | 4 | 5 | 44 | 47 | 44 | 68 | 67 |

*Table 2. Complete safe arrival, failures and prespecified distance/seed breakdowns. None of these scenes was used to select the frozen method.*

Relay160's safe-arrival fraction is 93.75% (Wilson 95% interval 88.55–96.68%). Its direct comparison with Relay0 gains 50 safe arrivals and loses three. The paired safe-arrival difference is 32.64 percentage points, with an exploratory scene-bootstrap interval of [24.31, 40.97]. Thus the additional planning margin has substantial empirical value under this controller and test distribution. This result does not establish that the nominal margin bounds execution error.

The comparison with a reasonable nonzero margin is much less decisive. Relative to Relay120, Relay160 gains seven safe arrivals and loses five: +1.39 percentage points, with a descriptive interval of [−3.47, 6.25]. Buffer failures decrease from nine to four, while timeouts increase from two to five. We cannot claim a stable advantage or an optimal 160 m cap. Relative to R1 it gains ten successes and loses four (+4.17 points; interval [−0.69, 9.03]). The aggregate hides a 1 km regression from 46/48 to 44/48.

| Control (difference = Relay160 − control) | Safe wins / losses | Common-safe n | Mean Δtime (s) | Median Δtime (s) | 95% interval for mean Δtime (s) | Mean Δpath (m) |
|---|---:|---:|---:|---:|---|---:|
| R1 | 10 / 4 | 125 | −129.33 | +20.0 | [−347.70, +54.97] | +200.50 |
| Risk60 | 8 / 4 | 127 | −145.60 | +20.0 | [−373.64, +54.02] | +183.19 |
| Relay0 | 50 / 3 | 85 | +55.48 | 0.0 | [−141.37, +224.39] | +250.29 |
| Relay120 | 7 / 5 | 128 | +52.89 | +2.5 | [−37.84, +135.14] | +240.98 |

*Table 3. Paired efficiency is conditional on both methods safely arriving. Different rows use different scene sets; their means must not be compared as unconditional rankings.*

Against R1, mean time differences at 1/3/5 km are +59.26/+30.85/−487.29 s on 43/41/41 common successes; medians are +42/+17/+7 s. The 5 km mean is sensitive to long R1 episodes, with a descriptive interval of [−1110.00, +50.67] s. Its time 90th percentile decreases from 5269 to 2488 s, while some individual cases regress severely. Across all distances the common-success path is 200.50 m longer on average. Against Relay120, mean path increases by 240.98 m (descriptive interval [88.19, 457.38] m), and the time 90th percentile increases from 1983.7 to 2158.9 s. The larger cap therefore entails an observable navigation cost rather than a general long-range speed improvement.

Risk60 gains four safe arrivals and loses two against R1. Their 127 common successes have mean time difference −9.88 s, median zero and interval [−80.90, +48.95] s. Across its 144 episodes, 4399 risk-positive decision steps produce 276 planning attempts, 43 proposed changes and 43 applied changes in 21 episodes. In 80 attempts all triggering obstacles have receding net radial trends over the preceding 10 s. These are not proven false alarms: a past trend is neither instantaneous closing speed nor future safety. The intervention evidence does not justify retaining an additional risk supervisor in the main.

The open-map negative control passes all 108 pair comparisons across 36 distinct scenes: Relay0/120/160 share identical physical, action, wind and target-event records, and R1 matches Risk60. Wall-clock timing fields are excluded. These are three comparisons per scene, not 108 independent scenarios.

![Complete outcome and conditional-efficiency statistics](../../runs/r3_ccdc_20261003T121146Z/figures/outcomes_and_efficiency.png)

*Figure 2. All five groups, including direct ablation and strong simple comparison. Time differences include only the indicated common-safe sets. Positive differences are costs to the main.*

### 5.3 Actual trajectories, intervention and failures

Figures 3–5 are recorded, unsmoothed trajectories selected by the frozen representative rule. The dotted route is an offline initial A* reference with R1's 80 m cap; it is not an executed trajectory or Relay160's planned route. Circles distinguish entity and unchanged safety boundaries. Applied waypoint markers are sparsely displayed; full trajectory and target-event tables accompany the figures.

![One-kilometre paired actual trajectories](../../runs/r3_ccdc_20261003T121146Z/figures/trajectory_1km.png)

*Figure 3. Open stable 1 km scene s2271_003: all displayed methods finish in 277 s. Relay120 and Relay160 overlap exactly. This negative control does not demonstrate obstacle-avoidance benefit.*

![Three-kilometre paired actual trajectories](../../runs/r3_ccdc_20261003T121146Z/figures/trajectory_3km.png)

*Figure 4. Channel stable 3 km scene s3271_049: R1/Relay120/Relay160 finish in 785/791/994 s. The main's path is 3765.63 m versus R1's 3052.02 m, showing the cost of this choice.*

![Five-kilometre paired actual trajectories](../../runs/r3_ccdc_20261003T121146Z/figures/trajectory_5km.png)

*Figure 5. Staggered fast 5 km scene s2271_070: times are 1677/1670/1689 s and minimum safety clearances 0.89/11.35/84.87 m for R1/Relay120/Relay160. Safer clearance in this example is not a universal minimum-clearance guarantee.*

![Development intervention regression](../../runs/r3_ccdc_20261003T121146Z/figures/development_bypass_regression032.png)

*Figure 6. Seen development case s1271_032. The first applied target difference occurs at 324 s after a 0.72036-point improvement. The later buffer intrusion illustrates a discarded branch, not an isolated causal effect of one target. The paired prefix and same-state score evidence are preserved.*

The posthoc favorable extreme s2271_066 reduces R1's safe 5 km time from 8703 to 1773 s; Relay120 fails at 682 s and is not counted as faster. The adverse extreme s2271_065 instead increases time from R1's 1824 s and Relay120's 1522 s to 4370 s, and lengthens the main's path to 15343.46 m. Both extremes and the frozen first adverse case are included in the offline gallery. In that first adverse case, s2271_040, Relay160 times out at 1800 s while R1 and Relay120 arrive at 416/372 s; it is not a buffer failure.

![Frozen obstacle-safety failure](../../runs/r3_ccdc_20261003T121146Z/figures/obstacle_safety_local.png)

*Figure 7. Additional frozen adverse case s2271_046. R1 succeeds; Relay120 and Relay160 enter the buffer. Insets preserve the original safety boundary and actual terminal positions.*

In s2271_046 the main keeps its initial waypoint throughout. At 733 s its target is still 192.93 m away, outside handoff. Both point and target-chord clearance are +0.3935 m, but the retained risk threshold is zero. Thus the chord remains valid and the risk rule is false. The actual 733–734 s displacement has clearance −0.2408 m and the subsequent call raises `NoRouteError`. This confirms a concrete gap between retained-chord logic and execution near a boundary. It does not establish that a different waypoint would have rescued the same state; no new counterfactual rollout was run after freezing.

## 6. Discussion and conclusion

This study converges to an empirical route-clearance adaptation with simple target relay, not to a validated new risk-intervention algorithm. The zero-margin ablation supports retaining planning allowance, while the competitive Relay120 result prevents claiming that 160 m is optimal or reliably superior. Relay160 is kept as the prospectively selected main, not retrospectively renamed after testing. Its 135/144 safe arrivals exceed R1's observed total, but it loses short-range cases and does not establish a consistent travel-time advantage. The R1 comparison changes both margin and target-selection logic; it does not isolate a causal benefit from removing the candidate library.

The decision-level cases explain why intervention counts are insufficient: calls can hold a target yet shift the planning clock, while a score-improving replacement can have a smaller chord clearance. Neither gate bypass nor extra risk calls supplies a safety certificate. A future mechanism study would need same-state evidence that an intervention changes an impending execution failure, rather than inferring that mechanism from aggregate success or event order.

The evidence is limited to one inherited controller, a complete static circular-obstacle map, synthetic wind, ideal state observations and the declared control-step clearance test. The adaptive cap and original-map fallback prevent interpreting nominal margin as a guaranteed buffer. The margin ablation estimates combined route/target effects, not an identified tracking-error tolerance. Open-water timeouts and reversals can remain unchanged. We recommend author revision as a bounded application and diagnostic study; claims of a new safety filter, universal efficiency, or field reliability are not supported. Formal asset attribution, the official submission template and a compiled page-budget check remain necessary before submission.

## Acknowledgments and AI-use disclosure

Human authors must confirm the author list, affiliations, funding and formal acknowledgment/citation for the inherited controller and dynamics. OpenAI Codex and GPT-family agents, coordinated through locally installed ARIS workflows, assisted planning, implementation, experiment orchestration, analysis, plotting code, source retrieval and drafting of all sections; GPT-6-Astra agents provided auxiliary review. Plots are drawn from recorded simulator trajectories, not generated imagery. Human authors remain responsible for verification, attribution, references and the submitted text.

## References

1. Andouglas Gonçalves da Silva Junior, Davi Henrique dos Santos, Alvaro Pinto Fernandes de Negreiros, João Moreno Vilas Boas de Souza Silva, Luiz Marcos Garcia Gonçalves. "High-Level Path Planning for an Autonomous Sailboat Robot Using Q-Learning." Sensors 20(6), 1550, 2020. DOI: [10.3390/s20061550](https://doi.org/10.3390/s20061550).

2. Takumi Suda, Daniel Nikovski. "Deep Reinforcement Learning for Optimal Sailing Upwind." 2022 International Joint Conference on Neural Networks (IJCNN), 1–8, 2022. DOI: [10.1109/ijcnn55064.2022.9892369](https://doi.org/10.1109/ijcnn55064.2022.9892369).

3. MingYi Wang, Natasha Patnaik, Anne Somalwar, Jingyi Wu, Alexander Vladimirsky. "Risk-Aware Stochastic Control of a Sailboat." 2024 American Control Conference (ACC), 2024. DOI: [10.23919/acc60939.2024.10644458](https://doi.org/10.23919/acc60939.2024.10644458).

4. Ahmad Irham Jambak, Ismail Bayezit, Mahmut Reyhanoglu. "Obstacle Avoidance for Autonomous Sailing Sea Drones with No-Go-Zone Recovery." Drones 10(8), 578, 2026. DOI: [10.3390/drones10080578](https://doi.org/10.3390/drones10080578).

5. Guoqing Zhang, Li Wang, Jiqiang Li, Weidong Zhang. "Improved LVS guidance and path-following control for unmanned sailboat robot with the minimum triggered setting." Ocean Engineering 272, 113860, 2023. DOI: [10.1016/j.oceaneng.2023.113860](https://doi.org/10.1016/j.oceaneng.2023.113860).

6. Qinbo Sun, Weimin Qi, Huihuan Qian. "MoWe: Motion Observation for Wind Estimation of Sailing Robots." Journal of Field Robotics 42(5), 2355–2374, 2025. DOI: [10.1002/rob.22512](https://doi.org/10.1002/rob.22512).

7. Emanuele Garone, Stefano Di Cairano, Ilya Kolmanovsky. "Reference and command governors for systems with constraints: A survey on theory and applications." Automatica 75, 306–328, 2017. DOI: [10.1016/j.automatica.2016.08.013](https://doi.org/10.1016/j.automatica.2016.08.013).

8. Kim Peter Wabersich, Melanie N. Zeilinger. "A predictive safety filter for learning-based control of constrained nonlinear dynamical systems." Automatica 129, 109597, 2021. DOI: [10.1016/j.automatica.2021.109597](https://doi.org/10.1016/j.automatica.2021.109597).
