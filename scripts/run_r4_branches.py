#!/usr/bin/env python3
"""Small offline branch experiment using the existing full navigation runner.

Each job re-executes the unchanged initial prefix, rather than constructing an
incomplete position-only restart. Only a one-time proposed target may change.
No observer or branch answer is used by a deployed planner.
"""
from pathlib import Path
import dataclasses, hashlib, json, math, sys
from collections import deque
import numpy as np
import run_r1 as runner
from sailboat_routing import navigation as nav
from sailboat_routing.r2_planner import RelayPlanner, RelayConfig
from sailboat_routing.planner import PlannerDecision, distance, NoRouteError
from sailboat_routing.metrics import segment_circle_clearance

ROOT=runner.ROOT
BASE_RUN=nav.run_episode
BASE_WORKER=runner.worker

def plain(x):
    if dataclasses.is_dataclass(x):return plain(dataclasses.asdict(x))
    if isinstance(x,np.ndarray):return x.tolist()
    if isinstance(x,np.generic):return x.item()
    if isinstance(x,(tuple,list,deque)):return [plain(y) for y in x]
    if isinstance(x,dict):return {str(k):plain(v) for k,v in x.items()}
    if isinstance(x,(str,int,float,bool)) or x is None:return x
    raise TypeError(type(x).__name__)

def numeric_attributes(obj):
    result={}
    for k,v in vars(obj).items():
        if k.startswith('__'):continue
        try:result[k]=plain(v)
        except TypeError:pass
    return result

def digest(arrays):
    h=hashlib.sha256()
    for a in arrays:
        z=np.asarray(a);h.update(str(z.dtype).encode());h.update(str(z.shape).encode());h.update(z.tobytes())
    return h.hexdigest()

class BranchRelay:
    def __init__(self,chart,cfg,mode,diagnostic):
        self.base=RelayPlanner(chart,cfg,mode);self.log=self.base.log
        self.diagnostic=diagnostic;self.events=[];self.fired=False

    def plan(self,v):
        ordinary=self.base.plan(v)
        cfg=self.diagnostic
        if self.fired or cfg['kind']=='none' or v.simulation_time!=cfg['time']:
            return ordinary
        self.fired=True;p=v.position_xy;old=v.current_goal_xy;chart=self.base.static_map
        kind=cfg['kind'];q=None
        if kind=='route':
            fresh=RelayPlanner(chart,self.base.config)
            try:q=fresh.plan(dataclasses.replace(v,current_goal_xy=None)).target_xy
            except NoRouteError:pass
        elif old is not None and kind=='extend':
            d=distance(p,old)
            if d>1e-8:q=(p[0]+500*(old[0]-p[0])/d,p[1]+500*(old[1]-p[1])/d)
        elif kind=='away' and chart.obstacles:
            o=min(chart.obstacles,key=lambda x:distance(p,x.center_xy)-x.exclusion_radius)
            d=distance(p,o.center_xy)
            length=cfg.get('length',500.)
            if d>1e-8:q=(p[0]+length*(p[0]-o.center_xy[0])/d,p[1]+length*(p[1]-o.center_xy[1])/d)
        else:raise ValueError('Unknown offline branch: '+kind)
        valid=q is not None and chart.segment_clear(p,q)
        if valid:
            try:chart.route(q,v.route[-1])
            except NoRouteError:valid=False
        changed=valid and distance(q,ordinary.target_xy)>1e-6
        self.events.append(dict(time=v.simulation_time,kind=kind,position=p,old_target=old,
            ordinary_proposal=ordinary.target_xy,alternative=q,geometrically_valid=valid,
            proposal_changed=changed,old_clearance=segment_circle_clearance(p,old,chart.obstacles)['safety_m'],
            alternative_clearance=segment_circle_clearance(p,q,chart.obstacles)['safety_m'] if q else None,
            after_protocol='Unmodified Relay160 management on every subsequent decision; original t-to-t+1 application.'))
        return PlannerDecision(q,ordinary.candidates,'offline_branch_'+kind,False) if valid else ordinary

def branch_worker(job):
    observed=[];made=[]
    def factory(chart,cfg,mode):
        p=BranchRelay(chart,cfg,mode,job['diagnostic']);made.append(p);return p
    runner.RelayPlanner=factory
    def observe(ctx):
        v=ctx['visible']
        if v.simulation_time not in job['diagnostic']['observe_times']:return
        physics=ctx['physics'];policy=ctx['policy'];planner=ctx['planner'].base
        observed.append(dict(time=v.simulation_time,visible=plain(v),frame=plain(ctx['frame']),
            raw=plain(ctx['raw']),observation=plain(ctx['observation']),
            pending_old_target_action=plain(ctx['decision'].action),
            physical_continuity=physics.continuity_snapshot(),
            environment_numeric_attributes=numeric_attributes(physics.env),
            physical_globals=numeric_attributes(physics.modules.globals),
            actor_hidden=plain(policy.hidden()),actor_previous=plain(policy.previous),
            actor_previous_action=plain(policy.previous_action),actor_steps=policy.steps,
            history_count=len(ctx['history']),command_count=len(ctx['commands']),
            actual_history_digest=digest(ctx['history']),actual_commands_digest=digest(ctx['commands']),
            target_manager=plain(vars(planner))))
    def observed_run(*args,**kwargs):return BASE_RUN(*args,**kwargs,decision_observer=observe)
    nav.run_episode=observed_run
    row=BASE_WORKER(job)
    out=Path(job['out'])
    nav._write_json(out/'branch_state.json',{'scope':'Offline observer after old-target action computation, before planning. Prefix fully regenerated; no physical/history reset at branch.','states':observed,'events':made[0].events})
    return row

if __name__=='__main__':
    # The mature batch runner owns deadline enforcement, four-worker pool,
    # per-job output isolation, source provenance and complete row accounting.
    batch=Path(sys.argv[1]);folder=batch.with_suffix('')
    if folder.exists():raise FileExistsError(folder)
    runner.worker=branch_worker
    runner.main()
    (folder/'run_r4_branches.py').write_bytes(Path(__file__).read_bytes())
