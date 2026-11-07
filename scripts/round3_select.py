"""Freeze the two new runs plus strong non-retraining controls before new50."""
import sys,json,hashlib,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from round3_policy import *
run=ROOT/'runs/round3_20261011_2308';seeds=(20261011,20261012)
assert all((run/f'train_{s}/complete.json').exists() for s in seeds)
assert not (run/'freeze.json').exists()
old=json.loads((ROOT/'runs/round2_20261011/freeze.json').read_text());experts=[];initials=[]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for seed in seeds:
    folder=run/f'train_{seed}';c=json.loads((folder/'complete.json').read_text());assert c['steps']>=40000 and c['stopped_by']=='requested_steps'
    init=json.loads((folder/'initialization.json').read_text());initials.append(init)
    assert init['resume_source'] is None and init['initial_steps']==0 and init['initial_replay_size']==0
    dev=[json.loads(x) for x in (folder/'development.jsonl').read_text().splitlines()]
    def score(d):return (sum(r['safe_complete'] for r in d['results']),-sum(r['time'] if r['safe_complete'] else 700 for r in d['results']),-d['steps'])
    selected=max(dev,key=score);source=folder/f'step_{selected["steps"]}.pt';dest=ROOT/f'checkpoints/round3/{seed}'
    assert not dest.exists();dest.mkdir();shutil.copy2(source,dest/'resume.pt')
    ck=torch.load(source,weights_only=False,map_location='cpu');assert ck['normalizer']['adaptation']=='headon_guard'
    assert ck['training_protocol']==dict(seed=seed,scene_base=720000 if seed==20261011 else 730000,handover_distribution='actual_routes',adaptation='headon_guard')
    for key in ('actor','normalizer'):torch.save(ck[key],dest/f'{key}.pth')
    olde=next(e for e in old['experts'] if e['train_seed']==seed);assert sha(ROOT/olde['checkpoint'])==olde['sha256']
    control=ROOT/f'checkpoints/round3/guard_on_round2_{seed}';assert not control.exists();control.mkdir()
    shutil.copy2(run/f'screen/{seed}_headon_guard.pt',control/'actor_only.pt')
    receipt=dict(train_seed=seed,checkpoint=str((dest/'resume.pt').relative_to(ROOT)),sha256=sha(dest/'resume.pt'),
        steps=ck['steps'],updates=ck['updates'],actor_updates=ck['actor_updates'],source=str(source.relative_to(ROOT)),
        score=score(selected),candidates=[dict(steps=d['steps'],score=score(d)) for d in dev],
        old_checkpoint=olde['checkpoint'],old_sha256=olde['sha256'],old_steps=olde['steps'],
        guard_old_checkpoint=str((control/'actor_only.pt').relative_to(ROOT)),guard_old_sha256=sha(control/'actor_only.pt'))
    (dest/'selection.json').write_text(json.dumps(receipt,indent=2));experts.append(receipt)
assert initials[0]['actor_sha256']==initials[1]['actor_sha256'] and initials[0]['critic_sha256']!=initials[1]['critic_sha256']
w0=torch.load(ROOT/'checkpoints/round3/w0/actor_init.pt',weights_only=False,map_location='cpu')
w0['normalizer']['adaptation']='headon_guard';torch.save(w0,ROOT/'checkpoints/round3/w0/final_interface.pt')
freeze=dict(experts=experts,initializations=initials,config=CFG,w0='checkpoints/round3/w0/final_interface.pt',
    w0_sha256=sha(ROOT/'checkpoints/round3/w0/final_interface.pt'),
    sources={f:sha(ROOT/f) for f in ('src/dynamic.py','src/round3_policy.py','scripts/train_round3.py','scripts/round3_evaluate.py')},
    confirmation='not generated or evaluated at freeze',matrix='2 common + 5 per training seed = 12 x 50 = 600')
(run/'freeze.json').write_text(json.dumps(freeze,indent=2));print(json.dumps(experts,indent=2))
