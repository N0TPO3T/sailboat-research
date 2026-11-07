"""R10 main-method evidence figures from exact recorded own/target trajectories."""
import sys,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
ROOT=Path(__file__).resolve().parents[1];run=Path(sys.argv[1]).resolve();out=run/'figures';out.mkdir(exist_ok=True);fd=run/'figure_data';fd.mkdir(exist_ok=True)
C={'sampled':'#0072B2','reactive':'#009E73','hold60':'#E69F00','nominal_hold':'#D55E00'};L={'sampled':'Candidate prediction /15s','reactive':'Reactive relay','hold60':'Candidate prediction /60s','nominal_hold':'Nominal prediction + hold'};export={}
def load(rel):
 p=ROOT/rel;d=json.loads(p.read_text());export[rel]={'scene':d['scene'],'row':d['row'],'trajectory':d['trajectory'],'changes':d['changes'],'predictions':d.get('predictions',[])};return d
old='runs/r8_closedloop_20261005T062543Z'
def traces(phase,sid,vs):return [(v,load(f'{old}/{phase}/{sid}__{v}/trace.json')) for v in vs]
def draw(ax,ds,title,marks=(150,300),limits=None):
 for o in ds[0][1]['scene'].get('static',[]):
  ax.add_patch(Circle(o['center_xy'],o['entity_radius']+60,fc='#eeeeee',ec='#888',ls='--',lw=.7));ax.add_patch(Circle(o['center_xy'],o['entity_radius'],fc='#888'))
 for v,d in ds:
  xy=np.asarray([x['raw'][:2] for x in d['trajectory']]);r=d['row'];ax.plot(xy[:,0],xy[:,1],c=C[v],lw=1.3,label=f"{L[v]}: {r['time_s']}s {'safe' if r['success'] else 'FAIL'}")
  for t in marks:
   if t<len(xy):ax.scatter(*xy[t],color=C[v],s=20);ax.annotate(str(t)+'s',xy[t],xytext=(3,3),textcoords='offset points',color=C[v],fontsize=6)
  if not r['success']:ax.scatter(*xy[-1],marker='x',s=70,color=C[v],linewidths=2)
 longest=max((d for _,d in ds),key=lambda d:len(d['trajectory']));q=np.asarray([x['targets'][0]['position'] for x in longest['trajectory']]);ax.plot(q[:,0],q[:,1],'k--',lw=1,label='Target vessel (same clock)')
 for t in marks:
  if t<len(q):ax.scatter(*q[t],marker='s',s=20,color='k');ax.annotate(str(t)+'s',q[t],xytext=(4,-9),textcoords='offset points',fontsize=6)
 ax.scatter(*longest['scene']['goal'],marker='*',s=65,c='k');ax.set_title(title,fontsize=10);ax.set_xlabel('World x (m)');ax.set_ylabel('World y (m)');ax.set_aspect('equal',adjustable='datalim');ax.grid(alpha=.2);ax.legend(fontsize=6.5,loc='best')
 if limits:ax.set_xlim(*limits[0]);ax.set_ylim(*limits[1])
