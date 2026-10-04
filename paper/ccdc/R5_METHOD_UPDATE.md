# R5: bounded method/related-work update proposal

Keep `draft.md` unchanged. R5 is an application adaptation, not a claim of a new controller, network, or safety theorem.

## Proposed attribution and method paragraph

We adapt the geometric recovery directions and side-commitment supervisor of A. I. Jambak, I. Bayezit, and M. Reyhanoglu, “Obstacle Avoidance for Autonomous Sailing Sea Drones with No-Go-Zone Recovery,” *Drones*, vol. 10, no. 8, art. 578, 2026, doi: 10.3390/drones10080578. The original equations (13) and (15) supply the obstacle-relative directions and alignment-plus-side-bonus score. Our interface produces finite world-coordinate position targets for a fixed SAC-LSTM rather than commanding the authors’ heading/PD/sail controller. We omit the wind-dependent projection and TACK branch because direct wind observations are outside the information setting. Therefore this is a partial, attributed adaptation, not a full WF-RS reproduction or a test of the source paper’s claims.

Necessary implementation choices are a 500 m position-reference length, all-obstacle/continuation checks, and explicit target update/exit timing. Development selected 90 m recovery scale, 60 s valid-target check period, and 90 m exit clearance, with normal Relay160 guidance. The period also delays exit checks, and invalid/close targets can trigger earlier updates. In the frozen evaluation, 48 of 50 recovery proposals used the clipped radial-perpendicular branch because the boat was inside the extra planning circle. Do not describe the results as verification of a true-tangent safety envelope.

## Evidence to add, with limits

The methods were frozen before 72 new instances: 36 routine 1/3/5 km and 36 prespecified risk instances. Primary safe arrivals were 34/36 routine and 36/36 risk; Relay160 34/36 and 33/36; Relay120 35/36 and 32/36. The three risk gains over Relay160 replaced timeouts, not collisions. Routine common-safe arrival time versus Relay120 increased 99.06 s on average (n = 34; median 15.5 s), whereas risk common-safe time versus Relay160 decreased 103.79 s (n = 33; median 0). Keep the populations and conditional denominators separate. Three discordant risk pairs give exact two-sided p = 0.25; these observations do not establish a general safety improvement.

The exit-135 ablation retains 33/36 risk safe arrivals with three buffer breaches, while the fixed-position alternative reaches 35/36. The primary still fails on the same 5 km staggered instance as Relay160, where Relay120 succeeds. It also adds 411 s to a routine 1 km case and loses 2050 s to Relay120 in the showcased 5 km gain over Relay160. Thus preserve the candidate as evidence of conditional application value, not as a universal replacement for the simple references. No extra module is justified merely to create novelty. An equal-length non-tangent reference control is missing; direction, reference length and management effects are not all independently identified.

## Related work boundary

A. İşleyen, N. van de Wouw, and Ö. Arslan, “Feedback Motion Prediction for Safe Unicycle Robot Navigation,” IROS 2023, doi: 10.1109/IROS55552.2023.10341787; author version https://arxiv.org/html/2209.12648v3. We read the feedback/prediction assumptions, but did not implement its controller-specific analytical regions or import their guarantees into the learned sailboat system.

Use the verified source map in `runs/r5_literature_20261004T080700Z/literature/`, the Chinese method note and complete research report before editing the manuscript. Add real favorable and unfavorable trajectories, not just aggregate rates. This note is an author-facing update proposal; it does not assert submission readiness.
