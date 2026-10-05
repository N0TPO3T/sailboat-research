"""R8 offline figures from saved physical traces only."""
import json,sys,csv,os
from pathlib import Path
import numpy as np
os.environ['MPLCONFIGDIR']=str(Path(__file__).resolve().parents[1]/'.cache/matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
R=Path(sys.argv[1]).resolve();F=R/'figures';F.mkdir(exist_ok=True)
C={'reactive':'#c44e52','sampled':'#0072b2','hold60':'#009e73'}
def read(batch,scene,v):return json.loads((R/batch/(scene+'__'+v)/'trace.json').read_text())
def save(fig,name,data):
 fig.tight_layout();fig.savefig(F/(name+'.png'),dpi=180);fig.savefig(F/(name+'.svg'));plt.close(fig);(F/(name+'.json')).write_text(json.dumps(data))
def tracks(ax,d,label,color,step=60):
 tr=d['trajectory'];p=np.array([x['raw'][:2] for x in tr]);ax.plot(*p.T,color=color,label=label)
 for i in range(0,len(tr),step):
  ax.scatter(*p[i],s=12,color=color);ax.annotate(str(tr[i]['time'])+'s',p[i],fontsize=6,color=color)
 for j,o in enumerate(tr[0]['targets']):
  q=np.array([next(z['position'] for z in x['targets'] if z['id']==o['id']) for x in tr]);ax.plot(*q.T,'--',color='#666666',alpha=.65,label='target vessel' if j==0 else None)
  for i in range(0,len(tr),step):ax.scatter(*q[i],s=12,color='#666666');ax.annotate(str(tr[i]['time'])+'s',q[i],fontsize=6)
 for o in d['scene'].get('static',[]):
  ax.add_patch(Circle(o['center_xy'],o['entity_radius'],color='gray',alpha=.4));ax.add_patch(Circle(o['center_xy'],o['entity_radius']+60,fill=False,color='gray',ls=':'))
 ax.scatter(*d['scene']['goal'],marker='*',s=80,color='black');ax.set_aspect('equal',adjustable='box');ax.set_xlabel('East / m');ax.set_ylabel('North / m');ax.grid(alpha=.2)
def margins(ax,d,label,color):
 tr=d['trajectory'];pts=[(x['time'],min(z['margin'] for z in x['dynamic'])) for x in tr[1:] if x.get('dynamic')]
 if pts:ax.plot(*np.array(pts).T,label=label,color=color)
 ax.axhline(0,color='black',ls=':');ax.set_xlabel('Time / s');ax.set_ylabel('Synchronous dynamic clearance minus 85 m');ax.grid(alpha=.2)
a=read('development2','confirm_mixed_3','reactive');b=read('development2','confirm_mixed_3','sampled')
fig,axes=plt.subplots(1,3,figsize=(15,4.5));tracks(axes[0],a,'Reactive',C['reactive']);tracks(axes[1],b,'Sampled15',C['sampled']);axes[0].set_title('Known development failure: 184 s');axes[1].set_title('Closed-loop recovery: 431 s')
for ax,d in zip(axes[:2],[a,b]):
 for ev in d['events']:
  if ev['event'] in ['enter','release']:
   p=d['trajectory'][ev['time']]['raw'][:2];ax.scatter(*p,marker='x',color='black');ax.annotate(ev['event']+' '+str(ev['time']),p,xytext=(0,35 if ev['event']=='enter' else -45),textcoords='offset points',fontsize=7,arrowprops={'arrowstyle':'-'})
 margins(axes[2],d,d['row']['variant'],C[d['row']['variant']]);ax.legend(fontsize=7);ax.set_xlim(-70,1060);ax.set_ylim(-330,450)
 bad=next((x for x in d['trajectory'][1:] if any(z['margin']<=0 for z in x.get('dynamic',[]))),None)
 if bad:
  ax.scatter(*bad['raw'][:2],marker='X',color='black');ax.annotate('first incursion '+str(bad['time'])+'s',bad['raw'][:2],xytext=(5,-25),textcoords='offset points',fontsize=7);ax.add_patch(Circle(bad['targets'][0]['position'],85,fill=False,color='black',ls='--',alpha=.5))
axes[2].legend();save(fig,'01_underway_recovery',{'source':['development2/confirm_mixed_3__reactive/trace.json','development2/confirm_mixed_3__sampled/trace.json'],'rows':[a['row'],b['row']]})
pr=next(p for p in b['predictions'] if p['time']==115);fig,axes=plt.subplots(1,2,figsize=(12,5));data=[]
for c in pr['candidates']:
 if c['name'] not in ['nominal','continue','turn90','turn-90']:continue
 paths=list((R/'branches').glob('*'+c['name']+'*/trace.json'))
 if not paths:continue
 d=json.loads(paths[0].read_text());actual=np.array([x['raw'][:2] for x in d['trajectory'][115:176]]);pred=np.array(c['prediction']['path']);line,=axes[0].plot(*actual.T,label=c['name']+' actual');axes[0].plot(*pred.T,'--',color=line.get_color());axes[1].plot(np.arange(116,116+len(c['prediction']['margins'])),c['prediction']['margins'],'--',color=line.get_color(),label=c['name']+' predicted');v=[min(z['margin'] for z in x['dynamic']) for x in d['trajectory'][116:176]];axes[1].plot(np.arange(116,116+len(v)),v,color=line.get_color());data.append({'candidate':c,'source':str(paths[0].relative_to(R))})
axes[0].set_aspect('equal',adjustable='box');axes[0].set_xlabel('East / m');axes[0].set_ylabel('North / m');axes[0].legend(fontsize=8);axes[0].set_title('Same prefix at 115 s; solid actual, dashed prediction');axes[1].axhline(30,color='gray',ls=':',label='planning guard');axes[1].axhline(0,color='black',ls=':');axes[1].axvline(130,color='gray',alpha=.4);axes[1].set_xlabel('Time / s');axes[1].set_ylabel('Dynamic margin / m');axes[1].legend(fontsize=7);save(fig,'02_candidate_execution',data)
if (R/'confirmation/completion.json').exists():
 rows=json.loads((R/'confirmation/rows.json').read_text());pairs={}
 for x in rows:pairs.setdefault(x['scene_id'],{})[x['variant']]=x
 adverse=sorted(pairs,key=lambda s:(pairs[s]['reactive']['success'] and not pairs[s]['sampled']['success'],(pairs[s]['sampled']['time_s']-pairs[s]['reactive']['time_s']) if pairs[s]['sampled']['success'] and pairs[s]['reactive']['success'] else -100000),reverse=True)[0]
 fig,axes=plt.subplots(2,1,figsize=(11,7));data=[]
 for v in ['reactive','sampled','hold60']:
  d=read('confirmation',adverse,v);tracks(axes[0],d,v,C[v],120);margins(axes[1],d,v,C[v]);data.append(d['row'])
 axes[0].set_title('Fresh adverse / largest time-cost case: '+adverse);handles,labels=axes[0].get_legend_handles_labels();unique=dict(zip(labels,handles));axes[0].legend(unique.values(),unique.keys(),fontsize=7);axes[1].legend();save(fig,'03_adverse_case',data)
 fig,axes=plt.subplots(1,2,figsize=(13,5));families=sorted(set(x['family'] for x in rows));xx=np.arange(len(families));data={}
 for j,v in enumerate(['reactive','sampled','hold60']):
  rates=[]
  for f in families:
   q=[x for x in rows if x['family']==f and x['variant']==v];rates.append(sum(x['success'] for x in q)/len(q));data[v+'_'+f]=q
  axes[0].bar(xx+(j-1)*.24,rates,width=.24,label=v,color=C[v])
  if v!='reactive':
   dt=sorted(p[v]['time_s']-p['reactive']['time_s'] for p in pairs.values() if p[v]['success'] and p['reactive']['success']);axes[1].plot(np.arange(1,len(dt)+1),dt,'o-',label=v,color=C[v])
 axes[0].set_title('Frozen 30 scenes: 6 per stratum');axes[1].set_title('Common-safe pairs only: n=28');axes[0].set_xticks(xx,families,rotation=20,ha='right');axes[0].set_ylim(0,1.1);axes[0].set_ylabel('Safe arrival fraction');axes[0].legend();axes[1].axhline(0,color='black',ls=':');axes[1].set_xlabel('Sorted common-safe pair');axes[1].set_ylabel('Arrival time difference vs reactive / s');axes[1].legend();save(fig,'04_fresh_results',data)
if (R/'long/completion.json').exists():
 rows=json.loads((R/'long/rows.json').read_text());scenes=list(dict.fromkeys(x['scene_id'] for x in rows));fig,axes=plt.subplots(4,1,figsize=(14,10));data=[]
 for ax,s in zip(axes.flat,scenes):
  for v in ['reactive','sampled','hold60']:
   d=read('long',s,v);tracks(ax,d,v,C[v],300);data.append(d['row'])
  ax.set_title(s);handles,labels=ax.get_legend_handles_labels();unique=dict(zip(labels,handles));ax.legend(unique.values(),unique.keys(),fontsize=7)
 save(fig,'05_long_continuous',data)

if (R/'joint_active_turn/completion.json').exists():
 fig,axes=plt.subplots(1,2,figsize=(12,5));data=[]
 for v in ['reactive','sampled','hold60']:
  d=read('joint_active_turn','dev_joint_active_turn195',v);tracks(axes[0],d,v,C[v],100);margins(axes[1],d,v,C[v]);data.append(d['row'])
 axes[0].set_title('Development: target turns at 195 s during active hold');axes[0].legend(fontsize=7);axes[1].axvline(195,color='black',ls='--',label='target turn');axes[1].legend();save(fig,'06_active_turn',data)

html='<html><meta charset="utf-8"><title>R8 actual closed-loop results</title><body><h1>R8 actual trajectory gallery</h1><p>All curves come from saved physical traces. Development and fresh evaluation identities are retained in figure data. Not a real-time guarantee.</p>'
for p in sorted(F.glob('*.png')):html+='<h2>'+p.stem+'</h2><img style="max-width:100%" src="'+p.name+'"><p><a href="'+p.with_suffix('.json').name+'">Data / sources</a> | <a href="'+p.with_suffix('.svg').name+'">SVG</a></p>'
(F/'index.html').write_text(html+'</body></html>')
print(str(F))
