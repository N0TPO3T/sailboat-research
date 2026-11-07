# Independent visual and factual check — 2026-10-13

This is one bounded independent check of the October 13 visual edition under the paper-figure workflow. The reviewer inspected the final manuscript and supplement, their Markdown and editable Word sources, CLOSEOUT_RESPONSE.md, the six referenced figures, all seven tables, frozen plotting data and relevant original records. No previous reviewer reports were read. No scientific experiment, scoring exercise or research-review loop was performed. Only this report was written.

**Finding: no factual or readability defect requiring repair was found in the checked visual revision.** This finding concerns the identified files and the checks below; it is not formal venue acceptance or a new validation of the research claims.

## Exact reviewed artifacts

| Artifact | Pages | SHA256 |
| --- | --- | --- |
| manuscript.pdf | 8 | `8c827b77912aa2cac783c2bc45a40a8a84edaba81fd2247db954472203dd8428` |
| SUPPLEMENT.pdf | 6 | `581e701385c62a69c694872a810c0ab70b0b67bc0da0047ba46181374f7761c5` |

Every page was visually inspected using `qa/final-1.png` through `final-8.png` and `qa/supp-final-1.png` through `supp-final-6.png`. The reviewer independently rerendered every page in memory with Poppler at a 1500-pixel maximum dimension. All fourteen rerenders matched the inspected images pixel for pixel. Thus this inspection is tied to these PDFs rather than an earlier layout. All PDF fonts were embedded: nine main-paper font resources and five supplement font resources.

## Figure checks

| Figure | Independent result and evidence |
| --- | --- |
| 1, interface | The main-paper page 2 diagram and caption retain the nominal-first early return and the fail branch that evaluates alternatives. Replay memory and restore setpoints remain separate. The old action precedes reference delivery at t+1; the first possible changed-reference effect is the t+1 to t+2 interval. The caption preserves integration-successful validity, isolated predicted history and executed-feedback-only real history. These statements agree with III-A, Algorithm 1 and S2. |
| 2, all matched tasks | `plot_data.json` contains exactly the 72 confirmation CSV rows and the 24 manifest-ordered task IDs. Mapping is reactive=R, simple=L, sampled=S15. Independent aggregation gives 19/23/24 safe tasks and 3/7/8 pressure-family completions, with all sixteen other tasks safe. Each predictor-versus-R time panel uses nineteen common-safe pairs; failed pairs are omitted rather than set to zero. All 72 actual margins and all task outcomes are retained. Every plotted margin lies inside the displayed -3 to 420 m bounds; all plotted time differences lie inside -35 to 330 s. The caption explicitly identifies the symmetric-log scale and its 3 m linear threshold. |
| 3, unique confirmation difference | Complete R/L/S15 trajectory columns match the six-case archive comparison described below. This case has 393/567/520 state samples and 392/566/519 s durations. The 260 s synchronized markers, target track, 85 m dynamic circle, static entity radius 45 m and additional 60 m ring agree with the frozen inputs and plotting code. The lower panel is explicitly the encounter interval, not the full-voyage time domain. Minimum-margin endpoints and unsafe R/L versus safe S15 remain visible and correctly described. Selection at 260 s, delivery at 261 s and first possible effect at 261–262 s remain in the adjacent text. |
| 4, adverse endpoint | Complete paths, target track and clearance histories are retained. R and L coincide exactly in the frozen coordinates, and the caption states this rather than visually separating them. Their durations are 279 s; S15 takes 587 s, preserving the +308 s counterexample. The 200 s synchronized markers and 85 m circle use the matching samples. |
| 5, guard sensitivity | The plotting data equal the supplied guard analysis. All four guards remain: 0/15/30/60 m. Time summaries use ten common-safe pairs, while worst margins use all twelve tasks. Independently checked means are 2.8/32.7/29.2/40.2 s; maxima are 28/334/267/321 s. Worst margins are 3.3468/24.8790/31.7812/61.7675 m. Mean and maximum have distinct marker/fill styles. The figure and text preserve the nonmonotone time cost and make no optimal-guard claim. |
| 6, fixed-protocol prediction | All twelve records match `matched_prediction_quality.json`. Snapshot/protocol order agrees with Table S3, including circle/triangle assignment and filled S15/open L markers. Common intervals are ten 60 s and two 58 s. Independent medians of branch-maximum errors are 1.1040168 m for S15 and 53.8177843 m for L. The 106.0636595 m adverse S15 error is plotted and rounded to 106.064 m in the text. Snapshot 4 nominal/continuation have identical errors and 140.990225/146.171208 m predicted/actual margins; their dependence is explicitly disclosed. The log error axis and signed predicted-minus-actual margin residual are correctly labeled. |

The plotted method colors are consistent across the data figures. Shapes, fills or line styles supplement color, and the captions distinguish safe/failure symbols where their meaning differs from the method key. No legend obscures the data, no relevant adverse observation is hidden by the displayed axes, and no figure label or caption was visibly clipped at the final layout size. The six referenced PNGs match the Word document's embedded media bytes exactly.

For the two complete-voyage case figures, the reviewer read only the six corresponding `trace.json` members of `r13_revision/R13_REPRODUCTION_internal.zip`. Their scene, row, time, own-position, target-position and interval-margin columns exactly equal `plot_data.json`, including every sample. Their six member hashes match FIGURE_DATA_CHECK.json. The entire recovery archive was not rehashed, and no other trajectory or simulation was rerun.

## Tables, text and preservation

Tables I–III and S1–S4 were inspected in the actual PDFs. All seven are editable Word tables. Independent cell-by-cell comparison established equality among current Markdown, current Word tables and the October 9 Markdown tables, including units, identifiers, signs, failure counts, overlap labels and denominators. No table is clipped or split through a data row. The main tables occupy pages 5–6; supplement S1 is on page 2, S2–S3 on page 4, and S4 on page 5.

Table I's CPU totals independently aggregate to 270.677134, 378.444523 and 2133.232056 s for R/L/S15, matching the displayed rounded values. Predictor-versus-R common-safe means are 6.631579 s for L and 25.157895 s for S15. The S15-versus-L comparison separately contains 23 common-safe pairs: five faster, thirteen equal and five slower, range -136 to +308 s, mean +7 s and median zero. These agree with the abstract, main text, supplement and closeout response. Equal travel times remain explicitly distinct from identical trajectories.

All 75 checked main-paper prose/caption blocks and 53 supplement prose/caption blocks match the Word text after whitespace and documented subscript-format normalization. Main Markdown outside figure captions is unchanged from October 9, preserving all six equations and the M1–M3 wording: measured trade-offs, integrated-effect rather than component-necessity claims, and the exact paired-time evidence. M4's nominal-first selection and timing remain in Fig. 1. The supplement's sole prose change is S5's description of the supplied Markdown/Word/PDF and portable plotting data. All 44 frozen evidence files are byte-identical to October 9.

The page inspection found no missing glyph, obscured equation, detached caption, overflowing table or omitted end section. The main paper remains eight pages and the supplement six. Existing limitations remain explicit: paused physical time, predictor computation cost, the low-order calibration scope, clustered diagnostic windows, twelve replayed prefixes versus six selected continuations, adverse cases, and lack of a uniform safety guarantee.

## Scope boundary

This check verifies faithful visual presentation, data mapping and preservation against the supplied records. It does not establish unknown inherited training provenance, generalization beyond the reported tasks, real-time deployability, exact hull safety or publisher-template compliance. CLOSEOUT_RESPONSE.md describes the inspected visual changes consistently. No repair or additional experiment is requested by this bounded check.
