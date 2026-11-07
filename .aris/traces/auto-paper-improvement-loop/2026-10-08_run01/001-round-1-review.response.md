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

