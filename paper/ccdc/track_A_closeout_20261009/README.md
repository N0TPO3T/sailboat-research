# CCDC 2027 Track A closeout

This is the 2026-10-09 editorial closeout of the 2026-10-08 author manuscript. Start with manuscript.pdf. The editable sources are manuscript.md, manuscript.docx and SUPPLEMENT.md. CLOSEOUT_RESPONSE.md maps the bounded review requests to the actual changes. AUTHOR_CHECKLIST_ZH.md records the remaining submission metadata and local/server status.

## Lightweight evidence and full recovery

This ZIP contains lightweight evidence and publication artifacts, not the complete simulator, model weights or all raw trajectories. Run `python check_paired_times.py` after extracting the ZIP anywhere. Python 3's standard library is sufficient. This regenerates PAIRED_TIME_CHECK.json from the supplied episodes.csv, using confirmation rows and both-success pairing only. Main-paper completion counts, family summaries and common-safe time/CPU aggregates can also be calculated from that CSV. Other diagnostic summaries retain their original evidence identities.

The full archive R13_REPRODUCTION_internal.zip is **not included**. Its SHA256 is d0fdc80b40b5252ced7dfd15370a30e092b3232cc1b7ef65e131bedac50ce640. It contains frozen source dependencies, the Actor/normalizer, environment lock, manifests and all 72 primary traces. Editors/reviewers can request it through the manuscript's editorial correspondence channel under the existing provision permission. Authors must still fill the corresponding author/contact metadata. No public repository or download service is asserted. Supplement S5/S11 explains the separate access and recovery procedure. Archive-internal runs/, src/ and checkpoints/ paths are identifiers in that archive, not author-machine paths that an external reader must possess.

## Rebuild the manuscript

The primary PDF is exported from the included Word template. The package contains the existing publication figures, so rebuilding the manuscript does not require matplotlib or the recovery archive.

1. Use Python with `python-docx` and `lxml` available: `python build_docx.py`.
2. On Windows with Microsoft Word installed, run `powershell -ExecutionPolicy Bypass -File export_pdf.ps1`. It exports manuscript.pdf with the font-embedding option used for this edition.
3. Visually inspect every exported page. Font embedding and page count do not certify IEEE PDF eXpress or PDF/A compliance.

Native Word equations are constructed by math_docx.py. The supplied official_template.docx retains its original styles, page size and margins. Publication fonts are not distributed as standalone files.

For Fig. 1 only, use Python with matplotlib: `python draw_interface.py`. This writes editable text SVG, vector PDF and 300 dpi PNG under figures/. All other figures are unchanged frozen publication images. No plot-regeneration script is presented as independently runnable without its required raw inputs.

Optional `python convert_to_latex.py` synchronizes latex/main.tex using the included IEEEtran.cls and vector figures. Native LaTeX compilation has not been verified and is not the source of the delivered Word PDF.

## Provenance boundaries

provenance/version_check.json records the actual starting-file/package comparison and read-only server check. The 20261008 trajectory-verification receipt is historical evidence from the earlier editorial pass; this closeout does not rerun 72 trajectories. Existing evidence JSON files may contain historical internal paths/statuses; they are preserved records, not instructions or current synchronization claims.

The independent closeout checker verifies this final artifact and the requested changes once, without a new acceptance score. No simulation, training, baseline calibration, guard search, server write, push or submission is part of this closeout.
