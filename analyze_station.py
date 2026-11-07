import json,csv,math,hashlib
from pathlib import Path
from collections import defaultdict
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[1];O=R/'analysis';O.mkdir(exist_ok=True);F=R/'figures';F.mkdir(exist_ok=True)
plt.rcParams.update({'font.size':10,'figure.dpi':130,'savefig.dpi':250,'axes.spines.top':False,'axes.spines.right':False})
variants=['relay','center','phase_small','phase_footprint','relay_no_tack'];labels={'relay':'Crosswind relay','center':'Centre pursuit','phase_small':'Phase / small circle','phase_footprint':'Phase / large circle','relay_no_tack':'Relay without no-go projection'};colors=dict(zip(variants,['#0072B2','#009E73','#D55E00','#CC79A7','#777777']))
rows=[];logs={}
for b in ['confirmation','scale_check']:
 for p in sorted((R/'runs'/b).glob('*.json')):
  z=json.loads(p.read_text());x=z['result'];j=x['job'];v=j['variant'];sc=j['scenario'];tr=z['trace'];row={k:x[k] for k in ['inside_fraction','max_outside_s','max_radius','completed','integration_failed','duration_s','actuator_variation_rad','max_heel_deg','cpu_s','wall_s']};row.update(batch=b,scenario=sc,variant=v,stratum=j['stratum'],path=str(p.relative_to(R)))
  row['first_entry_s']=next((a['t'] for a in tr if a['d']<=j['radius']),None)
  row['mean_abs_surge']=float(np.mean([abs(a['raw'][4]) for a in tr[:-1]]));row['low_speed_fraction']=float(np.mean([abs(a['raw'][4])<.5 for a in tr[:-1]]));rows.append(row);logs[(sc,v)]=z
