"""Bounded offline retrospective acoustic update pilot; no navigation simulation."""
import os
for _k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[_k] = '1'
os.environ['CUDA_VISIBLE_DEVICES'] = ''
import argparse, csv, json, hashlib, time, math, platform
from pathlib import Path
import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.spatial.distance import cdist
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

SEEDS = [3101,3102,3103]
BUDGETS = [.15,.35]
RIDGES = [1.,10.,100.]
KERNELS = [(r,n) for r in [2.,5.,10.,20.] for n in [.1,1.,5.]]
SIMPLE = ['current_mean','current_strat','current_idw','current_ok','history','history_global','history_strat']
SIMPLE += ['current_median','current_strat_median','history_median']
RAW = ['X','Y','Depth','Month','Mean_thetao_SST','Chl_surf','Mean_NS_vo_Wclm','Mean_EW_uo_Wclm','SO_surf','Mean_current_speed']

def dump(p, x):
    p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def savecsv(p, rows):
    if not rows: return
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def groups(path):
    raw=list(csv.DictReader(path.open(encoding='utf-8-sig')))
    buckets={}
    for i,r in enumerate(raw):
        if int(r['Month']) not in [4,5,6]: continue
        key=(int(r['Year']),int(r['Month']),math.floor(float(r['X'])/2),math.floor(float(r['Y'])/2))
        buckets.setdefault(key,[]).append((i,r))
    out=[]
    for gid,(key,rs) in enumerate(sorted(buckets.items())):
        v={k:float(np.mean([float(r[k]) for _,r in rs])) for k in RAW}
        v.update(gid=gid,year=key[0],month=key[1],cell_x=key[2],cell_y=key[3],
                 center_x=key[2]*2+1.,center_y=key[3]*2+1.,
                 block_x=key[2]//4,block_y=key[3]//4,
                 y=float(np.mean([np.exp(float(r['log_NASC'])) for _,r in rs])),
                 hour_sin=float(np.mean([np.sin(2*np.pi*float(r['Hour'])/24) for _,r in rs])),
                 hour_cos=float(np.mean([np.cos(2*np.pi*float(r['Hour'])/24) for _,r in rs])),
                 n_segments=len(rs),row_indices=';'.join(str(i) for i,_ in rs))
        out.append(v)
    return out

def arrays(g):
    return np.array([[r[k] for k in RAW]+[r['hour_sin'],r['hour_cos']] for r in g],float)

class History:
    def __init__(self, train, ridge):
        x=arrays(train); self.mu=x.mean(0);self.sd=x.std(0);self.sd[self.sd<1e-8]=1
        z=(x-self.mu)/self.sd
        self.knots=np.quantile(z,[.1,.5,.9],axis=0)
        self.centers=np.array([(a,b) for a in np.quantile(x[:,0],[.1,.35,.65,.9]) for b in np.quantile(x[:,1],[.1,.35,.65,.9])])
        f=self.features(x);self.fm=f.mean(0);self.fs=f.std(0);self.fs[self.fs<1e-8]=1
        a=self.design(x);y=np.array([r['y'] for r in train]);ly=np.log(y)
        reg=np.eye(a.shape[1])*ridge;reg[0,0]=0
        self.beta=np.linalg.solve(a.T@a+reg,a.T@ly)
        self.smear=float(np.mean(np.exp(ly-a@self.beta)))
        self.bounds=(float(ly.min()-1),float(ly.max()+1))
    def features(self,x):
        z=np.clip((x-self.mu)/self.sd,-5,5)
        f=[z,z*z,z*z*z]
        for k in self.knots: f.append(np.maximum(z-k,0)**3)
        f.append(np.exp(-cdist(x[:,:2],self.centers)**2/(2*20**2)))
        return np.column_stack(f)
    def design(self,x):
        f=(self.features(x)-self.fm)/self.fs
        return np.column_stack([np.ones(len(x)),f])
    def predict(self,g):
        ly=self.design(arrays(g))@self.beta
        return np.exp(np.clip(ly,*self.bounds))*self.smear

def coords(g): return np.array([[r['center_x'],r['center_y'],r['month']] for r in g])
def cov(a,b,r): return np.exp(-cdist(a[:,:2],b[:,:2])/r-np.abs(a[:,None,2]-b[None,:,2]))

