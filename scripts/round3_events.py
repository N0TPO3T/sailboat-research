"""Offline chronology of every final-range safety trade, without new rollouts."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from round3_policy import *
root=ROOT/'runs/round3_20261011_2308/confirmation50'
for train_seed in (20261011,20261012):
    folder=root/f'seed_{train_seed}';rows=[json.loads(l) for l in (folder/'episodes.jsonl').read_text().splitlines()]
    pairs=json.loads((folder/'pairs.json').read_text());ids=set()
    for key in ('final_range-minus-final_avoid','final_range-minus-old_range','final_range-minus-guard_old_range','final_avoid-minus-w0'):
        ids.update(pairs[key]['rescued']);ids.update(pairs[key]['lost'])
    cases={}
    for seed in sorted(ids):
        case={}
        for mode in ('normal','w0','old_avoid','old_range','guard_old_range','final_avoid','final_range'):
            row=next(r for r in rows if r['seed']==seed and r['mode']==mode)
            data=np.load(folder/f'trajectories/{seed}_{mode}.npz');spec=json.loads(str(data['spec']))
            sensor=Sensor();previous=dict(visible=False,valid=False,active=False);events=[];missing=0;blind_active=0;guard_steps=0
            for i in range(len(data['t'])):
                raw=data['raw'][i];m=sensor.observe(raw,i,None if spec['target_position'] is None else data['target'][i],np.array(spec['target_velocity']))
                current=dict(visible=m['visible'],valid=m['valid'],active=bool(data['active'][i]) if i<len(data['t'])-1 else None)
                changed=[k+('+' if v else '-') for k,v in current.items() if v is not None and v!=previous[k]]
                missing=0 if m['valid'] else missing+1
                if current['active'] and m['seen'] and missing>10:blind_active+=1
                # The online adapter uses this same legal world target velocity.
                guard=False
                if m['valid']:
                    vt=m['v']+velocity(raw);g=raw[12:14]
                    guard=bool(np.dot(vt,g)/(max(np.linalg.norm(vt),1e-6)*max(np.linalg.norm(g),1e-6))<-.7)
                if current['active'] and guard:guard_steps+=1
                if changed or i==len(data['t'])-1:
                    events.append(dict(t=i,changes=changed or ['terminal'],age=m['age'],
                        actual_distance=None if spec['target_position'] is None else float(np.linalg.norm(data['target'][i]-raw[:2])),
                        completely_missing_window=bool(m['seen'] and missing>10),guard_condition=guard,**current))
                if current['active'] is not None:previous=current
            case[mode]=dict(result=row,events=events,blind_active_steps=blind_active,guard_condition_active_steps=guard_steps,
                observation_only='Chronology is not a single-factor causal test; no confirmation-time branches or tuning')
        cases[str(seed)]=case
    (folder/'case_events.json').write_text(json.dumps(cases,indent=2))
    equivalence={}
    for a,b in (('w0','final_avoid'),('old_range','guard_old_range'),('guard_old_range','final_range')):
        eq={k:dict(n=0,identical=0) for k in KINDS}
        for r in [r for r in rows if r['mode']==a]:
            da=np.load(folder/f'trajectories/{r["seed"]}_{a}.npz');db=np.load(folder/f'trajectories/{r["seed"]}_{b}.npz')
            eq[r['kind']]['n']+=1;eq[r['kind']]['identical']+=int(all(np.array_equal(da[k],db[k]) for k in ('raw','action','active')))
        equivalence[f'{b}-vs-{a}']=eq
    (folder/'functional_equivalence.json').write_text(json.dumps(equivalence,indent=2));print(train_seed,len(cases))
