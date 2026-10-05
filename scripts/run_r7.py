#!/usr/bin/env python3
"""Small R7 experiment runner; reuses original physical/controller implementations."""
import os,sys,json,time,math,hashlib,subprocess,concurrent.futures,multiprocessing,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from sailboat_routing.runtime import configure_cpu
configure_cpu()
import numpy as np
from sailboat_routing.runtime import SeniorModules
from sailboat_routing.continuous import ContinuousPhysics
from sailboat_routing.obstacle_candidate import ObstacleController
from sailboat_routing.frames import LocalFrame
from sailboat_routing.planner import StaticMap,CircleObstacle,NoRouteError,NoLocalTargetError
from sailboat_routing.navigation import bind_time_indexed_wind,_write_json
from sailboat_routing.wind_fields import SyntheticWindField
from sailboat_routing.metrics import segment_circle_clearance
from sailboat_routing.r7_dynamic import *

def worker(job):
    begin=time.time();cpu=time.process_time();out=Path(job['out']);out.mkdir(parents=True,exist_ok=False);_write_json(out/'job.json',job)
    s=job['scene'];cfg=job['config'];limit=int(1.8*s['distance_m']);goal=np.asarray(s['goal']);specs=s.get('vessels',[])
    assert all(float(turn['time']).is_integer() for spec in specs for turn in spec.get('turns',[])), 'target turns must align with1s steps'
    static=tuple(CircleObstacle(tuple(o['center_xy']),o['entity_radius'],60.) for o in s.get('static',[]))
    chart=StaticMap((-2500,s['distance_m']+2500,-3000,3000),static,grid_resolution=25.)
    modules=SeniorModules();policy=ObstacleController(mode='eval');physics=ContinuousPhysics(modules,total_time_limit=limit,world_radius_limit=s['distance_m']+3000)
    planner=EncounterSupervisor(chart,cfg);field=SyntheticWindField(s['seed']+100000,math.radians(s['base_direction_degrees']),s['profile'],horizon=limit+1)
    raw=physics.reset(s['seed'],s['base_direction_degrees']);bind_time_indexed_wind(physics,field)
    observed=observe(specs,0,raw[:2]);target=planner.plan(raw[:2],raw[3],np.zeros(2),None,goal,0,observed)
    physics.set_goal(target);raw=physics.raw.copy();frame=LocalFrame.for_leg(raw[:2],target);observation=encode(frame,static,observed,raw);policy.reset(observation)
    history=[raw.copy()];oh=[observed];commands=[];changes=[];pending=[]
    def truth(t):return [dict(id=o['id'],position=target_truth(o,t)[0].tolist()) for o in specs]
    trace=[dict(time=0,raw=raw.tolist(),targets=truth(0),observations=observed,target=list(target))]
    minstatic=segment_circle_clearance(raw[:2],raw[:2],static)['safety_m'];mindynamic=math.inf;minentity=math.inf;length=0.;arrived=False;reason='time_limit';complete=True;plans=[]
    try:
        for t in range(min(limit,job.get('max_steps',limit))):
            if time.time()>job['deadline']:raise TimeoutError('R7 shared deadline')
            decision=policy.act(observation,record_features=False)
            older=max(0,len(history)-11);velocity=(raw[:2]-history[older][:2])/max(1,len(history)-1-older)
            now=time.perf_counter()
            try:newtarget=planner.plan(raw[:2],raw[3],velocity,target,goal,t,observed)
            except (NoRouteError,NoLocalTargetError) as error:reason=type(error).__name__;break
            plans.append(time.perf_counter()-now)
            before=raw.copy();raw,_,_,truncated,info=physics.step(decision.action);raw=raw.copy()
            history.append(raw.copy());commands.append(decision.action.copy());length+=float(np.linalg.norm(raw[:2]-before[:2]))
            # A delayed sensor supplies an actual older snapshot; timestamp stays old.
            delay=int(cfg.get('observation_delay',0));ot=max(0,t+1-delay)
            observed=observe(specs,ot,history[ot][:2]);oh.append(observed)
            clear=segment_circle_clearance(before[:2],raw[:2],static);minstatic=min(minstatic,clear['safety_m']);minentity=min(minentity,clear['entity_m'])
            ds=[]
            for o in specs:
                q0,_=target_truth(o,t);q1,_=target_truth(o,t+1);d,f=relative_minimum(before[:2],raw[:2],q0,q1)
                ds.append(dict(id=o['id'],distance=d,fraction=f,margin=d-SAFE));mindynamic=min(mindynamic,d-SAFE);minentity=min(minentity,d-ENTITY)
            trace.append(dict(time=t+1,raw=raw.tolist(),targets=truth(t+1),observations=observed,target=list(target),command=decision.action.tolist(),physical_action=np.asarray(info['physical_action']).tolist(),dynamic=ds,static_margin=clear['safety_m']))
            if info['integration_failed']:reason='integration_failed';break
            if minentity<=0:reason='entity_collision';break
            if np.linalg.norm(raw[:2]-goal)<=10:arrived=True;reason='arrived';break
            if truncated:reason='task_limit';break
            # Same1s application for all, optional common extra actuation delay.
            if np.linalg.norm(np.asarray(newtarget)-target)>1e-6 and not pending:
                pending.append((t+1+int(cfg.get('goal_delay',0)),newtarget,t))
            if pending and pending[0][0]<=t+1:
                _,newtarget,selected_at=pending.pop(0)
                snap=physics.continuity_snapshot();physics.set_goal(newtarget);frame=LocalFrame.for_leg(raw[:2],newtarget)
                observation,elapsed=replay(policy,frame,static,oh,history,commands)
                assert snap==physics.continuity_snapshot()
                changes.append(dict(selected_at=selected_at,applied_at=t+1,target=list(newtarget),reencode_seconds=elapsed,continuity_unchanged=True));target=newtarget
            else:observation=encode(frame,static,observed,raw,before)
        else:
            if job.get('max_steps',limit)<limit:complete=False;reason='bounded_smoke'
    except Exception as e:
        reason=type(e).__name__+':'+str(e);complete=False
    finally:policy.close();physics.close()
    row=dict(scene_id=s['id'],variant=job['variant'],family=s['family'],distance_m=s['distance_m'],success=bool(arrived and minstatic>0 and mindynamic>0),arrived=arrived,complete=complete,reason=reason,time_s=len(commands),path_length_m=length,min_dynamic_margin=mindynamic,min_static_margin=minstatic,min_entity_margin=minentity,target_changes=len(changes),interventions=sum(e['event']=='enter' for e in planner.events),releases=sum(e['event']=='release' for e in planner.events),reencoding_seconds=sum(c['reencode_seconds'] for c in changes),max_reencoding_seconds=max([c['reencode_seconds'] for c in changes],default=0),planning_seconds=sum(plans),max_planning_seconds=max(plans,default=0),wall_seconds=time.time()-begin,cpu_seconds=time.process_time()-cpu)
    _write_json(out/'trace.json',dict(scene=s,config=cfg,row=row,trajectory=trace,changes=changes,decisions=planner.log,events=planner.events,wind=field.diagnostics()))
    _write_json(out/'row.json',row);return row

