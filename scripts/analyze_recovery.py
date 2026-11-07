import json,csv,math,hashlib
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[1];O=R/'analysis_v2';O.mkdir(exist_ok=True);F=R/'figures';F.mkdir(exist_ok=True)
plt.rcParams.update({'font.size':10,'savefig.dpi':220,'axes.spines.top':False,'axes.spines.right':False})
V=['center','downwind','luff','luff_no_build','release_build','release'];L={'center':'Centre feedback','downwind':'Downwind reference only','luff':'Luff + speed build','luff_no_build':'Luff, immediate return','release_build':'Full release + speed build','release':'Full release, immediate return'};C=dict(zip(V,['#777777','#D55E00','#009E73','#E69F00','#CC79A7','#0072B2']))
rows=[];logs={};integrity=[];freeze=json.loads((R/'docs/FREEZE_V2.json').read_text())
assert hashlib.sha256((R/'scripts/station_recovery.py').read_bytes()).hexdigest()==freeze['source_sha256']
extension=json.loads((R/'docs/LUFF_MATCHED_EXTENSION.json').read_text())
assert hashlib.sha256((R/'scripts/station_luff_control.py').read_bytes()).hexdigest()==extension['source_sha256']
for batch,n in [('recovery_confirmation',144),('recovery_scale',32)]:
 extra='recovery_luff_control' if batch=='recovery_confirmation' else 'recovery_luff_scale'
 files=sorted((R/'runs'/batch).glob('*.json'))+sorted((R/'runs'/extra).glob('*.json'));assert len(files)==n
 assert hashlib.sha256((R/'runs'/extra/'runner_source.py').read_bytes()).hexdigest()==extension['source_sha256']
 assert hashlib.sha256((R/'runs'/batch/'runner_source.py').read_bytes()).hexdigest()==freeze['source_sha256'];initial={}
 for p in files:
  z=json.loads(p.read_text());x=z['result'];j=x['job'];tr=z['trace'];sc=j['scenario'];v=j['variant'];logs[sc,v]=z
  assert [a['t'] for a in tr]==list(range(len(tr)))
  assert all(math.isfinite(a['d']) and all(math.isfinite(b) for b in a['raw']) for a in tr)
  assert all('/sailboat-track-b/' in a for a in x['source_paths'].values());assert not(x['completed'] and x['integration_failed'])
  assert not x['completed'] or len(tr)==1201
  assert x['max_radius']==max(a['d'] for a in tr)
  assert abs(x['inside_fraction']-sum(a['d']<=j['radius'] for a in tr[:-1])/1200)<1e-12
  init=(tr[0]['raw'],tr[0]['wind'],tr[0]['wind_speed'])
  if sc in initial:assert initial[sc]==init
  else:initial[sc]=init
  active=[a['mode'].startswith('recovery_') for a in tr[:-1]];events=sum(b and (i==0 or not active[i-1]) for i,b in enumerate(active))
  row={k:x[k] for k in ['inside_fraction','max_outside_s','max_radius','completed','integration_failed','duration_s','actuator_variation_rad','max_heel_deg','cpu_s','wall_s']};row.update(batch=batch,scenario=sc,variant=v,condition=j['condition'],stratum=j['stratum'],recovery_seconds=sum(active),recovery_events=events,first_entry_s=next((a['t'] for a in tr if a['d']<=j['radius']),None),low_speed_fraction=sum(abs(a['raw'][4])<.5 for a in tr[:-1])/1200,path=str(p.relative_to(R)));rows.append(row)
 integrity.append(dict(batch=batch,episodes=n,tasks=len(initial),source_hash_matches=True,paired_initial_states_identical=True,finite_states=True,isolated_source_paths=True,endpoint_and_failure_checks=True))
