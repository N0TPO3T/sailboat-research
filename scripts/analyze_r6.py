"""R6 reuses R5 paired summaries and R4 physical metric audit; checks explicit R6 identity."""
from pathlib import Path
import json,sys,math,argparse
from analyze_r5 import analyze
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text())
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
            identity=(row['source_identity']['original_admission_reference']==read(ROOT/'runs/navigation_admission.json')['source_identity'] and row['source_identity']['r6_controller']==job['controller']))
        contract=dict(scene=job['scene'],suite=suite)
        if row['scene_id'] in scene_contracts:checks['paired_environment']=contract==scene_contracts[row['scene_id']]
        else:scene_contracts[row['scene_id']]=contract;checks['paired_environment']=True
        receipts.append(dict(scene_id=row['scene_id'],variant=row['variant'],checks=checks))
    result=dict(episodes=len(rows),all_passed=all(all(x['checks'].values()) for x in receipts),records=receipts)
    (folder/'raw_audit.json').write_text(json.dumps(result,indent=2));assert result['all_passed'],[x for x in receipts if not all(x['checks'].values())]
    print('Raw audit passed:',len(rows))

if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("folder");ap.add_argument("--audit",action="store_true");args=ap.parse_args();folder=Path(args.folder).resolve()
    assert read(folder/"completion.json")["complete"]
    analyze(folder,False)
    if args.audit:audit(folder)
