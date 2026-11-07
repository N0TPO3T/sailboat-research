"""Two real development figures, including normal/away preservation and losses."""
import os,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];os.environ['MPLCONFIGDIR']=str(ROOT/'.cache/matplotlib')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
run=ROOT/'runs/round3_20261011_2308';dest=run/'figures';dest.mkdir(exist_ok=True)
s=json.loads((run/'diagnosis/old50_summary.json').read_text());kinds=['none','away','late','cross','headon','edge_static']
fig,ax=plt.subplots(figsize=(10,4.5));x=np.arange(6);methods=['normal','w0','avoid_20261011','avoid_20261012']
for i,m in enumerate(methods):ax.bar(x+(i-1.5)*.18,[s[m]['by_kind'][k] for k in kinds],width=.18,label=m)
ax.set_xticks(x,kinds);ax.set_ylabel('Safe complete count (seen development)');ax.set_ylim(0,10);ax.legend(ncol=2);ax.grid(axis='y',alpha=.2)
ax.set_title('Old50 attribution: original slots retained; none/away checked')
fig.tight_layout();fig.savefig(dest/'01_w0_attribution.png',dpi=160);plt.close(fig)
branches=[json.loads(x) for x in (run/'diagnosis/branches/results.jsonl').read_text().splitlines()]
fig,axes=plt.subplots(2,2,figsize=(12,9));colors={'normal':'gray','initial':'tab:blue','trained':'tab:orange'}
for ax,scene in zip(axes.flat,[920033,920038,920046,920040]):
    rr=[r for r in branches if r['seed']==scene]
    for r in rr:
        d=np.load(run/'diagnosis/branches'/f'{r["file"]}.npz');cut=r['cut'];p=d['raw'][cut:,:2]
        ax.plot(p[:,0],p[:,1],color=colors[r['continuation']],label=f'{r["continuation"]}: {"safe" if r["safe_complete"] else "fail"}, {r["time"]}s')
        ax.plot(p[-1,0],p[-1,1],'o' if r['safe_complete'] else 'x',color=colors[r['continuation']])
        if r['continuation']=='normal':
            ax.plot(d['raw'][:cut+1,0],d['raw'][:cut+1,1],'k:',lw=1);ax.plot(p[0,0],p[0,1],'k*',ms=10)
            ax.plot(d['target'][:,0],d['target'][:,1],'r--',alpha=.4,label='target truth (offline)')
    ax.set_title(f'{scene}: identical real prefix, branch at {rr[0]["cut"]}s');ax.set_xlabel('World x (m)');ax.set_ylabel('World y (m)');ax.axis('equal');ax.legend(fontsize=7);ax.grid(alpha=.2)
fig.suptitle('Forced continuation to terminal; no branch handback; losses and beneficial case retained')
fig.tight_layout();fig.savefig(dest/'02_same_state_branches.png',dpi=150);plt.close(fig)
print(dest)
