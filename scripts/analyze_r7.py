#!/usr/bin/env python3
"""R7 saved-log summary and figures, no environment execution."""
from pathlib import Path
import sys,json,csv,math,os
os.environ["MPLCONFIGDIR"]=str(Path(__file__).resolve().parents[1]/".cache/matplotlib")
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
ROOT=Path(__file__).resolve().parents[1]
R=Path(sys.argv[1]);F=R/'figures';F.mkdir(exist_ok=True)
colors={'current':'#1769aa','commit':'#df6819','no_commit':'#42944a','compact':'#8d52a2'}
labels={'current':'Current-position R6','commit':'CPA + commitment','no_commit':'CPA without commitment','compact':'CPA offset180'}
batches=['pilot','development','refinement','confirmation','stationary','regression','long','sensitivity','latency']
allrows=[];summary={}
for name in batches:
 f=R/name/'rows.json'
 if not f.exists():continue
 rows=json.loads(f.read_text());allrows += [dict(batch=name,**row) for row in rows]
 variants=sorted(set(x['variant'] for x in rows));by={}
 for v in variants:
  a=[x for x in rows if x['variant']==v]
  by[v]=dict(n=len(a),safe=sum(x['success'] for x in a),arrived=sum(x['arrived'] for x in a),dynamic_violations=sum(x['min_dynamic_margin'] is not None and x['min_dynamic_margin']<=0 for x in a),static_violations=sum(x['min_static_margin'] is not None and x['min_static_margin']<=0 for x in a),entity_collisions=sum(x['min_entity_margin'] is not None and x['min_entity_margin']<=0 for x in a),max_reencoding=max(x['max_reencoding_seconds'] for x in a),max_planning=max(x['max_planning_seconds'] for x in a),mean_interventions=float(np.mean([x['interventions'] for x in a])))
 pairs={}
 for x in rows:pairs.setdefault(x['scene_id'],{})[x['variant']]=x
 compare={}
 for v in variants:
  if v=='current':continue
  matched=[a for a in pairs.values() if 'current' in a and v in a];common=[a for a in matched if a['current']['success'] and a[v]['success']]
  dt=[a[v]['time_s']-a['current']['time_s'] for a in common];dl=[a[v]['path_length_m']-a['current']['path_length_m'] for a in common]
  compare[v]=dict(paired=len(matched),gains=sum(a[v]['success'] and not a['current']['success'] for a in matched),losses=sum(a['current']['success'] and not a[v]['success'] for a in matched),common_safe=len(common),time_delta_mean=float(np.mean(dt)) if dt else None,time_delta_median=float(np.median(dt)) if dt else None,time_delta_p90=float(np.quantile(dt,.9)) if dt else None,path_delta_mean=float(np.mean(dl)) if dl else None)
 summary[name]=dict(methods=by,comparisons=compare)
