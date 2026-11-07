# R13 revision package

Start with manuscript.pdf (actual8page Word export), manuscript.docx (original supplied template, native editable equations), manuscript.md (canonical scientific content), and AUTHOR_NOTES_ZH.md. SUPPLEMENT.md supplies derivations, scenario envelopes and evidence boundaries. Final review conclusions are in FINAL_REVIEW_STATUS.md; simulated review is not CCDC acceptance.

`latex/main.tex` and R13_LaTeX.zip are editable matching source. Native compilation failed because platform standard directories were unavailable; no LaTeX-generated PDF is claimed. Use an existing pdfLaTeX environment with bundled IEEEtran.cls and figures.

Figures are real-log PNG/PDF/SVG. Run plot_r13.py from the authoritative repository root using its existing environment. This only creates R13 figures/analysis. Manuscript conversion: run build_docx.py with the bundled Python/python-docx; export_pdf.ps1 uses MicrosoftWord. convert_to_latex.py regenerates matching TeX. R12_TO_R13.diff records textual changes.

Review round snapshots preserve actually reviewed manuscripts and hashes; raw A/B/C reviews are unedited. Individual author responses identify completed revisions and remaining gaps. R13_REPRODUCTION_internal.zip is a separate full internal recovery bundle; its existing-env verification is documented in EVIDENCE_INDEX.md. No permission to publicly redistribute inherited assets is implied.
