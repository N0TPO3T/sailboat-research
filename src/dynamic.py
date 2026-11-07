"""Minimal causal dynamic environment; truth stays in simulator/scoring."""
from pathlib import Path
import json
import math
import time
from collections import deque
import numpy as np
import torch
from sailboat_routing.runtime import SeniorModules, OriginalSegment
from sailboat_routing.obstacle_candidate import CandidateModules, ObstacleController, loading_paths

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT/'configs/prototype.json').read_text())
KINDS = ('none', 'away', 'late', 'cross', 'headon', 'edge_static')

def wrap(x):
    return math.atan2(math.sin(x), math.cos(x))

def body(v, heading):
    c, s = math.cos(heading), math.sin(heading)
    return np.array([c*v[0]+s*v[1], -s*v[0]+c*v[1]])

def velocity(raw):
    c, s = math.cos(raw[3]), math.sin(raw[3])
    lateral=raw[5]*math.cos(raw[2])
    return np.array([c*raw[4]-s*lateral, s*raw[4]+c*lateral])

def cpa(r, v, horizon=30):
    tau = float(np.clip(-np.dot(r,v)/max(np.dot(v,v),1e-8), 0, horizon))
    return float(np.linalg.norm(r+tau*v)), tau

def swept_distance(r0, r1):
    return cpa(np.asarray(r0), np.asarray(r1)-r0, 1)[0]

def scenario(seed, kind=None):
    rng = np.random.default_rng(seed)
    kind = kind or KINDS[int(rng.integers(len(KINDS)))]
    speed = float(rng.uniform(.5,1.5))
    x = float(rng.uniform(170,330))
    encounter = x/3.2 + float(rng.uniform(-9,9))
    if kind == 'none':
        pos, vel = None, [0.,0.]
    elif kind == 'away':
        pos, vel = [x, float(rng.uniform(105,145))], [speed*.5, speed*.866]
    elif kind == 'late':
        pos, vel = [x, -speed*(encounter+110)], [0.,speed]
    elif kind == 'headon':
        vel = [-speed, float(rng.uniform(-.15,.15))]
        pos = [x+speed*encounter, -vel[1]*encounter+float(rng.uniform(-18,18))]
    else:
        side = float(rng.choice([-1,1]))
        angle = float(rng.uniform(-.22,.22))
        vel = [speed*math.sin(angle), side*speed*math.cos(angle)]
        pos = [x-vel[0]*encounter, -vel[1]*encounter]
    return dict(seed=int(seed), kind=kind, target_position=pos, target_velocity=vel,
                wind=float(rng.choice([60,90,120,-60,-90,-120])),
                statics=[[370., float(rng.choice([-70,70]))]] if kind=='edge_static' else [])

def bank(split):
    n = CFG['test_count'] if split=='test' else CFG['dev_count']
    base = 910000 if split=='test' else 810000
    return [scenario(base+i, KINDS[i%len(KINDS)]) for i in range(n)]

class Sensor:
    def __init__(self):
        self.last = None
    def observe(self, raw, t, position, target_velocity):
        visible = False
        if position is not None:
            delta = position-raw[:2]
            visible = np.linalg.norm(delta)<=CFG['range'] and abs(wrap(math.atan2(delta[1],delta[0])-raw[3]))<=math.radians(CFG['fov_degrees']/2)
        if visible:
            self.last = (np.array(position,copy=True),np.array(target_velocity,copy=True),t)
        age = t-self.last[2] if self.last is not None else 999.
        valid = self.last is not None and age<=CFG['cache_seconds']
        # No inaccessible truth is used beyond this point.
        r = self.last[0]+self.last[1]*age-raw[:2] if valid else np.zeros(2)
        v = self.last[1]-velocity(raw) if valid else np.zeros(2)
        return dict(visible=bool(visible), valid=bool(valid), seen=self.last is not None,
                    age=float(age), r=r, v=v,
                    last_observed_position=None if self.last is None else self.last[0].copy())

