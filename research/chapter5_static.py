"""Static-only baseline recovery: frozen scenarios, explicit protocols and evaluation.

Actor/Critic/SAC remain the chapter-5 reference implementation. Never interpret
legacy weights under the aligned protocol without an explicit diagnostic request.
"""
import argparse
import ast
import contextlib
import copy
import csv
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import time
from collections import deque

os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
if sys.platform.startswith('linux'):
    # CUDA/Torch caches otherwise default to the shared account's home directory.
    allowed=Path('/home/ot/Students/hs')
    if not Path(__file__).resolve().is_relative_to(allowed):
        raise RuntimeError('Server executable must resolve inside hs')
    for key,relative in {
        'TMPDIR':'tmp','XDG_CACHE_HOME':'cache','MPLCONFIGDIR':'cache/matplotlib',
        'CUDA_CACHE_PATH':'cache/cuda','TORCH_HOME':'cache/torch',
        'TORCH_EXTENSIONS_DIR':'cache/torch_extensions','TRITON_CACHE_DIR':'cache/triton',
        'TORCHINDUCTOR_CACHE_DIR':'cache/torchinductor','PYTORCH_KERNEL_CACHE_PATH':'cache/pytorch_kernels',
    }.items():
        cache=(allowed/relative).resolve()
        if not cache.is_relative_to(allowed):raise RuntimeError(f'Cache symlink escapes hs: {key}')
        cache.mkdir(parents=True,exist_ok=True);os.environ[key]=str(cache)
from chapter5_baseline import ROOT, REFERENCE, Actor, Double_Q_Critic, ZScoreNormalizer, ref_globals
import numpy as np
import torch
from SAC_lstm_att_normal import SAC_lstm_countinuous
from noise_utils import SensorNoise, ActuatorNoise

DEFAULT_CONFIG = ROOT/'configs/chapter5_static_aligned.json'


def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_config(path=DEFAULT_CONFIG):
    config=json.loads(Path(path).read_text())
    assert not config['dynamic_enabled']
    assert len(config['observation'])==18 and config['network']['history_length']==config['network']['attention_k']==10
    assert config['safety']['distance_m']==40 and config['control_frequency_hz']==1
    return config


def write_json(path, obj, exclusive=True):
    with Path(path).open('x' if exclusive else 'w') as file:
        json.dump(obj,file,indent=2,ensure_ascii=False,allow_nan=False)


def output_directory(path):
    path=Path(path).resolve()
    if sys.platform.startswith('linux') and not path.is_relative_to(Path('/home/ot/Students/hs')):
        raise ValueError('All server writes must resolve within hs')
    path.mkdir(parents=True,exist_ok=False)
    return path


def make_layout(rng, config):
    c=config['obstacles']; n=int(rng.integers(c['count'][0],c['count'][1]+1))
    for restart in range(50):
        positions=[]
        for _ in range(6000):
            p=[float(rng.uniform(*c['x_range_m'])),float(rng.uniform(*c['y_range_m']))]
            if any(np.linalg.norm(np.asarray(p)-q)<c['minimum_spacing_m'] for q in positions+[[0,0],[500,0]]):continue
            positions.append(p)
            if len(positions)==n:return positions
    raise RuntimeError('Cannot generate declared static layout; do not silently lower count')


def scenario(rng, config, index, kind, direction=None):
    winds=config['wind']['mean_direction_degrees']
    state=[0.]*18
    state[3]=float(np.deg2rad(rng.uniform(*config['initial_heading_degrees'])))
    state[12]=500.
    obstacles=[] if kind=='no_obstacle' else copy.deepcopy(config['obstacles']['fixed_layout']) if kind=='fixed_static' else make_layout(rng,config)
    return dict(id=f'{kind}_{index:04d}', kind=kind, initial_state=state, obstacles=obstacles,
                mean_wind_degrees=float(winds[index%len(winds)] if direction is None else direction),
                mean_wind_speed=config['wind']['mean_speed_m_s'],
                wind_seed=int(rng.integers(1,2**31)), sensor_seed=int(rng.integers(1,2**31)),
                actuator_seed=int(rng.integers(1,2**31)), policy_seed=int(rng.integers(1,2**31)))


def make_bank(config, path):
    rng=np.random.default_rng(config['evaluation']['bank_seed']); rows=[]
    for kind,count in [('no_obstacle',100),('fixed_static',50),('random_static',50)]:
        rows.extend(scenario(rng,config,i,kind) for i in range(count))
    bank={'schema':1,'purpose':'Fixed development/selection bank, not an untouched final paper test',
          'generation_config_sha256':digest(config),'scenarios':rows}
    bank['bank_sha256']=digest(rows)
    write_json(path,bank)
    return bank


def load_bank(path):
    bank=json.loads(Path(path).read_text())
    assert bank['bank_sha256']==digest(bank['scenarios'])
    assert len({s['id'] for s in bank['scenarios']})==len(bank['scenarios'])
    return bank


def segment_distance(a,b,p):
    d=b-a; denom=float(d@d)
    fraction=0. if denom<1e-20 else float(np.clip((p-a)@d/denom,0.,1.))
    return float(np.linalg.norm(a+fraction*d-p))


class _Trace(ast.NodeTransformer):
    def __init__(self):self.hits=0
    def visit_Assign(self,node):
        self.generic_visit(node)
        if isinstance(node.value,ast.Name) and node.value.id=='y_high' and any(ast.unparse(t)=='self.state[0:8]' for t in node.targets):
            self.hits+=1
            return [node,ast.parse('self._accepted_trace.append((float(t), self.state[:2].copy()))').body[0]]
        return node
    def visit_While(self,node):
        self.generic_visit(node)
        if ast.unparse(node.test)=='t < tf':
            node.body.insert(0,ast.parse('dt = min(dt, self._integration_cap, tf-t)').body[0])
        return node


