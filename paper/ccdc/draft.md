# Execution-Aware Waypoint Management for a Frozen Sailing Controller without Direct Wind Measurements

**Working CCDC draft, 3 October 2026.** Authors, affiliations, funding, inherited-asset authorship and permission to distribute those assets require author confirmation. This document is being completed while the prospectively specified experiments run; final selection and numerical results will replace the provisional portions below.

## 1. Introduction and related work

A waypoint is an input to a sailing controller, not a promise that the boat will follow the straight segment leading to it. Wind-dependent propulsion, finite turning response, and autonomous tacking can move the executed path toward an obstacle even when the target chord remains collision-free. This distinction matters when a local learned controller is reused for navigation across several kilometres. Retraining that controller changes the problem and may be impractical. The high-level planner must instead choose references that the existing controller can execute.

This study considers a complete static obstacle map and a frozen recurrent sail-and-rudder policy. Neither the high-level planner nor the policy observation receives direct wind measurements. The planner can use current position and heading and their causal history. We study a deliberately small intervention: additional geometric planning clearance, combined with a distinction between ordinary target holding and a request to reconsider a target near obstacles. The route margin is an empirical allowance for execution, not a bound on tracking error.

Several sailing studies condition decisions on current wind. Silva Junior et al. use Q-learning to generate high-level waypoints and exclude wind-dependent dead-zone actions [1]. Suda and Nikovski learn rudder or tack decisions for sailing upwind [2]. Their unknown stochastic wind process should be distinguished from unavailable wind measurements: current wind direction and strength enter their state. Wang et al. optimize the probability of arrival before a deadline [3]. Their reduced obstacle-free dynamics permit instantaneous velocity-direction changes within a tack and use wind direction as a feedback state. These settings motivate hierarchical decisions but do not directly evaluate our fixed-controller, unobserved-wind interface.

The closest obstacle supervisor among the inspected sources is the wind-feasible reactive supervisor of Jambak et al. [4]. It constructs obstacle tangents, projects infeasible headings, commits to an avoidance side, and uses hysteresis before returning to nominal guidance. Its environment supplies wind, current, and obstacle state. In contrast, our supervisor sends position targets to an inherited recurrent controller and leaves sail and rudder decisions unchanged. Zhang et al. combine wind-aware logic virtual ship guidance with event-triggered actuation [5]. Their triggering concerns controller-to-actuator communication; our target changes occur at a different level and are not interchangeable with actuator updates.

Wind estimation is another possible response to missing measurements. MoWe estimates wind from a sailing robot's own motion through dead-zone constraints or regression [6]. We do not require an explicit estimator. The architectural relation to reference governors is useful: an additional layer changes the references supplied to a pre-existing closed loop [7]. However, predictive admissibility and model assumptions are needed for a formal constraint guarantee. Predictive safety filters likewise rely on a dynamics model, uncertainty description, and a feasible backup construction [8]. An obstacle-distance trigger alone supplies none of these certificates.

The experimental question is therefore narrower than inventing a new sailing policy: how much of multi-waypoint safe completion comes from route clearance, and does a separate execution-risk trigger add value over a reasonable geometric relay? A useful result may retain the simpler method. Development selects a simple Relay with a 160 m empirical margin cap. The contribution under evaluation is controller-interface and route-clearance adaptation under a fixed information boundary, not a new A* algorithm, a new learned controller, or a predictive safety guarantee. The new evaluation is allowed to reject its advantage over strong controls.

## 2. Problem and fixed low-level interface

Let p_t in R² denote world position at the one-second decision boundary t, and let g_t be the currently issued waypoint. The final destination is G. A static obstacle i has known centre c_i, entity radius r_i, and evaluation buffer b_i. Its true safety radius is R_i = r_i + b_i. These radii are common to every method. The instantaneous obstacle clearance is

c_i(t) = ||p_t - c_i|| - R_i.

On an obstacle-free map the minimum clearance is positive infinity. Safety evaluation uses the minimum circle clearance along each straight segment between consecutive one-second recorded positions. This is a discrete control-step polyline test, not a certificate over the adaptive integrator's continuous curve. A mission succeeds only if it reaches within 10 m of G before its time limit, with no entity collision or safety-buffer intrusion during the entire episode. The limits are 1800, 5400, and 9000 s for 1, 3, and 5 km missions.

