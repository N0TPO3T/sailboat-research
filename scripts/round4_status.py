import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];run=ROOT/'runs/round4_20261025'
for folder in sorted(run.glob('train_v2_*')):
 if not folder.is_dir():continue
 def read(name):
  p=folder/name
  if not p.exists():return []
  return [json.loads(x) for x in p.read_text().splitlines()]
 learning=read('learning.jsonl');dev=read('development.jsonl')
 r=learning[-1] if learning else {}
 print(json.dumps(dict(run=folder.name,steps=r.get('steps',0),updates=r.get('updates',0),actor_updates=r.get('actor_updates',0),wall=r.get('wall_seconds',0),completed=(folder/'complete.json').exists(),extra_replay=sum(x['extra_replay'] for x in learning),dev=[dict(step=d['steps'],penalized_seconds=sum(x['time'] if x['safe_complete'] else 700 for x in d['results']),counts={m:sum(x['safe_complete'] for x in d['results'] if x['mode']==m) for m in ('avoid','range')}) for d in dev])))
 # Enforces same physical-step warmup/update schedule, independent of duplicate entries.
 for e in learning:assert e['updates']==max(0,e['steps']//4-63),(folder.name,e['steps'],e['updates'])

