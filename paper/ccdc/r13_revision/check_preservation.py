from pathlib import Path
import json,hashlib
r=Path.cwd();o=r/'paper/ccdc/r13_revision';f=json.loads((r/'runs/r12_revision_20261006/freeze.json').read_text());checks={n:hashlib.sha256((r/n).read_bytes()).hexdigest()==h for n,h in f['sources'].items()};assert all(checks.values())
old=json.loads((r/'runs/r12_revision_20261006/original_hashes.json').read_text());protected={n:hashlib.sha256((r/n).read_bytes()).hexdigest()==h for n,h in old.items()};assert all(protected.values())
(o/'evidence/r13_preservation_check.json').write_text(json.dumps(dict(r12_frozen_sources_unchanged=checks,old_assets_unchanged=protected,new_methods=False,new_independent_tasks=0,numerical_replays=3,gpu_hours=0,max_concurrent_experiment_workers=1),indent=2));print('Frozen scientific sources and original protected assets unchanged:',len(checks),len(protected))
