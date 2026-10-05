"""R9 figures from retained actual logs only; no resimulation."""
import sys,json,csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
R=Path(sys.argv[1]).resolve();F=R/'figures';F.mkdir(exist_ok=True)
plt.rcParams.update({'font.size':9,'svg.fonttype':'none'})
COL={'reactive':'#555555','ideal15':'#8064a2','delayed15':'#e48b23','fast15':'#ad6a00','fast60':'#ce4750','main':'#087fa4','slot_feedback60':'#087fa4','ignore_wait':'#aa4477'}
def load(batch,scene,variant):return json.loads((R/batch/(scene+'__'+variant)/'trace.json').read_text())
def save(fig,name):
 fig.savefig(F/(name+'.png'),dpi=170,bbox_inches='tight');fig.savefig(F/(name+'.svg'),bbox_inches='tight');plt.close(fig)
def route(ax,d,label,color,draw_target=True,marker_step=120):
 a=np.array([z['raw'][:2] for z in d['trajectory']]);ax.plot(a[:,0],a[:,1],color=color,label=label,lw=1.5)
 for t in range(0,len(a),marker_step):
  ax.scatter(*a[t],color=color,s=10);ax.annotate(str(t)+'s',a[t],fontsize=6,color=color)
 for o in d['scene'].get('static',[]):
  ax.add_patch(Circle(o['center_xy'],o['entity_radius'],color='gray',alpha=.5));ax.add_patch(Circle(o['center_xy'],o['entity_radius']+60,fill=False,color='gray',ls=':'))
 if draw_target and d['scene']['vessels']:
  q=np.array([z['targets'][0]['position'] for z in d['trajectory']]);ax.plot(q[:,0],q[:,1],color=color,ls='--',alpha=.65)
  for t in range(0,len(q),marker_step):
   ax.scatter(*q[t],color=color,marker='x',s=17);ax.annotate(str(t)+'s',q[t],fontsize=6,color=color)
 ax.scatter(*d['scene']['goal'],marker='*',s=85,c='black');ax.set_aspect('equal',adjustable='datalim');ax.set_xlabel('World x (m)');ax.set_ylabel('World y (m)');ax.grid(alpha=.2)
# Predefined short developmental recovery and both long confirmation instances.
fig,axes=plt.subplots(1,3,figsize=(15,4.5))
for ax,(batch,scene,method) in zip(axes,[('development2','confirm_mixed_3','slot_feedback60'),('long_confirmation','r9new_long_3000','main'),('long_confirmation','r9new_long_5000','main')]):
 for v in ['reactive',method]:
  d=load(batch,scene,v);route(ax,d,v,COL[v],draw_target=v==method,marker_step={1000:60,3000:180,5000:300}[d['scene']['distance_m']])
 ax.set_title(scene+(' (seen development)' if batch=='development2' else ' (frozen new)'));ax.legend(fontsize=7)
fig.suptitle('Actual own-vessel paths (solid) and target paths (dashed); labels share physical time')
save(fig,'01_actual_1_3_5km')
# Actual timing/margin plus selected model and executed prefix.
d=load('development2','confirm_mixed_7','slot_feedback60');tr=d['trajectory'];fig,axes=plt.subplots(3,1,figsize=(11,8))
tt=[z['time'] for z in tr[1:]];mm=[min((q['margin'] for q in z['dynamic']),default=np.nan) for z in tr[1:]]
axes[0].plot(tt,mm,label='Actual simultaneous dynamic margin');axes[0].axhline(0,color='red',ls='--');axes[0].set_ylabel('Margin (m)');axes[0].legend()
for i,e in enumerate(d['timeline']):
 axes[1].plot([e['plan_start'],e['plan_ready']],[i,i],lw=5,color='#e48b23');a=e['reference_apply']
 if a is not None:axes[1].plot([e['plan_ready'],a],[i,i],lw=2,color='#087fa4');axes[1].scatter([a],[i],marker='|',c='black')
 axes[1].text(e['plan_start'],i+.15,e['selected']+' / '+e['status'],fontsize=6)