assert len([x for x in rows if x['batch']=='confirmation'])==120
assert len([x for x in rows if x['batch']=='scale_check'])==24
with (O/'all_results.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
groups=[]
for b in ['confirmation','scale_check']:
 for st in ['all','inside','entry']:
  for v in variants:
   rs=[x for x in rows if x['batch']==b and x['variant']==v and (st=='all' or x['stratum']==st)]
   if not rs:continue
   g=dict(batch=b,stratum=st,variant=v,n=len(rs),complete=sum(x['completed'] for x in rs),all_samples_inside=sum(x['inside_fraction']==1 for x in rs))
   for key in ['inside_fraction','max_outside_s','max_radius','actuator_variation_rad','cpu_s','low_speed_fraction']:
    vals=np.array([x[key] for x in rs]);g[key+'_mean']=float(vals.mean());g[key+'_std']=float(vals.std(ddof=1)) if len(vals)>1 else 0;g[key+'_max']=float(vals.max());g[key+'_min']=float(vals.min())
   groups.append(g)
(O/'group_summary.json').write_text(json.dumps(groups,indent=2))
pairs=[]
for b in ['confirmation','scale_check']:
 for v in variants[1:]:
  scenes=sorted({x['scenario'] for x in rows if x['batch']==b and x['variant']==v})
  if not scenes:continue
  for st in ['all','inside','entry']:
   ss=[s for s in scenes if st=='all' or logs[s,'relay']['result']['job']['stratum']==st]
   delta=np.array([logs[s,'relay']['result']['inside_fraction']-logs[s,v]['result']['inside_fraction'] for s in ss]);cost=np.array([logs[s,'relay']['result']['actuator_variation_rad']-logs[s,v]['result']['actuator_variation_rad'] for s in ss]);pairs.append(dict(batch=b,against=v,stratum=st,n=len(ss),delta_occupancy_mean=float(delta.mean()),delta_occupancy_min=float(delta.min()),delta_occupancy_max=float(delta.max()),wins=int((delta>1e-12).sum()),ties=int((abs(delta)<=1e-12).sum()),losses=int((delta< -1e-12).sum()),delta_actuator_mean=float(cost.mean())))
(O/'paired_summary.json').write_text(json.dumps(pairs,indent=2))
scenes=sorted(s for s,v in logs if v=='relay' and s.startswith('confirmation'))
fig,axs=plt.subplots(2,1,figsize=(11,6),sharex=True)
for v in variants:
 vals=[logs[s,v]['result']['inside_fraction']*100 for s in scenes];cost=[logs[s,v]['result']['actuator_variation_rad'] for s in scenes];axs[0].plot(range(24),vals,'o-',ms=3,label=labels[v],color=colors[v]);axs[1].plot(range(24),cost,'o-',ms=3,color=colors[v])
for ax in axs:ax.axvline(15.5,color='black',ls='--',lw=.8);ax.grid(alpha=.2)
axs[0].set_ylabel('Inside samples (%)');axs[0].set_ylim(-3,103);axs[0].legend(ncol=3,fontsize=8,loc='lower left');axs[0].set_title('Frozen 50 m observation task: 16 inside starts | 8 approach starts')
axs[1].set_ylabel('Sail + rudder travel (rad)');axs[1].set_xlabel('Prespecified instance');axs[1].set_xticks(range(24));fig.tight_layout();fig.savefig(F/'01_all_tasks.png');plt.close(fig)
def caseplot(name,sc,vs,title):
 fig,axs=plt.subplots(1,3,figsize=(12,3.8));radius=logs[sc,'relay']['result']['job']['radius'];a=np.linspace(0,2*np.pi,256);axs[0].plot(radius*np.cos(a),radius*np.sin(a),'k--',lw=1,label='Observation boundary')
 for v in vs:
  tr=logs[sc,v]['trace'];xy=np.array([a['raw'][:2] for a in tr]);t=[a['t'] for a in tr];d=[a['d'] for a in tr];u=[a['raw'][4] for a in tr];axs[0].plot(xy[:,0],xy[:,1],lw=1,color=colors[v],label=labels[v]);axs[0].scatter(*xy[0],marker='x',color=colors[v]);axs[0].scatter(*xy[-1],marker='s',s=15,color=colors[v]);axs[1].plot(t,d,color=colors[v]);axs[2].plot(t,u,color=colors[v])
 axs[0].set_aspect('equal',adjustable='datalim');axs[0].set_xlabel('East (m)');axs[0].set_ylabel('North (m)');axs[0].legend(fontsize=7);axs[1].axhline(radius,color='k',ls='--');axs[1].set_ylabel('Distance from centre (m)');axs[2].set_ylabel('Surge speed (m/s)')
 for ax in axs[1:]:ax.set_xlabel('Physical time (s)');ax.grid(alpha=.2)
 fig.suptitle(title+' | '+sc);fig.tight_layout();fig.savefig(F/name);plt.close(fig)
worst=min(scenes,key=lambda s:(logs[s,'relay']['result']['inside_fraction']-logs[s,'center']['result']['inside_fraction'],s))
best=max(scenes,key=lambda s:(logs[s,'relay']['result']['inside_fraction']-logs[s,'phase_small']['result']['inside_fraction'],-int(s[-2:])))
caseplot('02_counterexample.png',worst,['relay','center','relay_no_tack'],'Largest relay loss versus strong centre comparator (post-hoc illustration)')
caseplot('03_phase_comparison.png',best,['relay','center','phase_small'],'Largest relay gain versus phase-small (post-hoc illustration)')
fig,axs=plt.subplots(1,2,figsize=(9,3.6));response=[]
for p in sorted((R/'runs/turn_admission').glob('*reverseTrue*.json')):
 z=json.loads(p.read_text());j=z['result']['job'];tr=z['trace'];label=f"u0={j['speed']}, target={j['desired']} deg";xy=np.array([a['raw'][:2] for a in tr[:61]]);t=[a['t'] for a in tr[:61]];e=[abs(math.degrees(math.atan2(math.sin(a['raw'][3]-math.radians(j['desired'])),math.cos(a['raw'][3]-math.radians(j['desired']))))) for a in tr[:61]];axs[0].plot(xy[:,0],xy[:,1],label=label);axs[1].plot(t,e);hit=next((a for a in tr if abs(math.degrees(math.atan2(math.sin(a['raw'][3]-math.radians(j['desired'])),math.cos(a['raw'][3]-math.radians(j['desired'])))))<10),None);response.append(dict(file=str(p.relative_to(R)),first_10deg_s=hit['t'] if hit else None,displacement_m=hit['d'] if hit else None))
axs[0].set_aspect('equal',adjustable='datalim');axs[0].set_xlabel('East (m)');axs[0].set_ylabel('North (m)');axs[0].legend(fontsize=7);axs[1].set_xlabel('Physical time (s)');axs[1].set_ylabel('Heading error (deg)');axs[1].axhline(10,color='k',ls='--');fig.suptitle('Actual finite-response admission: first 60 seconds');fig.tight_layout();fig.savefig(F/'04_response_scale.png');plt.close(fig)
(O/'response_scale.json').write_text(json.dumps(response,indent=2))
fig,axs=plt.subplots(1,2,figsize=(9,3.7));ss=sorted(s for s,v in logs if v=='relay' and s.startswith('scale'))
for v in ['relay','center','relay_no_tack']:
 axs[0].plot(range(8),[logs[s,v]['result']['inside_fraction']*100 for s in ss],'o-',label=labels[v],color=colors[v]);axs[1].plot(range(8),[logs[s,v]['result']['actuator_variation_rad'] for s in ss],'o-',color=colors[v])
for ax in axs:ax.axvline(3.5,color='k',ls='--');ax.set_xlabel('Frozen scale instance');ax.grid(alpha=.2)
axs[0].set_ylabel('Inside samples (%)');axs[0].legend(fontsize=7);axs[1].set_ylabel('Sail + rudder travel (rad)');fig.suptitle('100 m scale check: 4 inside starts | 4 approach starts');fig.tight_layout();fig.savefig(F/'05_scale_check.png');plt.close(fig)
(O/'selected_cases.json').write_text(json.dumps(dict(worst_vs_center=worst,best_vs_phase=best),indent=2))
html='<html><meta charset="utf-8"><title>B real-log gallery</title><body style="max-width:1200px;margin:auto;font-family:Arial"><h1>B station-keeping evidence</h1><p>All images come from logged physical trajectories. Case illustrations are selected after evaluation; all tasks remain in the result table.</p>'
for p in sorted(F.glob('*.png')):html+=f'<h2>{p.stem}</h2><img width="100%" src="../figures/{p.name}">'
html+='</body></html>'; (O/'gallery.html').write_text(html)
print(json.dumps(groups,indent=2));print('CASES',worst,best)
