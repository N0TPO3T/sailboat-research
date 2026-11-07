# Track A closeout response — 2026-10-09

## Scope and source

This is a bounded ARIS editorial closeout, not a new scientific version or another score-seeking review. The author used the supplied closeout prompt and independent review. The starting PDF SHA256 is 23e1c8fe24bac26d3114ef3194977511a7074ee3407e15f959f974082442a0b1. The local manuscript, Word, PDF, supplement, figure/build scripts and episodes.csv agree byte-for-byte with the previous delivered ZIP. Local and server HEADs differ, both have existing uncommitted work, and the server does not contain track_A_aris_20261008. Consequently this new local directory preserves the latest author content without pulling, resetting, copying over another worktree, or claiming server synchronization. Details are in provenance/version_check.json.

## Required changes

| Request | Implemented location and change | Verification |
| --- | --- | --- |
| M1: measured trade-offs, not justified cost | Abstract; Introduction final paragraph; Discussion final paragraph. Replaced the cost-justification question with measuring decision, safety, navigation-time and computation trade-offs. Removed the suggestion of an application-specific fidelity selection rule. | No added utility score or model-switching method. Positive findings and adverse cases remain. |
| M2: design, consistency and integrated effects | Introduction contribution paragraph. Candidate includes delivery, hold and nominal restoration; reconstruction/pending-action checks concern execution correspondence; task comparison evaluates the integrated predictor. III-A's separate memory replay and command accumulation remain. | No isolated safety benefit or first-ever claim is assigned to a reconstruction operation. Prior controller, dynamics and GVO attribution retained. |
| M3: common-safe paired distribution | Results V-A and Supplement S5. Added 5 faster / 13 equal-time / 5 slower, range −136 to +308 s, with explicit time-versus-trajectory distinction. | check_paired_times.py reads only confirmation rows, pairs by scene_id and requires both success=True. 72 rows / 24 scenes; 23 accepted pairs; exact Decimal differences, no tolerance; mean +7 s, median 0. PAIRED_TIME_CHECK.json lists every pair and the excluded unsafe L arrival. |
| M4: nominal early return in Fig. 1 | draw_interface.py; figures/figure1_interface.svg/.pdf/.png; Fig. 1 caption; Algorithm 1. Explicit nominal validity/integration/guard diamond; pass skips alternative prediction; fail restores and predicts alternatives then ranks/falls back. | Bounded read-only inspection of frozen r8_planner.py confirmed active-hold return before nominal manager, eligibility after manager, nominal break, then original ranking/fallback. Retained memory/setpoint split, separate branch histories, P hold/restoration, pending old action and t+1 delivery. No scientific code or timing changed. |

## Minor editorial requests

- Abstract: reduced numeric density; retained 19/23/24, combined-pressure scope, mean/max common-safe travel-time cost and paused physical time. CPU absolute values and 106.064 m error remain in Results and Discussion, not hidden or removed from the evidence.
- Algorithm and units: added inputs/outputs, real indentation and explicit branch/return structure. Defined until as hold expiry and next_plan as next review, initially 10 s; retained H/P/ρ. Equation (4)'s 20 and 10 coefficients are explicitly metres. The feasible-alternative cancellation and tied-margin fallback meaning are unchanged.
- Supplement numbering: Table S1 is input ordering; S2 historical outcomes; S3 source snapshots; S4 scene envelope. No supplementary figures are added; Fig. 1–6 references are explicitly main-paper figures. Historical evidence remains separate from confirmation. S4 also explicitly uses position-only selected-continuation wording, consistent with the existing 12/6 distinction.
- Reference pagination: Word reference paragraphs now stay together, with unchanged template styles/font sizes/margins. Metadata uses actual title/authors rather than template placeholders. No references were removed.
- Reproduction access: Supplement S5/S11 and README distinguish lightweight CSV/log reaggregation from the separate full recovery archive. Full weights/raw traces are not claimed to accompany the ZIP. Readers can extract materials anywhere; no author-machine sibling path is a required entry point. Access is through editorial correspondence under existing permission, with contact metadata still pending.
- Confirmed authors/affiliations and asset permissions unchanged. Only corresponding author, email and applicable funding remain in AUTHOR_CHECKLIST_ZH.md.

## Preservation and validation

No navigation experiment, training, baseline calibration, guard search or GPU work was performed. All copied scientific evidence and the five numerical plots remain byte-identical to the starting author edition. The six displayed equations, all three numerical tables and all ten bibliography entries remain unchanged. The 19/23/24 primary counts, pressure 3/7/8, all-safe remaining sixteen tasks, +308 s adverse case, 106.064 m error, computation cost, L calibration limits and ideal-compute scope remain.

The old manuscript directory and its original evidence are preserved. No server files, root B-line plans or scientific implementation were edited. The only statistics executed this round are the bounded CSV reaggregation. Earlier raw-trajectory checks are clearly marked as historical receipts.

The final Word PDF is eight pages. The author inspected all eight rendered pages at 1500-pixel height, including every figure, table, equation and reference. No clipping or reference-entry splitting was observed. CLOSEOUT_CHECK.json records the PDF hash, embedded-font and preservation checks. Optional LaTeX is synchronized but not natively compiled. Page/font checks are not conference-system certification.

## Independent closeout check

A fresh-context checker independently confirmed the CSV results and inspected all eight pages. It identified one wording-order ambiguity in Algorithm 1 line 2. The author corrected it to “Clear incumbent if hold expired; call nominal manager.” This matches the existing implementation and Supplement S2; no algorithm or experiment changed. The Word PDF was regenerated for one targeted recheck. The final report is INDEPENDENT_CLOSEOUT_CHECK.md; no score or acceptance recommendation is requested.