axes[1].set_xlim(0,len(tr)-1);axes[0].set_xlim(0,len(tr)-1);axes[1].set_ylim(-.3,len(d['timeline'])-.4);axes[1].set_ylabel('Request');axes[1].set_xlabel('Physical time (s): orange compute, blue delivery wait, | protocol application')
p=next(z for z in d['predictions'] if z['selected']!='nominal');c=next(z for z in p['candidates'] if z['name']==p['selected']);k=int(p['time']);a=np.array([z['raw'][:2] for z in tr[k:k+len(c['prediction']['path'])]]);pred=np.array(c['prediction']['path'])[:len(a)]
axes[2].plot(np.arange(len(a)),np.linalg.norm(pred-a,axis=1));axes[2].axvline(26,color='gray',ls='--');axes[2].set_xlabel('Seconds since snapshot (dashed: reference application)');axes[2].set_ylabel('Prediction position error (m)')
for ax in axes:ax.grid(alpha=.2)
fig.tight_layout();save(fig,'02_decision_timing')
# Explicit adverse case, including buffer-intrusion counterexample for simple60.
fig,axes=plt.subplots(1,2,figsize=(13,5))
for ax,scene,variants in [(axes[0],'r8new_endpoint_5',['reactive','slot_feedback60']),(axes[1],'confirm_mixed_6',['reactive','fast60','slot_feedback60'])]:
 for v in variants:
  d=load('development2',scene,v);route(ax,d,v+': '+str(d['row']['time_s'])+'s',COL[v],draw_target=v==variants[-1],marker_step=180)
  bad=next((z for z in d['trajectory'][1:] if any(q['margin']<=0 for q in z['dynamic'])),None)
  if bad:ax.scatter(*bad['raw'][:2],s=80,marker='X',color=COL[v]);ax.add_patch(Circle(bad['targets'][0]['position'],85,fill=False,color=COL[v],ls=':'))
 ax.set_title(scene);ax.legend(fontsize=8)
fig.suptitle('Adverse evidence: endpoint detour cost; simple60 buffer intrusion (X, 85m boundary)')
save(fig,'03_adverse_cases')
summary=json.loads((R/'analysis.json').read_text());timing=json.loads((R/'timing_analysis.json').read_text());rows=list(csv.DictReader((R/'all_rows.csv').open()))
fig,axes=plt.subplots(1,3,figsize=(15,4.5));variants=[v for v in summary['confirmation']['methods']]
for i,v in enumerate(variants):
 a=[x for x in rows if x['batch']=='confirmation' and x['variant']==v];vals=[float(x['min_dynamic_margin']) for x in a];axes[0].scatter([i]*len(vals),vals,color=COL.get(v,'gray'),s=20,alpha=.8)
axes[0].axhline(0,color='red',ls='--');axes[0].set_xticks(range(len(variants)),variants,rotation=35);axes[0].set_ylabel('Minimum actual dynamic margin (m)');axes[0].set_title('All frozen short instances, failures retained')
for i,v in enumerate(variants):
 vals=[]
 for x in rows:
  if x['batch']!='confirmation' or x['variant']!=v or x['success']!='True':continue
  b=next((z for z in rows if z['batch']=='confirmation' and z['scene_id']==x['scene_id'] and z['variant']=='reactive'),None)
  if b and b['success']=='True':vals.append(float(x['time_s'])-float(b['time_s']))
 axes[1].scatter([i]*len(vals),vals,color=COL.get(v,'gray'),s=20)
