**Overall score: 7/10 — Accept at the CCDC control/application-paper level. Provisional internal assessment only. Readiness: Almost.**

The manuscript has a defensible, bounded application contribution: it specifies how candidate reference protocols are predicted and delivered to an inherited recurrent sailing controller, then measures the resulting decisions and costs. The scientific result is modest but informative. Detailed prediction gains one safe completion over the calibrated low-order predictor in 24 designed tasks, while incurring substantially higher computation and a 308 s adverse travel-time case. The manuscript generally states this balance accurately. It does not establish deployment readiness, general safety, or the necessity of recurrent prediction. Those are limits of the evidence, and the current principal claims do not require them.

I inspected the current Markdown, LaTeX source, supplement, relevant evidence records, and every page of the current Word-export PDF. I did not read prior reviews or revision logs, modify the manuscript, run navigation experiments, or train a model. The PDF has eight pages. This meets the official initial-submission allowance; it should not be rejected for exceeding six pages. [CCDC 2027 submission requirements](https://www.ccdc.neu.edu.cn/firstSubmit/list.htm).

**Ranked strengths**

1. **The execution contract is unusually explicit for an application study.** Sections II-B and III-A–C distinguish the pending action, reference delivery, recurrent-history replay, actuator setpoints, hold expiry, and restored route feedback. In particular, selection at t does not affect t→t+1; delivery occurs at t+1 and the first affected interval is t+1→t+2. Supplement S2 also explains that memory replay conditions on actual past commands rather than inventing a counterfactual past. This is the concrete engineering contribution.

2. **The principal numerical claims agree with the supplied records.** Reaggregation of the 72 confirmation rows gives 19/24, 23/24 and 24/24 safe completions for R, L and S15. The 23 common-safe S15–L pairs have mean 7 s, median 0 s, minimum −136 s and maximum 308 s. Episode CPU totals round to 270.68, 378.44 and 2133.23 s. The reported fixed-protocol median maximum-position errors, 1.104 and 53.818 m, also reproduce from the twelve matched records on their stated common intervals. These checks corroborate the supplied records; they are not a fresh experiment.

3. **Prediction quality and complete-voyage outcomes are not conflated.** Section V-B presents the equal-prefix decision at 260 s but explicitly allows later replanning and different environmental exposure to affect the final voyage. Section V-D separately evaluates fixed protocols. The twelve branches are grouped into six source states, and the duplicate endpoint paths are disclosed. This supports a local decision contrast without claiming a single intervention caused the entire rescue.

4. **Negative results remain visible.** The abstract and conclusion retain the small advantage over L, the computation penalty, the 308 s endpoint penalty and the 106 m prediction error. Historical no-gain confirmation results are retained with separate denominators. L is acknowledged as a substantially cheaper alternative with nearly the same completion count. These are scientifically useful results, not facts that should be removed to make the paper sound stronger.

5. **The safety interpretation is calibrated.** Buffer incursions are distinguished from hull collisions and from NoRouteError. Accepted-substep replays preserve the decisive classification, including the new L incursion at approximately −1.117 m. The triangle-inequality statement uses a common protocol, obstacle set and time domain, and the manuscript correctly declines to infer a uniform error bound or safety guarantee from empirical maxima.

**Ranked issues: concrete text or presentation fixes**

**CRITICAL: None identified within the paper's stated descriptive scope.**

**MAJOR T1 — The fixed-branch parity sentence overstates which continuations were checked.**

Evidence: Section V-D, PDF page 6, states: “All twelve fixed real branches from six snapshots reproduce their full physical prefixes and the selected first 15 s exactly.” In `evidence/fixed_branches.json`, all twelve `actual.prefix_state_max_error` values are zero. However, `selected15s_position_parity` is zero for the six selected branches and null for the six alternatives. The reported continuation check is specifically a position check. Supplement S4 correctly limits this check to the selected branch. An unselected counterfactual protocol is not required to reproduce the selected trajectory.

Action: Replace the sentence with: “All twelve branches reproduce their recorded physical-state prefixes exactly. At each of the six snapshots, the selected branch also reproduces the original first 15 s of positions exactly.” Apply the same distinction wherever the check is summarized in Section IV-C and the supplement. If stronger state/action parity was checked elsewhere, name that evidence explicitly instead of extending the position receipt's meaning. This is a wording correction; the prediction-error results need not change.

**MINOR T2 — Qualify the abstract's ‘all differences’ statement.**

Evidence: Page 1 says “All differences occur in eight combined-pressure encounters,” immediately before reporting the travel-time comparison. Safe-completion differences are confined to pressure tasks, but the 308 s travel-time difference occurs in an endpoint task.

Action: Write “All safe-completion differences occur in the eight combined-pressure encounters.” This preserves the result and removes a literal ambiguity.

**MINOR T3 — Finish the small remaining execution and notation definitions.**

Evidence: Section III-A describes the nominal manager through numerical settings and the predicates “goal is occupied,” “clear incumbent,” and “clear segment,” but does not explicitly define their geometric tests. Its ranking term “distance plus 80 times absolute heading turn” leaves the angle unit unstated. Section III-B introduces a two-component wind vector without explicitly naming its coordinate frame. These omissions matter more here because the nominal manager is executed inside every prediction tail.

Action: In the supplement, state the exact clearance/radius convention for those predicates, define what the ranked distance measures, and give the angle unit and corresponding coefficient unit. State the wind-vector frame and wind-direction convention. A compact route-manager input/output contract is sufficient; do not replace the paper with a code listing. These should be documented from the evaluated implementation, with no algorithm change or new experiment.

**MINOR T4 — The related-work coverage should include direct sailing-obstacle-avoidance work.**

Evidence: The current introduction covers sailing Q-learning, GVO, reference governors, maritime branching-course MPC and feedback motion prediction, but omits Qi et al., “Collision Risk Assessment and Obstacle Avoidance Control for Autonomous Sailing Robots,” ICRA 2021, pp. 2511–2517. Its existence, authorship and venue are confirmed by the authors' institutional publication listing and IEEE record. [AIRS institutional listing](https://airs.cuhk.edu.cn/en/publications?page=0%2C9), [IEEE record](https://ieeexplore.ieee.org/document/9560859).

Action: Add a concise acknowledgment of this directly relevant application lineage. Establish any detailed mechanism comparison from its full paper before writing it; the retrieved primary listing alone does not justify assertions about its assumptions or limitations. This omission does not establish that the current execution interface already exists, and it does not justify demanding a new head-to-head experiment. The current contribution should remain supervisory integration and assessment, not first-ever sailing obstacle avoidance.

**MINOR T5 — Clarify overlapping plotted trajectories.**

Evidence: Figure 4 on page 6 includes R and L in its legend, but their identical tracks are mostly visually hidden by overplotting and by the shared S15 prefix. The records confirm both complete at 279 s with identical path length and minimum margin. Figure 3 also has extensive shared prefixes. Nothing appears missing, but the visual accounting requires inference.

Action: Add “R and L coincide” to the Figure 4 caption or use an explicit combined R=L trajectory label. A short shared-prefix annotation would also help Figure 3. Preserve the complete tracks and the adverse case.

**MINOR T6 — Polish the editable LaTeX notation and final-page balance.**

Evidence: `latex/main.tex` writes replay-state identifiers as literal escaped underscores, for example `s\_0` and `s\_t`, whereas the Word PDF uses subscripted state symbols. The PDF's eighth page contains only references [6]–[9] at the upper left and otherwise substantial white space.

Action: Use mathematical subscripts in the LaTeX source, and optionally rebalance the final text/reference columns. The eighth page is a layout inefficiency, not a page-limit violation. Do not shrink readable figures or remove relevant references merely to force six pages. I reviewed the Word-export PDF, not a separately compiled LaTeX PDF, so I do not claim to have verified the latter's layout.

**Ranked scientific evidence limitations — already substantially disclosed, not requirements for new experiments under the current claim**

1. **MAJOR E1 — The detailed predictor is not demonstrated as an online controller on the measured implementation.** Physical time is paused during planning, and the measured planning core has a 17.009 s median across the selected states, exceeding the 15 s review period. The confirmation record for the highlighted rescue task also contains an approximately 29.64 s maximum planning call; the three-state profile is not a worst-case bound. The paper correctly distinguishes these measures. This is a deployment limitation, not evidence of an acceptable operational tradeoff. Retain the explicit ideal-compute scope. Delay-aware execution would be required only to support a future deployment claim.

2. **MAJOR E2 — The L comparison identifies the tested predictor replacement, not the necessity of detailed dynamics or recurrent replay.** L is fitted on unchanged-reference 15 s windows and evaluated in 60 s hold/release predictions. It simultaneously omits recurrent state, actuators, wind and speed variation. Its first interval extrapolates motion instead of using the pending policy action. The manuscript states all of this. Therefore, one extra completion supports the result for this calibrated comparator, not superiority over a well-identified family of simpler predictors. No new calibration study is necessary for the present bounded comparison. Such a study would be needed before stronger necessity or mechanism-attribution claims.

3. **MAJOR E3 — Generalization and robust safety remain unestablished.** Prediction and execution share dynamics structure, target extrapolation matches the constant-velocity targets, observations are noiseless, and the inherited policy's training-scene provenance is unknown. The 24 tasks are designed scenes rather than a population sample. The six fixed-protocol snapshots are selected development states, partly overlapping calibration data. These facts limit external validity and the meaning of the error median. They do not invalidate the paired within-scene observation. Preserve the current restrictions; do not turn the count advantage into a collision-risk estimate, a guarantee, or evidence of transfer to other controllers.

**Claim calibration and contribution judgment**

The paper's positive claim should remain that executable reference protocols can change safety-relevant decisions within this simulator and that the integration can be measured reproducibly against shared-supervisor alternatives. The evidence supports that claim. It also supports the unfavorable conclusion that the tested detailed predictor has high cost and can make a large prediction error. The manuscript should not be weakened to say that it merely “might be useful,” because the equal-prefix decision contrast and paired outcomes are actual observations. Conversely, there is no supported conclusion that the detailed predictor is generally the preferable controller.

At CCDC application-paper level, an explicit execution contract plus a carefully bounded comparative study is a reasonable contribution. This is not a new general control-theoretic framework, and Equation (5) is an explanatory bound rather than a novel safety theorem. The manuscript mostly gets that distinction right. The lack of new training, formal safety proof or sea trial is not by itself a reason to reject this specific submission.

**Reference usage**

The nine current references have distinct roles and are used without transferring their guarantees or benchmark claims to the present system. In particular, MoWe motivates motion-based wind information rather than being represented as the implemented estimator; the recurrent 18-input asset is distinguished from the cited article's 14-input formulation; and the yacht dynamics are described as a model lineage rather than certified code equivalence. Those are appropriate boundaries. The directly relevant Qi et al. reference above is the only addition I specifically recommend. I did not complete an independent full-text bibliographic audit of every reference; the publisher/DOI page for [7] was inaccessible through the web tool during this review. That access failure is not evidence that the reference is incorrect.

**Fresh visual review of all eight PDF pages**

| Page | Inspection result |
| --- | --- |
| 1 | Title, human-supplied author block and affiliations are readable. The abstract is dense but legible. No clipping or overlapping blocks. |
| 2 | Figure 1 clearly distinguishes memory replay, command accumulation and the pending-action interval. The clearance equation and its degenerate case are readable. |
| 3 | Wind fitting, candidate ranking, Algorithm 1 and the bound fit inside their columns. Formula spacing and prose-style mathematical symbols could be polished, but no scientific expression is visibly lost. |
| 4 | The low-order equations and Tables I–II are legible. Table headings and denominator explanations are present. |
| 5 | Figure 2 separates time, actual margins and success status; failed pairs are not plotted as zero time cost. Figure 3 provides full trajectories and synchronized clearance. Small negative incursions are easier to read from the text than the plot, which is acceptable because exact values are reported. |
| 6 | The adverse endpoint case is prominent. Figure 5 and Table III are readable. R/L overlap in Figure 4 should be stated explicitly. |
| 7 | Figure 6 visibly retains the large detailed-prediction error, distinguishes predictors by fill and protocols by shape, and labels the source-state grouping. Discussion, availability statement and references are readable. |
| 8 | References [6]–[9] are intact and legible. The page is largely empty; optional balancing would improve finish. |

Poppler emitted display-font warnings during rendering, but inspection of the rendered pages did not reveal missing mathematical symbols, black boxes, clipped figures or unreadable text. The page images were created only in `review_render_round2/`.

**Recommended disposition: Almost ready after focused textual corrections.** Correct T1 before submission; also resolve the abstract qualifier and clarify the small execution-contract definitions. Add the direct sailing-avoidance citation if its full paper can be checked, and make the modest presentation fixes. No new navigation run or training is required to support the current explicitly bounded descriptive result. Preserve the reported failures, computation limitation, unfavorable endpoint behavior and unknown inherited-training provenance.