class StaticEnvironment:
    """One reference instance at a time; global state is explicitly snapshotted."""
    def __init__(self, config, protocol, version=None):
        self.config=config; self.protocol=protocol; self.version=version or config['environment']
        assert self.version in ('v2','v3') and protocol in ('legacy','aligned')
        if self.version=='v2' and config['noise']['sensor_enabled']:
            raise ValueError('V2 exposes global obstacle x/y; current SensorNoise treats slots 15/17 as angles. Disable sensor noise for V2 until a source-bound coordinate noise protocol exists.')
        filename=ROOT/f'sailboat_RL/gymnasium/envs/sailboat/sailboat_s14_obst_{self.version.upper()}.py'
        spec=importlib.util.spec_from_file_location('static_reference_'+self.version,filename)
        mod=importlib.util.module_from_spec(spec)
        tree=ast.parse(filename.read_text()); injection=_Trace(); tree=injection.visit(tree)
        assert injection.hits==1
        exec(compile(ast.fix_missing_locations(tree),str(filename),'exec'),mod.__dict__)
        self.env=getattr(mod,f'Sailboat_obst_{self.version}')(render_mode=None)
        self.env._integration_cap=config['safety']['max_integration_step_s'] if protocol=='aligned' else float('inf')
        self.env._accepted_trace=[]
        self.wind_rng=np.random.RandomState(0)
        self.sensor=SensorNoise(config['noise']['sensor_ratio'],seed=0)
        self.actuator=ActuatorNoise(config['noise']['actuator_ratio'],seed=0)
        self.current=None

    def reset(self, row):
        py_state=random.getstate(); np_state=np.random.get_state()
        random.seed(row['wind_seed']); np.random.seed(row['wind_seed'])
        try:self.env.reset(seed=row['wind_seed'])
        finally:random.setstate(py_state);np.random.set_state(np_state)
        self.wind_rng.seed(row['wind_seed']);self.sensor.rng.seed(row['sensor_seed']);self.actuator.rng.seed(row['actuator_seed'])
        self.env.state=np.asarray(row['initial_state'],dtype=np.float32).copy()
        self.env.target_sail_angle=float(self.env.state[8]);self.env.target_rudder_angle=float(self.env.state[9])
        ref_globals.state=self.env.state.copy()
        ref_globals.current_state=self.env.state[:12]
        ref_globals.obstacles=[tuple(p) for p in row['obstacles']];ref_globals.observed_obstacles=[]
        ref_globals.current_time=0;ref_globals.total_time=self.config['episode_limit'];ref_globals.path=[]
        wind=np.deg2rad(row['mean_wind_degrees']);speed=row['mean_wind_speed']
        ref_globals.w0=[speed,wind]
        ref_globals.w_ini_v=ref_globals.w_last_v=ref_globals.w_change_v=speed
        ref_globals.w_ini_d=ref_globals.w_last_d=ref_globals.w_change_d=wind
        if hasattr(self.env,'dryden_params'):self.env.dryden_params['V']=speed
        self.current=self.env.state.copy()
        return self.observe(self.current)

    def observe(self, raw):
        return self.sensor.add_observation_noise(raw) if self.config['noise']['sensor_enabled'] else raw.copy()

    def step(self, commanded):
        physical=np.asarray(commanded,dtype=np.float32)*self.env.action_space.high
        if self.config['noise']['actuator_enabled']:
            if self.protocol=='legacy':
                # Match original normalized-input noise call when enabled, never silently fix old weights.
                physical=self.actuator.apply_action_noise(commanded,self.env.action_space.high)*self.env.action_space.high
            else:physical=self.actuator.apply_action_noise(physical,self.env.action_space.high)
        physical=np.clip(physical,self.env.action_space.low,self.env.action_space.high)
        before=self.current.copy(); self.env._accepted_trace=[(0.,before[:2].copy())]
        state=np.random.get_state();np.random.set_state(self.wind_rng.get_state())
        try:raw,reward,terminated,truncated,info=self.env.step(physical)
        finally:self.wind_rng.set_state(np.random.get_state());np.random.set_state(state)
        raw=raw.copy(); self.current=raw
        assert np.isfinite(raw).all() and np.isfinite(reward) and np.isfinite(physical).all()
        nodes=[p for _,p in self.env._accepted_trace]
        separation=min((segment_distance(a,b,np.asarray(p)) for a,b in zip(nodes[:-1],nodes[1:])
                        for p in ref_globals.obstacles),default=float('inf'))
        endpoint=min((float(np.linalg.norm(raw[:2]-p)) for p in ref_globals.obstacles),default=float('inf'))
        violated=separation<self.config['safety']['distance_m']
        if self.protocol=='aligned' and violated:
            if not truncated:reward=float(reward)-100.
            truncated=True;terminated=False
        elapsed=int(ref_globals.current_time)
        timeout=elapsed>=self.config['episode_limit'];out=bool(np.linalg.norm(raw[:2])>=750)
        info=dict(time=elapsed, raw=raw, physical_action=physical, minimum_separation=separation,
                  endpoint_separation=endpoint, safety_violation=violated, timeout=timeout, out_of_bounds=out,
                  path_increment=sum(float(np.linalg.norm(b-a)) for a,b in zip(nodes[:-1],nodes[1:])),
                  sail_increment=abs(float(raw[8]-before[8])),rudder_increment=abs(float(raw[9]-before[9])),
                  goal_distance=float(np.linalg.norm(raw[:2]-raw[12:14])), wind=[ref_globals.w_change_v,ref_globals.w_change_d])
        return self.observe(raw),float(reward),bool(terminated),bool(truncated),info

    def snapshot(self):
        fields=['state','target_sail_angle','target_rudder_angle','dryden_state_u','dryden_state_v','dryden_params']
        values={k:v for k,v in vars(ref_globals).items() if not k.startswith('__') and not isinstance(v,type(np)) and not callable(v)}
        return copy.deepcopy(dict(env={k:getattr(self.env,k) for k in fields if hasattr(self.env,k)},globals=values,
            wind_rng=self.wind_rng.get_state(),sensor_rng=self.sensor.rng.get_state(),actuator_rng=self.actuator.rng.get_state(),current=self.current))

    def restore(self,state):
        state=copy.deepcopy(state)
        for k,v in state['env'].items():setattr(self.env,k,v)
        for k,v in state['globals'].items():setattr(ref_globals,k,v)
        self.wind_rng.set_state(state['wind_rng']);self.sensor.rng.set_state(state['sensor_rng']);self.actuator.rng.set_state(state['actuator_rng'])
        self.current=state['current']

    def close(self):self.env.close()


