"""Targeted deterministic checks for the new takeover-state sampling contract."""
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from dynamic import *
root=ROOT/'runs/round2_20261011'
assert hashlib.sha256((ROOT/'checkpoints/selected/resume.pt').read_bytes()).hexdigest()=='057773e12565567290a0174cc73551ab442db79d506d4717047a461cc5df4b48'
mods=CandidateModules();actor,norm=make_expert(mods);norm.state['mask_expired_metadata']=True
records=[]
for seed,mode in ((910009,'range'),(910009,'risk'),(910014,'risk')):
    data=np.load(ROOT/f'runs/confirmation/trajectories/{seed}_{mode}.npz');spec=json.loads(str(data['spec']))
    env=DynamicEnv();o18,o26,m=env.reset(spec);normal=ObstacleController(mods,mode='eval');normal.reset(o18)
    window=Window(o26);router=Router(mode);entered=None
    while True:
        np.testing.assert_array_equal(env.raw,data['raw'][env.t])
        take=router.choose(m);an=normal.act(o18).action
        if not m['valid']:assert not norm.normalize(torch.from_numpy(o26))[18:].any()
        if take:entered=env.t;break
        np.testing.assert_array_equal(an,data['action'][env.t].astype(np.float32))
        (n18,n26,nm),reward,done,info=env.step(an)
        normal.previous_action=an.copy();window.append(o26,an)
        o18,o26,m=n18,n26,nm
        if done:break
    records.append(dict(seed=seed,mode=mode,first_takeover=entered,normal_prefix=env.t))
    if seed==910009:assert entered==86 and entered>45
    else:assert entered is None
    normal.close();env.segment.close()
assert [ ('avoid','range','risk')[i%3] for i in range(6)]==['avoid','range','risk']*2
(root/'targeted_checks.json').write_text(json.dumps(dict(passed=True,records=records,
    checked=['round1 checkpoint unchanged','real normal prefix beyond legacy45s','validity mask remains from step0','risk can legitimately never activate']),indent=2))
print(json.dumps(records))
