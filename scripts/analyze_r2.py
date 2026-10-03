#!/usr/bin/env python3
"""R2 paired summaries; reuse R1 definitions, retain each raw evidence pointer."""
from pathlib import Path
import sys,json,csv,statistics,itertools,math,argparse
from analyze_r1 import summary,pairs,validate_coverage,outcome
ROOT=Path(__file__).resolve().parents[1]
METRICS=['time_s','path_length_m','tack_count','target_changes','planning_seconds']
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
    result={'scope':{'new_episodes':len(manifest['jobs']),'cached_reference_episodes':sum(r['cached_reference'] for r in rows),
        'reference':str(reference) if reference else None,'efficiency':'common safe arrivals only; cached compute costs are not a fresh timing benchmark'},
        'overall':summary(rows),'pairs':[paired_detail(rows,a,b) for a,b in itertools.combinations(variants,2)],
        'by_distance':{},'pairs_by_distance':{}}
    for d in sorted({r['distance_m'] for r in rows}):
        rr=[r for r in rows if r['distance_m']==d]
        result['by_distance'][str(d)]=summary(rr)
        result['pairs_by_distance'][str(d)]=[paired_detail(rr,a,b) for a,b in itertools.combinations(variants,2)]
    for field in ['layout','profile']:
        result['by_'+field]={v:summary([r for r in rows if r[field]==v]) for v in sorted({r[field] for r in rows})}
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
    print(json.dumps(result['overall'],indent=2));return result
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('folder');ap.add_argument('--reference');a=ap.parse_args();analyze(a.folder,a.reference)
