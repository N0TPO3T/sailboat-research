"""Replot existing R10/R8 evidence only; no environment or policy execution."""
from pathlib import Path
import json,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle,FancyBboxPatch
P=Path(__file__).resolve().parent;O=P/'figures';O.mkdir(exist_ok=True)
source=Path(sys.argv[1]) if len(sys.argv)>1 else P.parents[2]/'runs/r10_decision_20261005/preview/figure_data/plot_sources.json'
D=json.loads(source.read_text(encoding='utf8'))
plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman','DejaVu Serif'],'font.size':8,'axes.titlesize':9,'legend.fontsize':7,'axes.labelsize':8,'svg.fonttype':'none'})
C={'sampled':'#0072B2','reactive':'#009E73','nominal_hold':'#D55E00'};L={'sampled':'Search15','reactive':'Reactive','nominal_hold':'Nominal-prediction hold'};used={}
def get(sid,v):
 matches=[(k,x) for k,x in D.items() if x['row']['scene_id']==sid and x['row']['variant']==v];assert len(matches)==1
 k,x=matches[0];used[k]=x;return x
def save(f,name):
 f.tight_layout(pad=.65)
 for ext in ['png','svg','pdf']:f.savefig(O/(name+'.'+ext),dpi=300)
 plt.close(f)
f,ax=plt.subplots(figsize=(3.4,2.85));ax.set_xlim(0,10);ax.set_ylim(0,10);ax.axis('off')
def box(x,y,w,h,txt,fc='#f4f7fb'):
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.08',lw=.65,ec='#34495e',fc=fc));ax.text(x+w/2,y+h/2,txt,ha='center',va='center',fontsize=8)
def arr(a,b,txt=None):
 ax.annotate('',xy=b,xytext=a,arrowprops={'arrowstyle':'->','lw':.8})
 if txt:ax.text((a[0]+b[0])/2+.08,(a[1]+b[1])/2,txt,fontsize=7)
box(.25,8.1,9.4,1.2,'Actual state, issued commands, vessel history')
box(.25,5.4,4.2,1.65,'Causal wind fit\nRestore memory\nand setpoints')
box(5.25,5.4,4.4,1.65,'Nominal first\nThen each reference\nwith physical rollouts')
arr((2.4,8.1),(2.4,7.05));arr((7.5,8.1),(7.5,7.05));arr((4.45,6.2),(5.25,6.2))
box(.25,2.85,9.4,1.4,'Synchronous clearance and terminal progress\nSelect reference and hold / restore protocol')
arr((7.5,5.4),(7.5,4.25))
box(.25,.3,9.4,1.35,'Next-step reference delivery\nActual policy and physics\nNew observations','#eef7ee')
arr((5,2.85),(5,1.65),'reference');ax.annotate('',xy=(.15,8.7),xytext=(.15,.95),arrowprops={'arrowstyle':'->','connectionstyle':'angle,angleA=180,angleB=-90,rad=8','lw':.8});ax.text(0,4.8,'actual feedback',rotation=90,ha='right',va='center',fontsize=7)
ax.text(5,9.7,'Internal simulation is separate from actual execution',ha='center',fontsize=8)
save(f,'figure1_interface')
a=get('r8new_mixed_pressure_2','sampled');b=get('r8new_mixed_pressure_2','nominal_hold');p=next(x for x in a['predictions'] if x['time']==149)
f,axs=plt.subplots(2,1,figsize=(3.4,4.45))
for v,d in [('sampled',a),('nominal_hold',b)]:
 xy=np.array([x['raw'][:2] for x in d['trajectory'][149:181]]);axs[0].plot(xy[:,0],xy[:,1],c=C[v],label=L[v]+' actual')
for name,col in [('turn-90',C['sampled']),('continue',C['nominal_hold'])]:
 c=next(x for x in p['candidates'] if x['name']==name);xy=np.array(c['prediction']['path'])[:16];axs[0].plot(xy[:,0],xy[:,1],ls='--',lw=1.4,c=col,label=name+' prediction (15s)')
start=a['trajectory'][149]['raw'][:2];axs[0].scatter(*start,c='k',s=14);axs[0].annotate('149s shared state',start,xytext=(8,-15),textcoords='offset points',fontsize=7)
axs[0].set(title='(a) Reference-dependent maneuver',xlabel='World x (m)',ylabel='World y (m)');axs[0].legend(fontsize=6,loc='lower left');axs[0].grid(alpha=.2)
for v,d in [('sampled',a),('nominal_hold',b)]:
 m=[(x['time'],min(z['margin'] for z in x['dynamic'])) for x in d['trajectory'][1:] if x.get('dynamic')];m=np.array(m);axs[1].plot(m[:,0],m[:,1],c=C[v],label=L[v])
axs[1].axhline(0,c='k',ls='--',lw=.7);axs[1].axvline(150,c='#888',ls=':',lw=.8);axs[1].set(xlim=(140,450),ylim=(-12,210),xlabel='Physical time (s)',ylabel='Actual buffer margin (m)',title='(b) Actual synchronous clearance');axs[1].grid(alpha=.2);axs[1].legend(fontsize=6)
save(f,'figure2_mechanism')
f,axs=plt.subplots(2,1,figsize=(3.4,5.05))
for ax,sid,title,times in [(axs[0],'r8new_mixed_pressure_2','(a) Historical incursion avoided',(150,210)),(axs[1],'r10new_endpoint_0','(b) New confirmation: +271s cost',(250,300))]:
 ds=[(v,get(sid,v)) for v in ['reactive','sampled']]
 for o in ds[0][1]['scene'].get('static',[]):
  ax.add_patch(Circle(o['center_xy'],o['entity_radius']+60,fc='#eee',ec='#888',ls='--',lw=.6));ax.add_patch(Circle(o['center_xy'],o['entity_radius'],fc='#888'))
 for v,d in ds:
  xy=np.array([x['raw'][:2] for x in d['trajectory']]);ax.plot(xy[:,0],xy[:,1],c=C[v],lw=1,label=f"{L[v]}: {d['row']['time_s']}s")
  for ti,t in enumerate(times):
   ax.plot(*xy[t],'o',c=C[v],ms=3);ax.annotate(str(t)+'s',xy[t],xytext=((-25 if ti==0 else 7),(-17 if v=='sampled' else 9)),textcoords='offset points',fontsize=6,color=C[v])
  if not d['row']['success']:ax.plot(*xy[-1],'x',c=C[v],ms=7,mew=1.3)
 q=np.array([x['targets'][0]['position'] for x in ds[1][1]['trajectory']]);ax.plot(q[:,0],q[:,1],'k--',lw=.8,label='Target vessel')
 for ti,t in enumerate(times):
  ax.plot(*q[t],'ks',ms=3);ax.annotate(str(t)+'s',q[t],xytext=((-23 if ti==0 else 5),(16 if ti==0 else -17)),textcoords='offset points',fontsize=6)
 ax.add_patch(Circle(q[times[-1]],85,fill=False,ec='k',ls=':',lw=.7));ax.add_patch(Circle(q[times[-1]],25,fc='#ddd',ec='k',lw=.5));ax.plot(0,0,'ko',ms=3);ax.plot(*ds[1][1]['scene']['goal'],'k*',ms=6)
 ax.set(title=title,xlabel='World x (m)',ylabel='World y (m)');ax.set_aspect('equal',adjustable='datalim');ax.legend(fontsize=6,loc='best');ax.grid(alpha=.2)
save(f,'figure3_encounters')
(P/'figure_data.json').write_text(json.dumps(used),encoding='utf8')
print('three figures saved from',len(used),'existing traces')
