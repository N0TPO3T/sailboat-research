#!/usr/bin/env python3
"""Variant-paired, scenario-level analysis; failed truncations excluded from efficiency."""
from pathlib import Path
import json,csv,math,sys,collections,random,statistics

def outcome(r):
    if r['min_entity_clearance_m'] is not None and r['min_entity_clearance_m']<=0:return 'entity_collision'
    if r['min_safety_clearance_m'] is not None and r['min_safety_clearance_m']<=0:return 'buffer_violation'
    if r['reason']=='task_limit' and 'task_time_limit_s' in r: return 'time_limit' if r['time_s']>=r['task_time_limit_s'] else 'region_exit'
    return 'safe_arrival' if r['success'] else r['reason']
def interval(k,n):
    z=1.96;p=k/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [c-h,c+h]
def summary(rows):
    ans={}
    for v in sorted({r['variant'] for r in rows}):
        a=[r for r in rows if r['variant']==v];n=len(a);k=sum(r['success'] for r in a)
        ans[v]={'n':n,'safe_arrivals':k,'wilson95':interval(k,n),'outcomes':dict(collections.Counter(outcome(r) for r in a)),
           'mean_wall_s':statistics.mean(r['wall_seconds'] for r in a),'mean_planning_s':statistics.mean(r['planning_seconds'] for r in a),
           'mean_reencoding_s':statistics.mean(r['reencoding_seconds'] for r in a)}
    return ans

def pairs(rows,a,b):
    aa={r['scene_id']:r for r in rows if r['variant']==a};bb={r['scene_id']:r for r in rows if r['variant']==b};names=sorted(aa.keys()&bb.keys())
    if not names:return None
    gain=sum(bb[n]['success'] and not aa[n]['success'] for n in names);loss=sum(aa[n]['success'] and not bb[n]['success'] for n in names)
    common=[n for n in names if aa[n]['success'] and bb[n]['success']];d=gain+loss
    p=min(1.,2*sum(math.comb(d,i) for i in range(min(gain,loss)+1))/2**d) if d else 1.
    rng=random.Random(9021);diff=[int(bb[n]['success'])-int(aa[n]['success']) for n in names]
    boot=sorted(sum(rng.choices(diff,k=len(diff)))/len(diff) for _ in range(3000))
    result={'bootstrap_interpretation':'exploratory percentile; sparse discordances can miscover; [0,0] is not equivalence; use discordant counts and exact test', 'control':a,'treatment':b,'n':len(names),'wins':gain,'losses':loss,'success_difference':sum(diff)/len(diff),'paired_bootstrap95':[boot[75],boot[2924]],'mcnemar_exact_two_sided_p':p,'common_success_n':len(common),'common_success_scene_ids':common}
    for metric in ['time_s','path_length_m','tack_count','target_changes','planning_seconds']:
        if common:result[metric]={'control_mean':statistics.mean(aa[n][metric] for n in common),'treatment_mean':statistics.mean(bb[n][metric] for n in common),'paired_mean_difference':statistics.mean(bb[n][metric]-aa[n][metric] for n in common)}
    return result

def validate_coverage(rows,manifest):
    expected=[(j['scene']['id'],j['variant']) for j in manifest['jobs']]
    actual=[(r['scene_id'],r['variant']) for r in rows]
    if len(set(expected))!=len(expected) or len(set(actual))!=len(actual) or set(actual)!=set(expected):
        raise ValueError('Missing, extra or duplicate scene/variant outcomes; never shrink final denominator')

