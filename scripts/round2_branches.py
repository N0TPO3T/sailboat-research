"""Seven predeclared complete branches; recreate entire identical real prefix."""
import sys,json,hashlib,pickle
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from dynamic import *
OUT=ROOT/'runs/round2_20261011/diagnosis/branches';OUT.mkdir(parents=True,exist_ok=True)
jobs=[(910009,'risk',86,m) for m in ('trained','normal','initial')]+[(910009,'risk',102,m) for m in ('trained','normal')]+[(910010,'risk',90,m) for m in ('trained','initial')]
protocol=dict(jobs=jobs,choice='first actual takeover for cross/headon; first cache expiry on actual cross route',
    continuation='forced selected policy through terminal; trained/initial mean expert always after branch, no handback',
    restoration='replay identical executed prefix from reset; run own normal memory and expert window with actual commands; no cross-network hidden copy')
if (OUT/'results.jsonl').exists():raise RuntimeError('Branches already exist')
(OUT/'protocol.json').write_text(json.dumps(protocol,indent=2))
mods=CandidateModules();trained,norm=make_expert(mods)
ck=torch.load(ROOT/'checkpoints/selected/resume.pt',weights_only=False,map_location='cpu');trained.load_state_dict(ck['actor']);norm.load_state_dict(ck['normalizer'])
initial,unused=make_expert(mods);fingerprints={}
for seed,prefix_mode,cut,continuation in jobs:
    old=np.load(ROOT/f'runs/confirmation/trajectories/{seed}_{prefix_mode}.npz');spec=json.loads(str(old['spec']))
    env=DynamicEnv();o18,o26,m=env.reset(spec);normal=ObstacleController(mods,mode='eval');normal.reset(o18)
    window=Window(o26);route=Router(prefix_mode);rows=[];takes=0;switches=0;previous=False;fingerprint=None
    while True:
        routed=route.choose(m)
        if env.t<=cut:
            np.testing.assert_array_equal(env.raw,old['raw'][env.t])
            np.testing.assert_allclose([env.segment.env.target_sail_angle,env.segment.env.target_rudder_angle],old['setpoints'][env.t],rtol=0,atol=0)
            np.testing.assert_array_equal([env.segment.modules.globals.w_change_v,env.segment.modules.globals.w_change_d],old['wind'][env.t])
        if env.t==cut:
            state=dict(raw=env.raw,sets=old['setpoints'][cut],target=env.target,t=env.t,
                normal_history=normal.history(),previous_obs=normal.previous,previous_action=normal.previous_action,
                window=window.arrays(),sensor_last=env.sensor.last,route=route.__dict__.copy(),
                py=env.segment.random_state,np=env.segment.numpy_state,wind=old['wind'][cut])
            fingerprint=hashlib.sha256(pickle.dumps(state)).hexdigest()
            key=(seed,prefix_mode,cut)
            if key in fingerprints:assert fingerprint==fingerprints[key]
            fingerprints[key]=fingerprint
            torch.save(state,OUT/f'{seed}_{cut}_{continuation}_branch_state.pt')
        an=normal.act(o18).action;at=expert_action(trained,norm,window,o26);ai=expert_action(initial,norm,window,o26)
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
    filename=f'{seed}_{cut}_{continuation}'
    np.savez_compressed(OUT/f'{filename}.npz',**{k:np.array([r[k] for r in rows]) for k in rows[0]},spec=json.dumps(spec))
    result=dict(seed=seed,prefix_mode=prefix_mode,cut=cut,continuation=continuation,fingerprint=fingerprint,
        safe_complete=info['arrived'] and not info['violated'],arrived=info['arrived'],violated=info['violated'],
        time=env.t,min_distance=env.min_distance,path_length=env.path_length,file=filename)
    with (OUT/'results.jsonl').open('a') as f:f.write(json.dumps(result)+'\n')
    print(json.dumps(result),flush=True);normal.close();env.segment.close()
