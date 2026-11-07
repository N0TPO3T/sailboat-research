from pathlib import Path
import hashlib,json
p=Path(__file__).parent
f=p/'EVIDENCE_INDEX.md';s=f.read_text(encoding='utf8').replace('# R12 evidence index','# R13 evidence and recovery index')
s=s.replace('New raw run:', 'Inherited R12 raw run:')
s=s.replace('| Scene chosen for adverse trajectory figure | figure_cases.json; historical pressure2 plus largest new common-safe S15 time cost vs reactive |','| Current rescue/adverse figures | case_analysis.json; unique new L failure pressure1 and largest new S15 cost endpoint3 |')
s=s.replace('Matched two-predictor quality', 'Matched two-predictor quality (12 protocols /6 snapshots)')
s=s.replace('`.venv/bin/python scripts/plot_r12.py`','`.venv/bin/python paper/ccdc/r13_revision/plot_r13.py`')
s=s.replace('.venv/bin/python scripts/analyze_r12.py\n.venv/bin/python scripts/plot_r12.py\n.venv/bin/python scripts/verify_r12.py','.venv/bin/python paper/ccdc/r13_revision/plot_r13.py')
s=s.replace('`ARTIFACT_CONTRACT.md` documents the source relation.', '`manuscript.md` is canonical scientific content; Word and LaTeX derive from it. LaTeX compilation is not verified; the actual PDF is Word-exported.')
s+='''

## R13 delivered recovery and current evidence
- `R13_REPRODUCTION_internal.zip`: unified internal source/dependency/weights/manifests/72trace archive. Run `python verify_recovery.py` after extraction in the existing compatible environment. It verifies contents hashes, loads actual weights and reconstructs primary results. This archive is not a public release authorization. `evidence/recovery_check.json/log` records successful verification in a new server directory.
- `evidence/decision_260.csv` and `case_analysis.json`: all evaluated candidates in the exact shared260s state; full-voyage margins and timestamps.
- `evidence/new_case_substeps.json`: three original-command numerical replays, exact1s endpoints, no new independent sample.
- `SOURCE_FOLLOWUP.md`: actual primary/source lineage checks, limitations and outstanding human confirmations.
- `review_round_01_input/VERSION.json` and `review_round_02_input/VERSION.json`: immutable submitted text/PDF/supplement hashes. Raw opinions and itemized responses in `review/`.
- `VENUE_CHECK.md`: official initial-submission page checked2026-10-07. `LAYOUT_CHECK.json`: actual8page Word PDF visual inspection.
- `R12_raw_results.tar.gz` remains at ../r12_revision/ and includes complete historical diagnostic inputs; its SHA256 is a0d1be6102bccf99a01c947f58d47e1721630dff47bd0e910bb2ab9d3c7ad618. The separate current internal bundle contains all primary24×3traces directly.
'''
f.write_text(s,encoding='utf8')
(p/'README.md').write_text('''# R13 revision package

Start with manuscript.pdf (actual8page Word export), manuscript.docx (original supplied template, native editable equations), manuscript.md (canonical scientific content), and AUTHOR_NOTES_ZH.md. SUPPLEMENT.md supplies derivations, scenario envelopes and evidence boundaries. Final review conclusions are in FINAL_REVIEW_STATUS.md; simulated review is not CCDC acceptance.

`latex/main.tex` and R13_LaTeX.zip are editable matching source. Native compilation failed because platform standard directories were unavailable; no LaTeX-generated PDF is claimed. Use an existing pdfLaTeX environment with bundled IEEEtran.cls and figures.

Figures are real-log PNG/PDF/SVG. Run plot_r13.py from the authoritative repository root using its existing environment. This only creates R13 figures/analysis. Manuscript conversion: run build_docx.py with the bundled Python/python-docx; export_pdf.ps1 uses MicrosoftWord. convert_to_latex.py regenerates matching TeX. R12_TO_R13.diff records textual changes.

Review round snapshots preserve actually reviewed manuscripts and hashes; raw A/B/C reviews are unedited. Individual author responses identify completed revisions and remaining gaps. R13_REPRODUCTION_internal.zip is a separate full internal recovery bundle; its existing-env verification is documented in EVIDENCE_INDEX.md. No permission to publicly redistribute inherited assets is implied.
''',encoding='utf8')
print('Current evidence index and reproduction entry written')
