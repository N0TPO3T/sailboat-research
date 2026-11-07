# R13 evidence and recovery index

Authoritative repository: `/home/ot/Students/hs/sailboat-routing-v0`. Inherited R12 raw run: `runs/r12_revision_20261006/`. The preview contains copied source records; full R12 raw trace archive, including exact historical input traces needed by these analyses, is delivered separately as `R12_raw_results.tar.gz`. Neither archive grants inherited-asset redistribution rights.

| Claim / artifact | Canonical record |
|---|---|
| Budget, prespecified comparison | plan.json, calibration.json, freeze.json, development.json, guard.json, confirmation.json |
| Each complete voyage and failures | {development,guard,confirmation}/<scene>__<variant>/trace.json; each includes job/config, actual states, target truth, observations, commands, changes, decisions and predictions |
| New confirmation / guard summary | analysis.json, episodes.csv |
| Exact original S15 reproduction | parity.json |
| Selected actual prefixes | prediction_windows.csv, prediction_summary.json, analyze_r12_prefix.py |
| Fixed full protocols and parity | fixed_branches.json, branches_complete.json, check_r12_branches.py |
| Matched two-predictor quality (12 protocols /6 snapshots) | matched_prediction_quality.json/.csv, compare_r12_predictors.py |
| Same-state candidate decision | matched_decisions.json |
| Accepted-substep numerical safety | substep_safety.json |
| Planning-core timing | planning_profile.json, profile_r12.py |
| Original and frozen source preservation / task coverage | original_hashes.json, freeze.json, verification.json, INHERITED_SOURCE_CHECK.json |
| Current rescue/adverse figures | case_analysis.json; unique new L failure pressure1 and largest new S15 cost endpoint3 |
| Original failed branch selection and successful bounded retry | branches.log, branches_retry.log, branch_retry_note.json, branches_complete.json |

JSON/CSV copies are in this draft's `evidence/`; complete raw traces are in the raw archive. Scripts are in `code/scripts/` and the new model in `code/src/sailboat_routing/`. Install no new service; use the existing repository/environment and original assets. Analysis scripts infer repository root from their `scripts/` location.

Historical source groups remain separate: `runs/r8_closedloop_20261005T062543Z/{confirmation,long}/` and `runs/r10_decision_20261005/{dynamic_development,confirmation}/`. The seen R10 mechanism set overlaps R8. Existing R10 source/raw recovery archives and R11 EVIDENCE_INDEX remain valid. This package indexes rather than silently replaces them. R9 `runs/r9_timing_20261005T085308Z` is a different delivery protocol and is not pooled.

Recompute summary and figures without rerunning physics:

```sh
cd /home/ot/Students/hs/sailboat-routing-v0
.venv/bin/python paper/ccdc/r13_revision/plot_r13.py
```

A new physical rerun requires a new output directory and a new budget deadline; never point the runner at existing completed folders. `run_r12.py` accepts a manifest path; the frozen manifests show every job and parameter. The original detailed model and physical loop are imported, not replaced.

Editable Word/PDF: `build_docx.py`, `math_docx.py`, `export_pdf.ps1`. The user-provided Word template is retained as `official_template.docx`; Office Math is editable. `SUPPLEMENT.md` carries longer derivations. `manuscript.md` is canonical scientific content; Word and LaTeX derive from it. LaTeX compilation is not verified; the actual PDF is Word-exported.

## Primary reference checks

References [1]–[5] retain R11 primary-source verification: Sensors DOI10.3390/s20061550; full GVO paper https://gamma.cs.unc.edu/NHRVO/WilkieIROS09.pdf; governor survey author manuscript https://merl.com/publications/docs/TR2016-102.pdf; MoWe DOI10.1002/rob.22512; SAC https://proceedings.mlr.press/v80/haarnoja18b.html.

R12 checked [6] BC-MPC full text https://arxiv.org/html/1907.00039 and [7] feedback-motion prediction full text https://arxiv.org/html/2209.12648v3. These motivate control-induced prediction; their controller assumptions and guarantees are not inherited. [8] sailing-yacht paper metadata/abstract was checked on the University of Southern Denmark research portal, https://portal.findresearcher.sdu.dk/en/publications/modeling-and-nonlinear-heading-control-of-sailing-yachts/ ; no source-code equivalence was verified. Precise bibliographic entries are in manuscript.md.

The official-policy pages previously checked in R11 are http://www.ccdc.neu.edu.cn/001/list.htm and http://www.ccdc.neu.edu.cn/firstSubmit/list.htm . Template layout is applied; unresolved author/policy items are explicitly listed rather than guessed.


## R13 delivered recovery and current evidence
- `R13_REPRODUCTION_internal.zip`: unified internal source/dependency/weights/manifests/72trace archive. Run `python verify_recovery.py` after extraction in the existing compatible environment. It verifies contents hashes, loads actual weights and reconstructs primary results. This archive is not a public release authorization. `evidence/recovery_check.json/log` records successful verification in a new server directory.
- `evidence/decision_260.csv` and `case_analysis.json`: all evaluated candidates in the exact shared260s state; full-voyage margins and timestamps.
- `evidence/new_case_substeps.json`: three original-command numerical replays, exact1s endpoints, no new independent sample.
- `SOURCE_FOLLOWUP.md`: formal Yang et al. research source, confirmed provider/use/reviewer-provision scope, and 14D versus 18D identity limits.
- `review_round_01_input/VERSION.json` and `review_round_02_input/VERSION.json`: immutable submitted text/PDF/supplement hashes. Raw opinions and itemized responses in `review/`.
- `VENUE_CHECK.md`: official initial-submission page checked2026-10-07. `LAYOUT_CHECK.json`: actual8page Word PDF visual inspection.
- `R12_raw_results.tar.gz` remains at ../r12_revision/ and includes complete historical diagnostic inputs; its SHA256 is a0d1be6102bccf99a01c947f58d47e1721630dff47bd0e910bb2ab9d3c7ad618. The separate current internal bundle contains all primary24×3traces directly.

## R13 asset-confirmation continuation
User confirmation and supplied formal paper: SOURCE_FOLLOWUP.md; exact unchanged archive check: evidence/asset_resume_check.json. Research/reviewer provision is confirmed; public release is not claimed. Review round04 contains the actual amended manuscript and concentrated A1/B1/C1 response. No experiments or figures regenerated for this source update.