class History:
    def __init__(self, initial, length, protocol):
        self.protocol=protocol;self.length=length;self.t=0
        self.states=deque([initial.copy() for _ in range(length)],maxlen=length)
        self.actions=deque([np.zeros(2,dtype=np.float32) for _ in range(length)],maxlen=length)
        self.indices=deque([-1]*length,maxlen=length)
        self.previous=initial.copy();self.previous_action=np.zeros(2,dtype=np.float32)
    def arrays(self):return np.asarray(self.states).copy(),np.asarray(self.actions).copy()
    def advance(self,current,action,next_state):
        self.states.append((current if self.protocol=='aligned' else next_state).copy())
        self.actions.append(action.copy());self.indices.append(self.t if self.protocol=='aligned' else self.t+1)
        self.previous=current.copy();self.previous_action=action.copy();self.t+=1


def hidden_norm(actor):
    return math.sqrt(sum(float(t.detach().square().sum()) for pair in actor.hidden_states.values() for t in pair))


def act(actor,normalizer,observation,history,protocol,deterministic=True):
    device=next(actor.parameters()).device
    norm=lambda x:normalizer.normalize(torch.as_tensor(x,dtype=torch.float32,device=device).unsqueeze(0))
    with torch.no_grad():
        if protocol=='legacy':
            a,_=actor(current_state=norm(observation),prev_state=norm(history.previous),
                      prev_action=torch.as_tensor(history.previous_action,device=device).unsqueeze(0),
                      deterministic=deterministic,single_step_mode=True,env_ids=['static'])
        else:
            s,a_hist=history.arrays()
            a,_=actor(current_state=norm(observation),state_sequence=norm(s),
                      action_sequence=torch.as_tensor(a_hist,device=device).unsqueeze(0),deterministic=deterministic)
    assert torch.isfinite(a).all()
    return a[0].cpu().numpy().copy()


def load_weights(prefix, step, config, protocol, device='cpu'):
    actor=Actor(18,2,tuple(config['network']['actor_width']))
    critic=Double_Q_Critic(18,2,tuple(config['network']['critic_q1_width']),tuple(config['network']['critic_q2_width']))
    normalizer=ZScoreNormalizer(18,torch.device(device)); hashes={}
    for kind,model in [('actor',actor),('q_critic',critic),('normalizer',normalizer)]:
        path=Path(f'{prefix}_{kind}{step}.pth'); obj=torch.load(path,map_location='cpu',weights_only=True)
        if kind=='normalizer':
            assert obj['mean'].shape==obj['var'].shape==(18,) and obj['count']>0
            assert torch.isfinite(obj['mean']).all() and torch.isfinite(obj['var']).all() and (obj['var']>=0).all()
            model.load_state_dict(obj)
        else:model.load_state_dict(obj,strict=True)
        hashes[str(path)]=file_hash(path)
    assert all(torch.isfinite(p).all() for model in (actor,critic) for p in model.parameters())
    k=config['legacy']['attention_k'] if protocol=='legacy' else config['network']['attention_k']
    actor.history_window_size=critic.history_window_size=k
    return actor.to(device),critic.to(device),normalizer,hashes


