import sys,json,copy,time,random,hashlib,itertools
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from sailboat_routing.runtime import configure_cpu
configure_cpu()
import numpy as np
from sailboat_routing.r12_model import initial,advance
R=ROOT/'runs/r12_revision_20261006';old=ROOT/'runs/r8_closedloop_20261005T062543Z'
manifest=json.loads((old/'confirmation.json').read_text());scenes={j['scene']['id']:j['scene'] for j in manifest['jobs']}
ids=['r8new_mixed_pressure_'+str(i) for i in [0,2,4]]+['r8new_endpoint_'+str(i) for i in [0,2,5]]+['r8new_'+fam+'_'+str(i) for fam in ['underway_crossing','underway_overtaking','nonconflict'] for i in [0,1]]
assert all(x in scenes for x in ids),list(scenes)
def windows(ids):
    out=[]
    for sid in ids:
        d=json.loads((old/'confirmation'/(sid+'__sampled')/'trace.json').read_text());tr=d['trajectory']
        for t in range(10,len(tr)-16,15):
            q=np.asarray(tr[t+1]['target']);future=tr[t+1:t+16]
            if any(np.linalg.norm(np.asarray(x['target'])-q)>1e-5 for x in future):continue
            h=np.array([x['raw'] for x in tr[:t+1]]);out.append((sid,h,q,np.array([x['raw'][:2] for x in future])))
    return out
trainids=[x for x in ids if x.endswith(('_0','_2'))];validids=[x for x in ids if x not in trainids]
train=windows(trainids);valid=windows(validids)
def metric(params,data):
    by={}
    for sid,h,q,y in data:
        speed,course,rate,_=initial(h);p=h[-1,:2].copy();err=[]
        for k in range(15):p,course,rate=advance(p,course,rate,speed,q,params,k>0);err.append(float(np.linalg.norm(p-y[k])))
        by.setdefault(sid,[]).append(np.mean(err))
    return float(np.mean([np.mean(x) for x in by.values()])),{s:float(np.mean(x)) for s,x in by.items()}
rows=[]
for params in itertools.product([1.,3.,8.,20.],[.025,.05,.1,.2],[.04,.08,.16]):
    score,_=metric(params,train);rows.append({'params':params,'mean_task_mean_position_error':score})
best=min(rows,key=lambda x:x['mean_task_mean_position_error']);params=best['params'];vs,by=metric(params,valid)
out={'model':'finite course-rate lag, fixed causal speed, current heading-course offset for Relay; no wind access','parameters_tau_gain_ratecap':params,'fit_objective':'mean over source tasks of within-task mean15s position error','train_scene_ids':trainids,'validation_scene_ids':validids,'training_windows':len(train),'validation_windows':len(valid),'best_training_error_m':best['mean_task_mean_position_error'],'validation_error_m':vs,'validation_by_scene':by,'grid':rows,'frozen_epoch':time.time(),'note':'target-unchanged actual windows only; source tasks all previously seen; overlapping windows not independent tasks'}
(R/'calibration.json').write_text(json.dumps(out,indent=2));print('calibrated',params,'train',len(train),best['mean_task_mean_position_error'],'val',len(valid),vs,flush=True)
cfg={'sampled':True,'horizon':60,'period':15,'guard':30};simple=dict(cfg,low_order_params=params)
jobs=[{'scene':scenes[sid],'variant':'simple','config':simple} for sid in ids]
jobs += [{'scene':scenes['r8new_mixed_pressure_2'],'variant':'parity30','config':cfg}]
(R/'development.json').write_text(json.dumps({'run':str(R),'jobs':jobs},indent=2))
jobs=[{'scene':scenes[sid],'variant':'guard'+str(g),'config':dict(cfg,guard=g)} for sid in ids for g in [0,15,60]]
(R/'guard.json').write_text(json.dumps({'run':str(R),'jobs':jobs,'reuse_guard30':str(old/'confirmation'),'scene_ids':ids},indent=2))
print('prepared development13 and guard36; no new confirmation generated yet')
