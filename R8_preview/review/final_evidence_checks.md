# R8 final evidence checks — completed development and frozen evaluation

Scientific freeze: 29124b8ec3cef9a457e33500b05186874c031e1d.
Date: 2026-10-05. Same-family / provisional; no score or certification.
This is a bounded offline review of existing JSON/source. No simulation, training, GPU task or method edit was performed. The development-stage sections below record the earlier check, before fresh results completed. The final extension independently checks completed confirmation90, long12 and static12; see the final section for current evidence. No incomplete-batch success rate was calculated by this reviewer.

## Development-stage main finding

The completed evidence supports two known underway buffer-incursion rescues in mixed_3/mixed_7, plus a real safety-margin/efficiency tradeoff in mixed_6. It does not establish a reduction in entity collisions or that inverse wind estimation, GVO structure, or 15 s rolling alone caused the gains. Existing prediction_execution fields are arithmetically reproducible, but several field names are broader than what they measure.

No additional P1 method defect was identified by these checks. The following are reporting and inference boundaries, not permission to change the frozen method or retune against pending results.

## mixed_6: a CPA-induced failure reference, not a reactive rescue

Read these complete source traces:
- R7 confirmation85/confirm_mixed_6__current, __commit and __no_commit.
- R8 development2/confirm_mixed_6__reactive and __sampled.

The R7 current and R8 reactive trajectory arrays are exactly equal. The R7 commit/no_commit arrays are also equal throughout their common recorded prefix. Both CPA variants enter at t=45 using the same waypoint, but differ in subsequent exit behavior. Consequently, the shared incursion cannot be attributed solely to the later choice of release versus continued commitment.

| Method/source | Task outcome | Time | Minimum dynamic margin | Minimum entity margin |
|---|---|---:|---:|---:|
| R7 current = R8 reactive | safe arrival | 293 s | +20.052412 m | +80.052412 m |
| R7 CPA commit | arrives after buffer violation | 393 s | -19.541430 m | +40.458570 m |
| R7 CPA no_commit | NoRouteError after buffer violation | 195 s | -19.541430 m | +40.458570 m |
| R8 sampled | safe arrival | 336 s | +33.310122 m | +93.310122 m |

R8 sampled first intervenes at t=161, initially by retaining the current reference, and later uses turn-90 candidates. Against the already safe reactive baseline it adds 13.257711 m to minimum dynamic margin, at a cost of 43 s and 118.229305 m. It is not an additional safe-completion gain. There is no recorded entity collision in these mixed_6 traces. The two R7 CPA configurations differ from R8 in trigger, horizon, guard and control program; this case is not a controlled isolation of CPA mathematics versus a single new component.

The proper use of mixed_6 is to show that the old CPA supervisor can damage an otherwise successful case, and that the R8 full policy makes a different margin/cost tradeoff. Do not write “R8 rescued three reactive collision failures” by adding this case to mixed_3 and mixed_7.

## What prediction_execution actually measures

Source definition: scripts/analyze_r8.py:13-17. Each record uses only the selected candidate, not every evaluated alternative.

| Field | Actual meaning / required qualification |
|---|---|
| error_15 | Euclidean own-ship x/y error at end=min(15,available predicted steps,available actual steps). It is not always a 15 s error. |
| max_prefix_error | Maximum own-ship x/y error over that same shortened prefix, including its initial point. It is not a full-state, wind or target-trajectory error. |
| horizon_error | Own-ship x/y error at the last common predicted/recorded sample. It can cover fewer than 60 s. For sampled15, the actual policy may select further maneuvers after 15 s while the forecast assumes nominal rejoin. The field then includes a different continuation policy. |
| prefix_predicted_min | Minimum of predicted combined static and dynamic margins over the prefix. |
| prefix_actual_dynamic_min | Minimum recorded dynamic margin only. This does not include static margin, so it is not the exact same risk aggregate as the preceding field. |
| forecast_valid | The rollout navigation-valid flag. It is not synonymous with feasible or numerically successful: integration_failed and the selected candidate's feasible flag must be checked in the raw prediction. |
| prefix_steps | The actual prefix length used; it must accompany error_15, especially near task completion. |
| selected | Does not by itself distinguish ordinary navigation from exit/rejoin: both use nominal. Join to events at the same decision time. |