The inherited controller is the fourth-chapter 14-dimensional no-wind SAC-LSTM actor at checkpoint 7200, with its matching fixed normalizer. It is not the separate final checkpoint at 9000. The actor uses deterministic tanh(mu) actions in evaluation mode. The simulator maps its normalized commands to incremental sail and rudder actions with the inherited quantization, saturation, and rate limits. The inherited dynamics, weights, and observation normalization remain unchanged. The comparison uses the existing continuous-navigation adapter with no additional sensor or actuator noise; environmental variation comes from the declared synthetic wind field.

The observation contains position, roll and heading, body velocities, angular rates, actual sail and rudder angles, progress variables, and the position target. The shared adapter uses a rigid local frame chosen when a target is issued: the target becomes (500, 0) m, heading is rotated by the leg bearing, and the frame origin is 500 m behind the target. Distances are not rescaled; a physically shorter leg therefore starts closer to that local target. The frame stays fixed until the next target change. Progress fields are recomputed from consecutive real positions in this frame. Its recurrent state follows the actual sequence of observations and previous normalized commands. When a target changes, the existing adapter re-encodes the recorded real history for the new target; it does not invent a counterfactual physical trajectory or reset the mission. Exact asset hashes and inherited source locations are recorded in the project upstream manifest. Original training provenance, formal asset authorship, and the associated publication have not yet been established; author confirmation is necessary before submission and distribution.

The high-level interface exposes the known map, current position and heading, current waypoint, final route goal, simulation clock, and permitted causal history. The geometry-only methods receive no wind estimate. The simulator evaluates a private spatial and temporal wind field. Different trajectories may encounter different local wind values even within the same paired scenario. All paired methods share the field function, initial conditions, and random-disturbance protocol.

The command schedule is also common. At boundary t, the low-level policy first chooses the action for the existing target. The planner then proposes a target, and the already chosen action advances the environment to t+1. A surviving episode applies the proposed target at that next boundary. A proposal immediately preceding termination need not be applied. We therefore distinguish a risk detection, a planning attempt, a proposed target difference, and a target change actually applied by the navigation loop.

## 3. High-level methods under comparison

### 3.1 Route margin and scored waypoint selection

The original R1 planner constructs an A* route on a 25 m grid with additional obstacle clearance. At a planning call, its additional margin is

m_t = min(m, max(0, min(c(p_t), c(G)) - 5 m)).

Here c denotes the minimum clearance from the original safety boundaries. The same inflated map is used for the global route, candidate target chords, and candidate-to-route connections. If the inflated route is unavailable, the planner retries the original safety map. This fallback does not change the evaluation boundary. The empirical margin cap and fallback mean that m is not a uniform guaranteed distance from the executed trajectory.

The candidate set contains the incumbent when geometrically valid, visible route vertices and the final goal within 500 m, and radial targets at 150, 300, and 500 m with 15-degree angular spacing. Duplicate targets are removed. A candidate q must admit a clear chord from the boat and a clear connection to a suffix of the planned route. Its implemented cost is

J(q) = ||p_t-q|| + min_j (||q-v_j|| + L_j)
       + 15 |wrap(bearing(p_t,q)-heading_t)|
       + 0.04 ||q-g_t||,

where v_j is a visible route vertex and L_j is its remaining route length. The final term applies only when the incumbent is valid. Distances are in metres and angles in radians; the numerical coefficients are empirical score conversions. No wind or motion-bias term is active in these experiments.

Ordinary planning is considered every 10 s. A valid incumbent within 550 m is normally held for at least 20 s, and subsequently changes only if the score improves by more than 15. A nonfinal target within 40 m, an invalid chord, or the existing chord-clearance urgency rule bypasses parts of this logic. The hold and improvement checks also require that the incumbent survives the inflated-map candidate filter; validity on the original safety map alone is insufficient. We retain these exact baseline semantics instead of describing the controller as a strict straight-line tracker.

### 3.2 Simple geometric relay

The relay uses the same adaptive planning margin and A* route. It selects the furthest visible point encountered within a 500 m route-arc lookahead, without a radial candidate library or weighted score. It holds a valid target until the handoff distance or chord-risk condition requests a new route target. Development tuning is restricted to a small number of meaningful handoff, margin, and risk settings. This baseline tests whether the scored target library is necessary.

