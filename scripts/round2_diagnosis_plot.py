"""Static causal-event and same-prefix branch figures from recorded data only."""
import os,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];os.environ['MPLCONFIGDIR']=str(ROOT/'.cache/matplotlib')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
dest=ROOT/'runs/round2_20261011/diagnosis'
results={(r['seed'],r['mode']):r for r in map(json.loads,(ROOT/'runs/confirmation/episodes.jsonl').read_text().splitlines())}
for seed in (910009,910002):
    fig,axs=plt.subplots(3,1,figsize=(11,8),sharex=True,gridspec_kw={'height_ratios':[2,1,1]})
    for j,mode in enumerate(('normal','avoid','range','risk')):
        data=np.load(ROOT/f'runs/confirmation/trajectories/{seed}_{mode}.npz');t=data['t'];raw=data['raw'];active=data['active'].copy();active[-1]=active[-2]
        for offset,key,color in ((0,'visible','green'),(.25,'valid','dodgerblue'),(.5,'active','orange')):
            valid=active if key=='active' else data[key]
            axs[0].fill_between(t,j+offset,j+offset+.18,where=valid,step='post',color=color,label=key if j==0 else None)
        distance=np.linalg.norm(data['target']-raw[:,:2],axis=1)
        axs[1].plot(t,distance,label=mode);axs[2].plot(t,np.degrees(np.unwrap(raw[:,3])),label=mode)
        result=results[seed,mode];end='violation' if result['violated'] else 'arrival' if result['arrived'] else 'other stop'
        axs[0].annotate(end,(t[-1],j+.5),xytext=(4,0),textcoords='offset points',fontsize=8)
    axs[0].set_yticks(np.arange(4)+.35,['normal','avoid','range','risk']);axs[0].legend(loc='upper left',ncol=3)
    axs[0].set_title(f'Scene {seed}: observed visibility/cache and executed policy (different closed-loop paths)')
    axs[1].axhline(40,color='red',ls='--');axs[1].set_ylabel('Dynamic distance (m)');axs[1].legend(ncol=4,fontsize=8)
    axs[2].set_ylabel('Unwrapped heading (deg)');axs[2].set_xlabel('Simulation time (s)')
    for ax in axs:ax.grid(alpha=.2)
    fig.tight_layout();fig.savefig(dest/f'{seed}_timeline.png',dpi=150);plt.close(fig)
fig,axs=plt.subplots(1,2,figsize=(11,4.5))
for mode in ('trained','normal','initial'):
    d=np.load(dest/f'branches/910009_86_{mode}.npz');raw=d['raw'];t=d['t'];target=d['target']
    axs[0].plot(raw[:,0],raw[:,1],label=mode)
    axs[1].plot(t,np.linalg.norm(target-raw[:,:2],axis=1),label=mode)
axs[0].scatter([raw[86,0]],[raw[86,1]],c='black',s=25,label='identical state at86s');axs[0].scatter([500],[0],marker='*',color='green',s=80)
axs[0].set_xlabel('World x (m)');axs[0].set_ylabel('World y (m)');axs[0].set_aspect('equal');axs[0].legend(fontsize=8)
axs[1].axvline(86,color='black',ls=':');axs[1].axhline(40,color='red',ls='--');axs[1].set_xlabel('Time (s)');axs[1].set_ylabel('Dynamic distance (m)');axs[1].legend()
fig.suptitle('910009: identical real normal prefix, fixed policy after86s; full outcomes')
fig.tight_layout();fig.savefig(dest/'910009_same_state_branches.png',dpi=150);plt.close(fig)
