"""Select only from fixed development evaluations; final test never read."""
from pathlib import Path
import json
import argparse
import shutil
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--run',default='runs/train_columns');args=p.parse_args()
run=ROOT/args.run
evaluations=[json.loads(l) for l in (run/'development.jsonl').read_text().splitlines()]
def key(row):
    rr=row['results']
    return (sum(r['safe_complete'] for r in rr),-sum(r['time'] if r['safe_complete'] else 700 for r in rr),-row['steps'])
selected=max(evaluations,key=key)
dest=ROOT/'checkpoints/selected';dest.mkdir(parents=True,exist_ok=True)
source=run/f'step_{selected["steps"]}.pt'
if (dest/'resume.pt').exists():raise RuntimeError('Selected checkpoint already frozen; use explicit new protocol to replace')
shutil.copy2(source,dest/'resume.pt')
import sys
sys.path.insert(0,str(ROOT/'src'))
from dynamic import torch
ck=torch.load(source,weights_only=False,map_location='cpu')
torch.save(ck['actor'],dest/'actor.pth');torch.save(ck['normalizer'],dest/'normalizer.pth')
receipt=dict(source=str(source.relative_to(ROOT)),steps=selected['steps'],actor_updates=ck['actor_updates'],
             rule='maximize development safe-completion count; then minimize sum(time for safe, 700 for failure); then earliest step',
             all_candidates=[dict(steps=r['steps'],score=key(r)) for r in evaluations])
(dest/'selection.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))