(R/'docs/CONFIRMATION_INTEGRITY_V2.json').write_text(json.dumps(integrity,indent=2))
with (O/'all_results.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
groups=[]
for batch in ['recovery_confirmation','recovery_scale']:
 for cond in ['all','low_speed_upwind','ordinary']:
  for st in ['all','inside','entry']:
   for v in V:
    rs=[x for x in rows if x['batch']==batch and x['variant']==v and (cond=='all' or x['condition']==cond) and (st=='all' or x['stratum']==st)]
    if not rs:continue
    g=dict(batch=batch,condition=cond,stratum=st,variant=v,n=len(rs),complete=sum(x['completed'] for x in rs),all_samples_inside=sum(x['inside_fraction']==1 for x in rs),activated_tasks=sum(x['recovery_events']>0 for x in rs))
    for key in ['inside_fraction','max_outside_s','max_radius','actuator_variation_rad','max_heel_deg','cpu_s','recovery_seconds','recovery_events','low_speed_fraction']:
     a=np.array([x[key] for x in rs]);g[key+'_mean']=float(a.mean());g[key+'_std']=float(a.std(ddof=1)) if len(a)>1 else 0;g[key+'_max']=float(a.max());g[key+'_min']=float(a.min())
    groups.append(g)
(O/'group_summary.json').write_text(json.dumps(groups,indent=2))
pairs=[]
for batch in ['recovery_confirmation','recovery_scale']:
 for v in V[:-1]:
  for cond in ['all','low_speed_upwind','ordinary']:
   ss=sorted(x['scenario'] for x in rows if x['batch']==batch and x['variant']==v and (cond=='all' or x['condition']==cond))
   if not ss:continue
   delta=np.array([logs[s,'release']['result']['inside_fraction']-logs[s,v]['result']['inside_fraction'] for s in ss]);cost=np.array([logs[s,'release']['result']['actuator_variation_rad']-logs[s,v]['result']['actuator_variation_rad'] for s in ss]);pairs.append(dict(batch=batch,against=v,condition=cond,n=len(ss),delta_occupancy_mean=float(delta.mean()),delta_occupancy_min=float(delta.min()),delta_occupancy_max=float(delta.max()),wins=int((delta>1e-12).sum()),ties=int((abs(delta)<=1e-12).sum()),losses=int((delta< -1e-12).sum()),delta_actuator_mean=float(cost.mean())))
(O/'paired_summary.json').write_text(json.dumps(pairs,indent=2))
ss=sorted(s for s,v in logs if v=='release' and s.startswith('recovery_confirmation'))
fig,axs=plt.subplots(2,1,figsize=(11,6),sharex=True)
for v in V:
 axs[0].plot(range(24),[logs[s,v]['result']['inside_fraction']*100 for s in ss],'o-',ms=3,color=C[v],label=L[v]);axs[1].plot(range(24),[logs[s,v]['result']['actuator_variation_rad'] for s in ss],'o-',ms=3,color=C[v])
for ax in axs:ax.axvline(11.5,color='k',ls='--',lw=.8);ax.grid(alpha=.2)
axs[0].set_ylim(-3,103);axs[0].set_ylabel('Inside samples (%)');axs[0].set_title('Frozen physical conditions: 12 low-speed/upwind | 12 ordinary');axs[0].legend(ncol=2,fontsize=8,loc='lower right');axs[1].set_ylabel('Sail + rudder travel (rad)');axs[1].set_xlabel('Prespecified instance');axs[1].set_xticks(range(24));fig.tight_layout();fig.savefig(F/'06_recovery_all_tasks.png');plt.close(fig)
def casefig(sc,vs,name,title):
 fig,axs=plt.subplots(2,2,figsize=(10,7));rad=logs[sc,'release']['result']['job']['radius'];ang=np.linspace(0,2*np.pi,200)
 for ax in axs[0]:ax.plot(rad*np.cos(ang),rad*np.sin(ang),'k--',lw=1);ax.set_aspect('equal',adjustable='datalim');ax.set_xlabel('World x (m)');ax.set_ylabel('World y (m)')
 for v in vs:
  tr=logs[sc,v]['trace'];xy=np.array([a['raw'][:2] for a in tr]);t=[a['t'] for a in tr]
  for ax in axs[0]:ax.plot(xy[:,0],xy[:,1],color=C[v],lw=1,label=L[v]);ax.scatter(*xy[0],color=C[v],marker='x',s=20);ax.scatter(*xy[-1],color=C[v],marker='s',s=15)
  axs[1,0].plot(t,[a['d'] for a in tr],color=C[v]);axs[1,1].plot(t,[a['raw'][4] for a in tr],color=C[v])
 axs[0,0].set_title('Complete actual trajectory');axs[0,0].legend(fontsize=8);axs[0,1].set_xlim(-1.7*rad,1.7*rad);axs[0,1].set_ylim(-1.7*rad,1.7*rad);axs[0,1].set_aspect('equal',adjustable='box');axs[0,1].set_title('Local view; full path shown at left');axs[1,0].axhline(rad,color='k',ls='--');axs[1,0].set_ylabel('Centre distance (m)');axs[1,1].set_ylabel('Surge speed (m/s)')
 for ax in axs[1]:ax.set_xlabel('Physical time (s)');ax.grid(alpha=.2)
 fig.suptitle(title+' | '+sc);fig.tight_layout();fig.savefig(F/name);plt.close(fig)
best=max(ss,key=lambda s:(logs[s,'release']['result']['inside_fraction']-logs[s,'center']['result']['inside_fraction'],-int(s[-2:])))
worst=min(ss,key=lambda s:(logs[s,'release']['result']['inside_fraction']-logs[s,'luff_no_build']['result']['inside_fraction'],-(logs[s,'release']['result']['actuator_variation_rad']-logs[s,'luff_no_build']['result']['actuator_variation_rad']),s))
casefig(best,['center','luff_no_build','release'],'07_recovery_case.png','Largest occupancy gain versus centre (post-hoc illustration)')
casefig(worst,['center','luff_no_build','release'],'09_recovery_counterexample.png','Least favourable versus matched luff; ties by added actuation (post-hoc)')
active_scene=next(s for s in ss if any(a['mode'].startswith('recovery_') for a in logs[s,'release']['trace']))
tr=logs[active_scene,'release']['trace'];start=next(a['t'] for a in tr if a['mode'].startswith('recovery_'));end=next((a['t'] for a in tr if a['t']>start and not a['mode'].startswith('recovery_')),1200);subset=[a for a in tr if max(0,start-10)<=a['t']<=min(1199,start+120)];t=[a['t'] for a in subset]
fig,axs=plt.subplots(3,1,figsize=(9,7),sharex=True)
axs[0].plot(t,[math.degrees(a['sail_ref_rad']) for a in subset],label='Requested sail',ls='--');axs[0].plot(t,[math.degrees(a['raw'][8]) for a in subset],label='Actual sail');axs[0].plot(t,[math.degrees(a['raw'][9]) for a in subset],label='Actual rudder',alpha=.8);axs[0].set_ylabel('Angle (deg)');axs[0].legend(ncol=3,fontsize=8)
axs[1].plot(t,[a['raw'][4] for a in subset],label='Surge u');axs[1].plot(t,[a['raw'][5] for a in subset],label='Sway v');axs[1].set_ylabel('Body speed (m/s)');axs[1].legend(fontsize=8)
axs[2].plot(t,[abs(math.degrees(math.atan2(math.sin(a['raw'][3]-a['wind']-math.pi),math.cos(a['raw'][3]-a['wind']-math.pi)))) for a in subset]);axs[2].axhline(90,color='k',ls='--',label='Recovery exit: beam/downwind');axs[2].set_ylabel('Angle from upwind (deg)');axs[2].set_xlabel('Physical time (s)');axs[2].legend(fontsize=8)
for ax in axs:ax.axvspan(start,end,color='lightblue',alpha=.35);ax.grid(alpha=.2)
fig.suptitle(f'Actual recovery and actuator response | {active_scene}; shaded recovery');fig.tight_layout();fig.savefig(F/'08_recovery_mechanism.png');plt.close(fig)
sc=sorted(s for s,v in logs if v=='release' and s.startswith('recovery_scale'));fig,axs=plt.subplots(1,2,figsize=(10,3.7))
for v in ['center','luff','luff_no_build','release']:
 axs[0].plot(range(8),[100*logs[s,v]['result']['inside_fraction'] for s in sc],'o-',label=L[v],color=C[v]);axs[1].plot(range(8),[logs[s,v]['result']['actuator_variation_rad'] for s in sc],'o-',color=C[v])
for ax in axs:ax.axvline(3.5,color='k',ls='--');ax.set_xlabel('Frozen scale instance');ax.grid(alpha=.2)
axs[0].set_ylabel('Inside samples (%)');axs[0].legend(fontsize=8);axs[1].set_ylabel('Sail + rudder travel (rad)');fig.suptitle('100 m scale check: 4 low-speed/upwind | 4 ordinary');fig.tight_layout();fig.savefig(F/'10_recovery_scale.png');plt.close(fig)
(O/'selected_cases.json').write_text(json.dumps(dict(best_vs_center=best,worst_vs_matched_luff=worst,mechanism=active_scene,recovery_start=start,recovery_end=end,activation_record=tr[start]),indent=2))
html='<html><meta charset="utf-8"><title>B final real-log gallery</title><body style="max-width:1200px;margin:auto;font-family:Arial"><h1>Low-speed recovery: frozen evidence</h1><p>Actual simulation traces; all tasks retained. Risk and ordinary families are predefined. Illustration selection is disclosed in the report.</p>'
for p in sorted(F.glob('*.png')):
 if int(p.name[:2])>=6:html+=f'<h2>{p.stem}</h2><img width="100%" src="../figures/{p.name}">'
html+='</body></html>'; (O/'gallery.html').write_text(html)
print(json.dumps([x for x in groups if x['batch']=='recovery_confirmation' and x['stratum']=='all' and x['condition']!='all'],indent=2));print('CASES',best,worst,active_scene)
