#!/usr/bin/env python3
"""R2 paired summaries; reuse R1 definitions, retain each raw evidence pointer."""
from pathlib import Path
import sys,json,csv,statistics,itertools,math,argparse
from analyze_r1 import summary,pairs,validate_coverage,outcome
ROOT=Path(__file__).resolve().parents[1]
METRICS=['time_s','path_length_m','tack_count','target_changes','planning_seconds','reencoding_seconds','cpu_seconds','wall_seconds']
def quantile(values,q):
    a=sorted(values);z=(len(a)-1)*q;i=int(z)
    return a[i]+(a[min(i+1,len(a)-1)]-a[i])*(z-i)
def paired_detail(rows,a,b):
    result=pairs(rows,a,b)
    if result is None:return None
    aa={r['scene_id']:r for r in rows if r['variant']==a}
    bb={r['scene_id']:r for r in rows if r['variant']==b}
    names=result['common_success_scene_ids']
    for metric in METRICS:
        if not names:continue
        av=[aa[n][metric] for n in names];bv=[bb[n][metric] for n in names]
        diff=[y-x for x,y in zip(av,bv)]
        result.setdefault(metric,dict(control_mean=statistics.mean(av),treatment_mean=statistics.mean(bv),paired_mean_difference=statistics.mean(diff)))
        result[metric].update(control_median=statistics.median(av),treatment_median=statistics.median(bv),
            control_p90=quantile(av,.9),treatment_p90=quantile(bv,.9),
            paired_median_difference=statistics.median(diff),paired_difference_p10=quantile(diff,.1),
            paired_difference_p90=quantile(diff,.9))
    return result
def enrich(rows):
    for r in rows:
        job=json.loads((ROOT/r['evidence']).with_name('job.json').read_text());s=job['scene']
        r.update(task_time_limit_s=job['suite']['task_time_limit_s'],layout=s.get('layout',s['map']),
            profile=s['profile'],seed=s['seed'],distance_m=s.get('distance_m',1000))
    return rows
def write_csv(path,rows):
    if not rows:return
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def decision_mechanisms(rows):
    records=[]
    for row in rows:
        raw=ROOT/row['evidence'];logpath=raw.with_name('r2_decisions.json')
        if not logpath.exists():logpath=raw.with_name('r1_decisions.json')
        if not logpath.exists():continue
        logs=json.loads(logpath.read_text());data=json.loads(raw.read_text())
        applied={x['selected_at'] for x in data['target_changes']}
        job=json.loads(raw.with_name('job.json').read_text());cfg=job['config']
        pred=[x for x in logs if x.get('predictive_risk')]
        early=[x for x in pred if x['own_clearance']>=cfg.get('prediction_guard',40)]
        near=[x for x in pred if x['own_clearance']<cfg.get('prediction_guard',40)]
        sole=[]
        for x in pred:
            old=x['old_target'];close=old is not None and old!=job['scene']['goal'] and math.dist(x['position'],old)<=cfg.get('handoff',40)
            if not x['geometric_risk'] and not close and x['reason'] not in ['initial','invalid']:sole.append(x)
        def changed(xx):return sum(x['target']!=x.get('old_target') for x in xx)
        records.append(dict(scene_id=row['scene_id'],variant=row['variant'],plan_records=len(logs),
            actual_target_changes=len(applied),mean_feasible_candidates_per_logged_plan=statistics.mean(x.get('candidate_count',1) for x in logs) if logs else None,prediction_triggers=len(pred),prediction_own_ge_guard=len(early),
            prediction_own_below_guard=len(near),prediction_only_without_handoff=len(sole),
            prediction_changed_proposals=changed(pred),prediction_actually_applied=sum(x['time'] in applied for x in pred),
            early_prediction_actually_applied=sum(x['time'] in applied for x in early),
            prediction_only_actually_applied=sum(x['time'] in applied for x in sole),evidence=str(logpath.relative_to(ROOT))))
    return records
def analyze(folder,reference=None):
    folder=Path(folder).resolve();manifest=json.loads(folder.with_suffix('.json').read_text())
    rows=json.loads((folder/'rows.json').read_text());validate_coverage(rows,manifest)
    assert json.loads((folder/'completion.json').read_text())['complete']
    for r in rows:r['cached_reference']=False
    if reference:
        seen={r['scene_id'] for r in rows};actual={(r['scene_id'],r['variant']) for r in rows}
        refs=json.loads(Path(reference).read_text())
        for r in refs:
            if r['scene_id'] in seen and (r['scene_id'],r['variant']) not in actual:
                r['cached_reference']=True;rows.append(r);actual.add((r['scene_id'],r['variant']))
    rows=enrich(rows);variants=sorted({r['variant'] for r in rows})
    result={'scope':{'evaluation_stage':manifest.get('stage','unspecified'),'new_episodes':len(manifest['jobs']),'cached_reference_episodes':sum(r['cached_reference'] for r in rows),
        'reference':str(reference) if reference else None,'efficiency':'common safe arrivals only; cached compute costs are not a fresh timing benchmark'},
        'overall':summary(rows),'pairs':[paired_detail(rows,a,b) for a,b in itertools.combinations(variants,2)],
        'by_distance':{},'pairs_by_distance':{}}
    for d in sorted({r['distance_m'] for r in rows}):
        rr=[r for r in rows if r['distance_m']==d]
        result['by_distance'][str(d)]=summary(rr)
        result['pairs_by_distance'][str(d)]=[paired_detail(rr,a,b) for a,b in itertools.combinations(variants,2)]
    for field in ['layout','profile']:
        result['by_'+field]={v:summary([r for r in rows if r[field]==v]) for v in sorted({r[field] for r in rows})}
    seeds=sorted({r['scene_id'].split('_')[0] for r in rows})
    result['by_source_seed']={seed:summary([r for r in rows if r['scene_id'].split('_')[0]==seed]) for seed in seeds}
    (folder/'analysis.json').write_text(json.dumps(result,indent=2))
    (folder/'analysis_rows.json').write_text(json.dumps(rows,indent=2))
    flat=[{k:v for k,v in r.items() if k not in ['source_identity','config']}|{'safety_outcome':outcome(r)} for r in rows]
    write_csv(folder/'episodes.csv',flat)
    differences=[]
    for a,b in itertools.combinations(variants,2):
        aa={r['scene_id']:r for r in rows if r['variant']==a};bb={r['scene_id']:r for r in rows if r['variant']==b}
        for n in sorted(aa.keys()&bb.keys()):
            x,y=aa[n],bb[n];common=x['success'] and y['success']
            differences.append({'scene_id':n,'distance_m':x['distance_m'],'layout':x['layout'],'profile':x['profile'],
                'control':a,'treatment':b,'control_success':x['success'],'treatment_success':y['success'],'common_success':common,
                **{m+'_difference':y[m]-x[m] if common else None for m in METRICS}})
    write_csv(folder/'paired_episode_differences.csv',differences)
    write_csv(folder/'raw_index.csv',[{'scene_id':r['scene_id'],'variant':r['variant'],'cached_reference':r['cached_reference'],
        'raw_trace':r['evidence'],'job':str(Path(r['evidence']).with_name('job.json'))} for r in rows])
    write_csv(folder/'decision_mechanisms.csv',decision_mechanisms(rows))
    print(json.dumps(result['overall'],indent=2));return result
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('folder');ap.add_argument('--reference');a=ap.parse_args();analyze(a.folder,a.reference)
