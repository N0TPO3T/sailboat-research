# ARIS paper improvement log

## Scope and review independence

Local editorial improvement of the user-named Track A draft for CCDC 2027. Original PDF and frozen evidence retained. Two fresh-context GPT-6-Astra xhigh reviewers, same model family; all scores and readiness recommendations are provisional internal assessments, not conference decisions. Reviewers are not shown prior scores or fix lists. Main artifact uses the supplied Word template and actual Word-to-PDF regeneration in place of a TeX-only compilation workflow. Optional LaTeX is synchronized, not claimed to have compiled.

The manuscript contains no theorem environments and no explicit broad/general safety claim. The conditional clearance inequality is explanatory and scoped to a common domain. The theory/generality kill-argument branch is therefore not applicable. No new navigation trials, training, hardware deployment, posting or notifications were undertaken.

## Scores

| Review | Version reviewed | Score | Verdict |
| --- | --- | --- | --- |
| 1 | Original named manuscript | 6/10 | Almost |
| 2 | Round 1 regenerated manuscript | 7/10 | Almost; bounded CCDC application contribution |

## Round 1 fixes

- M1: Core interface made self-contained from archived executable source. Main text separates memory replay from actuator accumulation; supplement enumerates the 18 inputs, reset and replay inputs. Figure 1 shows pending-action timing and separate reconstruction paths.
- M2: Scoped the contribution to this controller and a finite empirical assessment; compressed repetitive provenance, defensive statements and workflow narrative. Kept low-order calibration limitations, single additional completion, adverse travel time, 106 m prediction error, common-model assumption and paused physical time.
- M3: Human supplied names and affiliations were inserted. Corresponding author, email and funding remain unspecified. No invented information.
- Minor presentation repairs: Table III width, redundant method encodings in data plots, prediction-protocol key, static-disk caption, equation-number alignment and inline subscripts. References renumbered by appearance; GVO page range verified and added. Diagnostic snapshot selection recovered from code and reported. Tangential delayed-protocol references removed without changing primary results.
- Verification: full 72-trace / 25,382-interval deterministic recomputation; equations and numerical table values unchanged; eight-page PDF. First-pass font audit found unembedded Times bold/italic; ISO 19005-1 export embeds all fonts with identical extracted page text and page count. Conformance itself is not certified.
- Issue accounting: 0 critical findings; 2 major scientific-writing concerns addressed; metadata concern partly resolved with human information and remaining fields documented. Minor issues above addressed without new scientific experiments.

### Round 1 full raw review

# Independent review of the current Track A manuscript

**Overall score: 6/10 — weak accept for a CCDC control/application paper.** This is a provisional internal assessment, not a prediction of the conference decision.

**Submission readiness: Almost.** The scientific results support a narrowly scoped simulation application paper. The current PDF still contains author/affiliation placeholders, and the core reconstruction interface needs a clearer, self-contained account.

## Review scope

I read the complete manuscript.md, latex/main.tex and SUPPLEMENT.md. I freshly rendered manuscript.pdf and visually inspected all eight pages; I did not use the existing rendered directory. I checked the primary numerical summaries against evidence/episodes.csv, the decision/case records, the fixed-protocol error records, calibration records and planning timings. I did not rerun navigation, inspect inaccessible server traces, or independently establish asset provenance. I did not read previous reviews or improvement logs.

