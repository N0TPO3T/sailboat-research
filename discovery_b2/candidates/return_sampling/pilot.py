import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:
    os.environ[key]='1'
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['MPLCONFIGDIR']=os.path.join(os.path.dirname(__file__),'cache','mpl')
import json, time, math, argparse, hashlib
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
from scipy.spatial import ConvexHull
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
DWELL=0.
def utc(): return datetime.now(timezone.utc).isoformat()
def wrap(x): return (x+np.pi)%(2*np.pi)-np.pi
def kernel(a,b,l):
    return np.exp(-np.sum((a[:,None,:]-b[None,:,:])**2,axis=2)/(2*l*l))
def turn(a,b,wind):
    # Heading denotes through-water bow direction; wind is upwind bearing.
    crossing=(np.sin(a-wind)*np.sin(b-wind)<-1e-8)
    return abs(wrap(b-a))/np.deg2rad(8)+(5. if crossing else 0.)

def edges(points,wind,current):
    headings=wind+np.deg2rad(np.arange(45,316,5))
    rel=np.abs(wrap(headings-wind))
    speed=1.25*(0.5+np.sin(rel))
    velocities=np.column_stack([np.cos(headings),np.sin(headings)])*speed[:,None]+current
    hull=ConvexHull(velocities).vertices
    E={}
    for i in range(len(points)):
      for j in range(len(points)):
        if i==j: continue
        delta=points[j]-points[i]; options=[]
        for k in range(len(hull)):
            a,b=hull[k],hull[(k+1)%len(hull)]
            M=velocities[[a,b]].T
            if abs(np.linalg.det(M))<1e-8: continue
            ts=np.linalg.solve(M,delta)
            if np.min(ts)<-1e-8: continue
            legs=[(float(t),int(idx)) for t,idx in zip(ts,[a,b]) if t>1e-7]
            for seq in [legs,legs[::-1]]:
                hs=[float(headings[idx]) for _,idx in seq]
                internal=sum(turn(hs[k-1],hs[k],wind) for k in range(1,len(hs)))
                duration=sum(t for t,_ in seq)+internal
                options.append((duration,seq,hs,internal))
        if not options: raise RuntimeError('Unreachable edge')
        # Preselect least intrinsic cost; tied order deterministic. This limits oracle family.
        duration,seq,hs,internal=min(options,key=lambda z:z[0])
        xy=[points[i].copy()]; elapsed=[0.]
        tnow=0.
        for k,(t,idx) in enumerate(seq):
            if k: tnow+=turn(hs[k-1],hs[k],wind)
            xy.append(xy[-1]+velocities[idx]*t); tnow+=t; elapsed.append(tnow)
        assert np.linalg.norm(xy[-1]-points[j])<1e-7
        assert min(abs(wrap(h-wind)) for h in hs)>=np.deg2rad(45)-1e-8
        E[i,j]={'time':duration,'start':hs[0],'end':hs[-1], 'xy':np.array(xy),
                'elapsed':elapsed,'headings':hs,'internal_turn':internal,
                'sailing':sum(t for t,_ in seq)}
    return E

def cost(route,E,wind,initial):
    if not route:return 0.
    t=0.; at=0; h=initial
    for dst in route+[0]:
        e=E[at,dst]; t+=turn(h,e['start'],wind)+e['time']+(DWELL if dst else 0)
        at=dst;h=e['end']
    return t
def maskof(route):return sum(1<<(i-1) for i in route)

def posterior_catalog(points,grid):
    means={}; variances=np.empty(256)
    for mask in range(256):
        ids=[0]+[i+1 for i in range(8) if mask>>i&1]
        X=points[ids]; K=kernel(X,X,220)+np.eye(len(ids))*.05**2
        cross=kernel(grid,X,220); W=np.linalg.solve(K,cross.T).T
        variances[mask]=np.mean(1-np.sum(W*cross,axis=1))
        means[mask]=(ids,W)
    return variances,means

def improve(route,E,wind,h):
    route=list(route)
    while True:
        old=cost(route,E,wind,h); best=route
        for i in range(len(route)):
            for j in range(i+1,len(route)):
                candidate=route[:i]+route[i:j+1][::-1]+route[j+1:]
                if cost(candidate,E,wind,h)<old-1e-8:
                    best=candidate; old=cost(candidate,E,wind,h)
        if best==route:return route
        route=best

def greedy(V,E,wind,h,budget):
    r=[]
    while True:
        options=[]; old=cost(r,E,wind,h); m=maskof(r)
        for j in range(1,9):
            if j in r:continue
            new=r+[j]; c=cost(new,E,wind,h)
            if c<=budget:
                gain=V[m]-V[m|1<<(j-1)]
                options.append((gain/max(c-old,1e-6),j))
        if not options:return r
        r.append(max(options)[1])