class DynamicEnv:
    def __init__(self):
        self.segment=OriginalSegment(SeniorModules(),noise_enabled=False)
    def reset(self, spec):
        self.spec=spec
        self.raw=self.segment.reset(spec['seed'],spec['wind'])
        self.t=0
        self.sensor=Sensor()
        self.target=None if spec['target_position'] is None else np.array(spec['target_position'],dtype=float)
        self.target_v=np.array(spec['target_velocity'],dtype=float)
        assert np.linalg.norm(self.target_v)<=CFG['target_speed_bound']
        self.statics=[np.array(p,dtype=float) for p in spec['statics']]
        self.observed_statics={}
        self.min_distance=float('inf')
        self.violated=False
        self.path_length=0.
        self.last_meta=None
        return self.observe()
    def observe(self):
        m=self.sensor.observe(self.raw,self.t,self.target,self.target_v)
        slots=[]
        if m['valid']:
            slots.append((float(np.linalg.norm(m['r'])),wrap(math.atan2(m['r'][1],m['r'][0])-self.raw[3])))
        for index,p in enumerate(self.statics):
            r=p-self.raw[:2]
            angle=wrap(math.atan2(r[1],r[0])-self.raw[3])
            if np.linalg.norm(r)<=CFG['range'] and abs(angle)<=math.radians(60):
                self.observed_statics[index]=p.copy()
        # Static positions remain valid after discovery; never use this cache for moving targets.
        for p in self.observed_statics.values():
            r=p-self.raw[:2]
            if np.linalg.norm(r)<=CFG['range']:
                slots.append((float(np.linalg.norm(r)),wrap(math.atan2(r[1],r[0])-self.raw[3])))
        slots=sorted(slots)[:2]
        obs18=np.r_[self.raw, np.array((slots+[(0.,0.),(0.,0.)])[:2]).flatten()].astype(np.float32)
        extra=np.r_[body(m['r'],self.raw[3]),body(m['v'],self.raw[3]),float(m['visible']),min(m['age'],30) if m['seen'] else 0.,float(m['valid']),float(m['seen'])]
        obs26=np.r_[obs18,extra].astype(np.float32)
        # Router receives only causal sensor quantities, own velocity/goal geometry.
        m['own_velocity']=velocity(self.raw)
        m['own_position']=self.raw[:2].copy()
        goal=self.raw[12:14]-self.raw[:2]
        m['goal_velocity']=goal/max(np.linalg.norm(goal),1e-8)*max(np.linalg.norm(m['own_velocity']),1.)
        self.last_meta=m
        return obs18,obs26,m
    def step(self, action):
        before=self.raw.copy()
        old_target=None if self.target is None else self.target.copy()
        self.raw,base_reward,arrive,trunc,info=self.segment.step(action)
        self.t+=1
        self.path_length+=float(np.linalg.norm(self.raw[:2]-before[:2]))
        if self.target is not None:
            self.target=self.target+self.target_v
        distances=[swept_distance(p-before[:2],p-self.raw[:2]) for p in self.statics]
        if self.target is not None:
            distances.append(swept_distance(old_target-before[:2],self.target-self.raw[:2]))
        d=min(distances,default=float('inf'))
        self.min_distance=min(d,self.min_distance)
        violation=d<CFG['safe_distance']
        self.violated |= violation
        # Truth is permitted for reward and evaluation, never Actor/router input.
        reward=base_reward - 4.*max(0.,(80.-d)/40.)**2 - 120.*violation
        done=arrive or trunc or violation or self.t>=CFG['max_steps']
        info.update(arrived=bool(arrive),violated=bool(self.violated),distance=d,
                    min_distance=self.min_distance, time=self.t,path_length=self.path_length,
                    timeout=bool(self.t>=CFG['max_steps'] and not arrive and not violation), base_reward=base_reward,
                    original_terminated=bool(arrive),original_truncated=bool(trunc))
        return self.observe(),float(reward),bool(done),info

