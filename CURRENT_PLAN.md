# Current Plan — R6 research reset

R6 supersedes V0-R5 stage restrictions: low-level weights/architecture/checkpoints (including 18D), normalization, causal memory and goal application timing are research variables. Preserve original assets/results, upstream read-only, causal deployment information, physical constraints and original evaluation. No device access inferred from idle GPU. Current authority: docs/prompt/SailBoatRL_R6_ARIS_Research_Reset.md and CURRENT_PLAN.md.

Objective: evidence-backed continuous sailboat navigation for CCDC; do not require a new network/theorem.
Budget: 24 h total, 4 CPU experiment workers; at most one explicitly assigned GPU and 12 GPU h. GPU allocation confirmation pending; CPU work proceeds.
Run: runs/r6_reset_20261004T115808Z/plan.json

Routes to compare: (A) existing 14D/18D asset and causal interface suitability; (B) continuous-waypoint low-level adaptation if evidence and throughput justify it; (C) a simple causal reference/control alternative if better supported.
Hypotheses: memory/history and target-coordinate distribution mismatch may contribute; low-level weights alone are not an established root cause.
Next: freeze selected18D boundary40/Relay120, evaluate54 new instances with7 paired methods (378 episodes), analyze adverse outcomes and matched input ablations, figures/reports and one evidence review. No further tuning on confirmation.

Verified development:293 full episodes audited;72 seen-scene primary completion71/72 (routine36/36,risk35/36), originalRelay120/16067/72 each, R5recovery70/72. Main has one new risk buffer breach; no universal safety claim. Selection receipt: runs/r6_reset_20261004T115808Z/selection.md. No new training or GPU usage.