The analyzer always uses 15 for prefix length, including hold60. Thus its prefix fields are not “complete hold-window errors” for that ablation. A release outside the prediction range can also occur without a prediction row; there were no such omitted releases among these 12 audited episodes, but the schema permits them.

For phase grouping, this review uses exit when the same-time event is release; otherwise avoidance when selected is not nominal; otherwise ordinary. Continue counts as avoidance/commitment even if it keeps the same coordinates, because it suspends ordinary target replacement.

## Whole-source-episode check

The review loaded every selected forecast from the completed sources: 142 development2 records across six source episodes, 56 sensitivity records across two derived episodes, and 27 hold60 records across four paired episodes. All 225 records matched direct recalculation of prefix_steps, error_15, max_prefix_error, horizon_error, prefix_predicted_min and prefix_actual_dynamic_min to numerical tolerance. No running fresh-evaluation output was used.

Nine records have a prefix shorter than 15 s:
- development2: mixed_3 t430/1 s; mixed_6 t326/10 s; mixed_7 t529/11 s; nonconflict_0 t235/9 s; overtaking_1 t376/6 s; overtaking_2 t442/4 s.
- active_sensitivity: delay t400/7 s; turn t430/3 s.
- hold_ablation_development: mixed_3 t430/2 s.

The table preserves complete source-episode grouping. O/A/E means ordinary/avoidance/exit. Error values are maxima of max_prefix_error within each category, in metres; prefixes can be shorter as listed above. “—” means no such decision, not zero error.

| Batch and episode | O/A/E decision counts | Maximum prefix error O/A/E |
|---|---:|---:|
| development2 mixed_3 sampled | 27 / 1 / 1 | 5.226 / 0.052 / 0.123 |
| development2 mixed_6 sampled | 15 / 3 / 2 | 6.179 / 4.556 / 9.970 |
| development2 mixed_7 sampled | 20 / 6 / 6 | 0.384 / 0.142 / 1.023 |
| development2 nonconflict_0 sampled | 16 / 0 / 0 | 3.005 / — / — |
| development2 overtaking_1 sampled | 19 / 0 / 0 | 8.452 / — / — |
| development2 overtaking_2 sampled | 24 / 1 / 1 | 4.912 / 1.225 / 0.860 |
| active_sensitivity delay sampled | 23 / 3 / 1 | 5.226 / 0.236 / 0.137 |
| active_sensitivity turn sampled | 27 / 1 / 1 | 5.226 / 0.052 / 0.287 |
| hold development mixed_3 hold60 | 6 / 1 / 1 | 4.869 / 0.069 / 0.013 |
| hold development mixed_7 hold60 | 4 / 2 / 1 | 0.108 / 0.139 / 0.057 |
| hold development overtaking_1 hold60 | 5 / 0 / 0 | 8.338 / — / — |
| hold development overtaking_2 hold60 | 5 / 1 / 1 | 4.665 / 0.378 / 0.192 |

Decision windows are correlated and often overlap. Sensitivity and hold-ablation episodes reuse original scenarios. Neither 225 nor 12 is a count of independent natural-traffic samples. Do not use a binomial confidence bound over these windows.

A useful counterexample to interpreting horizon_error as model error is mixed_6 at t=176: the selected exit forecast assumes nominal continuation, but the online policy re-enters avoidance at 191, reevaluates at 206 and releases at 221. The reported horizon_error is 181.264 m. Its 15 s error is 9.970 m before that next maneuver takes effect, so a genuine near-term forecast discrepancy remains; this review does not assign its root cause to wind or a particular model component. The later 181 m discrepancy is not a clean same-policy model diagnostic. Use the matched branch evidence in pre_freeze_review.md for a cleaner 60 s comparison.

