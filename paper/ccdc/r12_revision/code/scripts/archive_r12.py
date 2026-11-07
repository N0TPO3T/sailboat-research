"""Archive this run and exact historical input traces; never rewrite inputs."""
from pathlib import Path
import json,csv,tarfile,hashlib
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'runs/r12_revision_20261006'
assert (R/'verification.json').exists()
paths=set(row['source'] for row in csv.DictReader((R/'prediction_windows.csv').open()))
for sid in json.loads((R/'guard.json').read_text())['scene_ids']:
 for v in ['reactive','sampled']:
  paths.add(f'runs/r8_closedloop_20261005T062543Z/confirmation/{sid}__{v}/trace.json')
manifest={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(paths)}
(R/'historical_input_hashes.json').write_text(json.dumps(manifest,indent=2))
out=ROOT/'runs/R12_raw_results_20261006.tar.gz'
assert not out.exists(),'Preserve prior archive'
with tarfile.open(out,'w:gz',compresslevel=5) as tar:
 tar.add(R,arcname=str(R.relative_to(ROOT)))
 for p in sorted(paths):tar.add(ROOT/p,arcname=p)
print(out,out.stat().st_size,hashlib.sha256(out.read_bytes()).hexdigest())