The eight-page initial submission is within the current [CCDC 2027 initial-submission allowance](https://www.ccdc.neu.edu.cn/firstSubmit/list.htm). Page count is not a rejection reason here.

## Summary

The paper adapts control-induced prediction to an inherited recurrent sailing controller by explicitly representing reference delivery, hold duration, causal state reconstruction and restoration of nominal route feedback. The frozen 24-task comparison gives R/L/S15 safe-completion counts of 19/23/24, while the detailed predictor has a substantial computation cost and an adverse 308 s detour. Its defensible contribution is a carefully implemented supervisory interface and diagnostic application study, rather than a new control principle, certified safety method, or demonstrated deployable system.

## Ranked strengths

1. **The numerical story is internally consistent and preserves unfavorable results.** I independently recomputed the 19/23/24 counts, family counts, 19 common-safe pairs against R, 23 against L, +7 s S15-minus-L mean, +308 s maximum, and episode CPU totals from the supplied episode table. The main tables and text agree. The 106.064 m adverse prediction error is retained rather than omitted.
2. **Timing and causal information are treated seriously.** Section II-B identifies the already computed old-reference action and the first interval that can be affected by a new reference. Sections III and V distinguish a fixed-protocol branch from the trajectory after later replanning. The same-input decision contrast at 260 s is more informative than an unqualified comparison of complete trajectories.
3. **The comparator is operationally matched in useful ways.** Candidate generation, guard, horizon, hold/review period, ranking, endpoint manager and physical execution are shared. The manuscript correctly says that replacing L changes recurrent control, wind, actuator and speed modeling together.
4. **The safety metric is explicit and numerically checked.** The synchronized relative-segment definition avoids separate-time closest-point comparisons. Same-command accepted-substep checks retain the relevant unsafe/safe signs. The manuscript correctly distinguishes this result from swept-hull or formal continuous safety.
5. **Evidence denominators are unusually transparent.** Primary tasks, historical tasks, overlapping cases, diagnostic snapshots and clustered prediction windows remain separate. The introduction already cites the most directly relevant prediction/governor traditions and does not present the triangle inequality as new theory.

## CRITICAL issues

**No critical scientific contradiction or numerical mismatch was found in the reviewed material.** In particular, I found no demonstrated future-information leak in the stated protocol, no justification for rejecting the paper merely for having eight pages, and no reason to demand a new theoretical safety theorem for its current empirical scope.

## MAJOR issues and actionable fixes

### M1. The claimed core interface is still described too much as an implementation black box

**Evidence:** manuscript.md lines 29–31 and 53–55; Algorithm 1, lines 97–102; Fig. 1 on PDF page 2; SUPPLEMENT.md S2, lines 17–21. The body says that history is reencoded and issued commands are replayed, while Algorithm 1 compresses this into “reconstruct branch state.” This does not cleanly distinguish policy-memory reconstruction from actuator-setpoint reconstruction. The reader must infer the reset state, which historical observations are transformed into the candidate frame, the order of replay versus candidate application, and which state is copied versus recomputed.

This matters because execution consistency is the paper's main contribution. A reader should be able to understand that contract without receiving the full software archive. There is also an inaccurate completeness signal: manuscript.md line 27 sends readers to S9 and S11–S12 for the exact observation mapping, but those sections mostly identify files, hashes, access status and a recovery command; they do not actually enumerate the 18 inputs or give the complete reconstruction recurrence.

**Fix, without new experiments:** Replace some provenance prose with a compact state/reconstruction specification based on verified code. Define the augmented branch state, initial/reset memory, the observation transform used for historical replay, and the separate command accumulation that recovers actuator setpoints. State exactly which operation occurs at t, t+1 and the hold-release boundary. Revise Fig. 1 to expose the pending action and delayed reference delivery, or add a small timeline inside the existing figure. Include the exact 18-input ordering in the supplement and make the existing cross-reference truthful. Do not invent a recurrent update equation that differs from the actual Actor implementation.

### M2. Repeated defensive prose obscures a modest but intelligible contribution

**Evidence:** manuscript.md line 19 (“not proposed as new control theory”); lines 25 and 27 repeat the 14D-versus-18D distinction; line 29 discusses an unestablished adapter contribution and a historical check; line 53 warns that consistency is not future accuracy; line 89 says “We preserve it in code”; lines 184, 194, 209 and 232 add further negation or internal-process framing. SUPPLEMENT.md S5, S9, S11–S13 also contains revision identifiers, user permission chronology and archive-management narrative. These facts are not all equally relevant to a conference reader.

The abstract opens with the right problem, but then becomes an inventory: family counts, two completion comparisons, mean and maximum time, two CPU totals, a 106 m error and the computation assumption. This makes it harder to identify the one practical lesson. The phrase “The missing interface” at line 17 also sounds like a field-wide novelty claim even though the paper establishes a particular adaptation to this inherited policy.

**Fix, without changing any scientific assertion:** State the application contribution directly: the inherited recurrent controller needs a branch protocol that reproduces its reference transition and memory/actuator handling, and the study measures the benefit and cost of that protocol. Scope “missing interface” to this system unless a broader literature claim is substantiated. Consolidate asset identity and training provenance in one paragraph and move internal revision/access chronology out of the scientific supplement. Keep one precise limitation paragraph for common-model prediction, unknown training linkage and non-real-time execution. Shorten the abstract while retaining the primary completion counts, the computation condition, and an explicit adverse cost. Preserve all unfavorable table values and the adverse prediction case in Results. Do not turn the unnecessary endpoint intervention into a claimed beneficial tradeoff.

### M3. The current artifact is not submission-complete

**Evidence:** manuscript.md line 3 / PDF page 1 says “Authors and affiliations to be confirmed”; line 236 / PDF page 7 says author names, affiliations and funding remain to be completed.

**Fix:** Obtain the real author block and any applicable funding information from the authors, and remove production instructions from the acknowledgment. Use the venue's actual anonymity requirements if relevant; do not invent author identities or affiliations. The AI-assistance statement should describe the actual assistance and satisfy the venue's applicable disclosure requirement. This is a metadata completion issue, not a reason to alter the experimental results.

## Material evidence limits that cap the score, rather than require immediate new experiments

1. **The comparison establishes a result against this particular L implementation.** L is calibrated on unchanged-reference 15 s windows, while it is used for 60 s hold-and-restore forecasts; the selected rate cap is at the upper edge of the grid (Section IV-B, manuscript.md lines 127–135; supplement S3). Therefore the experiment cannot separate detailed-model fidelity from calibration support or establish that a stronger cheap predictor would lose. The manuscript already acknowledges this correctly. Preserve that boundary; a new 60 s/maneuver-matched calibration is needed only if the authors later claim the necessity or general superiority of detailed prediction.
2. **One additional completion over L is a finite designed-set result.** All gains occur in eight encounters that jointly change geometry, wind direction and static context (lines 119–123, 174). The comparison does not identify which factor makes detailed prediction valuable or estimate a population-level success advantage. This does not invalidate the paired count. Do not attach a general reliability or statistical-superiority claim to 24/24.
3. **The six diagnostic snapshots are informative cases, not a representative prediction-error benchmark.** The source identities and two protocols are given in S7, but the rule for selecting those particular times is not explained. Some source scenes also occur in L's development/calibration data. Add a short factual explanation of case selection and its purpose if recoverable from the existing plan; otherwise describe them explicitly as selected development diagnostics. Keep their median as a descriptive statistic of those branches, not an accuracy estimate for future encounters.
4. **Practical deployment remains untested.** The same dynamics structure, noiseless observations, one constant-velocity target and paused physical clock are favorable evaluation conditions. A 17.009 s representative detailed call exceeds the 15 s period. Those boundaries are already stated clearly; do not add further generic hedges, and do not claim real-time practicality merely from the episode CPU values.

These are the main reasons for 6 rather than 7 or 8. They do not all need to be resolved to submit the current scoped application paper.

## MINOR issues and precise fixes

- **Table III, PDF page 6:** the last header breaks “median/max” into “median/ma” and “x (s).” Use a short, deliberate two-line label or give the final column more width. Standardize decimals within the table. No numerical change is needed.
- **Figures 2–4 and 6:** R/L/S15 are primarily separated by color. On Fig. 2 most margin points use the same shape; on Figs. 3–4 the tracks use the same solid style. Add redundant line styles or method-specific markers where they do not hide overlapping trajectories. Keep the existing R/L/S15 colors consistent.
- **Fig. 6 and caption:** circle/triangle protocol identities require S7. Add concise protocol abbreviations or a compact per-snapshot key, so that the figure can be interpreted in the submitted PDF. Keep the duplicate snapshot-4 paths identified as one source state.
- **Fig. 3:** label the static circle/exclusion ring explicitly, since the caption mainly explains the moving target ring. Distinguish safety-buffer circles from entity disks in the legend or caption.
- **Equation presentation, PDF pages 2–4:** equations are readable, but numbers are attached at the end of the last expression rather than consistently aligned, and some inline indexed names appear as plain text. Use native equation formatting with consistent subscript notation for O_t, K_gamma, d_G and the real/predicted margins. Preserve the already correct mathematical definitions.
- **Supplement references in lines 219 and S14:** delayed-execution “boundary evidence” is mentioned, but S6/S14 largely provide a version description rather than the actual delayed protocol and outcomes. Either supply a concise factual locator/summary of that evidence or omit this tangential reference. It is not needed to establish the present ideal-compute result.
- **Supplement language:** strings such as “All24,” “seed202610612,” “all72,” and “23common-safe” should be spaced normally. Internal revision labels can remain in artifact paths, but do not need to organize the scientific explanation.

## Numerical and causal assessment

The key checked values are consistent:

| Checked item | Recomputed / checked value |
|---|---:|
| Safe completions R / L / S15 | 19 / 23 / 24 |
| Pressure safe completions R / L / S15 | 3 / 7 / 8 |
| Mean L minus R, 19 common-safe pairs | 6.6316 s |
| Mean S15 minus R, 19 common-safe pairs | 25.1579 s |
| Mean S15 minus L, 23 common-safe pairs | 7.0000 s |
| Maximum S15 minus L | 308 s |
| Episode CPU R / L / S15 | 270.6771 / 378.4445 / 2133.2321 s |
| Median fixed-branch maximum error, detailed / L | 1.1040 / 53.8178 m |
| Largest detailed fixed-branch position error | 106.0637 m |

The 260 s decision record supports the stated nominal margins and alternative costs. The selection/delivery/effect times 260/261/261–262 s are consistent with the stated delayed reference application. The manuscript correctly does not attribute the entire later voyage to this one intervention.

The clearance inequality is valid on the explicitly common protocol, obstacle set and time domain. It supplies no usable safety certificate without a uniform error bound; the manuscript says so. Prefix parity and selected-branch replay validate implementation consistency locally, not unseen-future prediction accuracy.

The aggregate files support these checks. I have not independently re-established every raw-state equality claim from full traces.

## References

I found no mandatory missing reference that justifies expanding the literature review. GVO, reference governors, maritime branching-course MPC, feedback motion prediction, motion-based wind estimation, SAC and the sailboat model lineage are already represented. The directly relevant feedback-prediction paper indeed studies controller-specific motion bounds and governor-based navigation; this supports the manuscript's positioning ([author paper](https://arxiv.org/abs/2209.12648)).

The needed change is a sharper comparison with these existing principles, not a longer citation list. I did not complete a full bibliographic audit of all nine entries. The inherited 2026 article's DOI did not resolve through the browser tool in this review; that tool failure is not evidence that the reference is false.

## Visual review

- **Coverage:** all eight pages of the actual Word-export PDF, freshly rendered at 120 dpi.
- **Readability:** body text, plotted axes and most captions are legible. No obvious clipping, overlapping text or missing figure was observed. Formula content is readable despite the formatting issues above.
- **Figure-caption agreement:** captions match the displayed experiments and correctly distinguish failed time pairs, synchronized encounter positions, selected diagnostics and duplicate protocols.
- **Layout:** no stranded section heading was found. Figure 1 is near its method description; result figures are near their discussion. Page 8 contains only four references with substantial unused space. This is visually unbalanced, but permissible under the eight-page initial limit; compacting repeated prose could improve balance without reducing type size.
- **Tables:** Tables I and II are readable and aligned. Table III needs the header repair. Bolding best values is optional because the results involve costs and safety, rather than one scalar ranking.
- **Color:** method colors are consistent, but method identity is not robust enough without color in all figures. Grayscale readability was assessed from the encoding design, not verified by a separate grayscale print test.
- **Production:** author placeholders are visibly present and must be resolved before upload.

## Final recommendation

Submit after making the reconstruction contract self-contained, removing redundant defensive/process prose, repairing the table/figure presentation and completing author metadata. Retain the exact primary counts, the costly endpoint case, the large prediction error, the comparator-calibration limitation and the paused-computation condition. The evidence supports a useful, modest CCDC simulation application contribution; it does not yet support a claim that detailed prediction is generally preferable or deployable.



## Round 2

Pending independent review.


## Round 2 fixes and final verification

- T1 (major): separated the twelve exact physical-state-prefix reconstructions from the six selected branches' exact first-15-second **position** checks. The alternative branches have no selected-continuation parity receipt. Corrected Section IV-C, V-D and Supplement S4/S14; no stronger state/action parity is asserted.
- T2: restricted the abstract statement to safe-completion differences, preserving the endpoint travel-time penalty.
- T3: documented exact point/segment clearance tests, endpoint-manager ranking distance and angle units, and world-frame blowing-toward wind convention from frozen source. No evaluated algorithm was changed.
- T4: added Qi et al., ICRA 2021, DOI 10.1109/ICRA48506.2021.9560859, as direct sailing-obstacle-avoidance lineage. Bibliography has ten entries, renumbered by appearance. Author/institutional publication listings and IEEE metadata support this acknowledgment; no full-text-dependent mechanism comparison was added. Primary records: https://crai.cuhk.edu.cn/page/361 and https://ieeexplore.ieee.org/document/9560859 .
- T5: Figure 4 now explicitly states that R and L coincide. Verified full raw physical-state arrays agree for r12new_endpoint_3. The existing Figure 3 discussion explicitly identifies the equal prefix through 260 s.
- T6: synchronized LaTeX subscripts. Optional final-page rebalancing was not imposed; the readable eight-page template layout remains within the verified initial-submission allowance. LaTeX native compilation remains unverified.
- Evidence limits E1–E3 remain: paused physical time/high measured cost, limited low-order calibration and bundled predictor replacement, and finite noiseless common-model simulation without proven training-scene separation. These limit stronger claims; this editorial pass does not resolve them experimentally.
- Final checks: deterministic reaggregation from 72 traces / 25,382 intervals passes; original six displayed equations and three numerical tables unchanged; original PDF preserved. All eight final rendered pages inspected (rendered_final-1.png through rendered_final-8.png), including every figure, table, equation, author block and references. No clipping or overlap observed. Page 8 remains sparse. All PDF fonts embedded; template styles unchanged; editable native Word math preserved; optional TeX cross-references/citations structurally checked. No PDF eXpress or independent PDF/A certification claimed.
- Round 2 accounting: one actionable major wording issue and five minor items addressed as above, with optional balancing deferred. No critical issue. The 7/10 score belongs to the second review before these final bounded fixes; no third review or higher final score is implied. Corresponding author/email/funding remain pending human information.

### Round 2 full raw review

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
