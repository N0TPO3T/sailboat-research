"""R4 evidence joins; physical traces remain the canonical source."""
from pathlib import Path
import json, sys, math, argparse
from analyze_r2 import analyze, write_csv
ROOT = Path(__file__).resolve().parents[1]

def read(p):
    return json.loads(p.read_text())

def branches(run):
    sys.path.insert(0,str(ROOT/'src'))
    from sailboat_routing.wind_fields import SyntheticWindField
    controls = {r['scene_id']: r for r in read(run/'replay_check/rows.json')}
    records, checks, field_checks = [], [], []
    for batch in ['branches1', 'branches_short']:
        for row in read(run/batch/'rows.json'):
            raw = ROOT/row['evidence']; data = read(raw); state = read(raw.parent/'branch_state.json')
            job=read(raw.with_name('job.json'));scene=job['scene']
            field=SyntheticWindField(scene['seed']+100000,math.radians(scene['base_direction_degrees']),
                scene['profile'],horizon=job['suite']['task_time_limit_s']+1)
            errors=[abs(field.sample(x['raw'][:2],x['time'])[1]-x['wind_direction_world']) for x in data['trajectory']]
            field_checks.append(dict(scene_id=row['scene_id'],variant=row['variant'],samples=len(errors),max_error_rad=max(errors)))
            control = controls[row['scene_id']]; cr = ROOT/control['evidence']; cd = read(cr)
            observed = state['states'][0]; t = observed['time']
            cs = next(x for x in read(cr.parent/'branch_state.json')['states'] if x['time'] == t)
            exact = observed == cs
            prefix = data['trajectory'][:int(t)+2] == cd['trajectory'][:int(t)+2]
            ev = state['events'][0]
            actual = next((x for x in data['target_changes'] if x['selected_at'] == t), None)
            applied_ok = (actual is not None and actual['applied_at'] == t+1) if ev['proposal_changed'] else actual is None
            checks.append(dict(scene_id=row['scene_id'], variant=row['variant'], state_exact=exact,
                trajectory_prefix_exact=prefix, original_application_timing=applied_ok))
            rec = dict(scene_id=row['scene_id'], variant=row['variant'], time=t,
                feasible=ev['geometrically_valid'], changed=ev['proposal_changed'],
                applied_at=actual['applied_at'] if actual else None,
                control_success=control['success'], branch_success=row['success'],
                control_time_s=control['time_s'], branch_time_s=row['time_s'],
                control_min_clearance=control['min_safety_clearance_m'], branch_min_clearance=row['min_safety_clearance_m'],
                alternative=ev['alternative'], old_target=ev['old_target'], position=ev['position'],
                raw=row['evidence'], control_raw=control['evidence'])
            for label, d in [('control', cd), ('branch', data)]:
                for horizon in [60, 120]:
                    window = [x for x in d['trajectory'] if t < x['time'] <= t+horizon]
                    values = [x['safety_clearance_m'] for x in window if x.get('safety_clearance_m') is not None]
                    rec[f'{label}_clearance_min_{horizon}s'] = min(values) if values else None
                    rec[f'{label}_observed_until_{horizon}s'] = window[-1]['time'] if window else None
                    if window:
                        rec[f'{label}_final_distance_{horizon}s'] = math.dist(window[-1]['raw'][:2], d['scene']['goal'])
            records.append(rec)
    write_csv(run/'branch_outcomes.csv', records)
    (run/'branch_outcomes.json').write_text(json.dumps(records, indent=2))
    (run/'branch_validation.json').write_text(json.dumps(dict(comparisons=len(checks),
        all_exact=all(all(x[k] for k in ['state_exact','trajectory_prefix_exact','original_application_timing']) for x in checks),
        checks=checks), indent=2))
    (run/'branch_field_validation.json').write_text(json.dumps(dict(
        scope='Offline recomputation at each branch own actual position and time; no environment advanced.',
        all_equal=all(x['max_error_rad']<1e-12 for x in field_checks),records=field_checks),indent=2))

