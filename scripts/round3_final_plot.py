"""True final results plus one three-case animation; selection is descriptive."""
import os,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];run=ROOT/'runs/round3_20261011_2308';dest=run/'figures';dest.mkdir(exist_ok=True)
os.environ['MPLCONFIGDIR']=str(ROOT/'.cache/matplotlib')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation,PillowWriter
from matplotlib.patches import Wedge,Circle
summary=json.loads((run/'confirmation50/summary.json').read_text())['training_seeds']
freeze=json.loads((run/'freeze.json').read_text());methods=('normal','w0','old_avoid','old_range','guard_old_range','final_avoid','final_range')
short=('normal','W0','old\nexpert','old\nrange','guard\nold range','new\nexpert','new\nrange')
colors=('#7b8794','#987bb7','#afb6c5','#a0b3cb','#d79e4c','#5fa882','#216a93')
fig,axs=plt.subplots(2,2,figsize=(12,8))
for j,e in enumerate(freeze['experts']):
    seed=e['train_seed'];ss=summary[str(seed)];ax=axs[0,j];yy=[ss[m]['safe_complete'] for m in methods]
    ax.bar(np.arange(7),yy,color=colors);ax.set_xticks(np.arange(7),short);ax.set_ylim(0,54);ax.set_ylabel('Safe complete / 50')
    for k,y in enumerate(yy):ax.text(k,y+.5,str(y),ha='center',fontsize=10)
    ax.set_title(f'Training seed {seed} | same unseen 50');ax.grid(axis='y',alpha=.2)
    dev=[json.loads(x) for x in (run/f'train_{seed}/development.jsonl').read_text().splitlines()]
    ax=axs[1,j];ax.plot([d['steps'] for d in dev],[sum(r['safe_complete'] for r in d['results']) for d in dev],'o-',color=colors[-1])
    ax.axvline(e['steps'],ls='--',color='darkred',label=f'Selected {e["steps"]} before new50')
    ax.set_ylim(0,12.6);ax.set_xlabel('Training environment steps');ax.set_ylabel('Old development safe / 12');ax.legend(fontsize=8);ax.grid(alpha=.2)
fig.suptitle('Round 3: two independent trainings; one 50-scene confirmation set',fontsize=13)
fig.tight_layout();fig.savefig(dest/'03_final_confirmation.png',dpi=170);plt.close(fig)
rows=[]
for seed in (20261011,20261012):rows.extend(json.loads(x) for x in (run/f'confirmation50/seed_{seed}/episodes.jsonl').read_text().splitlines())
lookup={(r['train_seed'],r['seed'],r['mode']):r for r in rows}
normal=next(r for r in rows if r['mode']=='normal' and r['kind']=='none' and r['safe_complete'])
returned=[r for r in rows if r['mode']=='final_range' and r['safe_complete'] and r['finished_normal_after_handback']]
def rank(r):
    old=lookup[r['train_seed'],r['seed'],'old_range'];n=lookup[r['train_seed'],r['seed'],'normal']
    return (not old['safe_complete'],not n['safe_complete'],r['kind'] in ('headon','cross'),-r['seed'],-r['train_seed'])
good=max(returned,key=rank) if returned else max((r for r in rows if r['mode']=='final_range'),key=lambda r:r['takeover_seconds'])
bad=[r for r in rows if r['mode']=='final_range' and not r['safe_complete']]
def badrank(r):
    competitors=[lookup[r['train_seed'],r['seed'],m]['safe_complete'] for m in ('w0','guard_old_range','final_avoid','old_range')]
    return (sum(competitors),bool(r['handback_times']),-r['seed'],-r['train_seed'])