(R/'analysis.json').write_text(json.dumps(summary,indent=2));
with (R/'all_rows.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(allrows[0]));w.writeheader();w.writerows(allrows)
if not (R/'confirmation/rows.json').exists():print(json.dumps(summary,indent=2));sys.exit()
rows=json.loads((R/'confirmation/rows.json').read_text());pairs={}
for x in rows:pairs.setdefault(x['scene_id'],{})[x['variant']]=x
# Examples selected AFTER evaluation for explanation, never for headline denominators.
win=max(pairs,key=lambda s:(int(pairs[s]['commit']['success'])-int(pairs[s]['current']['success']), (pairs[s]['commit']['min_dynamic_margin'] or 0)-(pairs[s]['current']['min_dynamic_margin'] or 0)))
loss=max(pairs,key=lambda s:(int(pairs[s]['current']['success'])-int(pairs[s]['commit']['success']),pairs[s]['commit']['time_s']-pairs[s]['current']['time_s']))
def get(batch,scene,v):return json.loads((R/batch/(scene+'__'+v)/'trace.json').read_text())
def save(fig,name,data):
 fig.tight_layout();fig.savefig(F/(name+'.png'),dpi=170);fig.savefig(F/(name+'.svg'));plt.close(fig);(F/(name+'.json')).write_text(json.dumps(data))
def track(ax,d,v):
 tr=d['trajectory'];p=np.array([x['raw'][:2] for x in tr]);t=np.array([x['time'] for x in tr]);q=np.array([x['targets'][0]['position'] for x in tr]) if tr[0]['targets'] else None
 ax.plot(p[:,0],p[:,1],color=colors[v],label=labels[v]);ax.scatter(*d['scene']['goal'],marker='*',s=95,color='black',label='Mission goal')
 if q is not None:
  ax.plot(q[:,0],q[:,1],'--',color='#555555',label='Target vessel')
  ticks=[int(z) for z in np.linspace(0,len(tr)-1,5)]
  for z in ticks:
   ax.scatter(*p[z],s=16,color=colors[v]);ax.scatter(*q[z],s=16,color='#555555',marker='s');ax.plot([p[z,0],q[z,0]],[p[z,1],q[z,1]],':',color='#888888',alpha=.35);ax.annotate(str(z)+'s',p[z],fontsize=7,xytext=(3,3),textcoords='offset points');ax.annotate(str(z)+'s',q[z],fontsize=7,xytext=(3,-9),textcoords='offset points')
  k=min(range(1,len(tr)),key=lambda i:min(x['margin'] for x in tr[i]['dynamic']));ax.add_patch(Circle(q[k],80,fill=False,ls=':',color='#777777'));ax.add_patch(Circle(q[k],15,color='#777777',alpha=.25))
 for o in d['scene'].get('static',[]):
  ax.add_patch(Circle(o['center_xy'],o['entity_radius'],color='gray',alpha=.5));ax.add_patch(Circle(o['center_xy'],o['entity_radius']+60,fill=False,ls='--',color='gray'))
 for e in d['events'][:2]:
  k=min(int(e['time']),len(tr)-1);ax.scatter(*p[k],marker='D' if e['event']=='release' else '^',color='black',s=35)
  if e['event']=='enter':ax.scatter(*e['target'],marker='x',color=colors[v],s=40)
 ax.set_aspect('equal',adjustable='datalim');ax.set_xlabel('World x (m)');ax.set_ylabel('World y (m)');ax.grid(alpha=.2);ax.set_title(labels[v]+f" | safe={d['row']['success']}, {d['row']['time_s']}s",fontsize=10)
for name,scene in [('01_encounter',win),('03_adverse',loss)]:
 ds={v:get('confirmation',scene,v) for v in ['current','commit']};fig,axs=plt.subplots(1,2,figsize=(12,5))
 for ax,v in zip(axs,ds):track(ax,ds[v],v);ax.legend(fontsize=7,loc='best')
 fig.suptitle(scene+' | recorded trajectories; dotted rings:80m relative safety',fontsize=11);save(fig,name,ds)
fig,axs=plt.subplots(2,1,figsize=(11,7),sharex=True);ds={v:get('confirmation',win,v) for v in ['current','commit','no_commit']}
for v,d in ds.items():
 tr=d['trajectory'];tm=[x['time']-1+z['fraction'] for x in tr[1:] for z in x['dynamic']];m=[z['margin'] for x in tr[1:] for z in x['dynamic']];axs[0].plot(tm,m,label=labels[v],color=colors[v]);p=np.array([x['raw'][:2] for x in tr]);axs[1].plot([x['time'] for x in tr],np.linalg.norm(p-np.array(d['scene']['goal']),axis=1),color=colors[v],label=labels[v])
for e in ds['commit']['events']:
 axs[0].axvline(e['time'],ls=':',color='#df6819',alpha=.5)
 if e['event']=='enter':axs[0].axvline(e['time']+1,ls='--',color='#df6819',alpha=.6)
axs[0].axhline(0,color='red',ls='--');axs[0].set_ylabel('Synchronous separation minus80m (m)');axs[1].set_ylabel('Distance to mission goal (m)');axs[1].set_xlabel('Physical time (s)');axs[0].legend();axs[0].set_title(win+' | CPA event dotted; applied reference dashed');[a.grid(alpha=.2) for a in axs];save(fig,'02_margin_progress',ds)
fig,axs=plt.subplots(1,2,figsize=(12,4.8));families=['overtaking','crossing','nonconflict','mixed'];vs=['current','commit','no_commit']
for k,v in enumerate(vs):
 vals=[]
 for fam in families:
  a=[x for x in rows if x['variant']==v and x['family']==fam];vals.append(sum(x['success'] for x in a)/len(a));
 bars=axs[0].bar(np.arange(4)+(k-1)*.25,vals,.24,color=colors[v],label=labels[v]);
 for j,b in enumerate(bars):
  a=[x for x in rows if x['variant']==v and x['family']==families[j]];axs[0].text(b.get_x()+b.get_width()/2,b.get_height()+.015,f"{sum(x['success'] for x in a)}/{len(a)}",ha='center',fontsize=7)
axs[0].set_xticks(range(4),families,rotation=15);axs[0].set_ylim(0,1.15);axs[0].set_ylabel('Complete safe arrival fraction');axs[0].legend(fontsize=7,loc='lower left')
for k,v in enumerate(vs[1:]):
 vals=[a[v]['time_s']-a['current']['time_s'] for a in pairs.values() if a[v]['success'] and a['current']['success']];axs[1].scatter(np.full(len(vals),k)+np.linspace(-.12,.12,len(vals)),vals,color=colors[v],alpha=.7);axs[1].plot([k-.2,k+.2],[np.median(vals)]*2,color='black')
axs[1].axhline(0,color='gray',ls='--');axs[1].set_xticks([0,1],['Commit','No commit']);axs[1].set_ylabel('Extra physical seconds vs current\n(pairwise common safe arrivals only)');axs[1].grid(alpha=.2);save(fig,'04_confirmation',dict(rows=rows,summary=summary['confirmation']))
if (R/'long/rows.json').exists():
 lr=json.loads((R/'long/rows.json').read_text());ss=[win]+[next(x['scene_id'] for x in lr if x['distance_m']==dist) for dist in [3000,5000]];fig,axs=plt.subplots(1,3,figsize=(15,4.8));dd=[]
 for ax,sc,ba in zip(axs,ss,['confirmation','long','long']):
  d=get(ba,sc,'current');dd.append(d);track(ax,d,'current');ax.set_title(f"{d['scene']['distance_m']/1000:g}km | {d['row']['time_s']}s, safe={d['row']['success']}");ax.legend(fontsize=6)
 save(fig,'05_continuous',dd)
(R/'examples.json').write_text(json.dumps(dict(encounter=win,adverse=loss)))
(F/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>R7 real trajectories</title><style>body{max-width:1300px;margin:auto;font-family:sans-serif}img{width:100%}</style><h1>R7 recorded dynamic encounters</h1><p>All curves from saved physical logs. Synchronous time labels; negative examples retained. JSON beside each image contains plotting data.</p>'+''.join('<h2>'+f.stem+'</h2><img src="'+f.name+'"><p><a href="'+f.stem+'.svg">SVG</a> | <a href="'+f.stem+'.json">Source data</a></p>' for f in sorted(F.glob('*.png'))))
print(json.dumps(summary,indent=2))