class Router:
    def __init__(self, mode):
        self.mode=mode; self.active=False; self.held=0; self.clear_count=0
        self.certified=False; self.switches=0
    def choose(self,m):
        if self.mode in ('normal','avoid'):
            return self.mode=='avoid'
        danger=False; clear=False
        if m['valid']:
            d=float(np.linalg.norm(m['r']))
            dcpa,_=cpa(m['r'],m['v'],CFG['horizon'])
            # Retargeting check uses current own speed along task direction,
            # not an unexecuted normal-policy command or simulated future truth.
            return_v=m['v']+m['own_velocity']-m['goal_velocity']
            return_d,_=cpa(m['r'],return_v,CFG['horizon'])
            danger=min(d,dcpa,return_d)<CFG['risk_distance']
            clear=(d>CFG['release_distance'] and np.dot(m['r'],m['v'])>0 and return_d>CFG['release_distance'])
        elif m.get('last_observed_position') is not None:
            # A set of possible positions, NOT an extrapolated current target.
            # Under the declared speed bound, all targets remain in this disk.
            sep=m['own_position']-m['last_observed_position']
            distance=float(np.linalg.norm(sep));bound=CFG['target_speed_bound']
            clearance=distance-bound*m['age']
            radial=sep/max(distance,1e-8)
            clear=(clearance>CFG['release_distance'] and
                   np.dot(radial,m['own_velocity'])>bound and
                   np.dot(radial,m['goal_velocity'])>bound)
        self.clear_count=self.clear_count+1 if clear else 0
        self.certified=self.clear_count>=CFG['release_steps']
        # Expiry alone is insufficient: only observed separation or a conservative
        # reachable-set clearance plus outward recovery direction permits release.
        enter=(m['visible'] or m['valid']) if self.mode=='range' else danger
        old=self.active
        if not self.active and enter:
            self.active=True; self.held=0
        elif self.active and self.held>=CFG['hold_steps'] and self.certified:
            if self.mode=='risk' or not m['valid']:
                self.active=False
        self.held=self.held+1 if self.active else 0
        self.switches+=int(old!=self.active)
        return self.active

class Window:
    """Exactly the same zero-initialized recurrent window in train and infer."""
    def __init__(self,initial):
        self.s=deque([initial.copy() for _ in range(CFG['window'])],maxlen=CFG['window'])
        self.a=deque([np.zeros(2,dtype=np.float32) for _ in range(CFG['window'])],maxlen=CFG['window'])
    def arrays(self):
        return np.array(self.s,dtype=np.float32),np.array(self.a,dtype=np.float32)
    def append(self,obs,executed):
        self.s.append(obs.copy()); self.a.append(executed.copy())

class FixedNormalizer:
    def __init__(self,state):
        self.state=state
    def normalize(self,x):
        result=(x-self.state['mean'])/(self.state['var'].sqrt()+1e-6)
        if self.state.get('mask_expired_metadata',False):
            # Policy/critic missing-slot representation. Router retains the real
            # age/seen metadata separately; this does not certify safety/release.
            result=result.clone()
            result[...,18:26]=result[...,18:26]*(x[...,24:25]>0)
        return result
    def update(self,*args):
        pass
    def state_dict(self):
        return self.state
    def load_state_dict(self,state):
        self.state=state

def make_expert(modules):
    actor=modules.network.Actor(26,2,(256,256)).cpu().eval()
    old=torch.load(loading_paths()['actor'],weights_only=True,map_location='cpu')
    new=actor.state_dict()
    for key in new:
        if new[key].shape==old[key].shape:
            new[key]=old[key].clone()
        elif key=='fc_input.0.weight':
            new[key].zero_(); new[key][:,:18]=old[key][:,:18]; new[key][:,26:]=old[key][:,18:]
        elif key=='current_state_fc.0.weight':
            new[key].zero_();new[key][:,:18]=old[key]
        else:
            raise ValueError('Unexpected incompatible key '+key)
    actor.load_state_dict(new)
    oldnorm=torch.load(loading_paths()['normalizer'],weights_only=True,map_location='cpu')
    norm=FixedNormalizer(dict(mean=torch.cat([oldnorm['mean'],torch.zeros(8)]),
        var=torch.cat([oldnorm['var'],torch.tensor([150.,150.,5.,5.,1.,30.,1.,1.])**2]),count=oldnorm['count']))
    return actor,norm

