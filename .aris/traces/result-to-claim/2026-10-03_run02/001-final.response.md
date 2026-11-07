# R2 RESULT-TO-CLAIM evaluation — fresh review

- claim_supported: no
- confidence: high
- review_independence: same-family
- acceptance_status: provisional
- integrity_status: unavailable
- routing_action: Close this bounded R2 study as a negative main result, preserve the frozen methods and evidence, and finish packaging. Do not automatically start experiments, tune the method, replace the frozen main method, or upgrade the result into a positive safety/efficiency claim.

The evaluated intended claim is: a simpler high-level waypoint method preserves R1 safety and improves 3/5 km efficiency under the fixed 14D SAC-LSTM @7200 controller, unknown wind and a known static map. The conjunction is not supported. A smaller candidate implementation is real, but safety equivalence is unestablished and the new-instance efficiency results run against the intended benefit. This is not a finding that every simpler method must fail, nor that Forward is universally worse on all scenes.

## What the results support

1. The frozen comparison contains 72 new balanced synthetic scenes and four freshly executed methods, for 288 complete episodes. I independently checked unique scene/method coverage, completion and absence of cached final rows. Method freeze precedes final scene generation in the saved protocol. All scientific-source hashes in final_protocol.json still matched the current source and assets when reviewed.

2. All four methods recorded 63/72 safe arrivals. The per-distance counts are R1 22/21/20, Forward 21/22/20, Relay 22/22/19, and RouteCost 22/23/18, each over 24 scenes at 1/3/5 km. Forward versus R1 has three rescued scenes and three newly failed scenes, with 60 common successes. The three new failures are s1271_007_open_slow_1000, s1271_032_islands_fast_5000, and s1271_033_channel_fast_5000. Equal totals do not establish preservation of safety for individual tasks or statistical noninferiority.

3. On the 60 Forward/R1 common safe arrivals, Forward minus R1 travel time is +90.683333 s mean and +1 s paired median. The 3 km and 5 km common-success means are +224.476190 s (n=21) and +49.111111 s (n=18), with paired medians +5 and +17.5 s. Path length increases by 50.849488 m overall. The report correctly calls the bootstrap intervals exploratory and conditional on common success. Its observed overall time interval [5.75, 229.445417] s cannot be interpreted as an unconditional mission-efficiency effect.

4. Candidate simplification and fewer switches do not imply faster closed-loop completion. On the same Forward/R1 common-success set, Forward averages 2.5 fewer actual target changes and 1.016667 fewer heuristic tack counts, while taking longer. Mean recorded planning time is 4.598496 to 4.505570 s and reencoding time 6.065180 to 5.711331 s, but navigation wall time is 37.731518 to 39.912281 s and CPU time 37.769295 to 39.928785 s. The report appropriately avoids a fixed-input speedup claim from the substantially lower all-72 episode average, which is confounded by different termination times and trajectories.

5. The strong simple controls remain relevant threats to extra complexity, without establishing a universal winner. Relay and RouteCost have the same overall safe-arrival count as Forward and shorter conditional overall travel times on their respective common-success sets. Relay has six buffer intrusions versus Forward's four; RouteCost has only 18/24 safe arrivals at 5 km versus Forward's 20/24. These are observed tradeoffs, not evidence of overall dominance by any method.

6. The adverse cases are real and materially limit interpretation. Raw records confirm the 3 km open-water example where Forward takes 5154 s versus R1's 1643 s, adding 3511 s; entry within 100 m occurs at 5098 versus 1584 s, so this is not merely a final-10-m artifact. Raw records also confirm the 1 km timeout at 1800 s and 25.125511 m remaining, and the 5 km obstacle case where Forward reaches a negative one-second-segment safety clearance at 503 s while R1 and Relay eventually arrive safely.

7. In the obstacle case, the target was selected at t=295 and applied at t=296, with no late pending replacement near the t=503 intrusion. I independently re-ran only the frozen planner's t=495 static scoring, without a physics rollout. Both candidate totals, 4487.790506789679 and 4481.94286617825, matched final_failure032_t495_recompute.json exactly; the 5.847640611429 improvement is below the strict 15 threshold, producing hysteresis. This supports the local decision explanation. It does not show that the rejected target was dynamically recoverable or that earlier triggering would have saved this episode.

## What the results do not support

- Safety equivalence, noninferiority or a safety guarantee. The experiment has only six Forward/R1 discordant scenes, no prespecified noninferiority margin, and actual new failures. A paired test p=1 is not positive evidence of equivalence.
- Improved 3/5 km efficiency or a stable practical reason to replace R1 with Forward. Both distance-specific conditional mean and median time differences are adverse.
- Global runtime acceleration, or attribution of wall-clock differences only to candidate count. Full episodes differ in duration, target-switch history, failures, initialization and logging work.
- A causal claim that hysteresis, the switch cost, the one-second application protocol, or the decaying clearance trigger is the unique cause of complete-episode failures. The existing evidence separates some local decisions but lacks the relevant controlled full-episode counterfactuals.
- Universal uselessness of extra angles, wind information or motion history; necessity of either retained score term; optimality of 80 m/500 m/15; transfer to another controller, generator, physical vessel or distribution; or publication novelty. The report generally states these boundaries correctly.

