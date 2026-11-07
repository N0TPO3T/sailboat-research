"""Render actual paired trajectories and learning data; no synthetic videos."""
import os
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ['MPLCONFIGDIR']=str(ROOT/'.cache/matplotlib')
import json
import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import Wedge,Circle
p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--train',required=True)
p.add_argument('--no-animation',action='store_true');p.add_argument('--selected-step',type=int)
args=p.parse_args();run=ROOT/args.run;dest=run/'figures';dest.mkdir(exist_ok=True)
records=[json.loads(l) for l in (run/'episodes.jsonl').read_text().splitlines()]
phase_boundaries=[]
def learning_chain(directory):
    config=json.loads((directory/'config.json').read_text())
    parent=config['args'].get('resume')
    previous=learning_chain((ROOT/parent).parent) if parent else []
    if previous:phase_boundaries.append((previous[-1]['steps'],directory.name))
    current=[json.loads(l) for l in (directory/'learning.jsonl').read_text().splitlines()]
    return previous+current
learn=learning_chain(ROOT/args.train)
fig,axs=plt.subplots(2,1,figsize=(9,6),sharex=True)
axs[0].plot([r['steps'] for r in learn],[r['reward'] for r in learn],alpha=.6)
axs[0].set_ylabel('Episode return');axs[0].grid(alpha=.3)
development=ROOT/args.train/'development.jsonl'
if development.exists():
    dev=[json.loads(line) for line in development.read_text().splitlines()]
    da=axs[0].twinx();da.plot([r['steps'] for r in dev],[sum(x['safe_complete'] for x in r['results']) for r in dev],
        'o-',color='darkgreen',lw=1,label='Development safe count')
    da.set_ylabel('Development safe count',color='darkgreen');da.set_ylim(-.2,len(dev[0]['results'])+.2)
axs[1].plot([r['steps'] for r in learn],[r['loss'].get('q_loss',np.nan) for r in learn],label='Q loss')
axs[1].set_yscale('symlog');axs[1].set_ylabel('Q loss');axs[1].set_xlabel('Environment steps');axs[1].grid(alpha=.3)
for step,label in phase_boundaries:
    for axis in axs:axis.axvline(step,color='gray',ls='--',alpha=.6)
    axs[0].text(step,.98,label,transform=axs[0].get_xaxis_transform(),rotation=90,va='top',fontsize=7)
if args.selected_step:
    for axis in axs:axis.axvline(args.selected_step,color='green',ls=':',label='selected checkpoint')
fig.tight_layout();fig.savefig(dest/'learning.png',dpi=160);plt.close(fig)
methods=['normal','avoid','range','risk']
fig,ax=plt.subplots(figsize=(8,4))
ax.bar(methods,[sum(r['safe_complete'] for r in records if r['mode']==m) for m in methods])
n_scenes=len({r['seed'] for r in records})
ax.set_ylabel(f'Safe completed / {n_scenes}');ax.set_ylim(0,n_scenes);fig.tight_layout();fig.savefig(dest/'safety.png',dpi=160);plt.close(fig)

def load(r):return np.load(run/f'trajectories/{r["seed"]}_{r["mode"]}.npz')
normal=next((r for r in records if r['mode']=='normal' and r['kind']=='none' and r['arrived']),records[0])
return_candidates=[r for r in records if r['mode'] in ('range','risk') and r['switches']>=2 and r['safe_complete']]
def return_priority(r):
    baseline=next(x for x in records if x['seed']==r['seed'] and x['mode']=='normal')
    return (not baseline['safe_complete'],r['kind'] in ('cross','headon','edge_static'))
returned=max(return_candidates,key=return_priority) if return_candidates else None
failure=next((r for r in records if r['mode']=='risk' and not r['safe_complete'] and
    next(x for x in records if x['seed']==r['seed'] and x['mode']=='avoid')['safe_complete']),None)
if failure is None:failure=next((r for r in records if r['mode'] in ('range','risk') and not r['safe_complete']),None)
if failure is None:
    failure=max(records,key=lambda r:r['time'])
selected=[('normal',normal),('failure_or_cost',failure)]
if returned:selected.insert(1,('avoid_and_return',returned))
else:
    takeover=max(records,key=lambda r:r['takeover_seconds'] if r['mode'] in ('range','risk') else -1)
    selected.insert(1,('takeover_without_verified_return',takeover))