## Predicted-safe versus actual-incursion check

Two explicit interpretations were checked against complete source traces:

1. Valid, numerically successful selected forecast with positive predicted prefix clearance, followed by actual static or dynamic clearance <=0 within the covered prefix.
2. Candidate marked feasible by the full-horizon rule, followed by an actual static or dynamic incursion anywhere in the overlapping recorded forecast horizon.

There were no such cases in these audited completed batches. All 225 selected candidates were marked feasible and all 12 corresponding complete method episodes were safe. This is a descriptive absence within known development data; it is not a validated false-safe rate. It also provides no counterfactual outcome for the many unselected candidates. The separate four-branch witness supplies only one source-state comparison.

To avoid comparing unlike metrics, the reviewer combined actual static and dynamic margins for this check, rather than relying only on prefix_actual_dynamic_min. Across the audited prefixes, the greatest overstatement of combined minimum clearance was 6.313448 m, in development2 overtaking_1. The largest observed own-position prefix discrepancy was 9.969861 m. These are empirical extrema of this data, not calibrated uncertainty bounds justifying a universal 30 m guard.

The activated target-turn example's small own-position error does not imply accurate target prediction: error_15 measures only own position, while the target turns after the forecast was issued. Report target-model assumptions and measured safety clearance separately.

## Queue and timestamp evidence

The current frozen queue implementation was already source-checked in pre_freeze_review.md. This follow-up checked every installed-reference record in the 12 completed method episodes:
- applied_at-selected_at equals 1 s in ordinary cases and 3 s in the shared-delay case;
- no recorded later selection is enqueued before the prior reference's application, consistent with the one-item pending queue;
- the delayed t=115 forecast correctly has an existing command selected at 113 due at 116; its 15 s position error is 0.001206 m.

The changes list is the authoritative reference-installation record. The trajectory row at an installation boundary is appended before applying the new goal, so its target/raw goal fields can still show the old reference. Do not infer an extra one-second actuation error from those fields. Also do not confuse selection/hold start with actual installation.

prediction_execution does not preserve the queue itself; its source path leads back to the trace and installed-reference records. Source inspection, source-bound receipts and those records support the timing conclusion. They do not establish an arbitrary sensor-delay protocol, which remains unsupported, or real-time tolerance to measured CPU overruns.

## Claims the report must avoid

- “mixed_6 is a reactive failure rescued by R8” or “three dynamic collision failures were rescued.” The matched reactive mixed_6 was already safe.
- “CPA itself is invalid” or “the inferred wind is the proven cause of improvement.” Multiple components and control protocols differ; no matched inverse-wind necessity ablation was checked.
- “All prediction errors are below 10 m for 60 s.” The table concerns at most 15 s prefixes; continuation-policy changes contaminate many longer errors, and the matched continue branch already has a 10.35 m 60 s error.
- “No false-safe predictions in 225 independent tests” or “30 m is a validated error bound.” These are correlated known-case records with no failing selected-method source episodes.
- “The 3 s stress test proves real-time deployment.” It models reference delivery, while computation peaks can exceed decision intervals.
- “hold60 isolates the value of replanning.” It changes both planning cadence and commitment duration.

Defensible wording: candidate-conditioned forecasts distinguish several actually executable branches at the inspected state; the full online policy removes two known buffer-incursion failures, retains a known no-conflict completion, and trades extra travel for margin in another already safe case. Generalization and net safety/efficiency value remain questions for the fixed completed fresh evaluation.

No pending new-evaluation success rate was computed. REVIEWER_MEMORY.md was updated with these boundaries.

## Method-note wording spot check

Read docs/R8_METHOD_NOTE.md after the completed-source checks. The t=115 decision table, guard interpretation, known branch limits, mixed_6 cost, and non-real-time limitation agree with the inspected evidence. No change to frozen behavior is requested.

