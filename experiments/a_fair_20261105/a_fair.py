"""Bounded, preregistered A-route diagnosis; never edits frozen science sources."""
import os,sys,json,time,hashlib,copy,math,itertools,traceback,shutil
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
import multiprocessing as mp

RUN=Path(__file__).resolve().parent
F=RUN/'frozen'
ORIGIN=Path(json.loads((RUN/'environment.json').read_text())['origin'])
sys.dont_write_bytecode=True
for key in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']:os.environ[key]='1'
os.environ.update(CUDA_VISIBLE_DEVICES='',TMPDIR=str(F/'.tmp'),XDG_CACHE_HOME=str(F/'.cache'),MPLCONFIGDIR=str(F/'.cache/matplotlib'),SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
sys.path[:0]=[str(F/'scripts'),str(F/'src')]
from sailboat_routing.runtime import configure_cpu
configure_cpu()
import numpy as np
import torch
import run_r12
import check_r12_branches as branches
from sailboat_routing.r12_model import LowOrderModel
from sailboat_routing.frames import LocalFrame

def load(p):return json.loads(Path(p).read_text())
def write(p,d):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    temp=p.with_suffix(p.suffix+'.tmp');temp.write_text(json.dumps(d,indent=2,ensure_ascii=False),encoding='utf-8');temp.replace(p)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def source(sid):return ORIGIN/'runs/r8_closedloop_20261005T062543Z/confirmation'/(sid+'__sampled')/'trace.json'
def oldrow(sid,variant):return ORIGIN/'runs/r12_revision_20261006/confirmation'/(sid+'__'+variant)/'row.json'
def integrity():
    freeze=load(RUN/'FREEZE.json')
    for file,key in [('EXPERIMENT_PLAN.md','protocol_sha256'),('new_scenes.json','new_scenes_sha256'),('a_fair.py','driver_sha256')]:assert sha(RUN/file)==freeze[key],file
    for rel,h in load(RUN/'SOURCE_HASHES.json').items():assert sha(F/rel)==h,rel
    assert shutil.disk_usage(RUN).free>2*1024**3,'Less than 2 GiB available; preserve all results and stop'

def smoke():
    integrity();torch.manual_seed(20261105)
    x=torch.randn(8,8);y=x@x
    assert y.shape==(8,8) and torch.isfinite(y).all()
    b=load(RUN/'original_confirmation.json')
    job=copy.deepcopy(next(j for j in b['jobs'] if j['variant']=='reactive'))
    out=RUN/'smoke'/str(time.time_ns());job.update(out=str(out),deadline=time.time()+600,max_steps=12)
    row=run_r12.worker(job)
    actual=load(out/'trace.json')
    expected=load(ORIGIN/'runs/r12_revision_20261006/confirmation'/(job['scene']['id']+'__reactive')/'trace.json')
    assert len(actual['trajectory'])==13
    for a,b in zip(actual['trajectory'],expected['trajectory']):
        assert np.array_equal(np.array(a['raw']),np.array(b['raw'])),'seeded physical prefix differs'
        if 'command' in a:assert a['command']==b['command'],'action differs'
    result={'pass':True,'torch_seed':20261105,'kernel_sum':float(y.sum()),'steps':12,'raw_prefix_exact':True,'commands_exact':True,'row':row,'output':str(out),'versions':{'python':sys.version,'torch':torch.__version__,'numpy':np.__version__}}
    write(out/'witness.json',result);print('WITNESS '+json.dumps(result),flush=True)

def select_snapshots():
    cal=load(RUN/'original_calibration.json');snapshots=[]
    for split,ids in [('train',cal['train_scene_ids']),('validation',cal['validation_scene_ids'])]:
        for sid in ids:
            d=load(source(sid));pred=next(p for p in d['predictions'] if p['time']>=10 and p['time']+1<len(d['trajectory']))
            t=int(pred['time']);scene,static,chart=branches.parts(d);base,nominal=branches.reconstructed_base(d,t,chart)
            assert np.allclose(nominal,pred['candidates'][0]['target'],rtol=0,atol=1e-8)
            current=branches.frame_at(d,t).goal_world;p=np.array(d['trajectory'][t]['raw'][:2]);axis=math.atan2(nominal[1]-p[1],nominal[0]-p[0])
            choices=[dict(name='nominal',target=nominal.tolist(),hold=0),dict(name='continue',target=list(current),hold=15)]
            for deg in [-90,-45,45,90]:choices.append(dict(name=f'turn{deg}',target=(p+350*np.array([math.cos(axis+math.radians(deg)),math.sin(axis+math.radians(deg))])).tolist(),hold=15))
            snapshots.append({'scene_id':sid,'split':split,'time':t,'source':str(source(sid)),'source_sha256':sha(source(sid)),'selected':pred['selected'],'candidates':choices})
    assert len(snapshots)==12
    write(RUN/'snapshots.json',snapshots)
    return snapshots

def branch_worker(job):
    sid=job['scene_id'];t=job['time'];c=job['candidate'];start=time.time();cpu=time.process_time()
    assert sha(source(sid))==job['source_sha256']
    d=load(source(sid));_,_,chart=branches.parts(d);base,nominal=branches.reconstructed_base(d,t,chart)
    result=branches.branch(d,t,c,base)
    assert result['steps']>0,'Zero-step truth branch cannot be scored'
    parity=None
    if c['name']==job['selected']:
        n=min(15,result['steps'],len(d['trajectory'])-1-t)
        parity=float(np.max(np.abs(np.array(result['path'][:n+1])-np.array([x['raw'][:2] for x in d['trajectory'][t:t+n+1]]))))
        assert parity==0,('selected continuation mismatch',sid,t,parity)
    result.update(scene_id=sid,time=t,candidate=c,split=job['split'],source_sha256=job['source_sha256'],selected15s_position_parity=parity,wall_seconds=time.time()-start,cpu_seconds=time.process_time()-cpu)
    path=RUN/'branches'/(sid+'__'+c['name']+'.json');write(path,result)
    return {'file':str(path),'scene_id':sid,'candidate':c['name'],'steps':result['steps'],'reason':result['reason']}

def grid_worker(job):
    params=job['params'];split=job['split'];model=LowOrderModel(params);rows=[]
    for snap in load(RUN/'snapshots.json'):
        if snap['split']!=split:continue
        sid=snap['scene_id'];t=snap['time'];d=load(source(sid));_,static,chart=branches.parts(d);base,_=branches.reconstructed_base(d,t,chart)
        tr=d['trajectory'];h=[np.array(z['raw'],np.float32) for z in tr[:t+1]];actions=[np.array(z['command'],np.float32) for z in tr[1:t+1]];oh=[z['observations'] for z in tr[:t+1]]
        for c in snap['candidates']:
            truth=load(RUN/'branches'/(sid+'__'+c['name']+'.json'))
            pred=model.rollout(h,actions,oh,branches.frame_at(d,t),c['target'],np.array(tr[t+1]['command'],np.float32),60,static,np.array(d['scene']['goal']),copy.deepcopy(base),c['hold'])
            n=truth['steps'];path=np.array(pred['path']);actual=np.array(truth['path'])[1:n+1]
            aligned=np.array([path[min(k,len(path)-1)] for k in range(1,n+1)])
            err=np.linalg.norm(aligned-actual,axis=1)
            rows.append({'scene_id':sid,'candidate':c['name'],'steps':n,'truth_reason':truth['reason'],'prediction_valid':pred['valid'],'prediction_steps':len(path)-1,'padded_steps':max(0,n-len(path)+1),'ade_m':float(err.mean()),'ade15_m':float(err[:15].mean()),'ade30_m':float(err[:30].mean()),'max_error_m':float(err.max()),'errors_m':err.tolist()})
    by={sid:float(np.mean([r['ade_m'] for r in rows if r['scene_id']==sid])) for sid in sorted({r['scene_id'] for r in rows})}
    out={'params':params,'split':split,'score_m':float(np.mean(list(by.values()))),'by_scene':by,'branches':rows}
    write(RUN/'grid'/(job['id']+'.json'),out);return {'id':job['id'],'params':params,'score_m':out['score_m']}

def pool(function,jobs,stage,deadline):
    assert time.time()<deadline
    integrity();rows=[];beg=time.time()
    with ProcessPoolExecutor(max_workers=4,mp_context=mp.get_context('spawn')) as executor:
        futures={executor.submit(function,j):j for j in jobs}
        for f in as_completed(futures):
            result=f.result();rows.append(result);write(RUN/(stage+'_progress.json'),rows)
            print(stage,len(rows),'/',len(jobs),json.dumps(result)[:500],flush=True)
            assert time.time()<deadline,'Six-hour execution limit reached'
    write(RUN/(stage+'_complete.json'),{'complete':True,'jobs':len(jobs),'started':beg,'finished':time.time()})
    return rows

def episode_worker(job):
    row=run_r12.worker(job)
    if not row['complete']:raise RuntimeError('Infrastructure/incomplete episode: '+json.dumps(row))
    return row

def summary():
    paired=[];tables={}
    old=load(RUN/'original_confirmation.json');ids=sorted({j['scene']['id'] for j in old['jobs']})
    oldrows=[load(oldrow(sid,v)) for sid in ids for v in ['reactive','simple','sampled']]
    oldrows += load(RUN/'old_Lstar_progress.json')
    newrows=load(RUN/'new_paired_progress.json');newscenes={s['id']:s for s in load(RUN/'new_scenes.json')['scenes']}
    for stage,rows in [('old_known_tasks',oldrows),('new_paired_tasks',newrows)]:
        scene_ids=sorted({r['scene_id'] for r in rows});methods=sorted({r['variant'] for r in rows});lookup={(r['scene_id'],r['variant']):r for r in rows}
        assert len(lookup)==len(rows)
        tables[stage]={'scene_count':len(scene_ids),'methods':{}}
        for v in methods:
            rr=[lookup[s,v] for s in scene_ids]
            tables[stage]['methods'][v]={'success':sum(r['success'] for r in rr),'arrivals':sum(r['arrived'] for r in rr),'entity_collisions':sum(r['reason']=='entity_collision' for r in rr),'cpu_seconds':sum(r['cpu_seconds'] for r in rr),'planning_seconds':sum(r['planning_seconds'] for r in rr),'failure_ids':[r['scene_id'] for r in rr if not r['success']]}
        deltas=[];wins=[];losses=[];geometry={};collision_losses=[]
        for sid in scene_ids:
            d,l=lookup[sid,'sampled'],lookup[sid,'simple_star'];gain=int(d['success'])-int(l['success'])
            geom=newscenes[sid]['geometry_id'] if stage=='new_paired_tasks' else sid
            geometry[geom]=geometry.get(geom,0)+gain
            if gain>0:wins.append(sid)
            if gain<0:losses.append(sid)
            if d['reason']=='entity_collision' and l['reason']!='entity_collision':collision_losses.append(sid)
            delta=d['time_s']-l['time_s'] if d['success'] and l['success'] else None
            if delta is not None:deltas.append(delta)
            paired.append(dict(stage=stage,scene_id=sid,geometry_id=geom,detailed_success=d['success'],low_order_success=l['success'],gain=gain,common_safe_delta_s=delta,detailed_margin=min(d['min_dynamic_margin'],d['min_static_margin']),low_order_margin=min(l['min_dynamic_margin'],l['min_static_margin'])))
        tables[stage]['detailed_vs_Lstar']={'wins':wins,'losses':losses,'net':len(wins)-len(losses),'geometry_net':geometry,'entity_collision_losses':collision_losses,'common_safe':{'n':len(deltas),'mean_delta_s':float(np.mean(deltas)) if deltas else None,'median_delta_s':float(np.median(deltas)) if deltas else None,'min_delta_s':min(deltas,default=None),'max_delta_s':max(deltas,default=None),'faster':sum(x<0 for x in deltas),'equal':sum(x==0 for x in deltas),'slower':sum(x>0 for x in deltas)}}
    new=tables['new_paired_tasks']['detailed_vs_Lstar'];go=new['net']>0 and sum(v>0 for v in new['geometry_net'].values())>=2 and not new['entity_collision_losses']
    result={'tables':tables,'paired':paired,'decision':'limited_followup_warranted' if go else 'stop_current_detailed_predictor_performance_route','criterion_pass':go,'interpretation':'Prespecified operational gate, not statistical significance or proof of universal equivalence. No extra tuning or samples allowed.','selected_calibration':load(RUN/'calibration.json')['selected_params']}
    write(RUN/'RESULTS.json',result)
    lines=['# A 方案诊断结果','',f"预设判断：{'可考虑有限的机制与成本后续研究' if go else '停止当前以详细预测提升性能为中心的路线'}。",'',f"低阶校准参数：{result['selected_calibration']}。",'','| 数据组 | 方法 | 安全完成 | 实体碰撞 | 完整回合 CPU 秒 |','|---|---|---:|---:|---:|']
    for stage,d in tables.items():
        for method,m in d['methods'].items():lines.append(f"| {stage} | {method} | {m['success']}/{d['scene_count']} | {m['entity_collisions']} | {m['cpu_seconds']:.3f} |")
    lines += ['','详细配对胜负、全部失败、共同安全航时及逐几何净胜见 RESULTS.json。旧任务为增强对照，新任务只有8个独立几何；16个风场实现不能当16个独立几何。原方法耗时从历史记录复用，旧/新时期 CPU 不作为硬件严格匹配的加速比。','本轮没有训练、guard搜索、结果筛选或投稿。全部原始记录保留；负结果不证明所有详细模型均无效。']
    (RUN/'RESULTS_ZH.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(result['tables'],ensure_ascii=False),flush=True)
    print('DECISION',result['decision'],flush=True)

def main():
    mode=sys.argv[1]
    if mode=='smoke':smoke();return
    if mode=='summary':summary();return
    assert mode=='run'
    assert not (RUN/'execution.json').exists(),'Do not blindly restart; inspect existing receipts first'
    began=time.time();deadline=began+21600
    write(RUN/'execution.json',{'started':began,'deadline':deadline,'pid':os.getpid(),'workers':4,'threads':1,'gpu':0,'command':sys.argv})
    try:
        integrity();smoke();snaps=select_snapshots()
        jobs=[dict(s,candidate=c) for s in snaps for c in s['candidates']]
        pool(branch_worker,jobs,'truth_branches',deadline)
        grid=[{'id':f'train_{i:02d}','params':list(p),'split':'train'} for i,p in enumerate(itertools.product([1.,3.,8.,20.],[.025,.05,.1,.2],[.04,.08,.16]))]
        rows=pool(grid_worker,grid,'grid_train',deadline)
        best=min(rows,key=lambda r:(r['score_m'],r['id']));params=best['params']
        validation=grid_worker({'id':'selected_validation','params':params,'split':'validation'})
        original_train=grid_worker({'id':'original_train','params':[8.,.1,.16],'split':'train'})
        original_validation=grid_worker({'id':'original_validation','params':[8.,.1,.16],'split':'validation'})
        write(RUN/'calibration.json',{'selected_params':params,'selected_training':best,'validation_report_only':validation,'original_training':original_train,'original_validation':original_validation,'all_training_grid':sorted(rows,key=lambda r:r['id']),'frozen_epoch':time.time(),'no_test_data_used':True})
        cfg={'sampled':True,'period':15,'horizon':60,'guard':30,'low_order_params':params}
        oldjobs=[]
        for j in load(RUN/'original_confirmation.json')['jobs']:
            if j['variant']=='simple':oldjobs.append(dict(scene=j['scene'],variant='simple_star',config=cfg,out=str(RUN/'old_Lstar'/j['scene']['id']),deadline=deadline))
        write(RUN/'old_Lstar_manifest.json',oldjobs)
        pool(episode_worker,oldjobs,'old_Lstar',deadline)
        methods={'reactive':{'availability':True},'simple_star':cfg,'sampled':{'sampled':True,'period':15,'horizon':60,'guard':30}}
        jobs=[dict(scene=s,variant=v,config=c,out=str(RUN/'new_paired'/(s['id']+'__'+v)),deadline=deadline) for s in load(RUN/'new_scenes.json')['scenes'] for v,c in methods.items()]
        write(RUN/'new_paired_manifest.json',jobs)
        pool(episode_worker,jobs,'new_paired',deadline)
        integrity();summary();write(RUN/'completion.json',{'complete':True,'finished':time.time(),'wall_seconds':time.time()-began,'branches':72,'grid':48,'old_episodes':24,'new_episodes':48,'exit_code':0})
    except BaseException:
        write(RUN/'failure.json',{'complete':False,'time':time.time(),'traceback':traceback.format_exc(),'no_automatic_resampling':True});raise

if __name__=='__main__':main()