def save(fig,name):fig.tight_layout();fig.savefig(out/(name+'.png'),dpi=180);fig.savefig(out/(name+'.svg'));plt.close(fig)
def margin(d):return [(x['time'],min(y['margin'] for y in x['dynamic'])) for x in d['trajectory'][1:] if x.get('dynamic')]
fig,axs=plt.subplots(1,3,figsize=(15,4.8))
for ax,phase,sid,title,marks in zip(axs,['confirmation','long','long'],['r8new_mixed_pressure_2','r8long_3000_crossing','r8long_5000_crossing'],['1 km: R8 pressure case','3 km: R8 crossing','5 km: R8 crossing'],[(150,210),(400,500),(600,800)]):draw(ax,traces(phase,sid,['reactive','sampled','hold60']),title+'\nHistorical R8, ideal compute',marks)
save(fig,'01_actual_1_3_5km')
sid='r8new_mixed_pressure_2';a=load(f'{old}/confirmation/{sid}__sampled/trace.json');b=load(f'runs/{run.name}/dynamic_development/{sid}__nominal_hold/trace.json');fig,axs=plt.subplots(1,3,figsize=(15,4.6));draw(axs[0],[('sampled',a),('nominal_hold',b)],'Same causal state at149s; different references',marks=(149,200),limits=((200,780),(-380,210)))
p=next(p for p in a['predictions'] if p['time']==149);c=next(c for c in p['candidates'] if c['name']==p['selected']);axs[0].scatter(*c['target'],marker='^',s=55,color=C['sampled']);axs[0].annotate('selected reference',c['target'],fontsize=7)
q=np.asarray(a['trajectory'][149]['targets'][0]['position']);axs[0].add_patch(Circle(q,85,fill=False,ec='black',ls=':',lw=.8))
for v,d in [('sampled',a),('nominal_hold',b)]:
 m=np.asarray(margin(d));axs[1].plot(m[:,0],m[:,1],color=C[v],label=L[v])
axs[1].axhline(0,c='k',ls='--');axs[1].axvline(150,c='#888',ls=':');axs[1].set_title('Actual simultaneous separation minus85m');axs[1].set_xlabel('Physical time(s)');axs[1].set_ylabel('Dynamic buffer margin(m)');axs[1].legend(fontsize=7);axs[1].grid(alpha=.2)
pred=np.asarray(c['prediction']['path'])[:16];actual=np.asarray([x['raw'][:2] for x in a['trajectory'][149:165]]);err=np.linalg.norm(pred-actual,axis=1);axs[2].plot(np.arange(len(err)),err,'o-',ms=3);axs[2].set_title('Selected reference: prediction vs execution\nFirst15s after decision; first tick uses old action');axs[2].set_xlabel('Seconds after snapshot149');axs[2].set_ylabel('Position error(m)');axs[2].grid(alpha=.2);save(fig,'02_same_state_selection')
(fd/'committed_prefix_error.json').write_text(json.dumps({'scene':sid,'snapshot':149,'errors_m':err.tolist(),'max_m':float(err.max())},indent=2))
fig,axs=plt.subplots(1,3,figsize=(16,5));draw(axs[0],traces('confirmation','r8new_endpoint_5',['reactive','sampled']), 'Historical R8: +267s\nBoth safe; ideal compute',marks=(250,300))
for ax,sid,title,vs,marks in [(axs[1],'r10new_endpoint_0','Frozen new instance: +271s\nBoth safe; ideal compute',['reactive','sampled'],(250,300)),(axs[2],'r10new_mixed_pressure_0','Frozen new instance: hold fails\nReactive also safe; no safety gain over it',['reactive','sampled','nominal_hold'],(200,280))]:draw(ax,[(v,load(f'runs/{run.name}/confirmation/{sid}__{v}/trace.json')) for v in vs],title,marks)
save(fig,'03_adverse_cost_and_failure')
rows=json.loads((run/'analysis_rows.json').read_text());new=[x for x in rows if x['phase']=='confirmation']
if new:
 fig,axs=plt.subplots(1,3,figsize=(15,4.8));vs=['reactive','nominal_hold','hold60','sampled'];counts=[sum(x['success'] for x in new if x['variant']==v) for v in vs];tot=[sum(x['variant']==v for x in new) for v in vs]
 axs[0].bar(range(4),counts,color=[C[v] for v in vs]);axs[0].set_ylim(0,max(tot)+2);axs[0].set_xticks(range(4),[L[v].replace(' ','\n') for v in vs],fontsize=8);axs[0].set_title('R10 frozen new instances: all outcomes');axs[0].set_ylabel('Safe completed / fixed12')
 for i,(c,n) in enumerate(zip(counts,tot)):axs[0].text(i,c+.1,f'{c}/{n}',ha='center')
 main={x['scene_id']:x for x in new if x['variant']=='sampled'}
 for i,v in enumerate(vs[:-1]):
  ds=[main[x['scene_id']]['time_s']-x['time_s'] for x in new if x['variant']==v and x['success'] and main[x['scene_id']]['success']];axs[1].scatter([i]*len(ds),ds,c=C[v],s=25,alpha=.7);axs[1].plot([i-.2,i+.2],[np.median(ds)]*2,c='k');axs[1].text(i,max(ds)+8,f'n={len(ds)}',ha='center',fontsize=8)
 axs[1].axhline(0,c='k',lw=.7);axs[1].set_xticks(range(3),[L[v].replace(' ','\n') for v in vs[:-1]],fontsize=8);axs[1].set_title('Common-safe flight-time cost');axs[1].set_ylabel('Sampled15 minus control(s)')
 cpu=[sum(x['cpu_seconds'] for x in new if x['variant']==v) for v in vs];axs[2].bar(range(4),cpu,color=[C[v] for v in vs]);axs[2].set_xticks(range(4),[L[v].replace(' ','\n') for v in vs],fontsize=8);axs[2].set_ylabel('Measured cumulative episode CPU(s)');axs[2].set_title('Same new batch; no realtime implication')
 save(fig,'04_frozen_confirmation')