Two precision corrections were sent to the owner:
- Line42 should state max_nfev=35 per least-squares starting point, with seven starting points at the first fit. The installed SciPy least_squares documentation separates this limit from additional residual calls for numerical Jacobian approximation, so “at most35 function calls per estimate” is not accurate.
- Line52 should define the evaluated trajectory as up to60 s or predicted arrival within the original goal radius. rollout stops at predicted task arrival while retaining valid=True; “complete prediction” must include that legitimate terminal condition rather than imply every feasible candidate always has60 recorded future steps.

The requested distinction remains explicit: no selected false-safe incursion appeared in the completed audited data; this does not prove that such errors cannot occur. The final fixed-evaluation summary was still pending at this spot check.

## Final extension: completed frozen confirmation and continuity checks

This section supersedes the earlier pending-evaluation status, while preserving which evidence was available at each stage. confirmation/completion.json records 90 complete episodes; long and static_regression each record 12. Timing-control completion was subsequently observed as four episodes, but its efficacy/prediction records were not included in this extension. No extra experiment or frozen-method edit was requested or performed.

Identity and arithmetic checks:
- At the initial identity check HEAD was 29124b8ec3cef9a457e33500b05186874c031e1d. Delivery subsequently advanced to f75130d729c4dd13f2946068a083f2ad63e3606f; git diff against the scientific freeze is still empty for r8_model.py, r8_planner.py, run_r8.py and r8_methods.json. All five confirmation source-snapshot SHA256 values match current source and provenance.
- All 30 confirmation scenes have exactly reactive/sample15/hold60, identical scene dictionaries and initial raw state, and identical external target positions throughout each common recorded time range.
- Independently reconstructed segment clearances from recorded own/target coordinates, original static circles and 85 m dynamic radius reproduce all 90 success/arrival outcomes. Maximum raw-to-row differences are 2.85e-14 m dynamic, 1.88e-5 m static and 7.25e-6 m path length, consistent with the runner's float32 arithmetic. No outcome discrepancy occurred. The same calculation agrees for all 12 long and 12 static episodes.
- Confirmation CPU sums also reproduce the report: reactive403.881863 s, sampled2640.783111 s, hold601047.181906 s. These are process CPU sums, not parallel elapsed time.

### Main fresh outcomes and the meaning of the two gains

| Method | Safe arrivals / scenes | Dynamic buffer incursions | Static incursions | Entity collisions |
|---|---:|---:|---:|---:|
| reactive | 28/30 | 2 | 0 | 0 |
| sampled15 | 30/30 | 0 | 0 | 0 |
| hold60 | 30/30 | 0 | 0 | 0 |

Both gains are r8new_mixed_pressure_2 and r8new_mixed_pressure_4, with no paired losses. The other 24 non-pressure scenes are safe for all three methods. The gains are underway buffer-incursion avoidance, not endpoint recovery:

| Scene | Reactive first incursion / stop | Reactive dynamic / entity margin | Distance to original goal at stop | sampled arrival / minimum dynamic margin | hold60 arrival / minimum dynamic margin |
|---|---:|---:|---:|---:|---:|
| mixed_pressure_2 | 219 s | -1.225020 / +58.774980 m | 385.721 m | 444 s / +43.589225 m | 403 s / +62.628339 m |
| mixed_pressure_4 | 300 s | -0.872436 / +59.127564 m | 345.734 m | 477 s / +38.454925 m | 564 s / +34.697896 m |

All six corresponding traces have empty goal_events. Reactive first invades the buffer and then stops with NoRouteError; the recorded entity margin remains positive. Do not infer a later physical collision after the stopped trace. sampled first enters at149 s in pressure_2 and228 s in pressure_4, before the matched baseline incursions. The result supports the complete policy's benefit on these paired simulated cases, without isolating inverse wind estimation, candidate search, guard size, or feedback cadence as the unique cause.

