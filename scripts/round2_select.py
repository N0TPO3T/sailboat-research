"""Freeze both independently trained experts before creating confirmation scenes."""
import sys,json,hashlib,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from dynamic import *
RUN=ROOT/'runs/round2_20261011';seeds=[20261011,20261012]
assert all((RUN/f'train_{s}/complete.json').exists() for s in seeds), 'Wait for both independent runs'
assert not (RUN/'freeze.json').exists(), 'Already frozen'
receipts=[];initializations=[]
for seed in seeds:
    run=RUN/f'train_{seed}';complete=json.loads((run/'complete.json').read_text())
    assert complete['stopped_by']=='requested_steps' and complete['steps']>=40000
    initial=json.loads((run/'initialization.json').read_text());initializations.append(initial)
    assert initial['resume_source'] is None and initial['initial_steps']==0 and initial['initial_replay_size']==0
    assert initial['mask_expired_metadata'] and initial['roll_projected_velocity']
    dev=[json.loads(x) for x in (run/'development.jsonl').read_text().splitlines()]
    def score(e):return (sum(r['safe_complete'] for r in e['results']),-sum(r['time'] if r['safe_complete'] else 700 for r in e['results']),-e['steps'])
    selected=max(dev,key=score);source=run/f'step_{selected["steps"]}.pt'
    dest=ROOT/f'checkpoints/round2/{seed}'
    if dest.exists():raise RuntimeError('Refuse to replace a frozen expert')
    dest.mkdir(parents=True);shutil.copy2(source,dest/'resume.pt')
    ck=torch.load(source,weights_only=False,map_location='cpu')
    assert ck['training_protocol']['seed']==seed and ck['training_protocol']['handover_distribution']=='actual_routes'
    torch.save(ck['actor'],dest/'actor.pth');torch.save(ck['normalizer'],dest/'normalizer.pth')
    receipt=dict(train_seed=seed,source=str(source.relative_to(ROOT)),checkpoint=str((dest/'resume.pt').relative_to(ROOT)),
        steps=ck['steps'],updates=ck['updates'],actor_updates=ck['actor_updates'],
        score=score(selected),candidates=[dict(steps=d['steps'],score=score(d)) for d in dev],
        rule='safe count descending; sum(safe time else700) ascending; earliest step')
    receipt['sha256']=hashlib.sha256((dest/'resume.pt').read_bytes()).hexdigest()
    (dest/'selection.json').write_text(json.dumps(receipt,indent=2));receipts.append(receipt)
assert initializations[0]['actor_sha256']==initializations[1]['actor_sha256']
assert initializations[0]['critic_sha256']!=initializations[1]['critic_sha256']
freeze=dict(experts=receipts,config=CFG,initializations=initializations,
    dynamic_sha256=hashlib.sha256((ROOT/'src/dynamic.py').read_bytes()).hexdigest(),
    confirmation='not generated or evaluated at freeze time')
(RUN/'freeze.json').write_text(json.dumps(freeze,indent=2));print(json.dumps(receipts,indent=2))
