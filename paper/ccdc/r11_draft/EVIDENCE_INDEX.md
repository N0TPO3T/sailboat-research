# R11 evidence and reproduction

Authoritative repository: /home/ot/Students/hs/sailboat-routing-v0. This draft runs no new physics, training or evaluation episodes.

Historical short/long: runs/r8_closedloop_20261005T062543Z/{confirmation,long}/, with manifests confirmation.json/long.json. Historical aggregate: all_rows.csv and analysis.json.
Seen mechanism/new confirmation: runs/r10_decision_20261005/{dynamic_development,confirmation}/. Exact manifests, analysis_rows.json, comparisons.json, episodes.csv, first_decision_differences.json and dynamic_same_state.json are retained there.
R9 boundary only: runs/r9_timing_20261005T085308Z; see docs/R9_RESEARCH_REPORT.md. Do not pool its delayed protocol with the main results.
Source/asset identities: evidence/SOURCE_HASHES.json, evidence/ASSET_HASHES.json. Full asset recovery: existing R10_source.zip and R10_raw_results.tar.gz and the repository's delivery records; preview ZIP does not contain weights or the full raw archive.

Plot input: figure_data.json contains the five actually used traces and prediction records, extracted from runs/r10_decision_20261005/figure_data/plot_sources.json without re-executing the policy. Replot on the existing server environment:

```sh
cd /home/ot/Students/hs/sailboat-routing-v0
.venv/bin/python paper/ccdc/r11_draft/plot_figures.py paper/ccdc/r11_draft/figure_data.json
```

Word rebuild: run build_docx.py with the available Python/python-docx, then run export_pdf.ps1 in Windows with Microsoft Word installed. The Markdown is the content source; manual Word edits are not automatically round-tripped to Markdown.

Citation verification used primary sources: Sensors DOI10.3390/s20061550; GVO full paper https://gamma.cs.unc.edu/NHRVO/WilkieIROS09.pdf; reference-governor survey DOI10.1016/j.automatica.2016.08.013 and author manuscript https://merl.com/publications/docs/TR2016-102.pdf; MoWe DOI10.1002/rob.22512; SAC https://proceedings.mlr.press/v80/haarnoja18b.html. GVO's control-induced motion is the adapted principle; governor/MoWe guarantees or implementations are not claimed. The supplied template and official policy pages are separate from scientific evidence.