The conditional time comparison is correctly restricted to 28 common-safe pairs. sampled sums +428 s, mean +15.285714 s, median0, maximum +267 s. hold60 sums +591 s, mean +21.107143 s, median0, maximum +265 s. A failed short baseline is not a fast completion. All 22 sampled traces with no intervention are exactly equal to reactive; this confirms that their success cannot be credited to active avoidance. hold60 has21 exactly equal full trajectories.

### Worst travel cost: endpoint_5

Reactive completes at317 s with minimum dynamic margin12.521997 m and path1220.249538 m. sampled completes at584 s with margin44.394162 m and path2229.093505 m: +267 s and +1008.843967 m. hold60 completes at582 s, margin31.038449 m, path2245.207877 m.

sampled enters at252, reevaluates at267 and releases at282. Its common endpoint handler then marks the goal unavailable at322 and available at510. Reactive has already finished and has no such endpoint event. hold60 enters at297, releases at357, and also waits through endpoint availability at510. The delay is a whole-policy interaction between conservative intervention, changed arrival timing and endpoint handling; +267 s is not a pure15 s hold penalty. The baseline was safe, so this is a genuine safety-margin/efficiency cost, not a necessary rescue proved by this data.

### Selected prediction windows: independent recomputation

Every confirmation selected forecast was joined to its complete source trace and same-time event. All922 protocol_prediction_diagnostics entries match direct recomputation of steps, own-position error, predicted minimum and actual dynamic minimum to1e-8. This consists of728 sampled and194 hold60 windows across60 source episodes. Windows are correlated, and are not922 independent traffic trials.

| Method / phase | Windows | Maximum own-position error over recorded protocol prefix |
|---|---:|---:|
| sampled / ordinary | 684 | 30.505975 m |
| sampled / enter | 17 | 1.038940 m |
| sampled / reevaluate | 10 | 0.228066 m |
| sampled / release | 17 | 0.626316 m |
| hold60 / ordinary | 171 | 134.947078 m |
| hold60 / enter | 10 | 8.853987 m |
| hold60 / reevaluate | 3 | 1.670494 m |
| hold60 / release | 10 | 17.077747 m |

The new analyzer correctly uses each configured15/60 s period, but H is still the minimum of that period, available prediction length and remaining actual steps. There are53 shorter windows:24 sampled and29 hold60. In three hold60 ordinary windows the prediction terminates at predicted arrival before the actual protocol prefix ends: crossing_3 t271 covers44 of45 steps, crossing_2 t310 covers28 of55, and crossing_5 t310 covers59 of60. Their complete real episodes remain safe. Nevertheless, these diagnostic fields do not claim coverage of the unpredicted tail, particularly the27 missing seconds in crossing_2. Report steps and call them the common recorded prefixes, not universally complete hold windows.

Both ordinary maxima occur in endpoint_1 at341 s. sampled's15 s predicted/actual minimum is169.560551/178.971427 m; hold60's60 s minimum is138.239533/146.171208 m. All three complete trajectories are equal, and both sampled methods remain nominal throughout. Thus this large error cannot be dismissed as later online avoidance changing the continuation policy. It is a real nominal execution-forecast discrepancy under endpoint feedback, with no identified single root cause in this bounded check. The same raw state does not imply the same fitted wind: sampled estimates [10.518909,3.043053], hold60 [10.911482,-1.272711]. The estimator warm-starts from its previous fitted wind and is called at different cadences. The two error maxima therefore do not isolate horizon length alone.

Combining actual static and dynamic margins, no valid/numerically successful selected forecast with positive predicted prefix clearance was followed by actual clearance <=0 in the covered prefix. No feasible selected full-horizon forecast was followed by an incursion in the overlapping recorded horizon either. This is an observed absence, not a proof of nonexistence. All60 source episodes were safe. The unexecuted alternative candidates have no counterfactual real outcomes. The maximum observed overstatement of prefix minimum clearance is19.507559 m for sampled and28.282382 m for hold60; neither those sample extrema nor the own-position errors establish a calibrated30 m uncertainty bound.

