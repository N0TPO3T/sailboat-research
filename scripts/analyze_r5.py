"""R5 uses existing complete-outcome and paired common-success definitions."""
from pathlib import Path
import json,sys,argparse,itertools
from analyze_r1 import summary,validate_coverage
from analyze_r2 import enrich,paired_detail,write_csv
ROOT=Path(__file__).resolve().parents[1]

def read(p):return json.loads(p.read_text())

def analyze(folder,audit=False):
    folder=Path(folder).resolve();rows=enrich(read(folder/'rows.json'))
    validate_coverage(rows,read(folder.with_suffix('.json')))
    methods=sorted({r['variant'] for r in rows});mechanisms=[]
    for row in rows:
        raw=ROOT/row['evidence'];job=read(raw.with_name('job.json'));s=job['scene']
        row['evaluation_family']=('risk' if s.get('evaluation_family')=='risk' else 'routine')
        row['initial_clearance_stratum_m']=s.get('initial_clearance_stratum_m')
        row['obstacle_bearing_stratum_deg']=s.get('obstacle_bearing_stratum_deg')
        if job['planner_kind']!='tangent':continue
        logs=read(raw.with_name('r2_decisions.json'));data=read(raw)
        applied={x['selected_at']:x for x in data['target_changes']}
        targets=[x for x in logs if x['event']=='target']
        actual=[x for x in targets if x['time'] in applied]
        assert all(tuple(x['target'])==tuple(applied[x['time']]['target']) for x in actual), 'Proposal/application mismatch'
        mechanisms.append(dict(scene_id=row['scene_id'],variant=row['variant'],
            family=row['evaluation_family'],entries=sum(x['event']=='enter' for x in logs),
            exits=sum(x['event']=='exit' for x in logs),
            no_candidate=sum(x['event']=='no_candidate' for x in logs),
            proposed_targets=len(targets),applied_recovery_targets=len(actual),
            first_applied=actual[0]['time']+1 if actual else None,
            initial_recovery=any(x['time']==0 for x in targets),
            success=row['success'],evidence=row['evidence']))
    report={}
    for family in ['all']+sorted({r['evaluation_family'] for r in rows}):
        rr=rows if family=='all' else [r for r in rows if r['evaluation_family']==family]
        report[family]={'episodes':len(rr),'scenes':len({r['scene_id'] for r in rr}),
            'summary':summary(rr),
            'paired':{a+'__to__'+b:paired_detail(rr,a,b) for a,b in itertools.combinations(methods,2)}}
    (folder/'analysis.json').write_text(json.dumps(report,indent=2))
    (folder/'analysis_rows.json').write_text(json.dumps(rows,indent=2))
    write_csv(folder/'episodes.csv',rows);write_csv(folder/'mechanisms.csv',mechanisms)
    (folder/'mechanisms.json').write_text(json.dumps(mechanisms,indent=2))
    write_csv(folder/'raw_index.csv',[dict(scene_id=r['scene_id'],variant=r['variant'],family=r['evaluation_family'],evidence=r['evidence']) for r in rows])
    if audit:
        from analyze_r4 import audit as raw_audit
        raw_audit(folder)
    for family,v in report.items():
        print(family, {m:sum(r['success'] for r in rows if r['variant']==m and (family=='all' or r['evaluation_family']==family)) for m in methods})

def merge_development(run):
    run=Path(run).resolve();rows=[];seen=set();sources=[]
    for name in ['pilot','adaptation','periods','coverage','release']:
        f=run/name
        if not (f/'completion.json').exists():continue
        rr=read(f/'rows.json');validate_coverage(rr,read(f.with_suffix('.json')))
        for r in rr:
            key=(r['scene_id'],r['variant']);assert key not in seen;seen.add(key)
            r['cached_reference']=False;rows.append(r)
        sources.append(str(f/'rows.json'))
    wanted={j['scene']['id'] for j in read(run/'periods.json')['jobs']}
    reference=ROOT/'runs/r4_method_20261004T034532Z/final/rows.json'
    for r in read(reference):
        key=(r['scene_id'],r['variant'])
        if r['scene_id'] in wanted and r['variant'] in ['relay_m120','relay_m160'] and key not in seen:
            r['cached_reference']=True;rows.append(r);seen.add(key)
    rows=enrich(rows);identities={};checks=[]
    for r in rows:
        j=read((ROOT/r['evidence']).with_name('job.json'));s=j['scene'];u=j['suite']
        identity=dict(scene={k:v for k,v in s.items() if k not in ['split','evaluation_family','initial_clearance_stratum_m','initial_clearance_actual_m','obstacle_bearing_stratum_deg','obstacle_bearing_actual_deg','repeat']},suite={k:v for k,v in u.items() if k not in ['purpose','limits','comparison_scenarios','capture_scenarios']})
        sid=r['scene_id']
        if sid in identities:assert identities[sid]==identity,('Physical input mismatch',sid)
        identities[sid]=identity
        r['evaluation_family']=('risk' if s.get('evaluation_family')=='risk' else 'routine')
        checks.append(dict(scene_id=sid,variant=r['variant'],cached_reference=r['cached_reference'],evidence=r['evidence']))
    out=run/'development';out.mkdir(exist_ok=True);report={}
    for family in ['all','routine','risk']:
        rr=rows if family=='all' else [r for r in rows if r['evaluation_family']==family]
        methods=sorted({r['variant'] for r in rr})
        report[family]=dict(summary=summary(rr),paired={a+'__to__'+b:paired_detail(rr,a,b) for a,b in itertools.combinations(methods,2)})
    (out/'analysis.json').write_text(json.dumps(report,indent=2))
    (out/'analysis_rows.json').write_text(json.dumps(rows,indent=2));write_csv(out/'episodes.csv',rows)
    write_csv(out/'raw_index.csv',checks)
    (out/'identity_checks.json').write_text(json.dumps(dict(paired_physical_inputs_equal=True,scenes=len(identities),new_sources=sources,cached_source=str(reference),note='Seen development data; variant denominators differ. Every pair uses its actual intersection. Cached cost is not a fresh runtime benchmark.'),indent=2))
    for family,v in report.items():print(family,{k:(x['safe_arrivals'],x['n']) for k,x in v['summary'].items()})

