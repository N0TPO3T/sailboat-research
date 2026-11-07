"""Offline timelines for confirmation rescue/loss cases; never changes controls."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from dynamic import *
run=ROOT/'runs/round2_20261011/confirmation50'
all_cases={}
for train_seed in (20261011,20261012):
    folder=run/f'seed_{train_seed}';rows=[json.loads(l) for l in (folder/'episodes.jsonl').read_text().splitlines()]
    pairs=json.loads((folder/'pairs.json').read_text());ids=set()
    for key in ('avoid-minus-normal','risk-minus-avoid','risk-minus-range'):
        ids.update(pairs[key]['rescued']);ids.update(pairs[key]['lost'])
    cases={}
    for seed in sorted(ids):
        case={}
        for mode in ('normal','avoid','range','risk'):
            row=next(r for r in rows if r['seed']==seed and r['mode']==mode)
            data=np.load(folder/f'trajectories/{seed}_{mode}.npz');spec=json.loads(str(data['spec']))
            sensor=Sensor();previous=dict(visible=False,valid=False,danger=False,active=False);events=[];missing=0;blind_active=0
            for i in range(len(data['t'])):
                raw=data['raw'][i];m=sensor.observe(raw,i,None if spec['target_position'] is None else data['target'][i],np.array(spec['target_velocity']))
                own=velocity(raw);goal=raw[12:14]-raw[:2];gv=goal/max(np.linalg.norm(goal),1e-8)*max(np.linalg.norm(own),1.)
                danger=False
                if m['valid']:
                    dcpa,_=cpa(m['r'],m['v']);return_d,_=cpa(m['r'],m['v']+own-gv)
                    danger=min(np.linalg.norm(m['r']),dcpa,return_d)<CFG['risk_distance']
                current=dict(visible=m['visible'],valid=m['valid'],danger=bool(danger),active=bool(data['active'][i]) if i<len(data['t'])-1 else None)
                changed=[k+('+' if v else '-') for k,v in current.items() if v is not None and v!=previous[k]]
                missing=0 if m['valid'] else missing+1
                if current['active'] and m['seen'] and missing>10:blind_active+=1
                if changed or i==len(data['t'])-1:
                    events.append(dict(t=i,changes=changed or ['terminal'],age=m['age'],
                        actual_distance=None if spec['target_position'] is None else float(np.linalg.norm(data['target'][i]-raw[:2])),
                        completely_missing_window=bool(m['seen'] and missing>10),**current))
                if current['active'] is not None:previous=current
            case[mode]=dict(result=row,events=events,blind_active_steps=blind_active,
                observation_only='Chronology does not isolate causality; no confirmation-time branches or tuning')
        cases[str(seed)]=case
    (folder/'case_events.json').write_text(json.dumps(cases,indent=2));all_cases[str(train_seed)]=cases
(run/'case_events.json').write_text(json.dumps(all_cases,indent=2))
print(json.dumps({s:list(c) for s,c in all_cases.items()}))
