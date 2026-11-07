# Template contract and build record

Source: user-supplied conference-template.docx, identical to the current official HTTP download on 2026-10-05.
SHA256: 8b9d63f2223b9e8ab547c9095ed80fad5b38cfe5f2146185effb7a7f3ea9257e.
Companion user LaTeX ZIP (not used): 4c0539eed7bd4221d026382a56c57ec1668c55a8ca72b581f7a28654401dedc9.
Download base: http://www.ccdc.neu.edu.cn/_upload/tpl/01/4f/335/template335/htmlRes/download/

Contract: preserve template A4 geometry, title and two-column body sections, styles, Times New Roman body, 24pt paper title, 9pt abstract, 8pt captions/references and original body spacing. Replace instructional/sample content with the actual manuscript; reduce sample author grid to a single explicit placeholder. Main column gap 0.25in, side margins approximately0.63in. Do not shrink typography to satisfy page limits. Figures use an available serif face and have vector counterparts; not claimed identical font metrics to Word.

Mapped content: title → paper title; abstract → Abstract; keywords → Keywords; sections → Heading1/2; body → Body Text; captions → figure caption/table head; references → references. Explicit numbering avoids duplicate automatic numbering. Equations are editable Office Math, split where needed for column width. Tables remain editable cells.

Build: bundled Python with python-docx executes build_docx.py. Microsoft Word COM opens manuscript.docx and ExportAsFixedFormat(...,17) creates manuscript.pdf. No terminal TeX or LibreOffice was installed. The built-in LaTeX editor is not involved because the chosen deliverable is Word. Poppler rendered every page; final PDF has6 pages. A first pass exposed overly long diagram text, overlapping time labels, and table-caption misclassification; these were corrected and all6 pages re-inspected. Poppler emitted missing fallback-font warnings for Symbol/ArialUnicode; visible equations and glyphs were inspected, not silently assumed correct.

This is a first draft using the official template, not a claim that unknown submission policies have been satisfied.
