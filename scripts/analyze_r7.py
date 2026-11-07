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
R=Path(sys.argv[1]).resolve();F=R/'figures';F.mkdir(exist_ok=True)
colors={'current':'#1769aa','commit':'#df6819','no_commit':'#42944a','compact':'#8d52a2'}
labels={'current':'Current-position R6','commit':'CPA + commitment','no_commit':'CPA reference (selected)','compact':'CPA offset180'}
batches=['pilot','development','refinement','confirmation','development85','confirmation85','stationary85','regression85','long85','sensitivity85','latency85','goal_probe','goal_early_probe','goal_development','goal_confirmation','goal_long','goal_sensitivity','goal_regression','goal_latency']
allrows=[];summary={}
for name in batches:
 f=R/name/'rows.json'
 if not f.exists():continue
 rows=json.loads(f.read_text())
 for row in rows:
  ev=[]
  if name.startswith('goal_'):
   raw=json.loads((R/name/(row['scene_id']+'__'+row['variant'])/'trace.json').read_text());ev=raw.get('goal_events',[])
  row['cpa_entries']=row['interventions']
  row['goal_stage_entries']=sum(e['event'] in ('goal_blocked','goal_planning_domain_blocked') for e in ev)
  row['goal_stage_releases']=sum(e['event']=='goal_released' for e in ev)
  row['staging_reference_updates']=sum(e['event']=='staging_reference' for e in ev)
 allrows += [dict(batch=name,evidence=str((R/name/(row['scene_id']+'__'+row['variant'])/'trace.json').relative_to(ROOT)),**row) for row in rows]
 variants=sorted(set(x['variant'] for x in rows));by={}
 for v in variants:
  a=[x for x in rows if x['variant']==v]
  by[v]=dict(n=len(a),safe=sum(x['success'] for x in a),arrived=sum(x['arrived'] for x in a),dynamic_violations=sum(x['min_dynamic_margin'] is not None and x['min_dynamic_margin']<=0 for x in a),static_violations=sum(x['min_static_margin'] is not None and x['min_static_margin']<=0 for x in a),entity_collisions=sum(x['min_entity_margin'] is not None and x['min_entity_margin']<=0 for x in a),max_reencoding=max(x['max_reencoding_seconds'] for x in a),max_planning=max(x['max_planning_seconds'] for x in a),mean_cpa_entries=float(np.mean([x['cpa_entries'] for x in a])),goal_active_episodes=sum(x['goal_stage_entries']>0 for x in a),goal_stage_entries=sum(x['goal_stage_entries'] for x in a))
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
 w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for row in allrows for k in row)));w.writeheader();w.writerows(allrows)

if not (R/'goal_confirmation/completion.json').exists():print(json.dumps(summary,indent=2));sys.exit()
colors.update(current_goal='#20804e',cpa_goal='#d46b20',ungated_goal='#9150a5')
labels.update(current_goal='Goal-window Relay',cpa_goal='CPA + goal relay',ungated_goal='Goal relay without time gate')
rows=json.loads((R/'goal_confirmation/rows.json').read_text());pairs={}
for x in rows:pairs.setdefault(x['scene_id'],{})[x['variant']]=x
win=max(pairs,key=lambda s:(int(pairs[s]['current_goal']['success'])-int(pairs[s]['current']['success']),(pairs[s]['current_goal']['min_dynamic_margin'] or 0)-(pairs[s]['current']['min_dynamic_margin'] or 0)))
loss=max(pairs,key=lambda s:(int(pairs[s]['current']['success'])-int(pairs[s]['current_goal']['success']),pairs[s]['current_goal']['time_s']-pairs[s]['current']['time_s']))
def get(batch,scene,v):
 d=json.loads((R/batch/(scene+'__'+v)/'trace.json').read_text());d['_source']=str((R/batch/(scene+'__'+v)/'trace.json').relative_to(ROOT));return d
def slim(d):return {k:v for k,v in d.items() if k not in ['decisions','wind']}
def save(fig,name,data):
 fig.tight_layout(rect=(0,0,1,.95));fig.savefig(F/(name+'.png'),dpi=170);fig.savefig(F/(name+'.svg'));plt.close(fig);(F/(name+'.json')).write_text(json.dumps(data))
