# Frozen manuscript scope — R10, 2026-10-05

Working title: **Candidate-Conditioned Reference Prediction for Local Sailboat Avoidance: A Closed-Loop Simulation Study**.

Center: selecting position references for an inherited learned sail/rudder controller under unknown wind, a known static chart, and causal moving-vessel observations. The paper studies an ideal-compute simulation protocol. It does not claim a real-time deployed collision-avoidance system.

## Contributions that may be written

1. An explicit adaptation of the control-induced-trajectory idea in Generalized Velocity Obstacles (Wilkie, van den Berg and Manocha, IROS 2009) to position-reference protocols: policy-history restoration, independent physical rollout, simultaneous clearance, and feedback after a finite commitment. This is an application/interface contribution, not a new GVO theorem, network, or original SAC controller.
2. Paired closed-loop evidence identifying when reference search helps relative to a defined nominal-triggered hold rule, together with adverse intervention cost, a competitive 60-second alternative, and limits under delayed command delivery. Do not claim uniformly better safety or efficiency than reactive relay: the frozen R10 new set provides no such improvement.

## Method section

1. Public observations, information boundary, inherited controller and continuous navigation contract.
2. Independent candidate rollout: causal wind fitting, constant-velocity vessel model, actuator and policy-history initialization.
3. Nominal-first evaluation, reference candidates, actual guard/cost/fallback, finite hold and feedback restoration.
4. Simulation timing: computation pauses physical time; existing one-step command delivery is retained. R9 timing-aware experiments are a separate transfer boundary.

Inherited R6 boundary input and shared endpoint-availability recovery belong to system setup. They are not additional independently established contributions. Keep R3 draft unchanged as historical prose material; rewrite its claims only in the subsequent author phase.

## Main evidence and figures

- Separate historical R8 30 short / 4 long instances, R10 13 seen mechanism cases, and R10 12 frozen new instances. No pooled success fraction or version-improvement curve.
- Main table: safe completion, buffer intrusion, conditional flight-time difference with denominator and worst tail, intervention count, measured CPU, all predefined new outcomes.
- Main figure: same-state149s nominal/search/hold distinction and actual simultaneous clearance; committed-prefix prediction error only.
- Actual1/3/5km paths: both vessels, synchronized time markers, provenance marked historical R8.
- Adverse evidence: historical+267s and new+271s safe-versus-safe detours. R9 false-safe margin82.692m versus−0.949m belongs in limitations, not a merged performance table.
- Static matched-input controls: compact supplemental negative evidence against boundary-formula necessity.

R10 results: sampled15 / hold60 / reactive12/12, nominal-triggered hold11/12. Sampled15 versus reactive mean+27.083s and max+271s over12 common-safe cases. Only2/12 sampled15 instances activated intervention. Sampled15 versus hold60 mean−9.25s but measured CPU777.05s versus328.77s. Neither period is established as optimal; retain the pre-frozen15s representative and competitive60s configuration transparently.

## Work remaining before human submission

Next stage is evidence consolidation and manuscript writing, not automatic method research. Build concise tables from the existing raw index, align claims and units throughout the old draft, and retain negative cases. No new experiment batch is required by this decision. Human authors must verify checkpoint/code attribution and publication permission, authorship, current official page/anonymity/AI-disclosure rules, and submission readiness. These are unresolved author tasks, not assumed permissions or an acceptance prediction.

No automatic reopening of training, arbitrary-delay robustness, full COLREGs, multi-vessel traffic, perception or real-boat testing. A real-time claim would require a new research authorization and evidence. A genuinely simpler rule that reproduces the rescues and reduces cost would justify revisiting the method.

Canonical scientific decision: `docs/R10_METHOD_DECISION.md`; all disputes and raw evidence: `docs/R10_RESEARCH_REPORT.md`. This is a coordinator decision after actual separated author/reviewer work; it is not a CCDC committee verdict.