def execution(folder):
    records=[]
    for row in read(folder/'analysis_rows.json'):
        raw=ROOT/row['evidence']; job=read(raw.with_name('job.json'))
        if job['planner_kind'] != 'execution': continue
        logs=read(raw.with_name('r2_decisions.json')); data=read(raw)
        applied={x['selected_at']:x for x in data['target_changes']}
        actual=[x for x in logs if x['changed'] and x['time'] in applied]
        attempts=[x for x in logs if x.get('event','intervention_attempt')=='intervention_attempt']
        records.append(dict(scene_id=row['scene_id'],variant=row['variant'],attempts=len(attempts),
            deferred_responses=sum(x.get('event')=='response_grace' for x in logs),
            feasible_changes=sum(x['changed'] for x in logs),actual_interventions=len(actual),
            first_actual=actual[0]['time'] if actual else None,
            nonpositive_progress_attempts=sum(x['progress_mps']<=0 for x in attempts),
            success=row['success'],raw=row['evidence']))
    write_csv(folder/'execution_mechanisms.csv',records)
    summary={v:dict(episodes=sum(x['variant']==v for x in records),
        intervened_episodes=sum(x['variant']==v and x['actual_interventions']>0 for x in records),
        attempts=sum(x['attempts'] for x in records if x['variant']==v),
        deferred_responses=sum(x['deferred_responses'] for x in records if x['variant']==v),
        actual_interventions=sum(x['actual_interventions'] for x in records if x['variant']==v)) for v in sorted({x['variant'] for x in records})}
    (folder/'execution_summary.json').write_text(json.dumps(summary,indent=2))
    return summary

def audit(folder):
    import numpy as np
    sys.path.insert(0,str(ROOT/'src'))
    from sailboat_routing.planner import CircleObstacle
    from sailboat_routing.metrics import segment_circle_clearance
    rows=read(folder/'rows.json');manifest=read(folder.with_suffix('.json'))
    from analyze_r1 import validate_coverage
    validate_coverage(rows,manifest)
    receipts=[];scene_contracts={}
    for row in rows:
        raw=ROOT/row['evidence'];data=read(raw);job=read(raw.with_name('job.json'));tr=data['trajectory'];suite=job['suite']
        circles=tuple(CircleObstacle(tuple(o['center_xy']),o['entity_radius'],o['safety_buffer']) for o in suite['maps'][job['scene']['map']])
        assert all(o.safety_buffer==60 for o in circles)
        assert suite['goal_radius_m']==10 and suite['task_time_limit_s']==int(1.8*job['scene']['distance_m'])
        xy=[np.asarray(x['raw'][:2],dtype=np.float32) for x in tr]
        clear=[segment_circle_clearance(xy[max(0,i-1)],p,circles) for i,p in enumerate(xy)]
        entity=min(x['entity_m'] for x in clear);safety=min(x['safety_m'] for x in clear)
        path=sum(float(np.linalg.norm(b-a)) for a,b in zip(xy,xy[1:]))
        eq=lambda a,b: b is None and math.isinf(a) or b is not None and abs(a-b)<1e-6
        checks=dict(complete=row['complete'],entity=eq(entity,row['min_entity_clearance_m']),
            safety=eq(safety,row['min_safety_clearance_m']),path=abs(path-row['path_length_m'])<1e-6,
            steps=row['steps']==len(tr)-1,time=row['time_s']==tr[-1]['time'],
            clock=all(x['time']==i for i,x in enumerate(tr)),
            target_count=row['target_changes']==len(data['target_changes']),
            application_timing=all(x['applied_at']==x['selected_at']+1 and x['continuity_unchanged'] for x in data['target_changes']),
            success=row['success']==bool(np.linalg.norm(xy[-1]-job['scene']['goal'])<=10 and safety>0),
            identity=row['source_identity']==read(ROOT/'runs/navigation_admission.json')['source_identity'])
        contract=dict(scene=job['scene'],suite=suite)
        if row['scene_id'] in scene_contracts:checks['paired_environment']=contract==scene_contracts[row['scene_id']]
        else:scene_contracts[row['scene_id']]=contract;checks['paired_environment']=True
        receipts.append(dict(scene_id=row['scene_id'],variant=row['variant'],checks=checks))
    result=dict(episodes=len(rows),all_passed=all(all(x['checks'].values()) for x in receipts),records=receipts)
    (folder/'raw_audit.json').write_text(json.dumps(result,indent=2));assert result['all_passed'],[x for x in receipts if not all(x['checks'].values())]
    print('Raw audit passed:',len(rows))

if __name__ == '__main__':
    ap=argparse.ArgumentParser();ap.add_argument('folder');ap.add_argument('--reference');ap.add_argument('--branches',action='store_true');ap.add_argument('--audit',action='store_true');args=ap.parse_args()
    folder=Path(args.folder).resolve()
    if args.audit:audit(folder)
    elif args.branches: branches(folder)
    else: analyze(folder,args.reference);print(json.dumps(execution(folder),indent=2))
