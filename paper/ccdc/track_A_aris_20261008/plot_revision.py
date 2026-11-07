"""R13: replot frozen R12 evidence; no physical experiments or changed algorithms."""
from pathlib import Path
import sys,zipfile
sys.path.insert(0,str(Path(__file__).resolve().parent/".tools/python"))
import json,csv,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
O=Path(__file__).resolve().parent; R=O/'evidence'; (O/'figures').mkdir(exist_ok=True,parents=True)
plt.rcParams.update({'font.family':'serif','font.size':8,'axes.titlesize':8,'legend.fontsize':6.5,'svg.fonttype':'none'})
C={'reactive':'#009E73','simple':'#D55E00','sampled':'#0072B2'};L={'reactive':'R','simple':'L','sampled':'S15'}
ids=list(dict.fromkeys(j['scene']['id'] for j in json.loads((R/'confirmation.json').read_text())['jobs']))
with zipfile.ZipFile(O.parent/'r13_revision/R13_REPRODUCTION_internal.zip') as z:
 traces=[json.loads(z.read(n)) for n in z.namelist() if n.endswith('trace.json')]
data={(d['row']['scene_id'],d['row']['variant']):d for d in traces}
MARK={'reactive':'s','simple':'^','sampled':'o'}
STYLE={'reactive':':','simple':'--','sampled':'-'}
def save(f,n):
 f.tight_layout(pad=.7)
 for ext in ['png','pdf','svg']:f.savefig(O/'figures'/(n+'.'+ext),dpi=280)
 plt.close(f)
f,ax=plt.subplots(3,1,figsize=(3.4,4.5),sharex=True,gridspec_kw={'height_ratios':[2,2,.75]})
for v,off in [('sampled',-.13),('simple',.13)]:
 xy=[(i+1+off,data[s,v]['row']['time_s']-data[s,'reactive']['row']['time_s']) for i,s in enumerate(ids) if data[s,v]['row']['success'] and data[s,'reactive']['row']['success']]
 ax[0].scatter(*zip(*xy),s=16,c=C[v],marker=MARK[v],label=L[v])
for j,v in enumerate(C):
 ax[1].scatter(np.arange(1,25)+(j-1)*.18,[data[s,v]['row']['min_dynamic_margin'] for s in ids],s=15,c=C[v],marker=MARK[v],label=L[v])
 for i,s in enumerate(ids):ax[2].scatter(i+1,j,marker='o' if data[s,v]['row']['success'] else 'x',s=13,c=C[v])
ax[0].set(ylabel='Common-safe Δtime vs R (s)',title='(a) Time cost: 19 common-safe pairs each');ax[0].legend(ncol=2)
ax[1].set(yscale='symlog',ylabel='Actual dynamic margin (m)',title='(b) All tasks; expanded near zero');ax[1].set_yscale('symlog',linthresh=3);ax[1].set_yticks([-1,0,3,30,300]);ax[1].set_yticklabels(['−1','0','3','30','300']);ax[1].legend(ncol=3)
ax[2].set(yticks=[0,1,2],yticklabels=[L[v] for v in C],xlabel='Frozen task index (1–24)',title='(c) ○ safe completion; × failure')
for a in ax[:2]:a.axhline(0,c='k',lw=.6);a.grid(alpha=.18)
ax[2].set_xticks([1,8,12,16,20,24]);save(f,'figure2_confirmation')
s=json.loads((R/'analysis.json').read_text()); g=[0,15,30,60]; rr=[s['guard']['guard'+str(x)] for x in g]
f,ax=plt.subplots(2,1,figsize=(3.4,3.05),sharex=True)
for key,label,fmt in [('mean','Mean','o-'),('max','Maximum','s--')]:ax[0].plot(g,[r['common_safe_time_delta_vs_R'][key] for r in rr],fmt,label=label,ms=3)
ax[0].set(ylabel='Δtime vs R (s)',title='(a) Ten common-safe pairs');ax[0].legend()
ax[1].plot(g,[r['min_dynamic_margin'] for r in rr],'o-',ms=3);ax[1].set(ylabel='Worst actual margin (m)',xlabel='Prediction guard ρ (m)',title='(b) All twelve tasks at each guard');ax[1].axhline(0,c='k',lw=.6)
for a in ax:a.grid(alpha=.2);a.set_xticks(g)
save(f,'figure3_guard')
q=json.loads((R/'matched_prediction_quality.json').read_text());f,ax=plt.subplots(2,1,figsize=(3.4,3.9),sharex=True)
for key,v,off in [('detailed','sampled',-.08),('simple','simple',.08)]:
 for k,x in enumerate(q):
  ix=k//2+1+(-.2 if k%2==0 else .2)+off
  ax[0].plot(ix,x[key+'_max_error'],'o' if k%2==0 else '^',ms=4,c=C[v],mfc=C[v] if v=='sampled' else 'white',mew=.8,label=L[v] if k==0 else None)
  ax[1].plot(ix,x[key+'_margin_common']-x['actual_margin_common'],'o' if k%2==0 else '^',ms=4,c=C[v],mfc=C[v] if v=='sampled' else 'white',mew=.8)
