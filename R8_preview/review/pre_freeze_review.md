# R8 pre-freeze review

Date: 2026-10-05. Same-family / provisional, no score.
Scope: delayed-reference queue, existing branch witnesses, activated target-turn/reference-delay evidence, and the repaired best-effort fallback. Read-only source and artifact inspection; no rollout, training, experiment, process control or source edit by this reviewer.

## Decision

No P1 issue was found in this bounded review that requires blocking the proposed fixed fresh comparison. This is not a result-to-claim approval for unseen performance. Keep reactive, sampled15 and hold60 definitions and the new-scene generator fixed before inspecting their outcomes. The current evidence supports proceeding to that comparison, not a general safety claim.

Current r8_model.py / r8_planner.py / run_r8.py hashes exactly match both branches/provenance.json and active_sensitivity/provenance.json:
- model: 0fa89f4e3ac9fbee514c709baf59936e0bda3d3867105d18c2005231d41cb175
- planner: ec6313eb3d5329198b0af63867705385b9334a272a13dd174a40235ef4a4dbc8
- runner: 1f63512f268892d9b76bbbe5bcf109d7b3301dd52665d02f13a2013d07626424

## Queue and rolling timing

The source implements the same one-item FIFO semantics in real execution and prediction:

1. The action already computed under the current reference is executed.
2. A different proposed reference is enqueued only if the queue is empty.
3. A due reference is then removed and applied at the end-of-step boundary.
4. Policy history is reencoded under the actually applied frame before the next action.

The real due time is t+1+goal_delay (run_r8.py:67-75). The model converts existing absolute due times to relative times using due-len(commands), and schedules new items at k+1+delay (r8_model.py:68,86-89). Because len(commands)=t in this 1 Hz protocol, these boundaries agree. Both reject replacement while a prior item is pending, and both enqueue before removing a due item; a current proposal can therefore be suppressed on the boundary where the old item applies. The predictor preserves that behavior rather than silently assuming latest-command replacement.

The planner passes a snapshot of the current pending queue and the same configured delay into every candidate (r8_planner.py:55). Copies of queue containers are internal to the model. No future real reference, wind or target turn schedule enters them. Initial target installation remains immediate in both methods.

The hold/reassessment clock begins at selection time. With a three-second delivery, a nominal 15 s decision hold does not mean 15 s of the new reference's physical influence. Describe selection, installation and reassessment times separately. The model's ordinary continuation after hold is still a conditional tail; the online planner can select another maneuver at the next reassessment.

Existing delayed logs exercise a nonempty pending queue: at t=115 a reference selected at 113 remains pending until 116. The selected nominal forecast's 15 s position error is 0.001206 m in that witness. This is compatible with the queue implementation; it is not a general delay error bound.

Best-effort fallback now first ranks valid, numerically successful forecasts; only when none exist does it explicitly choose continue or nominal (r8_planner.py:66-68). This fixes the incomplete-prefix ranking concern from the prior review. all_predicted_infeasible remains recorded, so the fallback is not labeled safe. Direct counting of the six development2 sampled traces found zero uses, consistent with the claim that this later correction does not explain their gains.

## Branch evidence independently checked

Source: branch_validation.json plus its four branch trace.json files; reference: development2/confirm_mixed_3__reactive/trace.json. The reviewer recalculated position errors and synchronized relative-segment clearance directly from existing arrays, without executing the simulator.

All four branches have equal full trajectory records through t=115, and also equal records for the unavoidable old-action transition to t=116. The nominal branch's entire 176 stored observations, from t=0 through 175, match the reference trace exactly. These are regenerated-prefix branches, not copied-coordinate restarts. The artifacts do not separately contain a new hidden-state snapshot audit, so the precise claim is deterministic replay and observed full-record equality.

| Candidate from t=115 | 15 s position error | 60 s position error | Predicted 60 s dynamic margin | Recomputed actual margin |
|---|---:|---:|---:|---:|
| nominal | 0.210277 m | 1.525035 m | 11.481793 m | 12.438334 m |
| continue | 0.164685 m | 10.349735 m | 110.103744 m | 110.138976 m |
| turn-90 | 0.031033 m | 0.861568 m | 84.135409 m | 84.382662 m |
| turn90, selected | 0.024544 m | 0.449027 m | 52.939700 m | 52.956139 m |

Margins are distance minus the common 85 m evaluation radius. In this witness the minimum is dynamic, not static. The turn90 reference is selected at 115 and installed at 116; branch ordinary rejoin is selected at 130 and installed at 131. These events match the predicted old-action/hold/rejoin protocol.

The nominal forecast's margin is positive but below the 30 m planning guard. Therefore the trigger is predicted loss of planning reserve, not a predicted physical collision within this 60 s horizon. The eventual reactive buffer incursion occurs later in the full task. Also retain the 10.35 m continuation-tail error; the selected branch's small error is not representative evidence for every candidate, state or wind profile. Four branches from one prefix are one mechanism witness, not four independent scenarios.

## Activated sensitivity is actually activated

| Perturbation | Verified active sequence | Sampled task | Reactive counterpart |
|---|---|---|---|
| Target changes ground velocity by 15 degrees at t=122 | enter 115, reference applies 116; changed velocity is observed at 122 while hold lasts until 130; release selected 130 and applies 131 | safe arrival at 433 s; minimum dynamic margin +48.429682 m | buffer incursion -0.404873 m, then NoRouteError |
| Shared total reference delivery of 3 s | goal_delay=2 for both methods; all recorded applications satisfy applied-selected=3. Sampled enters at 145, applies at 148; rechecks at 160 and 175; releases at 190 | safe arrival at 407 s; minimum dynamic margin +48.937835 m | buffer incursion -0.466195 m, then NoRouteError |

The delayed case is not an activation at t=115: it remains nominal then and activates at t=145. During target-turn hold, the low-level controller sees updated observed target positions, but the high-level selector does not immediately interrupt the hold; its next risk reassessment is t=130. The successful test therefore supports this particular bounded-hold response, not continuous high-level emergency reevaluation.

These are two perturbations of the same known development scene. They support activated examples, not a distribution-wide robustness estimate. Entity collisions were not observed in these reactive rows; call the improvement buffer-incursion avoidance rather than an observed reduction in entity collisions. Three-second delivery is modeled queue latency, not measured CPU-overrun safety. Existing planning peaks exceed the planning period; hard-real-time operation remains unverified.

## Scope reminders for freeze and reporting

- The original confirmation85 outcomes remain R7 evidence. R8's two known-case rescues are new development evidence and do not retroactively change R7 or establish unseen generalization.
- Observation delay is still not modeled: future_obs/clearance do not age a stale position to current time. The verified perturbation is reference delivery, not sensor delay.
- hold60 changes decision cadence and commitment duration together. It tests the coarser control protocol; it does not isolate one causal component.
- The generic branch hook calls the reactive planner during forced hold and has a post-application override. In the audited delay-zero, unoccupied-endpoint branch witness its trace agrees with the intended behavior. Do not reuse that helper as a validated arbitrary pending-queue/endpoint branch tool. Ordinary fresh jobs must omit branch_at/branch_hold/branch_target.
- Report development, interrupted implementation batches and fresh evaluation separately. Keep the initial fixed-reference predictor_witness errors separate from this matched-feedback branch evidence.

Memory was reconciled in REVIEWER_MEMORY.md. No scientific artifact, source, configuration or result was modified.