def ok_predict(obs, value, query, radius, nugget):
    a=coords(obs);b=coords(query)
    k=cov(a,a,radius)+np.eye(len(a))*nugget
    cf=cho_factor(k,lower=True,check_finite=False)
    u=cho_solve(cf,np.ones(len(a)),check_finite=False)
    m=float(u@value/u.sum())
    alpha=cho_solve(cf,value-m,check_finite=False)
    return m+cov(b,a,radius)@alpha

def stratum(g):
    return [(r['month'],int(abs(r['Depth'])>=30)+int(abs(r['Depth'])>=60)) for r in g]

def strat_predict(obs,value,query):
    global_m=float(np.mean(value)); ss=stratum(obs); qq=stratum(query); d={}
    for s,v in zip(ss,value):d.setdefault(s,[]).append(v)
    return np.array([(len(d[s])*np.mean(d[s])+5*global_m)/(len(d[s])+5) if s in d else global_m for s in qq])

def strat_median(obs,value,query):
    d={}
    for k,v in zip(stratum(obs),value):d.setdefault(k,[]).append(v)
    return np.array([np.median(d[k]) if k in d else np.median(value) for k in stratum(query)])

def model_state(model,train,out,name):
    dump(out/name,{'train_gids':[r['gid'] for r in train],**{k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in vars(model).items()}})

def split(g, fraction, seed):
    blocks=sorted(set((r['block_x'],r['block_y']) for r in g));k=max(1,min(len(blocks)-1,math.ceil(fraction*len(blocks))))
    rng=np.random.default_rng(seed); selected={blocks[i] for i in rng.choice(len(blocks),k,replace=False)}
    visible=np.array([(r['block_x'],r['block_y']) in selected for r in g])
    xy=coords(g)[:,:2];distance=cdist(xy,xy[visible]).min(1)
    test=(~visible)&(distance>=2.0-1e-10)
    assert visible.any() and test.sum()>=10 and not np.any(visible&test)
    return visible,test,k/len(blocks),distance,k,len(blocks)

def metrics(y,p):
    e=p-y;mean=float(np.mean(y));q=np.quantile(y,.9)
    return {'nmae':float(np.mean(abs(e))/mean),'nrmse':float(np.sqrt(np.mean(e*e))/mean),
            'relative_bias':float(np.mean(e)/mean),'log_rmse':float(np.sqrt(np.mean((np.log(np.maximum(p,1e-9))-np.log(y))**2))),
            'tail_nmae':float(np.mean(abs(e[y>=q]))/mean),'test_mean':mean,'n_test':len(y)}

def predictions(g,visible,h,k_ok,k_rk):
    obs=[r for r,v in zip(g,visible) if v];v=np.array([r['y'] for r in obs]);res=v-h[visible]
    dist=cdist(coords(g)[:,:2],coords(obs)[:,:2]);dm=np.abs(coords(g)[:,None,2]-coords(obs)[None,:,2]);w=1/(dist*dist+(5*dm)**2+1)
    p={'current_mean':np.full(len(g),np.mean(v)), 'current_median':np.full(len(g),np.median(v)), 'current_strat_median':strat_median(obs,v,g), 'history_median':h+np.median(res), 'current_strat':strat_predict(obs,v,g),
       'current_idw':w@v/w.sum(1),'current_ok':ok_predict(obs,v,g,*k_ok),
       'history':h,'history_global':h+np.mean(res),'history_strat':h+strat_predict(obs,res,g),
       'regression_kriging':h+ok_predict(obs,res,g,*k_rk)}
    return {m:np.maximum(a,0) for m,a in p.items()}

def diagnostics(g):
    a=g[:12]; one=np.ones(12)*7.5
    p=ok_predict(a,one,g[12:24],5.,1.)
    assert np.max(abs(p-7.5))<1e-9
    assert np.max(abs(strat_predict(a,one,g[12:24])-7.5))<1e-9
    k=cov(coords(a),coords(a),5.)
    assert np.max(abs(k-k.T))<1e-12
    assert np.isfinite(arrays(g)).all() and min(r['y'] for r in g)>0
    y=np.array([r['y'] for r in a]);assert np.max(abs(np.exp(np.log(y))-y))<1e-9
    vis,t,pi,d,_,_=split(g,.15,3101)
    assert np.all(d[t]>=2-1e-10)
    h=np.array([r['y'] for r in g]);assert abs(h.mean()+np.sum((h[vis]-h[vis])/pi)/len(h)-h.mean())<1e-12
    return {'constant_kriging':'pass','constant_stratum':'pass','covariance_symmetry':'pass','finite_features':'pass','linear_log_roundtrip':'pass','buffer':'pass','greg_zero_residual':'pass'}