def insertion(V,E,wind,h,budget):
    solutions=[greedy(V,E,wind,h,budget)]
    for start in [[]]+[[i] for i in range(1,9) if cost([i],E,wind,h)<=budget]:
        r=start
        while True:
            m=maskof(r); old=cost(r,E,wind,h); options=[]
            for j in range(1,9):
                if j in r:continue
                for pos in range(len(r)+1):
                    new=improve(r[:pos]+[j]+r[pos:],E,wind,h); c=cost(new,E,wind,h)
                    if c<=budget:
                        options.append(((V[m]-V[m|1<<(j-1)])/max(c-old,1e-6),new))
            if not options: break
            r=max(options,key=lambda z:z[0])[1]
        solutions.append(r)
    return min(solutions,key=lambda r:(V[maskof(r)],cost(r,E,wind,h)))

def exact(V,E,wind,h,budget):
    best=[];bestv=V[0]; calls=0
    # Exhaustive feasible prefix traversal. Turn/dwell times are nonnegative.
    def visit(r,m,at,last_heading,spent):
        nonlocal best,bestv,calls
        calls+=1
        if r:
            e=E[at,0]; total=spent+turn(last_heading,e['start'],wind)+e['time']
            if total<=budget and (V[m]<bestv-1e-12 or
               abs(V[m]-bestv)<1e-12 and total<cost(best,E,wind,h)):
                best=r.copy();bestv=V[m]
        for j in range(1,9):
            if m>> (j-1)&1:continue
            e=E[at,j]; nxt=spent+turn(last_heading,e['start'],wind)+e['time']+DWELL
            if nxt<=budget:
                visit(r+[j],m|1<<(j-1),j,e['end'],nxt)
    visit([],0,0,h,0.)
    return best,calls

def trajectory(route,E,wind,h):
    rows=[{'t':0.,'x':0.,'y':0.,'event':'start'}]; now=0.;at=0
    for dst in route+[0] if route else []:
        e=E[at,dst];now+=turn(h,e['start'],wind)
        rows.append({'t':now,'x':float(e['xy'][0,0]),'y':float(e['xy'][0,1]),'event':'turn_complete'})
        for pt,t in zip(e['xy'][1:],e['elapsed'][1:]):
            rows.append({'t':now+t,'x':float(pt[0]),'y':float(pt[1]),'event':'leg'})
        now+=e['time']
        if dst:now+=DWELL
        rows.append({'t':now,'x':float(e['xy'][-1,0]),'y':float(e['xy'][-1,1]),'event':'sample' if dst else 'home'})
        h=e['end'];at=dst
    assert abs(now-cost(route,E,wind,0.))<1e-6
    return rows

