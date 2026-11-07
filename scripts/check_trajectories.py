"""Recompute submitted metrics from actual trajectories, including invisible truth."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from dynamic import *
import argparse
p=argparse.ArgumentParser();p.add_argument('run');args=p.parse_args()
run=ROOT/args.run
rows=[json.loads(line) for line in (run/'episodes.jsonl').read_text().splitlines()]
details=[]
wind_by_seed={}
for row in rows:
    data=np.load(run/f'trajectories/{row["seed"]}_{row["mode"]}.npz')
    raw=data['raw'];target=data['target'];t=data['t'];spec=json.loads(str(data['spec']))
    if 'initial_raw' in spec:
        np.testing.assert_array_equal(raw[0],spec['initial_raw'])
        np.testing.assert_array_equal(data['setpoints'][0],spec['initial_setpoints'])
    if 'wind' in data:
        if row['seed'] in wind_by_seed:
            other=wind_by_seed[row['seed']];length=min(len(other),len(t))
            assert np.array_equal(data['wind'][:length],other[:length]), 'Unmatched exogenous wind'
        else:wind_by_seed[row['seed']]=data['wind'].copy()
    assert np.array_equal(t,np.arange(len(t)))
    assert len(t)-1==row['time']
    assert bool(np.linalg.norm(raw[-1,:2]-raw[-1,12:14])<=10)==row['arrived']
    assert int(data['active'][:-1].sum())==row['takeover_seconds']
    if row['mode'] in ('range','risk'):
        assert int(np.count_nonzero(np.diff(np.r_[False,data['active'][:-1]])))==row['switches']
    if 'setpoints' in data:
        physical=data['action'][:-1].astype(float)*float(np.float32(np.pi/18))
        increments=(physical//(np.pi/180))*(np.pi/180)
        limits=np.array([np.pi/2,np.pi/6])
        expected=np.clip(data['setpoints'][:-1]+increments,-limits,limits)
        assert np.allclose(data['setpoints'][1:],expected,atol=1e-8), 'Actuator setpoints reset or changed outside executed command'
    dmin=float('inf');invisible_violations=0
    for i in range(len(t)-1):
        d=[swept_distance(np.array(p)-raw[i,:2],np.array(p)-raw[i+1,:2]) for p in spec['statics']]
        if spec['target_position'] is not None:
            dynamic_d=swept_distance(target[i]-raw[i,:2],target[i+1]-raw[i+1,:2])
            d.append(dynamic_d)
            invisible_violations+=int(dynamic_d<40 and not data['visible'][i])
        dmin=min(dmin,min(d,default=float('inf')))
    assert (row['min_distance'] is None and math.isinf(dmin)) or abs(row['min_distance']-dmin)<1e-5
    assert (dmin<40)==row['violated']
    length=float(np.linalg.norm(np.diff(raw[:,:2],axis=0),axis=1).sum())
    assert abs(length-row['path_length'])<.001
    if spec['target_position'] is not None:
        expected=np.array(spec['target_position'])+t[:,None]*np.array(spec['target_velocity'])
        assert np.allclose(target,expected,atol=1e-6)
        r=target-raw[:,:2]
        visible=(np.linalg.norm(r,axis=1)<=150)&(np.abs(np.arctan2(np.sin(np.arctan2(r[:,1],r[:,0])-raw[:,3]),np.cos(np.arctan2(r[:,1],r[:,0])-raw[:,3])))<=math.radians(60))
        assert np.array_equal(visible,data['visible'])
        seen=np.flatnonzero(visible)
        first=None if len(seen)==0 else dict(t=int(t[seen[0]]),distance=float(np.linalg.norm(r[seen[0]])))
        entries=int(np.sum(visible[1:]&~visible[:-1]))+int(visible[0])
    else:first=None;entries=0
    details.append(dict(seed=row['seed'],mode=row['mode'],first_observation=first,
                        visibility_entries=entries,reappeared=entries>1,invisible_violations=invisible_violations))
result=dict(episodes_checked=len(rows),all_metric_checks_passed=True,
            reappearance_episodes=sum(r['reappeared'] for r in details),
            invisible_violation_episodes=sum(r['invisible_violations']>0 for r in details),details=details,
            limit='Distance uses relative line segments at 1 s boundaries, not exact continuous ODE minimum')
(run/'trajectory_checks.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='details'},indent=2))