# Q1 is a selection-relevant negative result; not a merged-system performance table.
fig,axs=plt.subplots(1,2,figsize=(12,4.7));sr=[x for x in rows if x['phase']=='static_development' and not x['cached']];sv=['boundary','matched_center','matched_clipped'];cc=['#0072B2','#CC79A7','#D55E00'];axs[0].bar(range(3),[sum(x['success'] for x in sr if x['variant']==v) for v in sv],color=cc);axs[0].set_xticks(range(3),['Boundary','Matched raw\ncenter','Matched capped\ncenter']);axs[0].set_ylim(0,9);axs[0].set_ylabel('Safe tasks /8 seen selected scenes');axs[0].set_title('Static dispute: raw center copies all4rescues')
for i,v in enumerate(sv):axs[0].text(i,sum(x['success'] for x in sr if x['variant']==v)+.1,f"{sum(x['success'] for x in sr if x['variant']==v)}/8",ha='center')
for v,color in zip(sv,cc):
 row=next(x for x in sr if x['variant']==v and x['scene_id']=='risk9471_006_c160_b-45_stable_1000');d=json.loads((ROOT/row['raw']).read_text());xy=np.asarray([x['raw'][:2] for x in d['trajectory']]);axs[1].plot(xy[:,0],xy[:,1],c=color,label=f"{v}: {row['time_s']:.0f}s {'safe' if row['success'] else 'FAIL'}");export[row['raw']]={'scene':d['scene'],'row':row,'trajectory':d['trajectory']}
job=json.loads((ROOT/next(x for x in sr if x['scene_id']=='risk9471_006_c160_b-45_stable_1000')['raw']).with_name('job.json').read_text());o=job['suite']['maps']['generated'][0];axs[1].add_patch(Circle(o['center_xy'],o['entity_radius']+60,fc='#eee',ec='#888',ls='--'));axs[1].add_patch(Circle(o['center_xy'],o['entity_radius'],fc='#888'));axs[1].set_aspect('equal',adjustable='datalim');axs[1].legend(fontsize=7);axs[1].set_title('Static encoding result is not dynamic performance');axs[1].set_xlabel('World x(m)');axs[1].set_ylabel('World y(m)');save(fig,'05_static_alternative_evidence')
(fd/'plot_sources.json').write_text(json.dumps(export,allow_nan=True));(fd/'analysis_rows.json').write_text(json.dumps(rows,allow_nan=True));(fd/'selection.json').write_text(json.dumps({'figure1':'old pressure2 and both crossing long cases, source versionR8','figure2':'first search-vshold disagreement in old pressure2; committed prefix only','figure3':'old endpoint5 and frozen new endpoint0 cost, frozen pressure0 hold failure; reactive also safe','figure4':'all fixed new12instances','figure5':'all8 static diagnosis and predeclared risk006'},indent=2));print('saved figures',out)