The analyzer's forecast_safe_actual_intrusion flag itself still compares predicted combined clearance with dynamic-only actual clearance and does not check validity/integration/feasibility. The review separately checked those flags and actual static margin. Its name must not be read as a safety certificate.

### Actual all-infeasible fallback, and timing

921 of922 confirmation selections are feasible. The remaining one is hold60 mixed_pressure_3 at310 s: all six candidates are valid, numerically successful61-point forecasts, but none attains30 m. The selected turn-90 has the greatest predicted minimum,28.169288 m, and the event correctly records all_predicted_infeasible=True. Actual60 s minimum is28.197318 m. This is successful best effort below the planning reserve, not a guard-satisfying solution. The development observation of zero fallbacks must not be extended to the fresh batch.

Two additional long-batch fallbacks were independently checked: hold60 5 km crossing at799, turn-90 predicted28.263700 m versus actual60 s28.552314 m; sampled 3 km crossing at551, nominal predicted60 s28.616714 m versus actual15 s84.414756 m. Both are complete valid forecasts below the30 m guard. The two actual numbers cover different execution periods and must retain their time labels. Across all140 long selected common prefixes, no positive-clearance valid forecast was followed by a real static/dynamic incursion; this remains descriptive, correlated evidence.

All confirmation installed-reference records obey applied_at-selected_at=1 s, and no selection overlaps the preceding pending reference. The original logging-order qualification still applies: changes is the reference-installation authority, not the pre-installation target in the same boundary trajectory row.

Completed long outcomes reproduce3/4 reactive versus4/4 sampled and4/4 hold60. The single reactive failure is3 km crossing at512 s, dynamic margin-1.128814 m and entity margin+58.871186 m. Static regression reproduces6/6 for each method. These are four continuous long scenarios and six known static scenarios; do not enlarge their population claim.

The largest completed long single-planning call is43.459499742 s for sampled 5 km crossing; hold60 reaches28.763779906 s. Confirmation peaks are28.961561064 s and17.209917445 s. Use43.4595 s, not the earlier development28 s figure, when describing the observed timing limit. Physics is paused during computation, so the frozen simulation does not demonstrate delivery within15 s. The source-bound3 s reference-delivery experiment does not remove this limitation.

### Reporting conclusion

No new blocking P1 implementation issue was found. The finite complete evaluation supports fewer underway buffered-clearance violations and restored task completion in this predefined synthetic pressure subset, plus the long-case observation. It does not establish fewer entity collisions, broad natural-traffic generalization,30 m certified robustness, real-time execution, or15 s superiority over60 s. The ordinary crossing/overtaking/nonconflict control population is18 scenes, all inactive; do not treat ordinary prediction windows as additional scenes. The report should retain the tail cost, fallback flags, shortened diagnostic windows, and the non-independent nature of the branch and window evidence.

The two method-note precision corrections are now present: max_nfev35 per starting point with first-fit7 starts, and termination at60 s or predicted arrival within the original10 m goal radius. The report's main confirmation counts, conditional time figures,22 identical sampled trajectories, CPU sums and43.4595 s timing boundary match the inspected evidence. Its temporary incomplete timing-control row was flagged to the owner for refresh after completion; no interim rate was adopted here.

Final owner corrections were spot-checked before closing: the report now records three fallback decisions, estimator-history differences and53 truncated confirmation windows. The analysis field error_15 has been renamed error_at_prefix_end while retaining prefix_steps. The earlier field-definition table records the pre-rename schema; its interpretation still applies. Delivery HEAD is f75130d729c4dd13f2946068a083f2ad63e3606f, with the four reviewed scientific-method/config files unchanged from29124b8. This bounded review is closed; no additional review or experiment is requested.
