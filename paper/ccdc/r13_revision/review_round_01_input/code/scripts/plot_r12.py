"""Publication plots from actual R12/R8 traces and paired results only."""
import json,sys,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'runs/r12_revision_20261006';O=ROOT/'paper/ccdc/r12_revision/figures';O.mkdir(parents=True,exist_ok=True)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import numpy as np
plt.rcParams.update({'font.family':'serif','font.size':8,'axes.titlesize':9,'axes.labelsize':8,'legend.fontsize':6.5,'svg.fonttype':'none'})
C={'reactive':'#009E73','sampled':'#0072B2','simple':'#D55E00'};L={'reactive':'Reactive','sampled':'Detailed S15','simple':'Low-order L'}
S=json.loads((R/'analysis.json').read_text());manifest=json.loads((R/'confirmation.json').read_text());ids=list(dict.fromkeys(j['scene']['id'] for j in manifest['jobs']));data={}
for sid in ids:
 for v in C:data[sid,v]=json.loads((R/'confirmation'/(sid+'__'+v)/'trace.json').read_text())
def save(f,n):
 f.tight_layout(pad=.8)
 for ext in ['png','pdf','svg']:f.savefig(O/(n+'.'+ext),dpi=300)
 plt.close(f)
f,ax=plt.subplots(2,1,figsize=(3.4,4.4),sharex=True)
for v,offset in [('sampled',-.13),('simple',.13)]:
 xs=[];ys=[]
 for i,sid in enumerate(ids):
  a=data[sid,v]['row'];b=data[sid,'reactive']['row']
  if a['success'] and b['success']:xs.append(i+offset);ys.append(a['time_s']-b['time_s'])
  else:ax[0].plot(i+offset,0,'x',c=C[v],ms=5)
 ax[0].scatter(xs,ys,c=C[v],s=14,label=L[v]);ax[1].plot(np.arange(len(ids))+offset,[data[s,v]['row']['min_dynamic_margin'] for s in ids],'.',c=C[v],label=L[v])
ax[0].axhline(0,color='k',lw=.6);ax[0].set(ylabel='Common-safe time − R (s)',title='(a) Frozen 24-task confirmation');ax[0].legend()
ax[1].plot(range(len(ids)),[data[s,'reactive']['row']['min_dynamic_margin'] for s in ids],'_',c=C['reactive'],label='Reactive');ax[1].axhline(0,c='k',ls='--',lw=.7);ax[1].set(ylabel='Actual dynamic margin (m)',xlabel='Prespecified task index',title='(b) All actual outcomes');ax[1].legend()
for a in ax:a.grid(alpha=.2);a.set_xticks([0,7,11,15,19,23],[1,8,12,16,20,24])
save(f,'figure2_confirmation')
g=[0,15,30,60];rr=[S['guard']['guard'+str(x)] for x in g]
f,ax=plt.subplots(3,1,figsize=(3.4,4.7),sharex=True)
ax[0].plot(g,[x['safe'] for x in rr],'o-',c=C['sampled']);ax[0].axhline(S['guard']['reactive']['safe'],c=C['reactive'],ls='--',label='Reactive');ax[0].set(ylabel='Safe tasks / 12',ylim=(min([x['safe'] for x in rr]+[S['guard']['reactive']['safe']])-.7,12.5));ax[0].legend()
for stat,label,fmt in [('median','Median','o-'),('max','Maximum','s--')]:ax[1].plot(g,[x['common_safe_time_delta_vs_R'][stat] for x in rr],fmt,label=label)
ax[1].set(ylabel='Common-safe\ntime − R (s)');ax[1].legend()
ax[2].plot(g,[x['min_dynamic_margin'] for x in rr],'o-',c=C['sampled']);ax[2].axhline(0,c='k',ls='--',lw=.7);ax[2].set(ylabel='Worst dynamic\nmargin (m)',xlabel='Additional prediction guard ρ (m)')
for a in ax:a.grid(alpha=.2);a.set_xticks(g)
save(f,'figure3_guard')
q=json.loads((R/'matched_prediction_quality.json').read_text());f,ax=plt.subplots(2,1,figsize=(3.4,4.5))
for key,v in [('detailed','sampled'),('simple','simple')]:
 ax[0].scatter([x['actual_margin_common'] for x in q],[x[key+'_margin_common'] for x in q],s=19,c=C[v],marker='o' if key=='detailed' else '^',label=L[v],alpha=.8)
 ax[1].plot(range(1,13),[x[key+'_max_error'] for x in q],'o-' if key=='detailed' else '^--',ms=3,c=C[v],label=L[v])
