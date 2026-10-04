# Current Plan — R6 research reset

R6 supersedes V0-R5 stage restrictions: low-level weights/architecture/checkpoints (including 18D), normalization, causal memory and goal application timing are research variables. Preserve original assets/results, upstream read-only, causal deployment information, physical constraints and original evaluation. No device access inferred from idle GPU. Current authority: docs/prompt/SailBoatRL_R6_ARIS_Research_Reset.md and CURRENT_PLAN.md.

Objective: evidence-backed continuous sailboat navigation for CCDC; do not require a new network/theorem.
Budget: 24 h total, 4 CPU experiment workers; at most one explicitly assigned GPU and 12 GPU h. GPU allocation confirmation pending; CPU work proceeds.
Run: runs/r6_reset_20261004T115808Z/plan.json

Routes to compare: (A) existing 14D/18D asset and causal interface suitability; (B) continuous-waypoint low-level adaptation if evidence and throughput justify it; (C) a simple causal reference/control alternative if better supported.
Hypotheses: memory/history and target-coordinate distribution mismatch may contribute; low-level weights alone are not an established root cause.
Next: verify matching assets/training semantics; CPU discriminative paired tests; select main route and cheap alternative; develop, ablate, freeze, confirm new instances; deliver R6 method/report/real figures/source/weights if trained.
Historical scenes through R5 are development-only. Preserve R3 draft and prior results. Review checks evidence, never substitutes for outcome. No push.

Verified development: first11 seen scenes ×6 variants complete (66 full episodes), baseline11 trajectories exactly replayR5; own physical audit passed. 18D10/11 vs original6/11 and training-window7/11 is a purposive screen, not generalized performance. Next44 compare18D zero/boundary-matched obstacle inputs and a small Relay120 cross. No model weight updates yet, no GPU usage.