bad=max(bad,key=badrank) if bad else max((r for r in rows if r['mode']=='final_range'),key=lambda r:r['time'])
selected=[('Normal / no target',normal),('Takeover and return' if returned else 'Takeover, no verified return',good),('Failure or cost',bad)]
fig,axes=plt.subplots(2,3,figsize=(15,8),gridspec_kw={'height_ratios':[1.5,1]});artists=[];all_frames=set();details=[]
for col,(label,r) in enumerate(selected):
    path=run/f'confirmation50/seed_{r["train_seed"]}/trajectories/{r["seed"]}_{r["mode"]}.npz'
    z=np.load(path);spec=json.loads(str(z['spec']));raw=z['raw'];target=z['target'];tt=z['t'];active=z['active'].copy();active[-1]=active[-2]
    ax=axes[0,col];dx=axes[1,col];ax.plot(raw[:,0],raw[:,1],color='#d9dde2',lw=1)
    dynamic=np.isfinite(target).all()
    if dynamic:ax.plot(target[:,0],target[:,1],'--',color='#ecc5bf',lw=1)
    for center in spec['statics']:ax.add_patch(Circle(center,40,color='gray',alpha=.25))
    xy=np.vstack([raw[:,:2],target[np.isfinite(target).all(axis=1)],[[0,0],[500,0]]])
    ax.set_xlim(xy[:,0].min()-160,xy[:,0].max()+160);ax.set_ylim(xy[:,1].min()-160,xy[:,1].max()+160)
    ax.set_aspect('equal');ax.set_xlabel('World x (m)');ax.set_ylabel('World y (m)');ax.scatter([500],[0],marker='*',c='green',s=70)
    own,=ax.plot([],[],'-',lw=2,color='#216a93');boat,=ax.plot([],[],'o',color='#216a93');other,=ax.plot([],[],'o',color='#be4938')
    fov=Wedge((0,0),150,-60,60,alpha=.13,color='#216a93');ax.add_patch(fov)
    circle=Circle((0,0),40,alpha=.13,color='#be4938');ax.add_patch(circle)
    if dynamic:dx.plot(tt,np.linalg.norm(target-raw[:,:2],axis=1),label='Target center distance')
    for i,center in enumerate(spec['statics']):dx.plot(tt,np.linalg.norm(raw[:,:2]-center,axis=1),label=f'Static {i}')
    if not dynamic and not spec['statics']:dx.text(.5,.5,'No physical target',ha='center',transform=dx.transAxes)
    dx.axhline(40,ls='--',c='red',label='40 m safety domain')
    dx.fill_between(tt,0,1,where=active,step='post',transform=dx.get_xaxis_transform(),alpha=.22,color='orange',label='Expert executed')
    cursor=dx.axvline(0,c='black',lw=1);dx.set_xlim(0,max(1,tt[-1]))
    if not dynamic and not spec['statics']:dx.set_ylim(0,150)
    dx.set_xlabel('Actual simulation time (s)');dx.set_ylabel('Distance (m)');dx.legend(fontsize=7);dx.grid(alpha=.2)
    title=ax.set_title('',fontsize=9)
    artists.append((r,z,raw,target,tt,active,own,boat,other,fov,circle,cursor,title,label))
    all_frames.update(r['takeover_times']+r['handback_times']+[r['time']])
    details.append(dict(label=label,train_seed=r['train_seed'],scene=r['seed'],method=r['mode'],safe_complete=r['safe_complete'],
        takeover_times=r['takeover_times'],handback_times=r['handback_times'],min_distance=r['min_distance'],trajectory=str(path.relative_to(ROOT))))
longest=max(r['time'] for _,r in selected);all_frames.update(np.linspace(0,longest,100).astype(int));frames=sorted(all_frames)
fig.suptitle('Actual trajectories | target truth shown only for offline evaluation | orange = expert executed',fontsize=12)
fig.tight_layout(rect=[0,0,1,.94])
def update(t):
    for r,z,raw,target,tt,active,own,boat,other,fov,circle,cursor,title,label in artists:
        i=min(t,len(tt)-1);own.set_data(raw[:i+1,0],raw[:i+1,1]);boat.set_data([raw[i,0]],[raw[i,1]])
        other.set_data([target[i,0]],[target[i,1]]);fov.set_center(raw[i,:2]);angle=np.degrees(raw[i,3]);fov.set_theta1(angle-60);fov.set_theta2(angle+60)
        circle.set_center(target[i] if np.isfinite(target[i]).all() else [-1e6,-1e6]);cursor.set_xdata([tt[i],tt[i]])
        terminal=i==len(tt)-1;who='expert' if active[i] else 'normal';tag=f'ended; last={who}' if terminal else f'executing={who}'
        title.set_text(f'{label} | seed {r["train_seed"]}, scene {r["seed"]}\n{r["mode"]}: t={tt[i]}s, visible={bool(z["visible"][i])}, {tag}')
animation=FuncAnimation(fig,update,frames=frames,interval=100);animation.save(dest/'04_actual_handover_and_cost.gif',writer=PillowWriter(fps=10));plt.close(fig)
manifest=[dict(label='旧50场历史接口与学习适配',file='01_w0_attribution.png',description='已见诊断，包含无目标和远离任务；不当作新确认。'),
 dict(label='四个真实同状态分支',file='02_same_state_branches.png',description='包含训练损失及训练独有的接管正例；不扫描切换时刻。'),
 dict(label='新50场与独立训练选点',file='03_final_confirmation.png',description='两个种子分别报告；相同50场，不合算100个独立场景。'),
 dict(label='真实正常、接管交还、失败或代价',file='04_actual_handover_and_cost.gif',description='三例同步显示实际时间；短回合结束后停帧，不伪造继续执行。',cases=details,
      selection='Post-hoc illustration only: first safe none; safe return prioritizing rescued old-range; failed final-range with most successful controls. No tuning.',frames=len(frames))]
(dest/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest,indent=2))