ax[0].plot([0,380],[0,380],'k:',lw=.7);ax[0].axhline(30,c='#999',ls='--',lw=.6);ax[0].axvline(30,c='#999',ls='--',lw=.6);ax[0].set(xlabel='Fixed-protocol actual margin (m)',ylabel='Predicted margin (m)',title='(a) Same executed reference protocols');ax[0].legend()
ax[1].set(yscale='log',xlabel='Branch index (six source snapshots)',ylabel='Maximum position error (m)',title='(b) Common horizon: ten 60s, two 58s');ax[1].set_xticks([1,3,5,7,9,11]);ax[1].legend()
for a in ax:a.grid(alpha=.2)
save(f,'figure4_prediction')
# A known historical rescue and the worst new common-safe S15 cost; no favorable-only selection.
eligible=[s for s in ids if data[s,'sampled']['row']['success'] and data[s,'reactive']['row']['success']]
bad=max(eligible,key=lambda s:data[s,'sampled']['row']['time_s']-data[s,'reactive']['row']['time_s'])
old=ROOT/'runs/r8_closedloop_20261005T062543Z/confirmation';sid='r8new_mixed_pressure_2';historic={v:json.loads(((R/'development' if v=='simple' else old)/(sid+'__'+v)/'trace.json').read_text()) for v in C}
f,axs=plt.subplots(2,1,figsize=(3.4,5.15));caseidx=[]
for ax,ds,title in [(axs[0],historic,'(a) Historical pressure task'),(axs[1],{v:data[bad,v] for v in C},'(b) Largest new S15 time cost vs R')]:
 scene=ds['sampled']['scene'];caseidx.append(scene['id'])
 for o in scene['static']:
  ax.add_patch(Circle(o['center_xy'],o['entity_radius']+60,fc='#eee',ec='#888',ls='--',lw=.5));ax.add_patch(Circle(o['center_xy'],o['entity_radius'],fc='#aaa'))
 ts=min(200,min(d['row']['time_s'] for d in ds.values())-1)
 for v,d in ds.items():
  xy=np.array([x['raw'][:2] for x in d['trajectory']]);ax.plot(xy[:,0],xy[:,1],c=C[v],lw=.9,label=f"{L[v]} {d['row']['time_s']}s");ax.plot(*xy[ts],'o',c=C[v],ms=3)
  if not d['row']['success']:ax.plot(*xy[-1],'x',c=C[v],ms=6)
 target=np.array([x['targets'][0]['position'] for x in max(ds.values(),key=lambda d:d['row']['time_s'])['trajectory']]);ax.plot(target[:,0],target[:,1],'k--',lw=.7,label='Target');ax.plot(*target[ts],'ks',ms=3);ax.add_patch(Circle(target[ts],85,fill=False,ec='k',ls=':',lw=.6));ax.annotate(f'Circle/square: {ts}s',target[ts],xytext=(-60,22),textcoords='offset points',fontsize=6,arrowprops={'arrowstyle':'-','lw':.5});ax.plot(*scene['goal'],'k*',ms=5)
 ax.set(title=title,xlabel='World x (m)',ylabel='World y (m)');ax.set_aspect('equal',adjustable='datalim');ax.grid(alpha=.2);ax.legend(loc='best',fontsize=5.8)
save(f,'figure5_encounters');(R/'figure_cases.json').write_text(json.dumps({'cases':caseidx,'selection':'historical prespecified pressure2 plus largest new common-safe S15 time cost vs reactive'},indent=2))
print('Four evidence figures saved',caseidx)