def frozen_details(folder,main):
    folder=Path(folder).resolve();rows=read(folder/'analysis_rows.json');mm=read(folder/'mechanisms.json')
    lookup={(r['scene_id'],r['variant']):r for r in rows};ids=sorted({r['scene_id'] for r in rows});variants=sorted({r['variant'] for r in rows})
    behavior=[];strata={};effects={}
    for sid in ids:
        baseline=read(ROOT/lookup[sid,'relay_m160']['evidence']);bd=baseline['trajectory']
        for v in variants:
            if v=='relay_m160':continue
            d=read(ROOT/lookup[sid,v]['evidence']);tr=d['trajectory'];same=tr==bd
            first=next((i for i,(a,b) in enumerate(zip(tr,bd)) if a!=b),None)
            behavior.append(dict(scene_id=sid,variant=v,full_trajectory_equal=same,first_trace_difference_time=tr[first]['time'] if first is not None else None,layout=lookup[sid,v]['layout'],family=lookup[sid,v]['evaluation_family']))
    for family in ['routine','risk']:
        rr=[r for r in rows if r['evaluation_family']==family]
        fields=['distance_m','layout','profile'] if family=='routine' else ['initial_clearance_stratum_m','obstacle_bearing_stratum_deg','profile']
        strata[family]={field:{str(value):summary([r for r in rr if r.get(field)==value]) for value in sorted({r.get(field) for r in rr})} for field in fields}
        effects[family]=dict(summary=summary(rr),comparisons={v:paired_detail(rr,v,main) for v in variants if v!=main})
    mechanics={}
    for v in [x for x in variants if x.startswith('tangent')]:
        mechanics[v]={}
        for family in ['routine','risk']:
            recs=[x for x in mm if x['variant']==v and x['family']==family]
            mechanics[v][family]=dict(episodes=len(recs),entered_episodes=sum(x['entries']>0 for x in recs),initial_recovery_episodes=sum(x['initial_recovery'] for x in recs),in_mission_recovery_target_episodes=sum(x['applied_recovery_targets']>0 for x in recs),recovery_targets_applied=sum(x['applied_recovery_targets'] for x in recs),entries=sum(x['entries'] for x in recs),exits=sum(x['exits'] for x in recs),no_candidate=sum(x['no_candidate'] for x in recs),identical_to_relay160=sum(x['variant']==v and x['family']==family and x['full_trajectory_equal'] for x in behavior))
    write_csv(folder/'behavior_comparisons.csv',behavior)
    (folder/'behavior_comparisons.json').write_text(json.dumps(behavior,indent=2))
    (folder/'stratified_results.json').write_text(json.dumps(strata,indent=2))
    (folder/'main_comparisons.json').write_text(json.dumps(effects,indent=2))
    (folder/'mechanism_summary.json').write_text(json.dumps(mechanics,indent=2))
    opens=[x for x in behavior if x['layout']=='open'];(folder/'open_map_invariance.json').write_text(json.dumps(dict(comparisons=len(opens),all_equal=all(x['full_trajectory_equal'] for x in opens),records=opens),indent=2))
    assert all(x['full_trajectory_equal'] for x in opens),'Unexpected open-map behavior; investigate before claims'
    print('Frozen detail analysis:',len(ids),'scenes; open-map equality:',len(opens))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('folder');ap.add_argument('--audit',action='store_true');ap.add_argument('--merge-development',action='store_true');ap.add_argument('--main');a=ap.parse_args()
    if a.merge_development:merge_development(a.folder)
    else:
        analyze(a.folder,a.audit)
        if a.main:frozen_details(a.folder,a.main)