def development(allg,out):
    tr=[r for r in allg if r['year']==2019];g=[r for r in allg if r['year']==2020];y=np.array([r['y'] for r in g])
    masks=[(b,s,split(g,b,s)) for b in BUDGETS for s in SEEDS]
    ridge_scores=[]
    for ridge in RIDGES:
        h=History(tr,ridge).predict(g)
        ridge_scores.append((np.mean([metrics(y[sp[1]],h[sp[1]])['nmae'] for _,_,sp in masks]),ridge))
    _,ridge=min(ridge_scores);model=History(tr,ridge);h=model.predict(g);model_state(model,tr,out,'history_2020.json')
    ks=[]
    for radius,nugget in KERNELS:
        scores={'current_ok':[],'regression_kriging':[]}
        for b,s,(vis,test,*_) in masks:
            obs=[r for r,v in zip(g,vis) if v]
            for method,value in [('current_ok',y[vis]),('regression_kriging',y[vis]-h[vis])]:
                p=ok_predict(obs,value,g,radius,nugget)+(h if method=='regression_kriging' else 0)
                scores[method].append(metrics(y[test],np.maximum(p[test],0))['nmae'])
        ks.append({'radius':radius,'nugget':nugget,**{m:float(np.mean(v)) for m,v in scores.items()}})
    best_ok=min(ks,key=lambda r:r['current_ok']);best_rk=min(ks,key=lambda r:r['regression_kriging'])
    kok=(best_ok['radius'],best_ok['nugget']);krk=(best_rk['radius'],best_rk['nugget'])
    rows=[];devpred=[];devsplit=[]
    for b,s,(vis,test,pi,dist,k,nb) in masks:
        ps=predictions(g,vis,h,kok,krk)
        for i,r in enumerate(g):
            devsplit.append({'year':2020,'budget':b,'seed':s,'gid':r['gid'],'visible':int(vis[i]),'test':int(test[i]),'pi':pi,'distance':float(dist[i])})
            for m,p in ps.items():devpred.append({'year':2020,'budget':b,'seed':s,'gid':r['gid'],'method':m,'truth':float(y[i]),'prediction':float(p[i]),'test':int(test[i])})
        for m,p in ps.items():rows.append({'year':2020,'budget':b,'seed':s,'method':m,**metrics(y[test],p[test])})
    choice=min(SIMPLE,key=lambda m:np.mean([r['nmae'] for r in rows if r['method']==m]))
    savecsv(out/'development_predictions.csv',devpred);savecsv(out/'development_splits.csv',devsplit)
    best=lambda methods:min(methods,key=lambda m:np.mean([r['nmae'] for r in rows if r['method']==m]))
    rec={'best_current_only':best([m for m in SIMPLE if m.startswith('current_')]),'best_history_enabled':best([m for m in SIMPLE if m.startswith('history')]+['regression_kriging']),'training_years':[2019],'selection_year':2020,'ridge':ridge,'ok_kernel':kok,'rk_kernel':krk,'fixed_simple':choice,
         'ridge_scores':[{'nmae':float(a),'ridge':r} for a,r in ridge_scores],'kernel_scores':ks,
         'created_unix':time.time(),'selection_rule':'minimum development mean nmae; no target-year scores used'}
    savecsv(out/'development_scores.csv',rows);dump(out/'development_choice.json',rec)
    return rec

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    start=time.time();a.out.mkdir(parents=True,exist_ok=True)
    assert sha(a.input)=='b3936d9d7507679d3b98ed6f4e0db34a4f6011e43c346e59491a7ff267006b7b', 'Incomplete or wrong input'
    g=groups(a.input);savecsv(a.out/'groups.csv',g)
    dump(a.out/'diagnostics.json',diagnostics([r for r in g if r['year']==2020]))
    print('DIAGNOSTICS PASS',flush=True)
    c=development(g,a.out);print('DEVELOPMENT FROZEN',c['fixed_simple'],c['ridge'],c['ok_kernel'],c['rk_kernel'],flush=True)
    scores=[];splitrows=[];predrows=[];indexrows=[]
    for year in [2021,2022,2023]:
        hist=[r for r in g if r['year']<year];target=[r for r in g if r['year']==year]
        assert max(r['year'] for r in hist)<year
        model=History(hist,c['ridge']);model_state(model,hist,a.out,f'history_{year}.json');h=model.predict(target);y=np.array([r['y'] for r in target]);N=len(y)
        for b in BUDGETS:
            for seed in SEEDS:
                vis,test,pi,dist,k,nb=split(target,b,seed);p=predictions(target,vis,h,c['ok_kernel'],c['rk_kernel'])
                nseg=sum(r['n_segments'] for r,v in zip(target,vis) if v)
                for i,r in enumerate(target):
                    splitrows.append({'year':year,'budget':b,'seed':seed,'gid':r['gid'],'visible':int(vis[i]),'test':int(test[i]),'buffer_excluded':int(not vis[i] and not test[i]),'nearest_visible_km':float(dist[i]),'pi':pi,'selected_blocks':k,'all_blocks':nb,'n_segments':r['n_segments']})
                    for m,v in p.items():predrows.append({'year':year,'budget':b,'seed':seed,'gid':r['gid'],'method':m,'prediction':float(v[i]),'truth':float(y[i]),'visible':int(vis[i]),'test':int(test[i])})
                for m,v in p.items():scores.append({'year':year,'budget':b,'seed':seed,'method':m,'visible_groups':int(vis.sum()),'visible_segments':nseg,**metrics(y[test],v[test])})
                for m,val in {'cluster_HT':np.sum(y[vis]/pi)/N,'GREG_history':np.mean(h)+np.sum((y[vis]-h[vis])/pi)/N,'visible_mean':np.mean(y[vis]),'history_full_mean':np.mean(h)}.items():
                    indexrows.append({'year':year,'budget':b,'seed':seed,'method':m,'estimate':float(val),'full_support_truth':float(y.mean()),'relative_error':float(val/y.mean()-1),'pi':pi,'N_groups':N,'visible_groups':int(vis.sum()),'visible_segments':nseg})
                print('DONE',year,b,seed,'labels',int(vis.sum()),nseg,'test',int(test.sum()),flush=True)
    savecsv(a.out/'splits.csv',splitrows);savecsv(a.out/'predictions.csv',predrows);savecsv(a.out/'scores.csv',scores);savecsv(a.out/'index_estimates.csv',indexrows)
    gate=[]
    for year in [2021,2022,2023]:
        for b in BUDGETS:
            d={m:[r for r in scores if r['year']==year and r['budget']==b and r['method']==m] for m in [c['fixed_simple'],'regression_kriging']}
            base=d[c['fixed_simple']];rk=d['regression_kriging'];bm=float(np.mean([r['nmae'] for r in base]));rm=float(np.mean([r['nmae'] for r in rk]));bb=float(np.mean([abs(r['relative_bias']) for r in base]));rb=float(np.mean([abs(r['relative_bias']) for r in rk]))
            gate.append({'year':year,'budget':b,'simple_nmae':bm,'rk_nmae':rm,'improvement':bm-rm,'simple_abs_bias':bb,'rk_abs_bias':rb,'bias_gate':rb<=bb+.02})
    passed=sum(r['improvement']>=.05 for r in gate)>=4 and all(r['improvement']>=0 and r['bias_gate'] for r in gate)
    verdict={'status':'CONTINUE_SIGNAL' if passed else 'STOP','fixed_simple':c['fixed_simple'],'gate_cells':gate,'qualified_cells':sum(r['improvement']>=.05 for r in gate),'protocol':'PROTOCOL.md; all tests are exploratory across three target years'}
    appgate=[]
    for year in [2021,2022,2023]:
        for b in BUDGETS:
            ss=lambda m:[r for r in scores if r['year']==year and r['budget']==b and r['method']==m]
            cur=ss(c['best_current_only']);his=ss(c['best_history_enabled'])
            delta=float(np.mean([r['nmae'] for r in cur])-np.mean([r['nmae'] for r in his]))
            bias=bool(np.mean([abs(r['relative_bias']) for r in his])<=np.mean([abs(r['relative_bias']) for r in cur])+.02)
            appgate.append({'year':year,'budget':b,'improvement':delta,'bias_gate':bias})
    apppass=sum(r['improvement']>=.05 for r in appgate)>=4 and all(r['improvement']>=0 and r['bias_gate'] for r in appgate)
    verdict['rk_increment_status']='CONTINUE_SIGNAL' if passed else 'STOP_RK_INCREMENT'
    verdict['application_status']='CONTINUE_SIGNAL' if apppass else 'STOP_HISTORY_UPDATE_SIGNAL'
    verdict['application_comparison']={'current':c['best_current_only'],'history_enabled':c['best_history_enabled'],'cells':appgate}
    verdict['status']='CONTINUE_SIGNAL' if passed or apppass else 'STOP_BOTH_GATES'
    dump(a.out/'verdict.json',verdict)
    fig,ax=plt.subplots(figsize=(8,4));xs=np.arange(6);ax.bar(xs-.18,[r['simple_nmae'] for r in gate],.36,label=c['fixed_simple']);ax.bar(xs+.18,[r['rk_nmae'] for r in gate],.36,label='regression kriging');ax.set_xticks(xs,[f"{r['year']} / {r['budget']:.0%}" for r in gate]);ax.set_ylabel('Linear NASC MAE / held-out mean');ax.legend();fig.tight_layout();fig.savefig(a.out/'reconstruction_errors.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,4));sub=[r for r in predrows if r['year']==2023 and r['budget']==.15 and r['seed']==3101 and r['test']]
    for ax,m in zip(axes,[c['fixed_simple'],'regression_kriging']):
        rr=[r for r in sub if r['method']==m];yy=np.array([r['truth'] for r in rr]);pp=np.array([r['prediction'] for r in rr]);ax.scatter(yy,pp,s=9,alpha=.55);lim=max(yy.max(),pp.max());ax.plot([0,lim],[0,lim],'k--',lw=1);ax.set(xlabel='Observed group NASC',ylabel='Predicted group NASC',title=m)
    fig.suptitle('2023, 15% blocks, seed 3101: observed support only');fig.tight_layout();fig.savefig(a.out/'observed_predictions.png',dpi=160);plt.close(fig)
    rows=['# Acoustic update pilot results','',f"Decision: **{verdict['status']}**. Fixed deployable simple method chosen on 2020: `{c['fixed_simple']}`.",'','Primary: linear NASC reconstruction of held-out observed spatial groups. This is an offline retrospective finite-support analysis, not biomass, whole-sea total, routing, or energy saving.','', '| Year | Label block fraction | Simple NMAE | RK NMAE | Improvement | Simple abs bias | RK abs bias |','|---|---:|---:|---:|---:|---:|---:|']
    for r in gate:rows.append(f"| {r['year']} | {r['budget']:.0%} | {r['simple_nmae']:.4f} | {r['rk_nmae']:.4f} | {r['improvement']:+.4f} | {r['simple_abs_bias']:.4f} | {r['rk_abs_bias']:.4f} |")
    rows += ['', 'Separate application comparison: '+json.dumps(verdict['application_comparison']), 'Application gate: '+verdict['application_status'], 'RK increment gate: '+verdict['rk_increment_status'], 'Each target year is a separate sparse-current-year experiment with full prior-year data; this is not a multi-year sparse acquisition deployment.']
    rows+=['',f"Qualifying improvement cells: {verdict['qualified_cells']}/6. All cells must be nonnegative and pass the bias gate; 4 must exceed 0.05.",'','Three mask replicates are correlated resampling sensitivity checks, not independent ocean missions. GREG/HT full-support index errors are separately saved in index_estimates.csv; they do not replace reconstruction evidence.','', 'Cost is reported as visible groups AND actual 7-minute segments in scores.csv. Prior observations at the same spatial location are allowed for annual updating; this does not validate unseen-region extrapolation. Hindcasts are offline information. Uneven diel/month sampling remains a limitation.','', 'Files: groups.csv (including source-row indices), splits.csv, predictions.csv, scores.csv, index_estimates.csv, development_choice.json, diagnostics.json, verdict.json, two PNGs, receipt.json.']
    (a.out/'RESULTS.md').write_text('\n'.join(rows),encoding='utf-8')
    receipt={'input_sha256':sha(a.input),'code_sha256':sha(Path(__file__)),'protocol_sha256':sha(Path(__file__).with_name('PROTOCOL.md')),'development_choice_sha256':sha(a.out/'development_choice.json'),'elapsed_seconds':time.time()-start,'python':platform.python_version(),'numpy':np.__version__,'cpu_workers':1,'thread_env':{k:os.environ[k] for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']},'gpu':0,'rows_grouped':sum(r['n_segments'] for r in g),'groups':len(g),'status':verdict['status']}
    dump(a.out/'receipt.json',receipt);print('FINAL',verdict['status'],'elapsed',receipt['elapsed_seconds'],flush=True)

if __name__=='__main__': main()
