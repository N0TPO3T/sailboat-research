#!/usr/bin/env python3
"""One same-state planner-only replay; never construct/advance a physics environment."""
from pathlib import Path
import sys,json,math,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from sailboat_routing.planner import PlannerInput,StaticMap,CircleObstacle
from sailboat_routing.r1_planner import RouteWaypointPlanner,R1Config
from sailboat_routing.r2_planner import RelayPlanner,RelayConfig
from sailboat_routing.r3_planner import RiskManagedPlanner,RiskConfig
from dataclasses import asdict
def read(p):return json.loads(Path(p).read_text())
def targets(raw):
    changes={c['applied_at']:tuple(c['target']) for c in raw['target_changes']}
    current=tuple(raw['planner_decisions'][0]['input']['current_goal_xy']);out={}
    for x in raw['trajectory']:
        current=changes.get(x['time'],current);out[x['time']]=current
    return out
def main(folder,variant,control,scene=None,rows=None):
    folder=Path(folder).resolve();rows=read(folder/'analysis_rows.json') if rows is None else rows
    lookup={(r['scene_id'],r['variant']):r for r in rows}
    names=[scene] if scene else sorted({r['scene_id'] for r in rows if r['variant']==variant})
    result=None
    for n in names:
        if (n,control) not in lookup:continue
        rr=lookup[n,variant];cr=lookup[n,control];raw=read(ROOT/rr['evidence']);base=read(ROOT/cr['evidence'])
        at=targets(raw);bt=targets(base)
        diff=next((t for t in sorted(at.keys()&bt.keys()) if math.dist(at[t],bt[t])>1e-6),None)
        if diff is None or diff==0:continue
        st=diff-1;events=read((ROOT/rr['evidence']).with_name('r3_decisions.json'))
        risk=next((x for x in events if x['time']==st and x['attempt'] and x.get('proposed_change',x.get('changed'))),None)
        direct=risk is not None
        if risk is None and scene is None:continue
        if risk is None:risk=next((x for x in events if x['time']==st),None)
        physical_equal=all(x['raw'][:12]==y['raw'][:12] and x.get('command')==y.get('command') for x,y in zip(raw['trajectory'],base['trajectory']) if x['time']<=diff)
        if not physical_equal:continue
        job=read((ROOT/rr['evidence']).with_name('job.json'));cj=read((ROOT/cr['evidence']).with_name('job.json'))
        chart=StaticMap(tuple(job['suite']['world_bounds']),tuple(CircleObstacle(tuple(o['center_xy']),o['entity_radius'],o['safety_buffer']) for o in job['suite']['maps'][job['scene']['map']]),25.)
        route=chart.route(tuple(raw['trajectory'][0]['raw'][:2]),tuple(job['scene']['goal']))
        candidate=RiskManagedPlanner(chart,RiskConfig(**job['config']))
        ctype,ctypecfg={'r1':(RouteWaypointPlanner,R1Config),'relay':(RelayPlanner,RelayConfig),'risk':(RiskManagedPlanner,RiskConfig)}[cj['planner_kind']]
        baseline=ctype(chart,ctypecfg(**cj['config']))
        initial=raw['trajectory'][0];v0=PlannerInput(tuple(initial['raw'][:2]),initial['raw'][3],None,route,0.,None)
        ca=candidate.plan(v0);ba=baseline.plan(v0)
        assert math.dist(ca.target_xy,at[0])<1e-6 and math.dist(ba.target_xy,bt[0])<1e-6
        for x in raw['trajectory']:
            t=x['time']
            if t>st:break
            v=PlannerInput(tuple(x['raw'][:2]),x['raw'][3],at[t],route,t,None)
            ca=candidate.plan(v);ba=baseline.plan(v)
        assert math.dist(ca.target_xy,at[diff])<1e-6
        assert math.dist(ba.target_xy,bt[diff])<1e-6
        result=dict(scene_id=n,variant=variant,control=control,selected_at=st,applied_at=diff,
            identical_physical_and_command_prefix_through_application=physical_equal,
            common_input=asdict(v),risk_record=risk,first_divergence_is_direct_risk_change=direct,
            preceding_risk_attempts=[x for x in events if x['time']<=st and x['attempt']][-3:],proposed=asdict(ca),baseline=asdict(ba),
            episode_rows=[cr,rr],raw_evidence=[cr['evidence'],rr['evidence']],
            scope='Planner-only replay over the identical pre-divergence physical history. No environment, no physics stepping, no future wind. Full task outcomes are separate original episodes.')
        break
    out=folder/('case_'+variant+'.json');out.write_text(json.dumps(result,indent=2))
    print(json.dumps(None if result is None else {k:result[k] for k in ['scene_id','selected_at','applied_at','risk_record']},indent=2))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('folder');ap.add_argument('--variant',required=True);ap.add_argument('--control',default='geom80');ap.add_argument('--scene');a=ap.parse_args();main(a.folder,a.variant,a.control,a.scene)
