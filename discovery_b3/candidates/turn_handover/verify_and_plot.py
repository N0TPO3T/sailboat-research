import os,sys
os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.dont_write_bytecode=True
from pathlib import Path
ROOT=Path(__file__).resolve().parent
os.environ['MPLCONFIGDIR']=str(ROOT/'cache')
import json,hashlib
import numpy as np
from pilot import run

def main():
    results=json.loads((ROOT/'runs/main_v3/results.json').read_text())
    frozen=json.loads((ROOT/'FROZEN_CONFIG.json').read_text())
    hard=next(c for c in frozen['cases'] if c['id']=='r8_u1.8_c0.3')
    out=ROOT/'runs/dt_check_v3';out.mkdir(exist_ok=True)
    finer=[run(hard,m,frozen['params'],out,dt=.0125) for m in frozen['methods']]
    (out/'results.json').write_text(json.dumps(finer,indent=2))
    checks=[]
    for r in results:
        a=np.load(ROOT/'runs/main_v3'/f"{r['case']['id']}_{r['method']}.npz")['trajectory']
        assert np.isfinite(a).all();assert np.all(np.diff(a[:,0])>0);assert np.all(np.diff(a[:,7])>=0)
        assert abs(a[:,12].min()-r['min_hull_margin_m'])<1e-10
        # Recompute full hull margin from x,y,yaw independently, not logged margin.
        x,y,psi=a[:,1],a[:,2],a[:,3];R=r['case']['radius']
        hx=abs(np.cos(psi))*1+abs(np.sin(psi))*.54
        hy=abs(np.sin(psi))*1+abs(np.cos(psi))*.54
        direct=np.minimum.reduce([x-hx+4,80+R+4-x-hx,y-hy+4,2*R+4-y-hy])
        assert np.max(abs(direct-a[:,12]))<1e-10
        # Distinct bins reconstructed from recorded state; use path phase as online classifier.
        bins=set()
        for row in a:
            t,x,y,psi,u,v,rr,ss=row[:8]
            line=0 if ss<80 else (1 if ss>80+np.pi*R else -1)
            course=psi+np.arctan2(v,u);angle=(course-(np.pi if line==1 else 0)+np.pi)%(2*np.pi)-np.pi
            valid=line>=0 and abs(y-(2*R if line==1 else 0))<=1 and abs(angle)<=np.deg2rad(10) and .8*r['case']['cruise']<=np.hypot(u,v)<=1.2*r['case']['cruise']
            if valid and 0<=x<80:bins.add((line,int(x)))
        assert len(bins)==r['valid_line_m']
        checks.append(dict(case=r['case']['id'],method=r['method'],raw_metric_match=True))
    # Reserve equality including all logged execution states.
    equal=[]
    for c in frozen['cases']:
        b=np.load(ROOT/'runs/main_v3'/f"{c['id']}_curvature.npz")['trajectory']
        q=np.load(ROOT/'runs/main_v3'/f"{c['id']}_reserve.npz")['trajectory']
        equal.append(dict(case=c['id'],exactly_equal=np.array_equal(b,q)))
    comparisons=[]
    for f in finer:
        r=next(r for r in results if r['case']['id']==hard['id'] and r['method']==f['method'])
        comparisons.append(dict(method=f['method'],duration_difference_s=f['elapsed_s']-r['elapsed_s'],line_difference_m=f['valid_line_m']-r['valid_line_m'],clearance_difference_m=f['min_hull_margin_m']-r['min_hull_margin_m']))
    report=dict(checks=checks,reserve_equalities=equal,dt_comparison=comparisons,config_sha256=hashlib.sha256((ROOT/'FROZEN_CONFIG.json').read_bytes()).hexdigest(),status='pass')
    (ROOT/'verification.json').write_text(json.dumps(report,indent=2))
    plot(results,frozen)
    print(json.dumps(report,indent=2))

def plot(results,frozen):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'figure.dpi':150})
    case='r8_u1.8_c0.3';colors={'curvature':'#1f77b4','heading':'#e07a1f','reserve':'#32936f'}
    fig,axs=plt.subplots(1,2,figsize=(11,4.5))
    for m in frozen['methods']:
        f=np.load(ROOT/'runs/main_v3'/f'{case}_{m}.npz');a=f['trajectory']
        if m=='curvature':axs[0].plot(f['reference'][:,0],f['reference'][:,1],color='black',ls=':',label='Reference')
        axs[0].plot(a[:,1],a[:,2],label=m,color=colors[m],ls='--' if m=='reserve' else '-',lw=1.5)
        axs[1].plot(a[:,0],a[:,9],label=m,color=colors[m],ls='--' if m=='reserve' else '-')
    axs[0].plot([-4,92,92,-4,-4],[-4,-4,20,20,-4],color='gray',ls='--',label='Operational boundary')
    axs[0].set(xlabel='North x (m)',ylabel='East y (m)',title='Actual 6DOF trajectories: R8, 1.8m/s, current0.3m/s');axs[0].axis('equal');axs[0].legend(fontsize=8)
    axs[1].set(xlabel='Time (s)',ylabel='Speed reference (m/s)',title='Executed reference schedules');axs[1].legend(fontsize=8)
    fig.tight_layout();fig.savefig(ROOT/'trajectory_response.png');plt.close(fig)
    fig,axs=plt.subplots(2,1,figsize=(11,7),sharex=True)
    idx=np.arange(8)
    for j,m in enumerate(frozen['methods']):
        rs=[next(r for r in results if r['case']['id']==c['id'] and r['method']==m) for c in frozen['cases']]
        axs[0].bar(idx+(j-1)*.25,[r['valid_line_m'] for r in rs],width=.24,color=colors[m],label=m)
        axs[1].bar(idx+(j-1)*.25,[r['elapsed_s'] for r in rs],width=.24,color=colors[m],label=m)
    axs[0].axhline(160,color='black',ls=':',label='160m maximum');axs[0].set(ylabel='Effective line bins (m)',ylim=(0,175),title='All eight paired task results; no sampling-recovery claim from task completion alone');axs[0].legend(ncol=4,fontsize=9)
    axs[1].set(ylabel='Whole task duration (s)',xticks=idx,xticklabels=[c['id'] for c in frozen['cases']]);axs[1].tick_params(axis='x',rotation=20)
    fig.tight_layout();fig.savefig(ROOT/'paired_results.png');plt.close(fig)
if __name__=='__main__':main()


