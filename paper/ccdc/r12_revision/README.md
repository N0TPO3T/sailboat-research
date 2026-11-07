# R12 revision package

Start with `manuscript.pdf` (7 pages), or edit `manuscript.docx`. The complete content source is `manuscript.md`; `R12_REVISION_REPORT.md` explains the evidence in Chinese. Body styles retain the supplied Word template; formulas are editable Office Math.

The frozen 24-task comparison gives safe completions R=19, detailed S15=24, low-order L=23. Detailed prediction gains one completion over L, with +7 s mean over 23 common-safe pairs, a +308 s adverse tail and larger computation. This is conditional value under ideal computation, not general dominance or a safety guarantee. All old results and failures are retained separately.

- `figures/`: four new evidence figures and the inherited interface schematic; PNG/PDF/SVG.
- `evidence/`: per-task CSV, prediction statistics, frozen manifests and source/asset checks.
- `code/`: runnable new predictor and experiment/analysis scripts for the existing repository.
- `SUPPLEMENT.md`: detailed mathematical interpretation and restoration protocols.
- `CODE_FORMULA_AUDIT.md`, `REVIEW_EVIDENCE.md`, `REVIEW.md`, `AUTHOR_RESPONSE.md`: one separated internal review pass and actual revisions.
- `AUTHOR_ASSET_CHECKLIST_ZH.md`: unresolved attribution, permission and author items.
- `server_state/`: updated authoritative server HANDOFF/STATE/PLAN; the older local dirty context files were not overwritten.
- `input/`: unchanged user revision inputs, clearly separated from the completed manuscript.

`R12_raw_results.tar.gz` is delivered beside this ZIP. It contains all new raw runs and the exact historical input traces used by the analyses, with hashes. `EVIDENCE_INDEX.md` gives recovery and reproduction paths. Existing R10_source.zip and R10_inherited_assets.zip in the local project root supply original code/assets; asset availability does not establish publication permission.

No training, GPU use, automatic push, submission or next research iteration was performed. The revised PDF has been actually exported and checked; this archive is not an acceptance assessment.