def analyze(folder):
    rows=json.loads((folder/'rows.json').read_text())
    manifest=json.loads(folder.with_suffix('.json').read_text())
    validate_coverage(rows,manifest)
    assert json.loads((folder/'completion.json').read_text())['complete']
    for r in rows:
        job=json.loads((folder/(r['scene_id']+'__'+r['variant'])/'job.json').read_text());scene=job['scene']
        r['task_time_limit_s']=job['suite']['task_time_limit_s']
        r.update(distance_m=scene.get('distance_m',1000),layout=scene.get('layout',scene['map']),profile=scene['profile'],seed=scene['seed'])
    variants=sorted({r['variant'] for r in rows})
    result={'overall':summary(rows),'pairs':[x for a in variants for b in variants if a<b and (x:=pairs(rows,a,b))],
      'by_distance':{str(d):summary([r for r in rows if int(r.get('distance_m',1000))==d]) for d in sorted({int(r.get('distance_m',1000)) for r in rows})},
      'by_layout':{v:summary([r for r in rows if r['layout']==v]) for v in sorted({r['layout'] for r in rows})},
      'by_profile':{v:summary([r for r in rows if r['profile']==v]) for v in sorted({r['profile'] for r in rows})}}
    (folder/'analysis.json').write_text(json.dumps(result,indent=2))
    flat=[{k:v for k,v in r.items() if k not in ['source_identity','config']}|{'safety_outcome':outcome(r)} for r in rows]
    keys=list(dict.fromkeys(k for r in flat for k in r))
    with (folder/'episodes.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(flat)
    print(json.dumps(result['overall'],indent=2));return result
def figures(folder):
    import os
    root=Path(__file__).resolve().parents[1]
    os.environ["MPLCONFIGDIR"]=str(root/".cache/matplotlib")
    os.environ["XDG_CACHE_HOME"]=str(root/".cache")
    os.environ["TMPDIR"]=str(root/".tmp")
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    rows=json.loads((folder/'rows.json').read_text());stats=json.loads((folder/'analysis.json').read_text())
    primary=json.loads(folder.with_suffix('.json').read_text()).get('primary_variant','geom80')
    variants=[v for v in ['anchor','geom80','narrow','no_margin','estimated','oracle'] if v in stats['overall']]
    colors=dict(zip(variants,['#666666','#0072B2','#009E73','#D55E00','#CC79A7','#E69F00']))
    ds=sorted(stats['by_distance'],key=int);fig,axes=plt.subplots(1,len(ds),figsize=(5*len(ds),4),squeeze=False)
    for ax,d in zip(axes[0],ds):
        a=stats['by_distance'][d]
        for i,v in enumerate(variants):
            if v not in a:continue
            q=a[v];rate=q['safe_arrivals']/q['n'];lo,hi=q['wilson95']
            ax.bar(i,rate,color=colors[v]);ax.errorbar(i,rate,yerr=[[rate-lo],[hi-rate]],fmt='none',ecolor='black',capsize=3)
            ax.text(i,rate+.04,f"{q['safe_arrivals']}/{q['n']}",ha='center',fontsize=8)
        ax.set_xticks(range(len(variants)),variants,rotation=35,ha='right');ax.set_ylim(0,1.15);ax.set_title(f'{int(d)//1000} km');ax.set_ylabel('Safe-arrival fraction');ax.grid(axis='y',alpha=.2)
    fig.suptitle('Frozen evaluation: episode-level Wilson 95% intervals');fig.tight_layout();fig.savefig(folder/'success_by_distance.png',dpi=170);plt.close(fig)
    selected=[]
    for d in ds:
        lookup={(r['scene_id'],r['variant']):r for r in rows if r.get('distance_m',1000)==int(d)}
        names=sorted({n for n,v in lookup})
        # One illustrative win per distance, otherwise a main-method failure, otherwise first case.
        winners=[n for n in names if (n,primary) in lookup and (n,'anchor') in lookup and lookup[n,primary]['success'] and not lookup[n,'anchor']['success']]
        failures=[n for n in names if (n,primary) in lookup and not lookup[n,primary]['success']]
        selected.append((winners or failures or names)[0])
    fig,axes=plt.subplots(1,len(selected),figsize=(6*len(selected),5),squeeze=False)
    for ax,name in zip(axes[0],selected):
        first=next(r for r in rows if r['scene_id']==name);job=json.loads((folder/(name+'__'+first['variant'])/'job.json').read_text())
        for o in job['suite']['maps'][job['scene']['map']]:
            ax.add_patch(Circle(o['center_xy'],o['entity_radius']+o['safety_buffer'],color='gray',alpha=.13));ax.add_patch(Circle(o['center_xy'],o['entity_radius'],color='gray',alpha=.5))
        for v in ['anchor','geom80','narrow','no_margin']:
            rr=next((r for r in rows if r['scene_id']==name and r['variant']==v),None)
            if rr is None:continue
            data=json.loads((folder/(name+'__'+v)/(name+'__'+rr['method']+'.json')).read_text());tr=data['trajectory'];x=[t['raw'][0] for t in tr];y=[t['raw'][1] for t in tr]
            ax.plot(x,y,color=colors[v],label=v+': '+('arrived' if rr['success'] else outcome(rr)),lw=1.3);ax.scatter(x[-1],y[-1],color=colors[v],s=12)
        ax.scatter(*job['scene']['goal'],marker='*',s=80,color='black');ax.set_title(name,fontsize=8);ax.set_aspect('equal',adjustable='datalim');ax.grid(alpha=.2);ax.legend(fontsize=7);ax.set_xlabel('x (m)');ax.set_ylabel('y (m)')
    fig.suptitle('Illustrative complete actual trajectories; original safety buffers shaded');fig.tight_layout();fig.savefig(folder/'trajectory_examples.png',dpi=170);plt.close(fig)
    (folder/'figure_selection.json').write_text(json.dumps({'scene_ids':selected,'primary_variant':primary,'rule':'first sorted main win versus anchor per distance; else main failure; else first case; illustrative, not aggregate evidence'},indent=2))

if __name__=='__main__':
    analyze(Path(sys.argv[1]))
    if '--plots' in sys.argv:figures(Path(sys.argv[1]))
