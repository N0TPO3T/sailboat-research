# Reproducing the R3 study

The canonical runtime is `/home/ot/Students/hs/sailboat-routing-v0` with its existing `.venv/bin/python`. The preview does not contain inherited weights, an environment, or a license grant for those assets. Reuse the verified project installation and check `docs/UPSTREAM_MANIFEST.md`; the actor is chapter4 14D @7200, not final @9000. Scientific source identity is stored in each batch `provenance.json`; final method/configuration and generator selection are recorded in `method_freeze.json`, `generation_receipt.json` and `final.json`.

## Read the evidence without rerunning

`runs/r3_ccdc_20261003T121146Z/iteration_ledger.md` records development decisions. Each completed batch contains `analysis.json`, `episodes.csv`, `paired_episode_differences.csv`, `raw_index.csv`, `rows.json`, `completion.json`, and `provenance.json`. Every raw-index row identifies the original `job.json` and full navigation trace. `risk_mechanisms.csv` separates requests from actually applied changes. First-round risk counts omit failed terminal planning calls; task outcomes do not omit failures. The later logger fixes that evidence omission without changing planner decisions.

The figure directory contains exact plotted positions, actual target events, scenario descriptions and case-selection rules. PNG/SVG paths are unsmoothed recorded trajectories. The framework drawing is a schematic. Open the supplied HTML locally; it requires no CDN or remote service.

## A separate future full reproduction

The following is a reproduction recipe, not an additional run performed for this delivery. Use a fresh directory. The archived runner refuses to overwrite an existing batch, and the original research deadline is deliberately not renewed in place. The recipe creates a new, explicit 12-hour reproduction budget; it does not modify archived results.

```bash
cd /home/ot/Students/hs/sailboat-routing-v0
.venv/bin/python - <<'PY'
import json,time
from pathlib import Path
source=Path('runs/r3_ccdc_20261003T121146Z/final.json')
batch=json.loads(source.read_text())
run=Path('runs/r3_reproduction_review').resolve()
run.mkdir(exist_ok=False)
batch.update(run=str(run),round=1,stage='frozen_reproduction')
(run/'final.json').write_text(json.dumps(batch,indent=2))
(run/'plan.json').write_text(json.dumps(dict(started_epoch=time.time(),deadline_epoch=time.time()+12*3600,max_scientific_rounds=1,max_cpu_workers=4,threads_per_worker=1,gpu_hours=0),indent=2))
PY
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  .venv/bin/python -B scripts/run_r1.py runs/r3_reproduction_review/final.json --workers 4
OPENBLAS_NUM_THREADS=1 .venv/bin/python -B scripts/analyze_r3.py runs/r3_reproduction_review/final
```

For a single main-method interface replay, use another fresh directory in the recipe and insert the following immediately after loading `batch` (before writing its new manifest). It selects the first predeclared scene, not a hand-picked successful scene. This optional recipe is not executed as an extra experiment in R3.

```python
batch['jobs'] = [j for j in batch['jobs'] if j['variant']=='relay_m160'][:1]
batch['purpose'] = 'Single main-method replay from the frozen R3 configuration'
```

The actual final groups are `geom80`, `relay_m120`, `relay_m160` (main), `relay_m0` (only extra margin removed), and `r1_replan60`. Full expanded parameters are also in `configs/r3_methods.json`. The runner selects the implementation from each job's `planner_kind` and `config`; the inherited `suite.planner_config` and readout fields are inactive metadata for these geometry-only R3 jobs. Relay0 retains the original safety radii, the 100 m handoff, 80 m chord-risk setting and 500 m route lookahead.

The full frozen manifest contains every paired scene and complete configuration, so no test generator needs to be resampled. All methods use the same scene, field function, initial state, safety radii, mission limit and t-to-t+1 application schedule. Different paths may sample different local wind from the same field. No extra sensor/actuator noise is enabled. Numerical wall times depend on host load and are not a portable speed benchmark.

## Regenerate analysis and figures without physical rollouts

From the canonical project root, these commands read the archived complete records. They do not run the controller or advance a simulator. Use a different `--out` directory when comparing plot implementations.

```bash
OPENBLAS_NUM_THREADS=1 .venv/bin/python -B runs/r3_ccdc_20261003T121146Z/verify_final.py
OPENBLAS_NUM_THREADS=1 .venv/bin/python -B scripts/analyze_r3.py runs/r3_ccdc_20261003T121146Z/final
OPENBLAS_NUM_THREADS=1 .venv/bin/python -B scripts/plot_r3.py runs/r3_ccdc_20261003T121146Z/final --main relay_m160 --simple relay_m120 --out runs/r3_ccdc_20261003T121146Z/figures --stage frozen
OPENBLAS_NUM_THREADS=1 .venv/bin/python -B scripts/plot_r3.py runs/r3_ccdc_20261003T121146Z/final --main relay_m160 --simple relay_m120 --out runs/r3_ccdc_20261003T121146Z/figures --stage frozen --only-additions --case runs/r3_ccdc_20261003T121146Z/round1/case_r1_fixed60_regression032.json --case-name development_bypass_regression032
OPENBLAS_NUM_THREADS=1 .venv/bin/python -B scripts/plot_r3.py runs/r3_ccdc_20261003T121146Z/final --main relay_m160 --simple relay_m120 --out runs/r3_ccdc_20261003T121146Z/figures --stage frozen --only-additions --case runs/r3_ccdc_20261003T121146Z/round1/case_r1_replan60_rescue034.json --case-name development_timer_rescue034
```

The two intervention cases are explicitly seen-development diagnostics, not new-test evidence. `development_case_prefixes.json` contains the two verbatim paired trajectory prefixes through the first target application, with original source paths; their full recorded prefixes compare exactly equal. `development_case_clearance.json` records same-state chord calculations and the canonical-float32 clearance recheck. Their same-state reconstruction is produced by `scripts/r3_case_analysis.py`, which uses fresh planner instances and recorded inputs without simulating physical transitions. For example:

```bash
OPENBLAS_NUM_THREADS=1 .venv/bin/python -B scripts/r3_case_analysis.py runs/r3_ccdc_20261003T121146Z/round1 --variant r1_fixed60 --control geom80 --scene s1271_032_islands_fast_5000
```

The generic case output is `case_r1_fixed60.json`; the named archived case above retains the selected diagnostic. The ordinary trajectory panels display R1, Relay120 and Relay160. All five frozen methods appear in outcome/paired-statistics data. Dotted reference paths are offline initial A* routes with the **R1 80 m cap**, not the recorded executed path or Relay160's internal route.

## Publication status

The English manuscript is an editable content draft. A compatible project TeX compiler and the current official template were not available in the inspected environment; no compiled-PDF claim is made. The verified bibliography, source-access receipts and submission notes are included. Human authors must settle inherited-asset authorship/publication attribution and permissions, author list, affiliations and funding, then apply the current CCDC template and perform final PDF checks. No submission, publication, upload or push is performed by this study.

## Offline reading views

Markdown remains canonical. The local ARIS helper `C:/Users/74095/.codex/skills/render-html/scripts/render_html.py` renders selected report/draft/review artifacts with `--offline` (and `--lang en` for the English draft). The orchestrator uses no separate HTML-agent review; the final once-only research review and local render-fidelity checks are recorded separately. The views contain source hashes and use no CDN assets. The existing plotter generates the separate image gallery. No paper PDF has been compiled or checked.
