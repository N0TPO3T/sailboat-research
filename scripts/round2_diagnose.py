"""Read first-round traces, reconstruct causal sensor/router events, no rollouts."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from dynamic import *
from round2_metrics import paired
out=ROOT/'runs/round2_20261011/diagnosis';out.mkdir(parents=True,exist_ok=True)
old=ROOT/'runs/confirmation';rows=[json.loads(x) for x in (old/'episodes.jsonl').read_text().splitlines()]
pair=paired(rows);(out/'round1_pairs.json').write_text(json.dumps(pair,indent=2))
by={(r['seed'],r['mode']):r for r in rows}
groups={
 'expert_lost':[s for s in sorted({r['seed'] for r in rows}) if not by[s,'avoid']['safe_complete'] and all(by[s,m]['safe_complete'] for m in ('normal','range','risk'))],
 'range_lost':[s for s in sorted({r['seed'] for r in rows}) if not by[s,'range']['safe_complete'] and all(by[s,m]['safe_complete'] for m in ('avoid','risk'))],
 'both_routes_lost':[s for s in sorted({r['seed'] for r in rows}) if by[s,'avoid']['safe_complete'] and all(not by[s,m]['safe_complete'] for m in ('range','risk'))]}
assert list(map(len,groups.values()))==[2,2,1]
result={'groups':groups,'cases':[]}
for seed in sorted(sum(groups.values(),[])):
    case={'seed':seed,'kind':by[seed,'normal']['kind'],'methods':{}}
    for mode in ('normal','avoid','range','risk'):
        d=np.load(old/f'trajectories/{seed}_{mode}.npz');spec=json.loads(str(d['spec']))
        sensor=Sensor();router=Router(mode);events=[];details=[];prev=dict(visible=False,valid=False,danger=False,active=False)
        invalid_streak=0
        for i,raw in enumerate(d['raw']):
            m=sensor.observe(raw,i,d['target'][i],np.array(spec['target_velocity']))
            own=velocity(raw);goal=raw[12:14]-raw[:2];gv=goal/max(np.linalg.norm(goal),1e-8)*max(np.linalg.norm(own),1.)
            m.update(own_velocity=own,own_position=raw[:2],goal_velocity=gv)
            dist=float(np.linalg.norm(d['target'][i]-raw[:2]));cp=ret=None;danger=False
            if m['valid']:
                cp,tau=cpa(m['r'],m['v']);ret,_=cpa(m['r'],m['v']+own-gv)
                danger=min(np.linalg.norm(m['r']),cp,ret)<CFG['risk_distance']
            active=router.choose(m) if i<len(d['t'])-1 else None
            if active is not None:assert active==d['active'][i],(seed,mode,i)
            assert m['visible']==d['visible'][i] and m['valid']==d['valid'][i]
            flags=dict(visible=m['visible'],valid=m['valid'],danger=bool(danger),active=active)
            changes=[k+('+' if v else '-') for k,v in flags.items() if v is not None and v!=prev[k]]
            invalid_streak=0 if m['valid'] else invalid_streak+1
            item=dict(t=i,**flags,age=m['age'],distance=dist,dcpa=cp,return_dcpa=ret,
                heading=float(raw[3]),speed=float(np.linalg.norm(own)),position=raw[:2].tolist(),
                action=d['action'][i].tolist() if active is not None else None,
                setpoints=d['setpoints'][i].tolist(),all_window_dynamic_missing=bool(m['seen'] and invalid_streak>10))
            if changes or i==len(d['t'])-1:events.append(dict(changes=changes or ['terminal'],**item))
            details.append(item)
            if active is not None:prev=flags
        case['methods'][mode]=dict(result=by[seed,mode],events=events,
            completely_missing_steps=sum(x['all_window_dynamic_missing'] for x in details[:-1]),
            timeline_file=f'{seed}_{mode}.json')
        (out/f'{seed}_{mode}.json').write_text(json.dumps(details,indent=2))
    result['cases'].append(case)
(out/'key_cases.json').write_text(json.dumps(result,indent=2))
ck=torch.load(ROOT/'checkpoints/selected/resume.pt',weights_only=False,map_location='cpu')
(out/'historical_checkpoint.json').write_text(json.dumps(dict(steps=ck['steps'],updates=ck['updates'],
    actor_updates=ck['actor_updates'],mask=ck['normalizer'].get('mask_expired_metadata'),
    roll_projected_velocity=ck.get('roll_projected_velocity'),keys=list(ck)),indent=2))
print(json.dumps(groups))
for case in result['cases']:
    print(case['seed'],case['kind'])
    for mode,item in case['methods'].items():
        print(mode,item['result']['safe_complete'],item['result']['time'],[(e['t'],e['changes']) for e in item['events']], 'missing',item['completely_missing_steps'])
for key,item in pair.items():print(key,len(item['common_safe']),item['time']['delta_mean'],item['path_length']['delta_mean'])
