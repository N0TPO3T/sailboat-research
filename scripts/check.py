import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from dynamic import *

raw=np.zeros(14);raw[4]=3
rolled=raw.copy();rolled[2]=math.pi/3;rolled[5]=2
assert np.allclose(velocity(rolled),[3,1]), 'Planar velocity must match 4DOF roll projection'
s=Sensor()
m=s.observe(raw,0,np.array([100.,0.]),np.array([0.,1.]))
assert m['visible'] and m['valid']
raw[3]=math.pi
m1=s.observe(raw,2,np.array([999.,999.]),np.array([99.,99.]))
m2=s.observe(raw,2,np.array([-999.,999.]),np.array([-99.,99.]))
assert np.array_equal(m1['r'],m2['r']) and np.array_equal(m1['v'],m2['v'])
assert np.array_equal(m1['r'],[100.,2.]) and m1['age']==2 and not m1['visible']
m=s.observe(raw,6,np.array([999.,999.]),np.array([99.,99.]))
assert not m['valid'] and np.array_equal(m['r'],[0,0]) and m['seen']
r=Router('range');r.active=True
m.update(visible=False,valid=False,own_position=raw[:2].copy(),own_velocity=velocity(raw),goal_velocity=np.array([3.,0.]))
for _ in range(20):assert r.choose(m), 'Expiration incorrectly released'
r=Router('range');r.active=True;r.held=10;r.clear_count=3
clear=dict(visible=False,valid=True,seen=True,age=2,r=np.array([-100.,0.]),v=np.array([-2.,0.]),
           own_velocity=np.array([3.,0.]),goal_velocity=np.array([3.,0.]),
           own_position=np.array([200.,0.]),last_observed_position=np.array([100.,0.]))
assert r.choose(clear), 'Range returned while valid cache would immediately re-enter'
clear['valid']=False;clear['age']=6
assert not r.choose(clear), 'Stored separation certificate should permit release after cache ends'
r=Router('range');r.active=True;r.held=10
uncertain=dict(clear,age=50)
for _ in range(6):assert r.choose(uncertain), 'Large possible-position disk must prevent release'
assert swept_distance(np.array([50.,0]),np.array([-50.,0]))==0
env=DynamicEnv();spec=scenario(810000,'none');spec['statics']=[[100.,0.]]
env.reset(spec);env.raw[:2]=0;env.raw[3]=0
o18,o26,_=env.observe()
assert o18[14]==100 and np.all(o26[18:]==0)
env.raw[3]=math.pi
o18,_,_=env.observe()
assert o18[14]==100, 'Known static landmark must not disappear with heading'
env.segment.close()
mods=CandidateModules();actor,norm=make_expert(mods)
masked=FixedNormalizer(dict(norm.state_dict(),mask_expired_metadata=True))
example=torch.zeros(26);example[23]=20;example[25]=1
assert torch.equal(masked.normalize(example)[18:],torch.zeros(8)) and example[23]==20
example[24]=1;example[23]=2
assert masked.normalize(example)[23]>0
normal=ObstacleController(mods,mode='eval')
o=np.arange(18,dtype=np.float32);expanded=np.r_[o,np.zeros(8)].astype(np.float32)
window=Window(expanded)
with torch.no_grad():
    ss,aa=window.arrays()
    old,_=normal.actor(state_sequence=normal.normalizer.normalize(torch.tensor(ss[None,:,:18])),
        action_sequence=torch.tensor(aa[None]),current_state=normal.normalizer.normalize(torch.tensor(o[None])),deterministic=True)
new=expert_action(actor,norm,window,expanded)
assert np.allclose(old.numpy()[0],new,atol=1e-6), 'Warmstart changed compatible function'
window.append(expanded,np.array([.2,-.3],dtype=np.float32))
assert np.allclose(window.arrays()[1][-1],[.2,-.3])
for mode in ('normal','avoid','range','risk'):
    result=run_episode(scenario(810000,'none'),mode,actor,norm,ROOT/f'runs/check/{mode}.npz')
    assert math.isfinite(result['reward'])
    print(result,flush=True)
print('PASS: visibility/cache, expired hold, swept crossing, warmstart equivalence, actual-action window and four physical loops')