def track(ax,d,v):
 tr=d['trajectory'];p=np.array([x['raw'][:2] for x in tr]);q=np.array([x['targets'][0]['position'] for x in tr]) if tr[0]['targets'] else None
 ax.plot(p[:,0],p[:,1],color=colors[v],label=labels[v]);ax.scatter(*d['scene']['goal'],marker='*',s=85,color='black',label='Final goal')
 if q is not None:
  ax.plot(q[:,0],q[:,1],'--',color='#555555',label='Target vessel')
  for z in [int(z) for z in np.linspace(0,len(tr)-1,5)]:
   ax.scatter(*p[z],s=14,color=colors[v]);ax.scatter(*q[z],s=14,color='#555555',marker='s');ax.plot([p[z,0],q[z,0]],[p[z,1],q[z,1]],':',color='#888888',alpha=.3);ax.annotate(str(z)+'s',p[z],fontsize=7,xytext=(3,3),textcoords='offset points');ax.annotate(str(z)+'s',q[z],fontsize=7,xytext=(3,-9),textcoords='offset points')
  k=min(range(1,len(tr)),key=lambda i:min(x['margin'] for x in tr[i]['dynamic']));fr=tr[k]['dynamic'][0]['fraction'];qm=q[k-1]+fr*(q[k]-q[k-1]);pm=p[k-1]+fr*(p[k]-p[k-1]);ax.add_patch(Circle(qm,85,fill=False,ls=':',color='#777777'));ax.add_patch(Circle(qm,15,color='#777777',alpha=.25));ax.add_patch(Circle(pm,10,fill=False,color=colors[v],alpha=.5))
 for o in d['scene'].get('static',[]):
  ax.add_patch(Circle(o['center_xy'],o['entity_radius'],color='gray',alpha=.5));ax.add_patch(Circle(o['center_xy'],o['entity_radius']+60,fill=False,ls='--',color='gray'))
 entries=[e for e in d.get('goal_events',[]) if e['event']=='goal_planning_domain_blocked']
 releases=[e for e in d.get('goal_events',[]) if e['event']=='goal_released']
 for e in entries[:1]+releases[:1]:
  k=min(int(e['time']),len(tr)-1);ax.scatter(*p[k],marker='D' if e['event']=='goal_released' else '^',color='black',s=40)
 if entries:
  e=entries[0];change=next((c for c in d['changes'] if c['selected_at']>=e['time']),None)
  if change:ax.scatter(*change['target'],marker='+',s=70,color=colors[v],label='First applied staging reference')
 ax.set_aspect('equal',adjustable='datalim');ax.set_xlabel('World x (m)');ax.set_ylabel('World y (m)');ax.grid(alpha=.2);ax.set_title(labels[v]+f" | safe={d['row']['success']}, {d['row']['time_s']}s",fontsize=10)
for name,scene in [('01_encounter',win),('03_adverse',loss)]:
 ds={v:get('goal_confirmation',scene,v) for v in ['current','current_goal']};fig,axs=plt.subplots(1,2,figsize=(12,5.5))
 for ax,v in zip(axs,ds):track(ax,ds[v],v);ax.legend(fontsize=7,loc='best')
 fig.suptitle(scene+' | recorded tracks; paired safety ring85m at closest approach',fontsize=11);save(fig,name,{v:slim(d) for v,d in ds.items()})
fig,axs=plt.subplots(2,1,figsize=(11,7),sharex=True);ds={v:get('goal_confirmation',win,v) for v in ['current','current_goal','ungated_goal']}
for v,d in ds.items():
 tr=d['trajectory'];tm=[x['time']-1+z['fraction'] for x in tr[1:] for z in x['dynamic']];m=[z['margin'] for x in tr[1:] for z in x['dynamic']];axs[0].plot(tm,m,label=labels[v],color=colors[v]);pp=np.array([x['raw'][:2] for x in tr]);axs[1].plot([x['time'] for x in tr],np.linalg.norm(pp-np.array(d['scene']['goal']),axis=1),color=colors[v],label=labels[v])
entries=[e for e in ds['current_goal'].get('goal_events',[]) if e['event']=='goal_planning_domain_blocked']
for e in entries:
 axs[0].axvline(e['time'],ls=':',color='#20804e',alpha=.5);axs[0].axvline(e['time']+1,ls='--',color='#20804e',alpha=.5)
 if e['occupancy_windows']:
  a,b=e['occupancy_windows'][0];axs[1].axvspan(e['time']+a,e['time']+b,color='gray',alpha=.12,label='Predicted goal occupancy at entry')
