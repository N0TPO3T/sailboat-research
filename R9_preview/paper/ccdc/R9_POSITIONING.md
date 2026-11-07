# R9 positioning update (R3 draft preserved)

Position the dynamic component as a bounded extension study of executable waypoint supervision under computation and delivery delay. The core empirical question is whether candidate-conditioned predictions retain avoidance benefits when the vessel keeps moving while planning.

Use Generalized Velocity Obstacles (Wilkie, van den Berg and Manocha, IROS2009, DOI10.1109/IROS.2009.5354175) as the source of control-conditioned trajectory evaluation. Our reference/hold/feedback and fixed delivery slot are adaptations to a learned sailboat controller, not a new safety theorem or a reproduction of full BC-MPC.

Report ideal and delayed R8 separately. A recurrence-only replay optimization preserves the saved-state candidate trajectories but can still change closed-loop outcomes through delivery timing. The strongest developmental contrast uses identical observed history at150s in mixed7: accounting for waiting changes the nominal prediction from88.689m to−1.032m and selects a different maneuver. Mixed3 is instead a scheduling effect with no nonnominal selection. Do not combine these into one unsupported causal claim.

State the independent planner/feedback executor assumption,25s slot,26s reference age,60s avoidance hold,86s horizon, deadline drops, controller-tick measurements, and the remaining endpoint777vs317s cost. Include every frozen win and loss from docs/R9_RESEARCH_REPORT.md, the two long instances, and activated turn/delay checks. Do not claim hard real time, broad generalization, COLREGs completeness or deployment readiness.

The frozen12short instances add no safety gain over reactive and incur57.42s mean extra time. One new3km case retains an avoidance gain, while the5km case costs32s. A30s-slot sensitivity has a false-safe prediction (82.692m predicted versus−0.949m actual common-window margin); report it explicitly, together with5guard fallback selections on the short set.

Recommendation: retain this as extension evidence and a failure-aware discussion, not a necessary condition for the current CCDC submission. No claim about acceptance follows from this round. R3 draft.md is unchanged.
