import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];run=ROOT/'runs/round4_20261025';live=[]
for name in ('training_processes.json','training_v2_processes.json','confirmation50/processes.json'):
 for r in json.loads((run/name).read_text()):
  p=Path('/proc')/str(r['pid'])/'cmdline'
  if p.exists():
   cmd=p.read_bytes().replace(b'\0',b' ').decode(errors='replace')
   if str(ROOT) in cmd and any(s in cmd for s in ('train_round4.py','round2_evaluate.py')):live.append(dict(pid=r['pid'],command=cmd))
assert not live,live
print(json.dumps(dict(recorded_training_and_evaluation_jobs_stopped=True)))
