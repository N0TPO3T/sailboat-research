# Current Plan — R8

R8: executable underway dynamic avoidance with candidate-conditioned prediction and rolling feedback. R6/R7 are baselines, not frozen constraints. High/low-level, causal memory, interface and training may change; no future truth online, no unassigned GPU, no automatic push.

Run: runs/r8_closedloop_20261005T062543Z

Hypotheses: causal physics/response prediction can distinguish candidate waypoint executions; rolling comparison can reduce underway incursions without long false commitment; common temporary endpoint handling prevents interface failure from confounding collision benefit.
Next: read GVO primary formulas; validate an independent predictor from observed state/history; test real R7 incursions, endpoint successes,740s adverse and normal controls; develop, freeze, fresh compare and activated sensitivity; deliver method/results/real plots.
Budget: shared24h,4 single-thread CPU workers, GPU only assigned permission. No training prohibition.

Verified development: common AvailabilityRelay4/6 vs sampled6/6; recovered confirmation85 mixed3/7 actual incursions, no740s penalty case. Four same-state regenerated-prefix branches at115s all match prefix; ordinary continuation matches full175s trace. Active target15deg turn at122 within115–130 hold and3s delivery stress both sampled safe, reactive intrudes. hold60 ablation underway. Sources/snapshots retained including interrupted implementation-defect batch. No final claims before fresh evaluation.