### 3.3 Separate near-obstacle intervention

For the initial risk experiment, a supervisor checks c_i(t) against a fixed clearance threshold d. The fixed trigger is active whenever any c_i(t) < d. A causal variant additionally requires positive net radial approach over the preceding 10 s:

v_i(t) = (||p_(t-10)-c_i|| - ||p_t-c_i||) / 10 s > 0.05 m/s.

This is a recent net approach measurement, not an instantaneous velocity or a predicted collision probability. The causal variant waits until eleven distinct one-second positions are available. Repeated calls at the same physical time do not add history. A 20 s cooldown limits intervention attempts.

A risk attempt asks the unchanged base planner to reconsider the reference. For R1 it temporarily removes the ordinary planning-period, minimum-hold, and 15-point improvement gates while retaining candidate generation and the candidate cost, including its target-change penalty. For the relay it bypasses only the hold decision and recomputes its usual route target. The original settings are restored immediately after that call. A replan-only R1 ablation removes the planning-period gate while retaining the hold and score-improvement gates. These variants isolate additional computation from actually relaxing target commitment. They do not force a new waypoint when the original selection remains best.

Every completed R1 planning call updates its planning timestamp even when it retains the current target. An unscheduled risk call can therefore postpone the next periodic call. This timer effect is part of the implemented variant and must not be described as uniformly earlier target intervention. A simple20s planning-period control tests whether a less frequent ordinary schedule is sufficient. A separate Relay variant uses200m lookahead only during a risk attempt; a constant200m relay controls for the use of shorter targets. The risk wrapper restores its ordinary500m configuration after the call; the constant200m comparator keeps200m throughout. Actual target application remains governed by the common navigation interface.

The frozen main is Relay with margin cap 160 m, lookahead 500 m, handoff 100 m, chord-risk setting 80 m, maximum target distance 550 m, and no predictive trigger. It retains the ordinary Relay hold logic; no new own-clearance supervisor is active in the main. The final controls are original R1, Relay with cap 120 m, the identical Relay with zero extra margin, and R1 replan-only at a fixed 60 m own-clearance threshold. All parameters are immutable after this development choice.

## 4. Experimental protocol

The development data include all previously inspected seed271, seed371, and seed1271 scenarios. None is described as an unseen test. The initial paired screen uses the first36 seed1271 scenes, balanced across four layouts, three wind profiles, and three mission lengths. It combines complete new closed-loop episodes with preserved baseline results after source and full-episode parity checks. Historical timing records are not treated as a new compute benchmark.

The private wind field has nominal speed8m/s. Stable wind is constant. Slow and fast profiles smoothly activate after100s and combine two bounded spatial/temporal directional waves with precomputed random perturbations. The slow profile uses25-degree wave amplitude plus3-degree perturbation,12% speed variation, a primary1800s period, and2400m wavelength. The fast profile uses45degrees plus6degrees,20% speed variation,480s, and1200m. Activation lasts60s and30s respectively. The field is a deterministic function of world position and physical time after scenario initialization; sampling does not advance its private random generator. The navigation adapter updates wind at physical decision boundaries for the next one-second transition; it does not query a future field during high-level planning. These are synthetic stress profiles, not reconstructed weather records.

The final evaluation is prospectively specified as two fresh seed batches,2271 and3271, each containing72 paired scenes. Four layouts (islands, channel, staggered, and open water), three wind profiles, and 1/3/5 km lengths remain in the generator. Methods, parameters, comparisons, and selection rules will be frozen before these scenes are generated. Both batches will be reported regardless of their outcomes.

The primary metric is complete safe arrival. We report buffer intrusion, timeout, and raw program termination separately because a safety violation can be followed by a NoRouteError. Paired safe-arrival wins and losses expose changes hidden by equal aggregate counts. Efficiency is calculated only on the explicitly listed common-safe-success set of each pair, with mean, median, upper tail, and descriptive paired scene-bootstrap intervals. Early failures are never counted as faster arrivals. These intervals characterize this synthetic scenario distribution and are not evidence of field reliability.

Only four single-thread CPU workers are permitted. There is no low-level training and no GPU use. Experiments are limited to eight scientific rounds and twelve wall-clock hours including development, analysis, writing, and review. Method selection must occur before approximately60% of the wall budget is spent.