## Missing evidence

No further evidence is required to report the bounded negative result honestly. Positive replacement claims would require a prespecified safety noninferiority/superiority criterion with adequate scene replication, a failure-aware mission-level evaluation alongside conditional timing, reproducible positive 3/5 km results on fresh validation data, and controls that isolate the claimed mechanism. Fixed-input timing would be needed for a computational speedup claim. Dynamic feasibility or safety claims would need more than one-second chord clearance.

The formal ARIS evidence helper was unavailable through the supplied/configured resolution paths, and EXPERIMENT_AUDIT.json is absent. I confirmed absence of the project-local helper, installed-skills pointer, formal audit and formal precheck; ARIS_REPO was unset on the server. The saved final_integrity.json reports the project's own 288-episode verifier passing. This is useful supporting verification, not a formal independent experiment audit, and does not upgrade this same-family judgment beyond provisional.

## Suggested claim revision

“In this frozen-controller synthetic benchmark, reducing the radial proposal set to a single forward 500 m proposal, while retaining route vertices, the goal and a valid incumbent, produced 63/72 safe arrivals, the same total as R1 but with three wins and three losses. It reduced target switching on common successes, but did not improve long-range travel time: mean differences were +224.48 s at 3 km and +49.11 s at 5 km. Geometrically feasible targets and a smaller search do not ensure safe or efficient closed-loop execution.”

Use the negative comparison and reproducible failure analysis as the contribution currently supported. Retain Forward as a frozen research configuration; do not promote it to the default on these data. The report's phrase “在多数已测案例中保留接近的行为” is less precise than this revision because “接近” has no declared trajectory-level metric or threshold. Replace that phrase with the explicit observed counts and conditional timing, or tie it narrowly to the documented development trajectory-equality result versus narrow. This is a wording improvement, not a hidden positive result.

## Next experiments needed — recommendation only

None should run as part of closing this already bounded study. If a future round is explicitly authorized, the report's single proposed discriminative test is reasonable: hold Forward candidates, costs, controller and timing fixed; compare the current clearance trigger with an independently specified own-clearance trigger; record trigger, newly selected target, application and outcome separately. Tune only on new development data, then freeze and use fresh validation scenes, retaining false-positive/long-range time costs. The test must allow the conclusion that an earlier trigger still finds no useful executable maneuver. It should not tune directly to scene032 or call seed1271 unseen again. A successful local rescue alone would still not establish the original long-range-efficiency claim.

## Report issues and verification scope

Two concrete report issues were found and reported to the parent executor, then verified corrected in the current report:

1. The supplemental figure-note pointer originally omitted its directory. The file is figures/figure_supplement_note.json under the run directory; docs/R2_RESEARCH_REPORT.md line53 now uses that path.
2. The pseudocode originally said candidates were filtered on the original safety map. Actual r2_planner.py lines68–71 filters and connects candidates using planned, normally the inflated map; lines44–46 fall back to the original map on NoRouteError. The report line141 now explicitly reflects this.

No unresolved must-fix numerical, leakage, adverse-selection or time-accounting issue was found within this bounded review. The broader “near behavior” wording above should be tightened for precision. The frozen protocol's “all-method common successes” figure wording is slightly ambiguous against the three displayed methods, but I independently recomputed selection using both three and all four methods; all three ordinary figure IDs are unchanged. Thus this ambiguity caused no selection change in the delivered figures.

I independently recomputed report_pairs and report_pairs_by_distance from analysis_rows for all three controls and all distance groups: common IDs, wins/losses, means, paired medians and individual p90 values for all eight reported metrics matched. I checked all six completion receipts and fresh-row counts: 3+108+144+252+144+288=939 unique new episodes; their CPU and batch-wall sums agree with resources.json. I read the online planner/navigation/timing code, the analysis and scene/figure-selection code, inspected all 16 raw traces for the four central positive/adverse cases, and visually inspected the obstacle and largest-efficiency-regression PNGs. I did not independently re-integrate physical trajectories, repeat the entire 288-episode raw-metric verifier, rerun simulations, or conduct a formal external audit.

Reviewed report SHA256 after the two corrections: f58404d32df62bde4289b2070f4763c277d803159c18eaff25324622d3fff3ef. Evidence root: /home/ot/Students/hs/sailboat-routing-v0/runs/r2_autoresearch_20261003T063153Z/. Scientific implementation remained 3003228f6cabbf3f1b1dcaa875329fbc2d9338af during review.
