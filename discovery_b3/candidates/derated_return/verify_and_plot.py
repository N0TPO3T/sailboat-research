import os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
os.environ['MPLCONFIGDIR']=str(ROOT/'cache')
import json,hashlib,datetime,time
import numpy as np
from pilot import run,otter,shaft_to_force
os.environ['MPLCONFIGDIR']=str(ROOT/'cache')

def main():
    data=json.loads((ROOT/'runs/main_v1/results.json').read_text());cfg=json.loads((ROOT/'FROZEN_CONFIG.json').read_text())
    hard=next(c for c in cfg['cases'] if c['id']=='rho0.25_left_c0.3')
    out=ROOT/'runs/dt_check';out.mkdir(exist_ok=True);start=time.time();utc=datetime.datetime.now(datetime.timezone.utc).isoformat()
    finer=[run(hard,m,cfg['params'],out,dt=.0125) for m in cfg['methods']]
    (out/'results.json').write_text(json.dumps(finer,indent=2))
    (out/'receipt.json').write_text(json.dumps(dict(pid=os.getpid(),started_utc=utc,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),wall_s=time.time()-start,dt=.0125,n_runs=3),indent=2))
    rows=[];v=otter()
    for r in data:
        a=np.load(ROOT/'runs/main_v1'/f"{r['case']['id']}_{r['method']}.npz")['trajectory']
        assert np.isfinite(a).all() and np.all(np.diff(a[:,0])>0) and np.all(np.diff(a[:,7])>=0)
        psi=a[:,3];hx=abs(np.cos(psi))+abs(np.sin(psi))*.54;hy=abs(np.sin(psi))+abs(np.cos(psi))*.54
        margin=np.minimum.reduce([a[:,1]-hx+4,92-a[:,1]-hx,a[:,2]-hy+4,20-a[:,2]-hy]);assert np.max(abs(margin-a[:,12]))<1e-10
        cmdforces=shaft_to_force(v,a[:,17:19]);caps=a[:,19:21];ratios=caps/119.682
        assert np.all(cmdforces<=caps+1e-8) and np.all(cmdforces>=-66.708*ratios-1e-8)
        assert np.all(a[:,10:12]<=v.n_max+1e-8) and np.all(a[:,10:12]>=v.n_min-1e-8)
        inds=np.flatnonzero(a[:,16]>0)
        if len(inds):
            assert a[inds[0],7]>=40 and np.all(a[:inds[0],7]<40)
            assert abs(a[inds[0],0]-r['fault_time_s'])<1e-10
        rows.append(dict(case=r['case']['id'],method=r['method'],hull_recomputed=True,commands_within_known_derated_limits=True,actual_within_original_hard_limits=True))
    comparisons=[]
    for f in finer:
        r=next(r for r in data if r['case']['id']==hard['id'] and r['method']==f['method'])
        comparisons.append(dict(method=f['method'],main_safe=r['safe_completed'],fine_safe=f['safe_completed'],time_difference_s=f['elapsed_s']-r['elapsed_s'],clearance_difference_m=f['min_hull_margin_m']-r['min_hull_margin_m']))
    report=dict(status='pass',checks=rows,dt_comparison=comparisons,config_sha256=hashlib.sha256((ROOT/'FROZEN_CONFIG.json').read_bytes()).hexdigest())
    (ROOT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));plot(data,cfg)

def plot(data,cfg):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'figure.dpi':150})
    colors={'curvature':'#1f77b4','fixed':'#de7a21','reserve':'#309c6b'}
    case='rho0.25_left_c0.3';fig,axs=plt.subplots(1,3,figsize=(14,4.5))
    for m in cfg['methods']:
        f=np.load(ROOT/'runs/main_v1'/f'{case}_{m}.npz');a=f['trajectory']
        if m=='curvature':axs[0].plot(f['reference'][:,0],f['reference'][:,1],color='black',ls=':',label='Reference')
        axs[0].plot(a[:,1],a[:,2],color=colors[m],label=m)
        k=np.flatnonzero(a[:,16]>0)[0];axs[0].scatter(a[k,1],a[k,2],color=colors[m],s=25)
        axs[1].plot(a[:,0],a[:,9],color=colors[m],label=m)
        axs[2].plot(a[:,0],a[:,12],color=colors[m],label=m)
    axs[0].plot([-4,92,92,-4,-4],[-4,-4,20,20,-4],color='gray',ls='--',label='Operational boundary');axs[0].axis('equal');axs[0].set(xlabel='North x (m)',ylabel='East y (m)',title='Actual 6DOF motion; dots: derating')
    axs[1].set(xlabel='Time (s)',ylabel='Speed reference (m/s)',title='Known left command capacity:25%')
    axs[2].axhline(0,color='black',ls=':');axs[2].set(xlabel='Time (s)',ylabel='Hull clearance (m)',title='Full-task boundary margin')
    for ax in axs:ax.legend(fontsize=8)
    fig.tight_layout();fig.savefig(ROOT/'trajectory_response.png');plt.close(fig)
    fig,axs=plt.subplots(2,1,figsize=(12,7),sharex=True);idx=np.arange(10)
    for j,m in enumerate(cfg['methods']):
        rr=[next(r for r in data if r['case']['id']==c['id'] and r['method']==m) for c in cfg['cases']]
        axs[0].bar(idx+(j-1)*.25,[r['elapsed_s'] for r in rr],width=.24,color=colors[m],label=m)
        axs[1].bar(idx+(j-1)*.25,[r['shaft_variation_rad_s'] for r in rr],width=.24,color=colors[m],label=m)
        for i,r in enumerate(rr):
            if not r['safe_completed']:axs[0].text(i+(j-1)*.25,r['elapsed_s']+3,'FAIL',ha='center',fontsize=7,rotation=90)
    axs[0].set(ylabel='Whole-task duration (s)',title='All ten predetermined tasks; failures retained');axs[0].legend(ncol=3)
    axs[1].set(ylabel='Total shaft-speed variation (rad/s)',xticks=idx,xticklabels=[c['id'] for c in cfg['cases']]);axs[1].tick_params(axis='x',rotation=30)
    fig.tight_layout();fig.savefig(ROOT/'paired_results.png');plt.close(fig)
if __name__=='__main__':main()