## 5. Results

### 5.1 Development evidence and discarded hypotheses

The first complete36-scene paired screen provides a reason to preserve target acceptance rather than bypass it indiscriminately. These scenes were already inspected in prior work and are development data.

| Variant | Safe arrival /36 | Buffer intrusion | Timeout |
|---|---:|---:|---:|
| geom80 | 32 | 2 | 2 |
| r1_replan60 | 33 | 1 | 2 |
| r1_fixed60 | 31 | 3 | 2 |
| r1_closing60 | 31 | 3 | 2 |
| relay100_clear80 | 32 | 3 | 1 |
| relay_fixed60 | 29 | 6 | 1 |
| relay_closing60 | 29 | 6 | 1 |

The replan-only variant gains one safe completion and loses none relative to R1 in this screen. On their32common safe arrivals, mean travel time changes by-90.5s and the median by0s. This is concentrated evidence rather than a uniform speedup. The closing gate reduces R1 bypass attempts from86to61and actual risk-associated target changes from50to44, but both variants complete31/36safely. Attempt counts in this first implementation exclude failed terminal planning calls; complete-task outcomes include every episode. The later logger records these exceptions. The policies can have different trajectories and exposure durations, so attempt totals are not a causal estimate of false-alarm reduction.

The adverse development case s1271_032 shows why a risk trigger should not automatically discard acceptance rules. At323s, both policies have the same physical/action history. The fresh incumbent score is4497.14098; the best alternative is4496.42062, only0.72036better. Risk bypass applies the new target at324s and its full episode later violates the buffer at1447s; original R1 safely arrives at3945s. This sequence does not establish that the first replacement alone accounts for all subsequent failure dynamics.

The apparent rescue in s1271_034 has a different timing mechanism. At364s, an extra planning call retains the target because the20s hold has not expired. Updating the planner timestamp postpones the next periodic call: original R1 selects a replacement at371s and applies it at372s, whereas the variant selects its replacement at374s and applies it at375s. Their issued targets first differ at372s while physical state and command prefixes are still identical. The variant safely finishes at1831s; R1 violates the buffer much later at7708s. This is evidence that additional planning can delay a target change, not evidence of a uniformly earlier risk intervention. A simple20s nominal-period control is therefore included in the next development round.

In s1271_028, forcing Relay to recompute at3201s replaces a225.603m target by a500m target. The modified episode later fails at3271s, while ordinary Relay safely finishes at3763s. The conditional200m lookahead experiment tests whether a near-obstacle response should retain a shorter target scale. Constant200m Relay is its simple control.

The completed second screen tests simpler alternatives on the same 36 scenes. A 120 m margin cap in Relay reaches 34/36 safely, with two intrusions and no timeout. Against the 80 m Relay it gains two safe arrivals and loses none, but on their 32 common safe arrivals its mean travel time is 158.59 s longer (median 0 s; descriptive bootstrap 95% interval [-119.41, 462.47] s). Against R1 it wins three and loses one, with a conditional mean increase of 75.48 s on 31 common successes. More safe arrivals therefore do not establish a speed improvement.

Increasing the R1 margin cap to 120 m leaves its aggregate at 32/36. A 20 s nominal R1 planning period also reaches 32/36, with one win and one loss relative to original R1. A 100 m risk-replanning threshold yields 32/36, with one fewer intrusion and one additional timeout than original R1. Constant 200 m Relay is poor (26/36, eight timeouts); using 200 m only during a 60 m risk request reaches 30/36. These short-target branches are not retained. The last development round validates Relay caps 120/160 m and risk thresholds 60/100 m on a second already-seen seed block; 160 m is also evaluated on the original block for a matched small margin-sensitivity comparison.

On the matched 72 development scenes, Relay caps 80/120/160 m safely complete 65/67/69 tasks; original R1 completes 64 and risk-replan thresholds 60/100 m complete 65/64. Relay160 gains seven safe arrivals and loses two relative to R1. On their 62 common safe arrivals, it is 93.47 s slower on average (median 21.5 s; descriptive interval [-23.29, 211.60] s). The seed blocks disagree on the best cap: Relay160 is 36/36 on seed371 versus Relay120's 33/36, but 33/36 on seed1271 versus 34/36. We freeze Relay160 for the declared safety-first selection while explicitly retaining this uncertainty. The sweep does not establish an optimum.