d=ds['current_goal'];tr=d['trajectory'];q=np.array([x['targets'][0]['position'] for x in tr]);axs[1].plot([x['time'] for x in tr],np.linalg.norm(q-np.array(d['scene']['goal']),axis=1)-85,'--',color='black',alpha=.7,label='Recorded target-to-goal safety margin')
axs[0].axhline(0,color='red',ls='--');axs[1].axhline(0,color='gray',ls='--');axs[0].set_ylabel('Synchronous separation minus85m (m)');axs[1].set_ylabel('Distance / margin (m)');axs[1].set_xlabel('Physical time (s)');axs[0].legend(fontsize=8);axs[1].legend(fontsize=7)
msg=(f" | stage selected{entries[0]['time']}s / applies{entries[0]['time']+1}s" if entries else ' | no goal-stage intervention')
axs[0].set_title(win+msg);axs[1].set_xlim(0,max(len(d['trajectory'])-1 for d in ds.values()));[a.grid(alpha=.2) for a in axs];save(fig,'02_margin_progress',{v:slim(d) for v,d in ds.items()})
fig,axs=plt.subplots(1,2,figsize=(13,5));families=['overtaking','crossing','nonconflict','mixed'];vs=['current','current_goal','cpa_goal','ungated_goal']
for k,v in enumerate(vs):
 vals=[]
 for fam in families:
  a=[x for x in rows if x['variant']==v and x['family']==fam];vals.append(sum(x['success'] for x in a)/len(a))
 bars=axs[0].bar(np.arange(4)+(k-1.5)*.2,vals,.19,color=colors[v],label=labels[v])
 for j,b in enumerate(bars):
  a=[x for x in rows if x['variant']==v and x['family']==families[j]];axs[0].text(b.get_x()+b.get_width()/2,b.get_height()+.01,f"{sum(x['success'] for x in a)}/{len(a)}",ha='center',fontsize=6)
axs[0].set_xticks(range(4),families,rotation=15);axs[0].set_ylim(0,1.15);axs[0].set_ylabel('Complete safe arrival fraction');axs[0].legend(fontsize=7,loc='lower left')
for k,v in enumerate(vs[1:]):
 vals=[a[v]['time_s']-a['current']['time_s'] for a in pairs.values() if a[v]['success'] and a['current']['success']];axs[1].scatter(np.full(len(vals),k)+np.linspace(-.12,.12,len(vals)),vals,color=colors[v],alpha=.7)
 if vals:axs[1].plot([k-.2,k+.2],[np.median(vals)]*2,color='black')
axs[1].axhline(0,color='gray',ls='--');axs[1].set_xticks([0,1,2],['Goal window','CPA + goal','No time gate']);axs[1].set_ylabel('Extra seconds vs current\n(pairwise common safe arrivals only)');axs[1].grid(alpha=.2);save(fig,'04_confirmation',dict(rows=rows,summary=summary['goal_confirmation']))
if (R/'goal_long/completion.json').exists():
 lr=json.loads((R/'goal_long/rows.json').read_text());ss=[win]+[next(x['scene_id'] for x in lr if x['distance_m']==dist and x['family']=='overtaking') for dist in [3000,5000]];fig,axs=plt.subplots(2,3,figsize=(15,9));dd=[]
 for j,(sc,ba) in enumerate(zip(ss,['goal_confirmation','goal_long','goal_long'])):
  for i,v in enumerate(['current','current_goal']):
   d=get(ba,sc,v);dd.append(slim(d));track(axs[i,j],d,v);axs[i,j].set_title(f"{d['scene']['distance_m']/1000:g}km {labels[v]}\n{d['row']['time_s']}s, safe={d['row']['success']}",fontsize=9);axs[i,j].legend(fontsize=6)
 fig.suptitle('Representative distinct instances | same-time ownship/target markers; no physical resets');save(fig,'05_continuous',dd)
(R/'examples.json').write_text(json.dumps(dict(encounter=win,adverse=loss)))
(F/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>R7 real trajectories</title><style>body{max-width:1300px;margin:auto;font-family:sans-serif}img{width:100%}</style><h1>R7 recorded dynamic encounters</h1><p>Recorded physical logs only. Each panel ends at its own episode termination. Same-time labels join ownship and target. Circle85m is paired safety, not target hull. Triangle: goal-stage entry; diamond: release. Sources beside each image.</p>'+''.join('<h2>'+ff.stem+'</h2><img src="'+ff.name+'"><p><a href="'+ff.stem+'.svg">SVG</a> | <a href="'+ff.stem+'.json">Source data</a></p>' for ff in sorted(F.glob('*.png'))))
print(json.dumps(summary,indent=2))
