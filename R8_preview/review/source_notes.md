# R8 primary source and implementation notes

Read 2026-10-05. Bounded source review, same-family / provisional.

## Primary framework

Wilkie, van den Berg and Manocha, *Generalized Velocity Obstacles*, IROS 2009, DOI 10.1109/IROS.2009.5354175. Read the [author-hosted PDF](https://gamma.cs.unc.edu/NHRVO/WilkieIROS09.pdf), sections IV-V and conclusion. Extracted text was available; the web screenshot operation failed, so no visual PDF inspection is claimed.

Equations (2)-(3) define collision-producing controls using the induced position A(t,u) and obstacle position B(t), then minimize their simultaneous distance. Section IV-C restricts time to [0,H]. Equation (10) chooses a feasible control nearest the preferred control. Section V samples controls and checks every obstacle; the car example holds speed and steering fixed. Equation (9) uses locally linear obstacle motion.

| Source component | Proposed R8 treatment | Guarantee not transferred |
|---|---|---|
| Control-induced trajectory | Candidate waypoint plus explicit feedback/hold protocol drives SAC and independent dynamics | Exact car trajectory |
| Minimum simultaneous distance | Numerical relative-segment clearance over [0,H] | Exact continuous minimum |
| Feasible preferred-control search | Reject unsafe samples; rank remaining candidates by progress/change cost | Completeness or global optimality |
| Finite horizon and obstacle prediction | Current-observation constant-velocity target extrapolation | Safety after turns or beyond H |

The paper notes numerical distance error, missed feasible samples, measurement noise and local minima. An estimated-wind sailboat model adds further uncertainty. These support a finite candidate adaptation, not inherited safety certification.

## R8-specific mapping and contracts

The following is proposed engineering interpretation, not a claim made by Wilkie et al.

Let I_t contain observed raw states through t, actual issued commands before t, observed target histories, the current reference/manager state, and the already-computed command a_t. A candidate c specifies a reference and its subsequent management. The predictor computes Xhat_(t+k)(c | I_t, what_recent), using constant-velocity target estimates from the last valid timestamp. It may simulate future observations and commands internally; those are assumptions, not measurements.

The first step must use a_t for all c. New reference and LocalFrame take effect at t+1. Future commands come from the same frozen actor, normalizer, history interpretation and candidate protocol used by execution. If normal navigation replans within the horizon, its model must do the same. Avoidance hold duration, safety interruption, reference handoff and rejoin rules must be recorded. Replanning at the next hold boundary does not by itself guarantee continued feasibility.

Current implementation evidence (reviewed main db9336dab91284044908f829b9b23f53148db693):

| File / lines | Verified behavior relevant to prediction |
|---|---|
| third_party/senior/sailboat_s14.py:164-169,216-251 | 14D observation; ±10 degree command scale and 10 degree/s rates; persistent clipped target-angle accumulators; floor-to-degree increments; actual angles interpolate within each 1 s step |
| same:284-315,403-441 | Wind enters force model; roll affects world translation and yaw rate; nonlinear hydrodynamics are already implemented |
| same:444-555 | Adaptive integration, persistent actual angles, 1 s clock and end-of-step wind update |
| src/sailboat_routing/continuous.py:119-194 | Independent module ownership required; wrapper scales normalized commands and does not reset physical state on goal changes |
| src/sailboat_routing/navigation.py:40-48 | Environment-only field lookup uses real current position and time |
| src/sailboat_routing/frames.py:63-124 | Rigid target frame; progress recomputation; replay of causal raw history with actual previous commands |
| src/sailboat_routing/r7_dynamic.py:17-59 | Truth functions separated from observations; 85 m safety radius; simultaneous relative-segment minimum; history-specific obstacle encoding |
| scripts/run_r7.py:38-67 | Compute old-reference action, plan, execute, update observation, then install/reencode the next reference |
| src/sailboat_routing/obstacle_candidate.py:103-136 | Persistent actor state, previous observation/action, and attention history; candidate rollouts must isolate all of them |

Target actuator reconstruction uses the same initial target values, action scaling and per-step floor/clipping as real execution. Reading current actual sail/rudder values is insufficient to reconstruct target backlog. Wind fitting from the most recent completed transition gives a lagged estimate; the real next field sample remains hidden.

## Evidence identities and scope

Read R7_METHOD_NOTE, R7_RESEARCH_REPORT, R6_METHOD_NOTE, HANDOFF and relevant PROJECT_MEMORY entries. R7 report lines 22 and 35-43 distinguish real confirmation85 failures from final endpoint gains and the 740 s adverse case. R4_RESEARCH_REPORT line 150 records the ordinary-feedback counterexample. No raw R7 outcome was recomputed in this bounded review.

Source SHA256 at review time:
- r7_dynamic.py: 4bc7a961f2ab1bf8ec077bd0ffa18aa9ef6049ab01f6a578712ae3839bad2533
- r6_controller.py: 5d15a6975b990d19fa8bb5255930b132904dc84409cbb48bd01d6f23bc5b034d
- frames.py: f2b8712971f31c78ce1f40d52a6e1384eef74051680f8df37e5eeabb2602eef1
- continuous.py: 2971ab5efe3e70757418e1d8140782f5cd6b29a0f6291c360eadc0871f67a3ce
- third_party/senior/sailboat_s14.py: 8668f769194b65857667b255eeca6467e45d3e248131ea46af245bfbdc156313
- scripts/run_r7.py: 44ab0903ac5b6d094960d2386b9f1ea2ba649c41d5773aa0f7a2897278641635

Only design_review.md and source_notes.md are reviewer outputs. No implementation, historical evidence, project memory or experiment state was changed.