def constrain_dynamic_columns(actor):
    """Freeze inherited navigation mapping; optimize only eight new input columns."""
    actor.requires_grad_(False)
    for name in ('fc_input','current_state_fc'):
        weight=getattr(actor,name)[0].weight
        weight.requires_grad_(True)
        mask=torch.zeros_like(weight);mask[:,18:26]=1
        weight.register_hook(lambda grad,mask=mask:grad*mask)

def expert_action(actor,norm,window,current,deterministic=True):
    s,a=window.arrays()
    with torch.no_grad():
        result,_=actor(state_sequence=norm.normalize(torch.from_numpy(s[None])),
            action_sequence=torch.from_numpy(a[None]),current_state=norm.normalize(torch.from_numpy(current[None])),
            deterministic=deterministic,with_logprob=False,single_step_mode=False)
    return result[0].numpy().copy()

def run_episode(spec,mode,actor=None,norm=None,save=None):
    env=DynamicEnv(); o18,o26,m=env.reset(spec)
    normal=ObstacleController(mode='eval');normal.reset(o18)
    window=Window(o26);route=Router(mode)
    rows=[];reward_sum=0.;actor_seconds=0.;total=time.perf_counter();takes=0
    while True:
        started=time.perf_counter()
        selected=route.choose(m)
        # Normal memory is maintained on every step, using actual prior command.
        an=normal.act(o18).action
        aa=expert_action(actor,norm,window,o26) if mode!='normal' else an
        action=aa if selected else an
        actor_seconds+=time.perf_counter()-started
        rows.append(dict(t=env.t,raw=env.raw.copy(),target=np.full(2,np.nan) if env.target is None else env.target.copy(),
                         visible=m['visible'],age=m['age'],valid=m['valid'],active=selected,action=action.copy(),
                         setpoints=np.array([env.segment.env.target_sail_angle,env.segment.env.target_rudder_angle]),
                         wind=np.array([env.segment.modules.globals.w_change_v,env.segment.modules.globals.w_change_d])))
        (n18,n26,nm),reward,done,info=env.step(action)
        normal.previous_action=action.copy()
        window.append(o26,action)
        takes+=int(selected);reward_sum+=reward
        o18,o26,m=n18,n26,nm
        if done:break
    rows.append(dict(t=env.t,raw=env.raw.copy(),target=np.full(2,np.nan) if env.target is None else env.target.copy(),
                     visible=m['visible'],age=m['age'],valid=m['valid'],active=False,action=np.zeros(2),
                     setpoints=np.array([env.segment.env.target_sail_angle,env.segment.env.target_rudder_angle]),
                     wind=np.array([env.segment.modules.globals.w_change_v,env.segment.modules.globals.w_change_d])))
    result=dict(seed=spec['seed'],kind=spec['kind'],mode=mode,arrived=info['arrived'],
                safe_complete=info['arrived'] and not info['violated'],violated=info['violated'],
                min_distance=None if math.isinf(env.min_distance) else env.min_distance,
                time=env.t,path_length=env.path_length,switches=route.switches,takeover_seconds=takes,
                original_terminated=info['original_terminated'],original_truncated=info['original_truncated'],
                termination_reason=('safety_violation' if info['violated'] else 'arrival' if info['arrived'] else
                    'boundary' if np.linalg.norm(env.raw[:2])>=750 else 'time_limit' if env.t>=CFG['max_steps'] else 'other_truncation'),
                decision_seconds=actor_seconds,wall_seconds=time.perf_counter()-total,reward=reward_sum)
    if save:
        save=Path(save);save.parent.mkdir(parents=True,exist_ok=True)
        np.savez_compressed(save,**{key:np.array([r[key] for r in rows]) for key in rows[0]},spec=json.dumps(spec))
    normal.close();env.segment.close()
    return result
