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

def merge_development(run):
    """Merge seen R6 episodes with explicitly cached, physically matched R5 controls."""
    import itertools,copy
    from analyze_r1 import summary
    from analyze_r2 import enrich,paired_detail,write_csv
    rows=[];seen=set();sources=[]
    for phase in ['screen','adaptation','validation']:
        folder=run/phase
        assert read(folder/'completion.json')['complete'] and read(folder/'raw_audit.json')['all_passed']
        for original in read(folder/'rows.json'):
            row=copy.deepcopy(original);row['cached_reference']=False
            if row['variant']=='legacy':row['variant']='relay_m160'
            key=(row['scene_id'],row['variant']);assert key not in seen;seen.add(key);rows.append(row)
        sources.append(str(folder/'rows.json'))
    cache=ROOT/'runs/r5_literature_20261004T080700Z/final/rows.json'
    for original in read(cache):
        if original['variant'] not in ['relay_m120','relay_m160','tangent_exit90']:continue
        row=copy.deepcopy(original);key=(row['scene_id'],row['variant'])
        if key in seen:continue
        row['cached_reference']=True;rows.append(row);seen.add(key)
    rows=enrich(rows);contracts={};checks=[]
    for row in rows:
        job=read((ROOT/row['evidence']).with_name('job.json'));scene=job['scene'];suite=job['suite']
        contract=dict(scene={k:scene[k] for k in ['id','seed','profile','base_direction_degrees','goal','map','distance_m','layout']},
            suite={k:suite[k] for k in ['maps','world_bounds','world_radius_limit_m','task_time_limit_s','goal_radius_m']})
        sid=row['scene_id']
        if sid in contracts:assert contracts[sid]==contract,('Physical contract mismatch',sid)
        else:contracts[sid]=contract
        row['evaluation_family']='risk' if scene.get('evaluation_family')=='risk' else 'routine'
        checks.append(dict(scene_id=sid,variant=row['variant'],cached_reference=row['cached_reference'],evidence=row['evidence']))
    out=run/'development';out.mkdir(exist_ok=True);report={}
    for family in ['all','routine','risk']:
        rr=rows if family=='all' else [x for x in rows if x['evaluation_family']==family]
        methods=sorted({x['variant'] for x in rr})
        report[family]=dict(summary=summary(rr),paired={a+'__to__'+b:paired_detail(rr,a,b) for a,b in itertools.combinations(methods,2)})
    (out/'analysis_rows.json').write_text(json.dumps(rows,indent=2));(out/'analysis.json').write_text(json.dumps(report,indent=2));write_csv(out/'episodes.csv',rows);write_csv(out/'raw_index.csv',checks)
    (out/'identity_checks.json').write_text(json.dumps(dict(paired_physical_inputs_equal=True,scenes=len(contracts),sources=sources,cached_source=str(cache),note='All scenes are seen development; method denominators differ. Pairwise results use actual intersection. Cached wall times are not controlled runtime benchmarks.'),indent=2))
    for family,v in report.items():print(family,{k:(x['safe_arrivals'],x['n']) for k,x in v['summary'].items()})

def details(folder,main):
    import statistics
    from analyze_r1 import summary,outcome
    from analyze_r2 import paired_detail,write_csv
    rows=read(folder/'analysis_rows.json');methods=sorted({r['variant'] for r in rows});lookup={(r['scene_id'],r['variant']):r for r in rows};report={};pair_rows=[]
    groups={'all':rows,'routine':[r for r in rows if r['evaluation_family']=='routine'],'risk':[r for r in rows if r['evaluation_family']=='risk']}
    for d in [1000,3000,5000]:groups[f'routine_{d}']=[r for r in rows if r['evaluation_family']=='routine' and r['distance_m']==d]
    for group,rr in groups.items():
        comparisons={};ids=sorted({r['scene_id'] for r in rr})
        for v in methods:
            if v==main:continue
            common=[sid for sid in ids if (sid,v) in lookup and (sid,main) in lookup]
            gain=[sid for sid in common if lookup[sid,main]['success'] and not lookup[sid,v]['success']]
            loss=[sid for sid in common if not lookup[sid,main]['success'] and lookup[sid,v]['success']]
            safe=[sid for sid in common if lookup[sid,main]['success'] and lookup[sid,v]['success']]
            ratios=[lookup[sid,main]['time_s']/lookup[sid,v]['time_s'] for sid in safe]
            comparisons[v]=dict(paired_scenes=len(common),safe_gains=gain,safe_losses=loss,common_safe=len(safe),median_time_ratio=statistics.median(ratios) if ratios else None,paired=paired_detail(rr,v,main))
            if group=='all':
                for sid in common:
                    a=lookup[sid,v];b=lookup[sid,main];pair_rows.append(dict(scene_id=sid,control=v,main=main,control_outcome=outcome(a),main_outcome=outcome(b),control_time_s=a['time_s'],main_time_s=b['time_s'],common_safe=a['success'] and b['success'],time_ratio=b['time_s']/a['time_s'] if a['success'] and b['success'] else None))
        timeliness={v:{str(fraction):sum(r['success'] and r['time_s']<=fraction*1.8*r['distance_m'] for r in rr if r['variant']==v)/sum(r['variant']==v for r in rr) for fraction in [.25,.5,.75,1.]} for v in methods if any(r['variant']==v for r in rr)}
        report[group]=dict(summary=summary(rr),comparisons=comparisons,safe_completion_fraction=timeliness)
    (folder/'main_comparisons.json').write_text(json.dumps(report,indent=2));write_csv(folder/'paired_episodes.csv',pair_rows)
    costs=[]
    for row in rows:
        changes=read(ROOT/row['evidence'])['target_changes']
        costs.append(dict(scene_id=row['scene_id'],variant=row['variant'],steps=row['steps'],cpu_seconds=row['cpu_seconds'],wall_seconds=row['wall_seconds'],reencoding_seconds=row['reencoding_seconds'],max_single_reencoding_seconds=max([x['wall_seconds'] for x in changes],default=0)))
    (folder/'compute_costs.json').write_text(json.dumps(costs,indent=2));write_csv(folder/'compute_costs.csv',costs)
    print('Main details',main)

if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("folder");ap.add_argument("--audit",action="store_true");ap.add_argument("--merge-development",action="store_true");ap.add_argument("--main");args=ap.parse_args();folder=Path(args.folder).resolve()
    if args.merge_development:
        merge_development(folder);sys.exit(0)
    assert read(folder/"completion.json")["complete"]
    analyze(folder,False)
    if args.audit:audit(folder)
    if args.main:details(folder,args.main)
