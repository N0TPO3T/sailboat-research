# CCDC 2027 Track A — visual closeout, 2026-10-13

Start with manuscript.pdf (8 pages), or FIGURES.html for the six figures and seven tables in one overview. Editable sources: manuscript.md/docx and SUPPLEMENT.md/docx. The supplement is also supplied as a 6-page PDF. CLOSEOUT_RESPONSE.md maps the visual changes and preservation of the earlier M1–M4 closeout. INDEPENDENT_VISUAL_CHECK.md is the independent check of this edition; dated reports under provenance/ concern earlier editions.

## Contents and scope

The six main figures use concise labels and muted blue/teal/ochre with redundant shapes or line styles. Fig. 1 is the approved full-width diagram. Tables I–III and S1–S4 retain every cell value and use consistent headers, alignment and light rules. The body text, equations, authors, bibliography and scientific conclusions remain unchanged except for figure captions. All 44 evidence files are unchanged. No experiment, training, calibration, guard search or Track B modification was performed.

This is a lightweight publication/evidence package. It contains extracted plotting columns, not complete raw traces, the simulator, model weights or the full recovery archive. The separate R13_REPRODUCTION_internal.zip is not included; SHA256 d0fdc80b40b5252ced7dfd15370a30e092b3232cc1b7ef65e131bedac50ce640. Editors/reviewers can request that archive through the manuscript's editorial correspondence channel under the already confirmed permission. Corresponding-author metadata still needs to be filled. No public repository or download service is asserted. Supplement S5/S11 describes this separation.

## Portable checks and regeneration

All commands resolve supplied inputs relative to their scripts; ordinary rebuilding does not require any directory on an author's machine.

- Python standard library: `python check_paired_times.py` recomputes the 23 S15/L common-safe pairs from evidence/episodes.csv.
- Python with NumPy and Matplotlib: `python draw_interface.py` and `python plot_figures.py` regenerate all six figures from their editable source and supplied plot_data.json. SVG retains editable text/paths, PDF is vector, PNG is 300 dpi. Individual data-plot entry scripts are under figures/.
- Python with python-docx and lxml: `python build_docx.py`, then `python build_docx.py --supplement` rebuild the two editable documents using official_template.docx.
- Windows with Microsoft Word: `powershell -ExecutionPolicy Bypass -File export_pdf.ps1`, then `powershell -ExecutionPolicy Bypass -File export_pdf.ps1 -InputName SUPPLEMENT.docx -OutputName SUPPLEMENT.pdf` export the PDFs.
- Python with python-docx, lxml and pypdf: `python check_visual_artifacts.py` checks Markdown/Word table and paragraph agreement, page counts and font embedding. If the previous local edition happens to exist as a sibling, it also checks preserved evidence/text; it does not require that sibling for portable checks.
- `python make_overview.py` recreates the local figure/table overview.

Optional `python extract_figure_data.py PATH_TO_RECOVERY_ARCHIVE` documents how plotting columns were copied from frozen source records. The existing plot_data.json is already supplied, so the recovery archive is unnecessary for figure regeneration. FIGURE_DATA_CHECK.json records source hashes and sample counts. No navigation is run by this extraction.

The actual PDFs were exported by Microsoft Word and rasterized with Poppler. Every page was visually inspected. The generic render_docx.py helper could not run because LibreOffice is absent; its failure was not treated as a successful render. Font embedding/page inspection is not IEEE PDF eXpress or PDF/A certification. Optional LaTeX is not part of this edition's delivery.

## Status

Local output only. Read-only server listing on October 13 found no October 8/9/13 editing directory; the server still retains track_A_submit and historical editions. This package has not been synchronized, uploaded, pushed or submitted. Earlier files and existing uncommitted changes were preserved. Only corresponding author, email and applicable funding remain for the authors to supply; see AUTHOR_CHECKLIST_ZH.md.