def evaluate(actor,normalizer,config,bank,out,protocol,version=None,limit=None,representative_ids=None):
    config=copy.deepcopy(config)
    config['history_protocol']=protocol
    config['environment']=version or config['environment']
    if protocol=='legacy':config['baseline_definition']='Recovered legacy checkpoint; environment identity requires separate verification'
    out=output_directory(out);env=StaticEnvironment(config,protocol,version)
    write_json(out/'config_snapshot.json',config)
    write_json(out/'provenance.json',provenance(config,bank))
    rows=bank['scenarios'][:limit] if limit else bank['scenarios']
    selected=set(representative_ids or [rows[i]['id'] for i in sorted(set([0,min(1,len(rows)-1),min(2,len(rows)-1),len(rows)//2,len(rows)-1]))])
    results=[];captures={}; attention=[];lstm_norm=[]
    hooks=[actor.attention.register_forward_hook(lambda m,i,o:attention.append(o[1].detach().cpu().numpy()[0].tolist())),
           actor.lstm.register_forward_hook(lambda m,i,o:lstm_norm.append(float(o[1][0].detach().norm())))]
    actor.train(protocol=='legacy' and config['legacy']['inference_dropout'])
    try:
        for index,row in enumerate(rows):
            torch.manual_seed(row['policy_seed'])
            before=hidden_norm(actor);actor.reset_hidden_state();after=hidden_norm(actor);assert after==0.
            obs=env.reset(row);k=config['legacy']['attention_k'] if protocol=='legacy' else config['network']['attention_k']
            actor.history_window_size=k
            history=History(obs,k if protocol=='legacy' else config['network']['history_length'],protocol)
            record=[];total_reward=length=sail_tv=rudder_tv=0.;minimum=float('inf');violation=False;term=trunc=False
            for t in range(config['episode_limit']):
                attention.clear();lstm_norm.clear()
                action=act(actor,normalizer,obs,history,protocol)
                nxt,reward,term,trunc,info=env.step(action)
                total_reward+=reward;length+=info['path_increment'];sail_tv+=info['sail_increment'];rudder_tv+=info['rudder_increment']
                minimum=min(minimum,info['minimum_separation']);violation|=info['safety_violation']
                if row['id'] in selected:
                    record.append(dict(time=t+1,x=float(info['raw'][0]),y=float(info['raw'][1]),sail=float(info['raw'][8]),rudder=float(info['raw'][9]),
                        goal_distance=info['goal_distance'],separation=None if not np.isfinite(info['minimum_separation']) else info['minimum_separation'],
                        hidden_norm=hidden_norm(actor),lstm_output_hidden_norm=lstm_norm[-1],attention=attention[-1],
                        history_indices=list(history.indices),prev_state_time=-1 if t==0 else t-1,
                        command=action.tolist(),physical_action=info['physical_action'].tolist()))
                history.advance(obs,action,nxt);obs=nxt
                if term or trunc:break
            result=dict(scenario=row['id'],kind=row['kind'],mean_wind_degrees=row['mean_wind_degrees'],steps=t+1,
                task_success=term,safe_success=bool(term and not violation),safety_violation=bool(violation),timeout=info['timeout'],
                out_of_bounds=info['out_of_bounds'],minimum_separation_m=minimum if np.isfinite(minimum) else None,
                navigation_time_s_if_success=t+1 if term else None,trajectory_length_m=length,sail_variation_rad_s=sail_tv/(t+1),
                rudder_variation_rad_s=rudder_tv/(t+1),reward=total_reward,hidden_before_reset=before,hidden_after_reset=after)
            result['failure_types']=[name for name,flag in [
                ('FAILURE_SAFETY',violation),('FAILURE_TIMEOUT',info['timeout']),
                ('FAILURE_OUT_OF_BOUND',info['out_of_bounds']),('FAILURE_NAVIGATION',not term)] if flag]
            results.append(result)
            if record:captures[row['id']]={'scenario':row,'metrics':result,'trajectory':record}
            with (out/'episodes.jsonl').open('a') as f:f.write(json.dumps(result)+'\n')
            if index%10==0:print(json.dumps({'evaluation':str(out),'done':index+1,'total':len(rows),'last':result}),flush=True)
    finally:
        for hook in hooks:hook.remove()
        actor.reset_hidden_state();env.close()
    no=[r for r in results if r['kind']=='no_obstacle'];static=[r for r in results if r['kind']!='no_obstacle']
    mean=lambda values:float(np.mean(values)) if values else None
    no_rate=mean([r['safe_success'] for r in no]);static_rate=mean([r['safe_success'] for r in static])
    metrics=dict(no_obstacle_success_rate=no_rate,static_safe_success_rate=static_rate,
        static_safety_violation_rate=mean([r['safety_violation'] for r in static]),timeout_rate=mean([r['timeout'] for r in results]),
        minimum_separation_mean_m=mean([r['minimum_separation_m'] for r in static if r['minimum_separation_m'] is not None]),
        minimum_separation_median_m=float(np.median([r['minimum_separation_m'] for r in static])) if static else None,
        successful_navigation_time_s=mean([r['steps'] for r in results if r['safe_success']]),
        successful_trajectory_length_m=mean([r['trajectory_length_m'] for r in results if r['safe_success']]),
        sail_variation_rad_s=mean([r['sail_variation_rad_s'] for r in results]),rudder_variation_rad_s=mean([r['rudder_variation_rad_s'] for r in results]))
    complete=len(results)==200 and len(no)==100 and len(static)==100
    summary=dict(config_sha256=digest(config),bank_sha256=bank['bank_sha256'],history_protocol=protocol,environment=version or config['environment'],
        evaluated_count=len(results),full_bank_evaluated=complete,metrics=metrics,
        numerical_gate=bool(complete and no_rate>=config['evaluation']['gate_no_obstacle'] and static_rate>=config['evaluation']['gate_static_safe']),
        trajectory_review='PENDING',STATIC_BASELINE_STATUS='IN_PROGRESS',
        safety_definition='40m, accepted integration-node linear segments; legacy termination unchanged, aligned stops on detected violation')
    def group_metrics(group):
        return dict(count=len(group),success_rate=mean([r['safe_success'] for r in group]),
            safety_violation_rate=mean([r['safety_violation'] for r in group]),timeout_rate=mean([r['timeout'] for r in group]),
            minimum_separation_m=mean([r['minimum_separation_m'] for r in group if r['minimum_separation_m'] is not None]),
            navigation_time_s=mean([r['steps'] for r in group if r['safe_success']]),
            trajectory_length_m=mean([r['trajectory_length_m'] for r in group if r['safe_success']]),
            sail_variation_rad_s=mean([r['sail_variation_rad_s'] for r in group]),rudder_variation_rad_s=mean([r['rudder_variation_rad_s'] for r in group]))
    summary['strata']={'no_obstacle':group_metrics(no),'static':group_metrics(static)}
    # Geometric proxy frozen before training; does not relabel or alter bank rows.
    difficulty={r['id']:('hard' if min(segment_distance(np.array([0.,0.]),np.array([500.,0.]),np.asarray(p)) for p in r['obstacles'])<40
                 else 'medium' if min(segment_distance(np.array([0.,0.]),np.array([500.,0.]),np.asarray(p)) for p in r['obstacles'])<80 else 'easy')
                 for r in rows if r['obstacles']}
    summary['difficulty_definition']='nominal straight-route clearance: hard <40m, medium [40,80)m, easy >=80m; geometry proxy, not sailing feasibility'
    for level in ['easy','medium','hard']:
        summary['strata'][level]=group_metrics([r for r in static if difficulty[r['scenario']]==level])
    write_json(out/'summary.json',summary);write_json(out/'representative_trajectories.json',captures)
    return summary


def plot_evaluation(directory):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    directory=Path(directory);captures=json.loads((directory/'representative_trajectories.json').read_text())
    chosen=list(captures.items())[:5]
    fig,axes=plt.subplots(1,len(chosen),figsize=(5*len(chosen),5),squeeze=False)
    for ax,(name,c) in zip(axes[0],chosen):
        rows=c['trajectory'];ax.plot([0]+[r['x'] for r in rows],[0]+[r['y'] for r in rows],label='vessel')
        for x,y in c['scenario']['obstacles']:
            ax.add_patch(plt.Circle((x,y),40,color='tab:red',alpha=.15));ax.plot(x,y,'r.')
        ax.plot(0,0,'go');ax.plot(500,0,'k*');ax.set_title(f"{name}\nwind={c['scenario']['mean_wind_degrees']} deg; safe={c['metrics']['safe_success']}",fontsize=9)
        ax.set_aspect('equal',adjustable='datalim');ax.grid(alpha=.25);ax.set_xlabel('x (m)');ax.set_ylabel('y (m)')
    fig.suptitle('Static checkpoint diagnostics — protocol and selection fixed in summary.json')
    fig.tight_layout();fig.savefig(directory/'five_trajectories.png',dpi=140);plt.close(fig)
    fig,axes=plt.subplots(3,1,figsize=(10,8))
    for name,c in chosen:
        t=[r['time'] for r in c['trajectory']]
        for ax,key in zip(axes,['sail','rudder','lstm_output_hidden_norm']):ax.plot(t,[r[key] for r in c['trajectory']],label=name)
    for ax,label in zip(axes,['sail angle (rad)','rudder angle (rad)','LSTM h norm']):ax.set_ylabel(label);ax.grid(alpha=.2)
    axes[0].legend(fontsize=7);axes[-1].set_xlabel('time (s)');fig.tight_layout();fig.savefig(directory/'actuators_hidden.png',dpi=140);plt.close(fig)


def provenance(config,bank):
    sources=[Path(__file__),ROOT/'research/chapter5_baseline.py',REFERENCE/'utils_lstm_att_normal.py',
             REFERENCE/'SAC_lstm_att_normal.py',REFERENCE/'noise_utils.py',REFERENCE/'globals.py',
             ROOT/'sailboat_RL/gymnasium/envs/sailboat/sailboat_s14_obst_V3.py']
    if config['environment']=='v2':sources.append(ROOT/'sailboat_RL/gymnasium/envs/sailboat/sailboat_s14_obst_V2.py')
    run=lambda args:subprocess.check_output(args,cwd=ROOT,stderr=subprocess.DEVNULL)
    try:
        revision=run(['git','rev-parse','HEAD']).decode().strip()
        diff_hash=hashlib.sha256(run(['git','diff','--binary','HEAD'])).hexdigest()
    except subprocess.CalledProcessError:
        deployed=json.loads((ROOT/'research/validation/static_deployment_manifest.json').read_text())
        revision=deployed['git_revision'];diff_hash=deployed['git_tracked_diff_sha256']
        for path,expected in deployed['source_sha256'].items():
            assert file_hash(ROOT/path)==expected, f'Deployment source mismatch: {path}'
    return dict(config_sha256=digest(config),bank_sha256=bank['bank_sha256'],
                source_sha256={str(p.relative_to(ROOT)):file_hash(p) for p in sources},
                git_revision=revision,git_tracked_diff_sha256=diff_hash,
                runtime=dict(python=sys.version,torch=str(torch.__version__),numpy=np.__version__))


def pack(value):
    if isinstance(value,np.ndarray):return {'__numpy_array__':torch.from_numpy(value.copy())}
    if isinstance(value,np.generic):return value.item()
    if isinstance(value,dict):return {k:pack(v) for k,v in value.items()}
    if isinstance(value,list):return [pack(v) for v in value]
    if isinstance(value,tuple):return tuple(pack(v) for v in value)
    return value


def unpack(value):
    if isinstance(value,dict):
        if set(value)=={'__numpy_array__'}:return value['__numpy_array__'].cpu().numpy().copy()
        return {k:unpack(v) for k,v in value.items()}
    if isinstance(value,list):return [unpack(v) for v in value]
    if isinstance(value,tuple):return tuple(unpack(v) for v in value)
    return value


def rng_snapshot():
    return dict(python=random.getstate(),numpy=np.random.get_state(),torch=torch.get_rng_state(),
                cuda=torch.cuda.get_rng_state_all() if torch.cuda.is_initialized() else [])


def restore_rng(state):
    random.setstate(state['python']);np.random.set_state(state['numpy']);torch.set_rng_state(state['torch'].cpu())
    if state['cuda']:torch.cuda.set_rng_state_all(state['cuda'])


def build_agent(config,device):
    c=config['sac'];n=config['network']
    agent=SAC_lstm_countinuous(dvc=torch.device(device),state_dim=18,action_dim=2,net_width=n['hidden_size'],
        batch_size=c['batch_size'],a_lr=c['actor_lr'],c_lr=c['critic_lr'],gamma=c['gamma'],alpha=c['alpha'],adaptive_alpha=c['adaptive_alpha'])
    # Guard the config/reference contract; never silently ignore a changed hyperparameter.
    assert agent.seq_len==n['history_length'] and agent.actor.history_window_size==n['attention_k']
    assert agent.replay_buffer.max_size==config['replay']['capacity'] and agent.tau==c['tau']
    assert agent.policy_update_freq==c['actor_update_period'] and agent.max_grad_norm==c['grad_clip']
    assert agent.alpha_optim.param_groups[0]['lr']==c['alpha_lr']
    assert agent.actor_optimizer.param_groups[0]['weight_decay']==c['weight_decay']
    return agent


def agent_snapshot(agent):
    rb=agent.replay_buffer
    return dict(actor=agent.actor.state_dict(),critic=agent.q_critic.state_dict(),target=agent.q_critic_target.state_dict(),
        actor_optimizer=agent.actor_optimizer.state_dict(),critic_optimizer=agent.q_critic_optimizer.state_dict(),
        alpha_optimizer=agent.alpha_optim.state_dict(),log_alpha=agent.log_alpha.detach().clone(),
        normalizer=agent.state_normalizer.state_dict(),training_step=agent.training_step,critic_update_count=agent.critic_update_count,
        replay={k:v for k,v in vars(rb).items() if k!='dvc'},
        losses=dict(q=agent.q_loss_history[-1000:],a=agent.a_loss_history[-1000:],alpha=agent.alpha_loss_history[-1000:]))


def restore_agent(agent,state):
    agent.actor.load_state_dict(state['actor'],strict=True);agent.q_critic.load_state_dict(state['critic'],strict=True)
    agent.q_critic_target.load_state_dict(state['target'],strict=True)
    agent.actor_optimizer.load_state_dict(state['actor_optimizer']);agent.q_critic_optimizer.load_state_dict(state['critic_optimizer'])
    with torch.no_grad():agent.log_alpha.copy_(state['log_alpha'].to(agent.dvc))
    agent.alpha_optim.load_state_dict(state['alpha_optimizer']);agent.alpha=agent.log_alpha.exp()
    agent.state_normalizer.load_state_dict(state['normalizer']);agent.training_step=state['training_step'];agent.critic_update_count=state['critic_update_count']
    for k,v in state['replay'].items():setattr(agent.replay_buffer,k,v.to(agent.dvc) if isinstance(v,torch.Tensor) else v)
    agent.q_loss_history=state['losses']['q'];agent.a_loss_history=state['losses']['a'];agent.alpha_loss_history=state['losses']['alpha']


def save_training(path,agent,environment,history,loop,scenario_rng,config,bank,origin):
    if Path(path).exists():raise FileExistsError(path)
    payload=dict(schema=1,config=config,provenance=origin,step=loop['step'],history_protocol='aligned',
        agent=agent_snapshot(agent),environment=environment.snapshot(),history=vars(history) if history else None,
        loop=loop,scenario_rng=scenario_rng.bit_generator.state,rng=rng_snapshot())
    if history:
        payload['history']={k:list(v) if isinstance(v,deque) else v for k,v in vars(history).items()}
    temporary=Path(str(path)+'.partial')
    with temporary.open('xb') as file:
        torch.save(pack(payload),file);file.flush();os.fsync(file.fileno())
    os.replace(temporary,path)


def check_resume(payload,config,bank,current_origin):
    assert payload['history_protocol']=='aligned', 'Never resume legacy weights as aligned training'
    assert payload['provenance']['config_sha256']==digest(config), 'Frozen config changed'
    assert payload['provenance']['bank_sha256']==bank['bank_sha256'], 'Evaluation bank changed'
    assert payload['provenance']['source_sha256']==current_origin['source_sha256'], 'Executable source changed'
    assert payload['provenance']['runtime']==current_origin['runtime'], 'Runtime changed; exact resume not verified'


def train(config,bank,directory,through,device='cpu',resume=None,smoke=False,evaluate_checkpoints=True):
    """One seed, one static run. Stop at a declared stage for evidence review."""
    import fcntl
    assert config['history_protocol']=='aligned' and not config['dynamic_enabled']
    if not smoke:assert through in config['training_stages']
    else:assert 0<through<=50000
    directory=Path(directory).resolve()
    if sys.platform.startswith('linux'):assert directory.is_relative_to(Path('/home/ot/Students/hs'))
    directory.mkdir(parents=True,exist_ok=bool(resume))
    lock=(directory/'run.lock').open('a+')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:lock.close();raise RuntimeError('This static run is already active')
    origin=provenance(config,bank)
    bank_file_hash=file_hash(ROOT/config['static_eval_bank'])
    torch.manual_seed(config['seed']);random.seed(config['seed']);np.random.seed(config['seed'])
    torch.use_deterministic_algorithms(True)
    agent=build_agent(config,device);env=StaticEnvironment(config,'aligned');rng=np.random.default_rng(config['seed']+700000)
    history=None;loop=dict(step=0,episode=0,observation=None,current_scenario=None,episode_metrics=None)
    segment=directory/f'log_from_{0 if resume is None else "resume"}_{time.time_ns()}.jsonl'
    if resume:
        payload=unpack(torch.load(resume,map_location='cpu',weights_only=True));check_resume(payload,config,bank,origin)
        restore_agent(agent,payload['agent']);env.restore(payload['environment']);loop=payload['loop'];rng.bit_generator.state=payload['scenario_rng']
        if payload['history']:
            history=History(np.zeros(18,dtype=np.float32),config['network']['history_length'],'aligned')
            for k,v in payload['history'].items():setattr(history,k,deque(v,maxlen=history.length) if k in ('states','actions','indices') else v)
        restore_rng(payload['rng'])
        assert loop['step']<through, 'Requested stage already completed'
    else:
        write_json(directory/'config.json',config);write_json(directory/'provenance.json',origin)
        import shutil
        for relative in origin['source_sha256']:
            target=directory/'source_snapshot'/relative;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/relative,target)
        shutil.copyfile(ROOT/config['static_eval_bank'],directory/'static_eval_bank.json')
    telemetry={}
    def q_hook(module,inputs,output):
        telemetry['q_abs_max']=max(float(t.detach().abs().max()) for t in output)
    def actor_hook(module,inputs,output):
        telemetry['action_saturation_fraction']=float((output[0].detach().abs()>=.98).float().mean())
        if output[1] is not None:telemetry['sample_entropy_estimate']=float(-output[1].detach().mean())
    hooks=[agent.q_critic.register_forward_hook(q_hook),agent.actor.register_forward_hook(actor_hook)]
    if not resume and not smoke and evaluate_checkpoints:
        saved_env=env.snapshot();saved_rng=rng_snapshot()
        try:
            save_training(directory/'step_0.pt',agent,env,None,loop,rng,config,bank,origin)
            evaluate(agent.actor,agent.state_normalizer,config,bank,directory/'eval_0','aligned')
        finally:env.restore(saved_env);restore_rng(saved_rng)
    started=time.monotonic(); c=config['sac']
    try:
        with segment.open('x') as log:
            while loop['step']<through:
                if history is None:
                    kind='no_obstacle' if rng.random()<config['obstacles']['no_obstacle_probability'] else 'random_static'
                    row=scenario(rng,config,loop['episode'],kind,direction=float(rng.choice(config['wind']['mean_direction_degrees'])))
                    obs=env.reset(row);history=History(obs,config['network']['history_length'],'aligned')
                    loop.update(observation=obs,current_scenario=row,episode_metrics=dict(reward=0.,steps=0,length=0.,sail=0.,rudder=0.,minimum=None,violation=False))
                obs=loop['observation'];s_hist,a_hist=history.arrays();agent.actor.eval()
                if loop['step']<c['warmup_steps']:
                    choice=rng.random();action=np.zeros(2,dtype=np.float32)
                    if .3<=choice<.5:action=rng.uniform(-.2,.2,2).astype(np.float32)
                    elif .5<=choice<.65:action[int(rng.integers(2))]=rng.uniform(-.5,.5)
                    elif choice>=.65:action=rng.uniform(-1.,1.,2).astype(np.float32)
                else:action=act(agent.actor,agent.state_normalizer,obs,history,'aligned',deterministic=False)
                nxt,reward,term,trunc,info=env.step(action);history.advance(obs,action,nxt)
                next_s,next_a=history.arrays()
                agent.replay_buffer.add(s_hist,a_hist,obs,action,float(reward),next_s,next_a,nxt,bool(term or trunc))
                loop['step']+=1;loop['observation']=nxt;m=loop['episode_metrics']
                m['reward']+=reward;m['steps']+=1;m['length']+=info['path_increment'];m['sail']+=info['sail_increment'];m['rudder']+=info['rudder_increment']
                if np.isfinite(info['minimum_separation']):m['minimum']=min(m['minimum'] if m['minimum'] is not None else float('inf'),info['minimum_separation'])
                m['violation']|=info['safety_violation']
                if loop['step']>=c['warmup_steps'] and loop['step']%c['update_period']==0 and agent.replay_buffer.size>=c['batch_size']:
                    agent.actor.train();agent.q_critic.train();agent.q_critic_target.eval()
                    agent.replay_buffer.update_beta(min(loop['step']/2000000,1.))
                    for _ in range(c['updates_per_period']):
                        loss=agent.train()
                        assert all(np.isfinite(loss[k]) for k in ['q_loss','a_loss','alpha_loss','alpha'])
                        assert all(np.isfinite(v) for v in telemetry.values()), 'Non-finite training health telemetry'
                        log.write(json.dumps(dict(type='update',step=loop['step'],**loss,**telemetry))+'\n')
                if term or trunc:
                    log.write(json.dumps(dict(type='episode',step=loop['step'],episode=loop['episode'],scenario=loop['current_scenario']['id'],
                        metrics=m,task_success=term,safe_success=bool(term and not m['violation']),timeout=info['timeout'],out_of_bounds=info['out_of_bounds']))+'\n')
                    loop['episode']+=1;history=None
                if loop['step']%1000==0:
                    log.flush()
                    progress=dict(training_step=loop['step'],episodes=loop['episode'],wall_seconds=time.monotonic()-started,**telemetry)
                    if device=='cuda':
                        progress['gpu_snapshot']=subprocess.check_output(['nvidia-smi','--query-gpu=index,utilization.gpu,memory.used','--format=csv,noheader,nounits'],text=True).strip()
                    write_json(directory/'progress.json',progress,exclusive=not (directory/'progress.json').exists())
                    print(json.dumps(progress),flush=True)
                if loop['step']%config['checkpoint_interval']==0 or loop['step']==through:
                    checkpoint=directory/f'step_{loop["step"]}.pt'
                    save_training(checkpoint,agent,env,history,loop,rng,config,bank,origin);log.flush()
                    if evaluate_checkpoints:
                        saved_env=env.snapshot();saved_rng=rng_snapshot()
                        try:
                            result=evaluate(agent.actor,agent.state_normalizer,config,bank,directory/f'eval_{loop["step"]}','aligned')
                            write_json(directory/f'eval_{loop["step"]}'/'checkpoint_identity.json',
                                dict(sha256={str(checkpoint):file_hash(checkpoint)},training_seed=config['seed'],kind='full_training_bundle'))
                            metric=result['metrics']
                            score=(metric['static_safe_success_rate'] or 0., -(metric['static_safety_violation_rate'] or 0.),
                                   -metric['timeout_rate'], -(metric['successful_navigation_time_s'] or 1e9))
                            best_path=directory/'best.json'
                            best=json.loads(best_path.read_text()) if best_path.exists() else None
                            if best is None or tuple(best['score'])<score:
                                write_json(best_path,dict(checkpoint=checkpoint.name,sha256=file_hash(checkpoint),score=score,evaluation=f'eval_{loop["step"]}'),exclusive=best is None)
                                import shutil
                                shutil.copyfile(checkpoint,directory/'best_static_safe_success.pt')
                            episodes=[json.loads(line)['metrics']['reward'] for file in directory.glob('log_from_*.jsonl') for line in file.read_text().splitlines() if json.loads(line)['type']=='episode']
                            recent=float(np.mean(episodes[-20:])) if episodes else None
                            reward_path=directory/'best_reward.json'
                            old=json.loads(reward_path.read_text()) if reward_path.exists() else None
                            if recent is not None and (old is None or recent>old['last20_episode_return_mean']):
                                import shutil
                                shutil.copyfile(checkpoint,directory/'best_reward.pt')
                                write_json(reward_path,dict(checkpoint=checkpoint.name,last20_episode_return_mean=recent),exclusive=old is None)
                            assert file_hash(ROOT/config['static_eval_bank'])==bank_file_hash, 'Evaluation bank file changed during training'
                        finally:env.restore(saved_env);restore_rng(saved_rng)
                    write_json(directory/'latest.json',dict(checkpoint=checkpoint.name,sha256=file_hash(checkpoint),step=loop['step'],
                        status='STAGE_COMPLETE_REVIEW_REQUIRED' if loop['step']==through else 'RUNNING',STATIC_BASELINE_STATUS='IN_PROGRESS'),exclusive=not (directory/'latest.json').exists())
    finally:
        for hook in hooks:hook.remove()
        env.close();fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
    return directory/f'step_{loop["step"]}.pt'


def select_free_gpu():
    raw=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.used','--format=csv,noheader,nounits'],text=True)
    busy=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid','--format=csv,noheader'],text=True)
    for line in raw.splitlines():
        index,uuid,memory=[x.strip() for x in line.split(',')]
        if int(memory)<500 and uuid not in busy:
            os.environ['CUDA_VISIBLE_DEVICES']=index
            assert torch.cuda.is_available()
            x=torch.arange(64,device='cuda',dtype=torch.float32).reshape(8,8)
            assert torch.isfinite(x@x.T).all()
            return index
    raise RuntimeError('No free GPU. Nothing launched; do not use residual memory of occupied cards.')


def freeze_baseline(evaluation, review, destination):
    """Immutable export only after numeric gates and evidence-bound visual review."""
    import shutil
    evaluation=Path(evaluation);review=json.loads(Path(review).read_text())
    summary=json.loads((evaluation/'summary.json').read_text())
    assert summary['full_bank_evaluated'] and summary['numerical_gate'], 'Static metric gate has not passed'
    assert review['summary_sha256']==file_hash(evaluation/'summary.json')
    for field in ['repeatable_evaluation','hidden_reset','safety_check','reasonable_trajectories','no_high_frequency_actuation']:
        assert review.get(field) is True, f'Missing reviewed evidence: {field}'
    identity=json.loads((evaluation/'checkpoint_identity.json').read_text())
    bank=load_bank(ROOT/'research/validation/static_eval_bank.json')
    assert bank['bank_sha256']==summary['bank_sha256']
    origin=provenance(json.loads((evaluation/'config_snapshot.json').read_text()),bank)
    for filename,expected in identity['sha256'].items():
        path=Path(filename);path=path if path.is_absolute() else ROOT/path
        assert file_hash(path)==expected
    destination=output_directory(destination)
    for filename in ['summary.json','config_snapshot.json','checkpoint_identity.json','representative_trajectories.json']:
        shutil.copyfile(evaluation/filename,destination/filename)
    for filename in identity['sha256']:
        path=Path(filename);path=path if path.is_absolute() else ROOT/path
        shutil.copyfile(path,destination/path.name)
    shutil.copyfile(ROOT/'research/validation/static_eval_bank.json',destination/'static_eval_bank.json')
    write_json(destination/'review.json',review)
    write_json(destination/'baseline.json',dict(STATIC_BASELINE_STATUS='PASSED',history_protocol=summary['history_protocol'],
        bank_sha256=summary['bank_sha256'],checkpoint_identity=identity,
        training_seed=identity.get('training_seed','unknown for legacy checkpoint'),
        git_revision=origin['git_revision'],git_diff_sha256=origin['git_tracked_diff_sha256'],
        source_sha256=origin['source_sha256']))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['bank','evaluate','plot','train','freeze'])
    p.add_argument('--config',type=Path,default=DEFAULT_CONFIG)
    p.add_argument('--bank',type=Path)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--history-protocol',choices=['legacy','aligned'])
    p.add_argument('--environment',choices=['v2','v3'])
    p.add_argument('--checkpoint-prefix',type=Path);p.add_argument('--checkpoint-step',type=int)
    p.add_argument('--limit',type=int)
    p.add_argument('--through-stage',type=int,default=100000)
    p.add_argument('--resume',type=Path)
    p.add_argument('--device',choices=['cpu','cuda'],default='cuda')
    p.add_argument('--smoke',action='store_true',help='CPU integration test only, not a recovery verdict')
    p.add_argument('--evaluation',type=Path);p.add_argument('--review',type=Path)
    args=p.parse_args();config=read_config(args.config)
    if args.command=='bank':make_bank(config,args.output)
    elif args.command=='plot':plot_evaluation(args.output)
    elif args.command=='freeze':
        if not args.evaluation or not args.review:p.error('freeze requires evaluation and evidence-bound review')
        freeze_baseline(args.evaluation,args.review,args.output)
    elif args.command=='train':
        if args.history_protocol!='aligned':p.error('New static training requires explicit aligned protocol')
        if args.device=='cuda':print('Selected idle GPU',select_free_gpu(),flush=True)
        elif not args.smoke:p.error('Large training is GPU-only; CPU is limited to explicit engineering smoke')
        bank=load_bank(args.bank or ROOT/config['static_eval_bank'])
        train(config,bank,args.output,args.through_stage,args.device,args.resume,args.smoke,evaluate_checkpoints=not args.smoke)
    else:
        if not args.history_protocol or not args.checkpoint_prefix or args.checkpoint_step is None:
            p.error('Evaluation requires explicit history-protocol and checkpoint identity')
        config['history_protocol']=args.history_protocol
        if args.environment:config['environment']=args.environment
        bank=load_bank(args.bank or ROOT/config['static_eval_bank'])
        actor,critic,normalizer,hashes=load_weights(args.checkpoint_prefix,args.checkpoint_step,config,args.history_protocol)
        result=evaluate(actor,normalizer,config,bank,args.output,args.history_protocol,args.environment,args.limit)
        write_json(args.output/'checkpoint_identity.json',dict(prefix=str(args.checkpoint_prefix),step=args.checkpoint_step,sha256=hashes))
        print(json.dumps(result,indent=2))


if __name__=='__main__':main()