def run(smoke=False):
    out=ROOT/('smoke' if smoke else 'results');out.mkdir(exist_ok=True)
    receipt={'pid':os.getpid(),'start_utc':utc(),'threads':{k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']},'gpu':'','script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2))
    results=[]; traces=[]; detail=[];start=time.monotonic()
    grid=np.array([(x,y) for x in np.linspace(-700,700,13) for y in np.linspace(-700,700,13)])
    for seed in range(100,101 if smoke else 112):
        rng=np.random.default_rng(seed)
        points=np.vstack([np.zeros(2),rng.uniform(-600,600,(8,2))])
        wind=(seed-100)*np.pi/6
        current=np.array([.18*np.cos(wind+.8),.18*np.sin(wind+.8)])
        E=edges(points,wind,current);V,models=posterior_catalog(points,grid)
        # Public geometry-only deadline: alternating 45/65% of directed nearest-neighbour full tour.
        remaining=list(range(1,9));tour=[]
        while remaining:
            j=min(remaining,key=lambda x:cost(tour+[x],E,wind,0.))
            tour.append(j);remaining.remove(j)
        budget=cost(tour,E,wind,0.)*(.45 if seed%2==0 else .65)
        plans={};times={}
        for method,fn in [('greedy',greedy),('insertion',insertion),('exact',exact)]:
            st=time.perf_counter();result=fn(V,E,wind,0.,budget-2.);times[method]=time.perf_counter()-st
            plans[method]=result[0] if method=='exact' else result
        assert V[maskof(plans['exact'])]<=V[maskof(plans['insertion'])]+1e-10
        assert V[maskof(plans['insertion'])]<=V[maskof(plans['greedy'])]+1e-10
        for ell in [120,350]:
            truth_rng=np.random.default_rng(seed*10+int(ell))
            allpts=np.vstack([points,grid]);K=kernel(allpts,allpts,ell)
            truth=np.linalg.cholesky(K+np.eye(len(K))*1e-9)@truth_rng.standard_normal(len(K))
            measurements=truth[:9]+truth_rng.normal(0,.05,9)
            for method,route in plans.items():
                ids,W=models[maskof(route)];pred=W@measurements[ids]
                rmse=float(np.sqrt(np.mean((pred-truth[9:])**2)))
                duration=cost(route,E,wind,0.)
                row={'seed':seed,'true_lengthscale':ell,'method':method,'route':route,'rmse':rmse,
                     'variance':float(V[maskof(route)]),'duration_s':duration,'budget_s':budget,
                     'on_time':bool(duration+times[method]<=budget+1e-8),'samples':len(route),'plan_s':times[method]}
                results.append(row)
                traces.append({'seed':seed,'lengthscale':ell,'method':method,'rows':trajectory(route,E,wind,0.)})
            detail.append({'seed':seed,'lengthscale':ell,'points':points.tolist(),'grid':grid.tolist(),'truth':truth[9:].tolist(),'wind':wind,'current':current.tolist()})
        print(json.dumps({'seed':seed,'elapsed_s':time.monotonic()-start,'planning_s':times}),flush=True)
    (out/'episodes.json').write_text(json.dumps(results,indent=2))
    (out/'trajectories.json').write_text(json.dumps(traces,indent=2))
    (out/'fields.json').write_text(json.dumps(detail))
    pairs=[]
    for seed in range(100,101 if smoke else 112):
      for ell in [120,350]:
        rr={r['method']:r for r in results if r['seed']==seed and r['true_lengthscale']==ell}
        b,p=rr['insertion'],rr['exact']
        pairs.append({'seed':seed,'lengthscale':ell,'rmse_reduction':(b['rmse']-p['rmse'])/b['rmse'],
                      'variance_reduction':(b['variance']-p['variance'])/b['variance']})
    reductions=np.array([p['rmse_reduction'] for p in pairs]); vr=np.array([p['variance_reduction'] for p in pairs])
    summary={'tasks':len(pairs),'all_on_time':all(r['on_time'] for r in results),
             'median_rmse_reduction':float(np.median(reductions)),'mean_rmse_reduction':float(np.mean(reductions)),
             'wins':int(np.sum(reductions>1e-10)),'ties':int(np.sum(abs(reductions)<=1e-10)),
             'mean_variance_reduction':float(vr.mean()),'pairs':pairs,
             'means':{m:{k:float(np.mean([r[k] for r in results if r['method']==m])) for k in ['rmse','variance','samples','duration_s','plan_s']} for m in plans}}
    summary['continue_gate_passed']=summary['all_on_time'] and summary['median_rmse_reduction']>=.1 and summary['wins']>=17 and summary['mean_variance_reduction']>=.05
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    fig,ax=plt.subplots(1,2,figsize=(10,4))
    for ell,color in [(120,'tab:orange'),(350,'tab:blue')]:
        rr=[p for p in pairs if p['lengthscale']==ell]
        ax[0].scatter([p['seed'] for p in rr],[100*p['rmse_reduction'] for p in rr],label=f'true GP l={ell}m',c=color)
    ax[0].axhline(0,color='black',lw=.8);ax[0].axhline(10,color='gray',ls='--');ax[0].legend(fontsize=8)
    ax[0].set(xlabel='geometry/wind seed',ylabel='RMSE reduction vs insertion (%)')
    for m in plans:
        a=[r['rmse'] for r in results if r['method']==m];ax[1].plot(a,label=m,marker='.',alpha=.7)
    ax[1].legend();ax[1].set(xlabel='paired task index',ylabel='final full-domain RMSE')
    fig.tight_layout();fig.savefig(out/'paired_errors.png',dpi=160);plt.close(fig)
    d=detail[0];fig,axs=plt.subplots(1,3,figsize=(13,4),sharex=True,sharey=True)
    for ax,m in zip(axs,plans):
        ax.scatter(grid[:,0],grid[:,1],c=d['truth'],s=25,cmap='viridis',alpha=.5)
        xy=np.array([[r['x'],r['y']] for tr in traces if tr['seed']==100 and tr['lengthscale']==120 and tr['method']==m for r in tr['rows']])
        ax.plot(xy[:,0],xy[:,1],'-r');pts=np.array(d['points']);ax.scatter(pts[1:,0],pts[1:,1],marker='x',c='k');ax.scatter([0],[0],marker='*',s=100,c='white',edgecolors='k')
        for i,pt in enumerate(pts[1:],1):ax.text(*pt,str(i))
        ax.set(title=m,xlabel='east (m)',aspect='equal')
    axs[0].set_ylabel('north (m)');fig.suptitle('Preselected seed 100 / true lengthscale 120m: executed proxy trajectories')
    fig.tight_layout();fig.savefig(out/'trajectories.png',dpi=160);plt.close(fig)
    receipt.update(end_utc=utc(),elapsed_s=time.monotonic()-start,exit_status='completed')
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps(summary),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--smoke',action='store_true');a=p.parse_args();run(a.smoke)