### 5.2 Frozen evaluation

The method was frozen at 3.116 hours of the shared budget, before generating seeds 2271 and 3271. The complete five-group comparison is running; its results and actual trajectory figures will be inserted before delivery. No parameters will be selected from these outcomes.

## 6. Discussion and conclusion

The final conclusion must distinguish empirical route adaptation from any extra value of risk intervention. A preserved margin can be useful without being a tracking-error bound. A risk detector may identify a dangerous situation without finding a target that the unchanged controller can exploit. A simpler geometric relay may remove the need for a scored candidate library. These alternatives are being tested rather than assumed.

The study is limited to one inherited controller, complete static circular-obstacle maps, synthetic wind, and the declared discrete trajectory-clearance test. Training provenance and inherited-asset publication attribution remain to be confirmed by the authors. Results do not establish a formal safety guarantee, a new reinforcement-learning algorithm, or real-sea performance.

## Acknowledgments and AI-use disclosure

Author identities, affiliations, funding, and the formal acknowledgment/citation for the inherited controller and dynamics await human confirmation. OpenAI Codex with GPT-family agents, coordinated through locally installed ARIS workflows, assisted research planning, implementation, experiment orchestration, data analysis, plotting code, source retrieval, and drafting of all sections. Plots represent recorded simulator trajectories rather than generated imagery. Human authors must verify the results, attribution, references, and final submission text.

## References

1. Andouglas Gonçalves da Silva Junior, Davi Henrique dos Santos, Alvaro Pinto Fernandes de Negreiros, João Moreno Vilas Boas de Souza Silva, Luiz Marcos Garcia Gonçalves. "High-Level Path Planning for an Autonomous Sailboat Robot Using Q-Learning." Sensors 20(6), 1550, 2020. DOI: [10.3390/s20061550](https://doi.org/10.3390/s20061550).

2. Takumi Suda, Daniel Nikovski. "Deep Reinforcement Learning for Optimal Sailing Upwind." 2022 International Joint Conference on Neural Networks (IJCNN), 1–8, 2022. DOI: [10.1109/ijcnn55064.2022.9892369](https://doi.org/10.1109/ijcnn55064.2022.9892369).

3. MingYi Wang, Natasha Patnaik, Anne Somalwar, Jingyi Wu, Alexander Vladimirsky. "Risk-Aware Stochastic Control of a Sailboat." 2024 American Control Conference (ACC), 2024. DOI: [10.23919/acc60939.2024.10644458](https://doi.org/10.23919/acc60939.2024.10644458).

4. Ahmad Irham Jambak, Ismail Bayezit, Mahmut Reyhanoglu. "Obstacle Avoidance for Autonomous Sailing Sea Drones with No-Go-Zone Recovery." Drones 10(8), 578, 2026. DOI: [10.3390/drones10080578](https://doi.org/10.3390/drones10080578).

5. Guoqing Zhang, Li Wang, Jiqiang Li, Weidong Zhang. "Improved LVS guidance and path-following control for unmanned sailboat robot with the minimum triggered setting." Ocean Engineering 272, 113860, 2023. DOI: [10.1016/j.oceaneng.2023.113860](https://doi.org/10.1016/j.oceaneng.2023.113860).

6. Qinbo Sun, Weimin Qi, Huihuan Qian. "MoWe: Motion Observation for Wind Estimation of Sailing Robots." Journal of Field Robotics 42(5), 2355–2374, 2025. DOI: [10.1002/rob.22512](https://doi.org/10.1002/rob.22512).

7. Emanuele Garone, Stefano Di Cairano, Ilya Kolmanovsky. "Reference and command governors for systems with constraints: A survey on theory and applications." Automatica 75, 306–328, 2017. DOI: [10.1016/j.automatica.2016.08.013](https://doi.org/10.1016/j.automatica.2016.08.013).

8. Kim Peter Wabersich, Melanie N. Zeilinger. "A predictive safety filter for learning-based control of constrained nonlinear dynamical systems." Automatica 129, 109597, 2021. DOI: [10.1016/j.automatica.2021.109597](https://doi.org/10.1016/j.automatica.2021.109597).
