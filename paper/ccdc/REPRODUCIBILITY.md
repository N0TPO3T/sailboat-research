# Reproducing the R3 study

The canonical runtime is `/home/ot/Students/hs/sailboat-routing-v0` with its existing `.venv/bin/python`. The preview does not contain inherited weights, an environment, or a license grant for those assets. Reuse the verified project installation and check `docs/UPSTREAM_MANIFEST.md`; the actor is chapter4 14D @7200, not final @9000. Scientific source identity is stored in each batch `provenance.json`; final method/configuration and generator selection will be recorded in the frozen manifest.

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

The full frozen manifest contains every paired scene and complete configuration, so no test generator needs to be resampled. All methods use the same scene, field function, initial state, safety radii, mission limit and t-to-t+1 application schedule. Different paths may sample different local wind from the same field. No extra sensor/actuator noise is enabled. Numerical wall times depend on host load and are not a portable speed benchmark.

## Publication status

The English manuscript is an editable content draft. A compatible project TeX compiler and the current official template were not available in the inspected environment; no compiled-PDF claim is made. The verified bibliography, source-access receipts and submission notes are included. Human authors must settle inherited-asset authorship/publication attribution and permissions, author list, affiliations and funding, then apply the current CCDC template and perform final PDF checks. No submission, publication, upload or push is performed by this study.