manifest=[]
for label,r in selected:
    data=load(r);spec=json.loads(str(data['spec']));raw=data['raw'];target=data['target'];t=data['t']
    # The terminal row has no command; its false active flag is a placeholder,
    # not a handback. Extend the last executed interval only for display.
    display_active=data['active'].copy();display_active[-1]=display_active[-2]
    fig,axes=plt.subplots(1,2,figsize=(11,5),gridspec_kw={'width_ratios':[1.5,1]})
    ax,distax=axes
    ax.plot(raw[:,0],raw[:,1],color='lightgray',label='full own trajectory')
    if np.isfinite(target).all():ax.plot(target[:,0],target[:,1],'--',color='lightcoral',label='target (truth for display)')
    ax.scatter([500],[0],marker='*',s=90,color='green',label='goal')
    for center in spec['statics']:ax.add_patch(Circle(center,40,color='gray',alpha=.3))
    all_xy=np.vstack([raw[:,:2],target[np.isfinite(target).all(axis=1)],[[0,0],[500,0]]])
    ax.set_xlim(all_xy[:,0].min()-170,all_xy[:,0].max()+170);ax.set_ylim(all_xy[:,1].min()-170,all_xy[:,1].max()+170)
    ax.set_aspect('equal');ax.set_xlabel('World x (m)');ax.set_ylabel('World y (m)')
    own,=ax.plot([],[],'b-',lw=2);boat,=ax.plot([],[],'bo');other,=ax.plot([],[],'ro')
    fov=Wedge((0,0),150,-60,60,alpha=.12,color='blue');ax.add_patch(fov)
    safety=Circle((0,0),40,alpha=.1,color='red');ax.add_patch(safety)
    dynamic_distance=np.linalg.norm(target-raw[:,:2],axis=1)
    distax.plot(t,dynamic_distance,label='dynamic center distance')
    for i,center in enumerate(spec['statics']):distax.plot(t,np.linalg.norm(raw[:,:2]-center,axis=1),label=f'static {i}')
    distax.axhline(40,color='red',ls='--',label='safety threshold')
    distax.fill_between(t,0,1,where=display_active,step='post',transform=distax.get_xaxis_transform(),color='orange',alpha=.25,label='avoid active')
    cursor=distax.axvline(0,color='black');distax.set_xlabel('Synchronized simulation time (s)');distax.set_ylabel('Distance (m)');distax.legend(fontsize=7)
    ax.legend(fontsize=7);title=fig.suptitle('',fontsize=10);fig.tight_layout(rect=[0,0,1,.93])
    def update(i):
        own.set_data(raw[:i+1,0],raw[:i+1,1]);boat.set_data([raw[i,0]],[raw[i,1]])
        other.set_data([target[i,0]],[target[i,1]])
        fov.set_center(raw[i,:2]);angle=np.degrees(raw[i,3]);fov.set_theta1(angle-60);fov.set_theta2(angle+60)
        safety.set_center(target[i] if np.isfinite(target[i]).all() else [-1e6,-1e6])
        cursor.set_xdata([t[i],t[i]])
        minimum='n/a' if r['min_distance'] is None else f'{r["min_distance"]:.2f} m'
        policy='avoid' if display_active[i] else 'normal'
        policy_label=f'terminal; last policy={policy}' if i==len(t)-1 else f'policy={policy}'
        train_label=f'train {r["train_seed"]}; ' if 'train_seed' in r else ''
        title.set_text(f'{train_label}{label}: {r["mode"]}, scene {r["seed"]}, t={t[i]} s | visible={bool(data["visible"][i])} | {policy_label} | min={minimum}')
        title.set_fontsize(9)
    update(len(t)-1);fig.savefig(dest/f'{label}.png',dpi=150)
    frames=np.unique(np.r_[np.arange(0,len(t),max(1,len(t)//100)),len(t)-1]).astype(int)
    if not args.no_animation:
        animation=FuncAnimation(fig,update,frames=frames,interval=100)
        animation.save(dest/f'{label}.gif',writer=PillowWriter(fps=10))
    plt.close(fig)
    manifest.append(dict(label=label,result=r,file=f'{label}.png' if args.no_animation else f'{label}.gif',full_trajectory_samples=len(t),displayed_frames=len(frames)))
(dest/'animation_manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(manifest,indent=2))