def main():
    manifest=Path(sys.argv[1]);batch=json.loads(manifest.read_text());run=Path(batch['run']).resolve();assert run.is_relative_to((ROOT/'runs').resolve())
    plan=json.loads((run/'plan.json').read_text());assert time.time()<plan['deadline_epoch']
    folder=manifest.with_suffix('');folder.mkdir(exist_ok=False);source=folder/'source';source.mkdir();files=[ROOT/'src/sailboat_routing/r7_dynamic.py',Path(__file__)]
    for f in files:(source/f.name).write_bytes(f.read_bytes())
    _write_json(folder/'provenance.json',dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),sources={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},workers=4,threads=1,gpu_hours=0,parent_pid=os.getpid(),started=time.time()))
    jobs=[]
    for j in batch['jobs']:
        j=copy.deepcopy(j);j.update(out=str(folder/(j['scene']['id']+'__'+j['variant'])),deadline=plan['deadline_epoch']);jobs.append(j)
    rows=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context('spawn')) as pool:
        for f in concurrent.futures.as_completed([pool.submit(worker,j) for j in jobs]):
            row=f.result();rows.append(row);_write_json(folder/'rows.json',rows);print('R7',len(rows),'/',len(jobs),row['scene_id'],row['variant'],row['success'],row['reason'],row['min_dynamic_margin'],flush=True)
    _write_json(folder/'completion.json',dict(complete=True,episodes=len(rows),finished=time.time()))
if __name__=='__main__':main()