ax[1].tick_params(axis='x',labelsize=6.2)
ax[0].set(yscale='log',ylabel='Maximum position error (m)',title='(a) Six snapshots × two fixed protocols');ax[0].legend()
ax[1].set(ylabel='Predicted − actual margin (m)',xlabel='Snapshot and circle / triangle protocols',xticks=range(1,7),xticklabels=['1\n-90/N','2\nC/N','3\n+45/N','4\nN/C','5\nN/C','6\n-90/N']);ax[1].axhline(0,c='k',lw=.6)
for a in ax:
 for i in range(1,7):a.axvspan(i-.45,i+.45,color='#ddd',alpha=.25)
 a.grid(alpha=.18)
save(f,'figure4_prediction')
case_summary={}
for sid,name in [('r12new_mixed_pressure_1','figure5_rescue'),('r12new_endpoint_3','figure6_adverse')]:
 ds={v:data[sid,v] for v in C};f,ax=plt.subplots(2,1,figsize=(3.4,4.45),gridspec_kw={'height_ratios':[1.5,1]});sync=260 if 'pressure' in sid else 200
 for o in ds['sampled']['scene']['static']:ax[0].add_patch(Circle(o['center_xy'],o['entity_radius']+60,fc='#eee',ec='#888',ls='--',lw=.5));ax[0].add_patch(Circle(o['center_xy'],o['entity_radius'],fc='#aaa'))
 summary={}
 for v,d in ds.items():
  tr=d['trajectory'];xy=np.array([x['raw'][:2] for x in tr]);ax[0].plot(*xy.T,c=C[v],ls=STYLE[v],lw=1.15,label=f"{L[v]} {d['row']['time_s']}s");ax[0].plot(*xy[sync],'o',ms=3,c=C[v]);tt=[x['time'] for x in tr[1:]];mm=[x['dynamic'][0]['margin'] for x in tr[1:]];ax[1].plot(tt,mm,c=C[v],ls=STYLE[v],lw=1.15)
  mi=int(np.argmin(mm))+1;ax[0].plot(*xy[mi],marker='x' if mm[mi-1]<=0 else '+',ms=5,c=C[v]);summary[v]={'row':d['row'],'minimum_at_step_end':tr[mi]['time'],'minimum_fraction':tr[mi]['dynamic'][0]['fraction']}
 target=np.array([x['targets'][0]['position'] for x in max(ds.values(),key=lambda d:d['row']['time_s'])['trajectory']]);ax[0].plot(*target.T,'k--',lw=.7,label='Target');ax[0].plot(*target[sync],'ks',ms=3);ax[0].add_patch(Circle(target[sync],85,fill=False,ec='k',ls=':',lw=.6));ax[0].plot(*ds['sampled']['scene']['goal'],'k*',ms=5)
 ax[0].set(title=f'(a) {"Unique L failure" if "pressure" in sid else "S15 adds 308 s"} — markers: {sync}s',xlabel='World x (m)',ylabel='World y (m)');ax[0].set_aspect('equal',adjustable='datalim');ax[0].legend(ncol=2,fontsize=6)
 ax[1].set(xlabel='Physical time (s)',ylabel='Dynamic margin (m)',title='(b) Synchronized segment clearance');ax[1].axhline(0,c='k',ls='--',lw=.7)
 if 'pressure' in sid:ax[1].set_ylim(-8,180);ax[1].set_xlim(240,460)
 for a in ax:a.grid(alpha=.2)
 save(f,name);case_summary[sid]=summary

print("Regenerated five data figures from frozen traces; no experiments.")