axes[1].axhline(0,color='gray');axes[1].set_xticks(range(len(variants)),variants,rotation=35);axes[1].set_ylabel('Time difference vs reactive (s)');axes[1].set_title('Common-safe pairs only')
for i,v in enumerate(variants):
 z=timing.get('confirmation/'+v,{});w=z.get('walls',{});age=z.get('ages',{})
 if v=='ideal15':axes[2].text(i,1,'ideal',ha='center',fontsize=8,color='gray')
 if v=='reactive':axes[2].text(i,1,'no prediction',ha='center',fontsize=7,color='gray',rotation=90)
 if w.get('n'):axes[2].bar(i-.16,w['p95'],width=.3,color='#e48b23');axes[2].bar(i+.16,age.get('p95',0),width=.3,color='#087fa4')
axes[2].set_xticks(range(len(variants)),variants,rotation=35);axes[2].set_ylabel('Seconds');axes[2].set_title('P95 compute (orange) / snapshot age (blue)')
for ax in axes:ax.grid(axis='y',alpha=.2)
fig.tight_layout();save(fig,'04_compute_and_outcomes')
# Main-method false-safe sensitivity, not only a competing baseline failure.
a=load('development2','confirm_mixed_3','slot_feedback60');b=load('sensitivity','confirm_mixed_3','slot30');fig,axes=plt.subplots(1,2,figsize=(13,5))
route(axes[0],a,'25s slot: safe399s','#087fa4',draw_target=True,marker_step=120)
route(axes[0],b,'30s slot: intrusion184s','#ce4750',draw_target=False,marker_step=60)
p=next(z for z in b['predictions'] if z['time']==101);c=next(z for z in p['candidates'] if z['name']==p['selected']);pp=np.array(c['prediction']['path']);axes[0].plot(pp[:,0],pp[:,1],':',color='#ad6a00',label='30s slot prediction at101s',lw=2)
idx=next(i for i,z in enumerate(b['trajectory']) if z.get('dynamic') and min(q['margin'] for q in z['dynamic'])<=0);z=b['trajectory'][idx];prev=b['trajectory'][idx-1];frac=z['dynamic'][0]['fraction'];q=(1-frac)*np.array(prev['targets'][0]['position'])+frac*np.array(z['targets'][0]['position']);own=(1-frac)*np.array(prev['raw'][:2])+frac*np.array(z['raw'][:2]);axes[0].scatter(*own,c='#ce4750',marker='X',s=70);axes[0].add_patch(Circle(q,85,fill=False,color='#ce4750',ls=':'));axes[0].legend(fontsize=7);axes[0].set_title('Same known scene; both clocks explicitly modeled')
t=101;actual=b['trajectory'][t+1:];H=min(len(actual),len(c['prediction']['margins']));am=[min(z['static_margin'],min(q['margin'] for q in z['dynamic'])) for z in actual[:H]]
axes[1].plot(np.arange(1,H+1),c['prediction']['margins'][:H],label='Predicted combined margin',c='#ad6a00');axes[1].plot(np.arange(1,H+1),am,label='Actual combined margin',c='#ce4750');axes[1].axhline(0,c='black',ls='--');axes[1].axhline(30,c='gray',ls=':',label='Planning guard30m');axes[1].axvline(31,c='#087fa4',ls=':',label='Application+31s');axes[1].set_xlabel('Seconds since101s snapshot');axes[1].set_ylabel('Margin (m)');axes[1].set_title('Prediction+82.692m; actual−0.949m common window');axes[1].legend(fontsize=8);axes[1].grid(alpha=.2)
fig.tight_layout();save(fig,'05_false_safe_delay')
html='<html><meta charset="utf-8"><title>R9 actual evidence</title><body><h1>R9 timing-aware avoidance</h1><p>All paths and metrics are actual retained logs. Dashed vessel paths are real synchronized target histories, not predictions.</p>'
for f in sorted(F.glob('*.png')):html+='<h2>'+f.stem+'</h2><img style="width:100%;max-width:1400px" src="figures/'+f.name+'">'
(R/'gallery.html').write_text(html+'</body></html>')
print(str(F))
