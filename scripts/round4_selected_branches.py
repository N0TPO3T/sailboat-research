"""Four predeclared states, frozen final selected expert; post-selection diagnostic only."""
import sys,json,hashlib,pickle
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from dynamic import *
OUT=ROOT/'runs/round4_20261025/diagnosis/selected_branches';OUT.mkdir(parents=True,exist_ok=True)
jobs=[(ts,seed,'range',cut,m) for ts,seed,cut in [(20261011,920033,72),(20261011,920038,50),(20261012,920046,58),(20261011,920040,43)] for m in ('trained',)]
protocol=dict(jobs=jobs,choice='three second-round losses and one beneficial combination; first actual range takeover only',
    continuation='forced selected policy through terminal; trained/initial mean expert always after branch, no handback',
    restoration='replay identical executed prefix from reset; run own normal memory and expert window with actual commands; no cross-network hidden copy')
if (OUT/'results.jsonl').exists():raise RuntimeError('Branches already exist')
(OUT/'protocol.json').write_text(json.dumps(protocol,indent=2))
mods=CandidateModules();trained,norm=make_expert(mods)
initial,unused=make_expert(mods);fingerprints={}
for train_seed,seed,prefix_mode,cut,continuation in jobs:
    ck=torch.load(ROOT/next(e['checkpoint'] for e in json.loads((ROOT/'runs/round4_20261025/freeze.json').read_text())['experts'] if e['train_seed']==train_seed),weights_only=False,map_location='cpu');trained.load_state_dict(ck['actor']);norm.load_state_dict(ck['normalizer'])
    old=np.load(ROOT/f'runs/round2_20261011/confirmation50/seed_{train_seed}/trajectories/{seed}_{prefix_mode}.npz');spec=json.loads(str(old['spec']))
    env=DynamicEnv();o18,o26,m=env.reset(spec);normal=ObstacleController(mods,mode='eval');normal.reset(o18)
    window=Window(o26);route=Router(prefix_mode);rows=[];takes=0;switches=0;previous=False;fingerprint=None
    while True:
        routed=route.choose(m)
        if env.t<=cut:
            np.testing.assert_array_equal(env.raw,old['raw'][env.t])
            np.testing.assert_allclose([env.segment.env.target_sail_angle,env.segment.env.target_rudder_angle],old['setpoints'][env.t],rtol=0,atol=0)
            np.testing.assert_array_equal([env.segment.modules.globals.w_change_v,env.segment.modules.globals.w_change_d],old['wind'][env.t])
        if env.t==cut:
            assert routed and not bool(old['active'][cut-1]) and bool(old['active'][cut])
            state=dict(raw=env.raw,sets=old['setpoints'][cut],target=env.target,t=env.t,
                normal_history=normal.history(),previous_obs=normal.previous,previous_action=normal.previous_action,
                window=window.arrays(),sensor_last=env.sensor.last,route=route.__dict__.copy(),
                observed_statics=env.observed_statics,o18=o18,o26=o26,meta=m,
                path_length=env.path_length,min_distance=env.min_distance,violated=env.violated,
                py=env.segment.random_state,np=env.segment.numpy_state,wind=old['wind'][cut])
            fingerprint=hashlib.sha256(pickle.dumps(state)).hexdigest()
            key=(train_seed,seed,prefix_mode,cut)
            if key in fingerprints:assert fingerprint==fingerprints[key]
            fingerprints[key]=fingerprint
            torch.save(state,OUT/f'{train_seed}_{seed}_{cut}_{continuation}_branch_state.pt')
        an=normal.act(o18).action;at=expert_action(trained,norm,window,o26);ai=expert_action(initial,norm,window,o26)
        if env.t<cut:np.testing.assert_array_equal(an,old['action'][env.t].astype(np.float32))
        if env.t==cut:
            branch_input=dict(position=env.raw[:2].tolist(),heading_deg=math.degrees(env.raw[3]),
                own_velocity=velocity(env.raw).tolist(),distance=float(np.linalg.norm(m['r'])),
                target_relative=m['r'].tolist(),original_slots=o18[14:18].tolist(),
                setpoints=old['setpoints'][cut].tolist(),normal_action=an.tolist(),trained_action=at.tolist(),w0_action=ai.tolist())
        if env.t<cut:command=old['action'][env.t].astype(np.float32);active=bool(old['active'][env.t])
        else:command={'trained':at,'normal':an,'initial':ai}[continuation];active=continuation!='normal'
        switches+=int(active!=previous);previous=active;takes+=int(active)
        rows.append(dict(t=env.t,raw=env.raw.copy(),target=env.target.copy(),visible=m['visible'],valid=m['valid'],age=m['age'],
            active=active,action=command.copy(),normal_action=an,trained_action=at,initial_action=ai,
            setpoints=np.array([env.segment.env.target_sail_angle,env.segment.env.target_rudder_angle])))
        (n18,n26,nm),reward,done,info=env.step(command);normal.previous_action=command.copy();window.append(o26,command)
        o18,o26,m=n18,n26,nm
        if done:break
    rows.append(dict(rows[-1],t=env.t,raw=env.raw.copy(),target=env.target.copy(),visible=m['visible'],valid=m['valid'],age=m['age'],active=False,action=np.zeros(2),
        setpoints=np.array([env.segment.env.target_sail_angle,env.segment.env.target_rudder_angle]),
        normal_action=np.full(2,np.nan),trained_action=np.full(2,np.nan),initial_action=np.full(2,np.nan)))
    filename=f'{train_seed}_{seed}_{cut}_{continuation}'
    np.savez_compressed(OUT/f'{filename}.npz',**{k:np.array([r[k] for r in rows]) for k in rows[0]},spec=json.dumps(spec))
    result=dict(train_seed=train_seed,seed=seed,prefix_mode=prefix_mode,cut=cut,continuation=continuation,fingerprint=fingerprint,branch_input=branch_input,
        safe_complete=info['arrived'] and not info['violated'],arrived=info['arrived'],violated=info['violated'],
        time=env.t,min_distance=env.min_distance,path_length=env.path_length,file=filename)
    with (OUT/'results.jsonl').open('a') as f:f.write(json.dumps(result)+'\n')
    print(json.dumps(result),flush=True);normal.close();env.segment.close()

