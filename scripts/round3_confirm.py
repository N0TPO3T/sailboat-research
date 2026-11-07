"""One frozen 600-rollout confirmation; no filtering by policy outcomes."""
import sys,json,hashlib,subprocess,time,shutil,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from round3_policy import *
from round2_metrics import paired
run=ROOT/'runs/round3_20261011_2308';frozen=json.loads((run/'freeze.json').read_text());out=run/'confirmation50'
assert not out.exists();assert frozen['config']==CFG
for file,digest in frozen['sources'].items():assert hashlib.sha256((ROOT/file).read_bytes()).hexdigest()==digest
out.mkdir();kinds=sum(([k]*n for k,n in [('none',8),('away',8),('late',8),('cross',9),('headon',9),('edge_static',8)]),[])
specs=[scenario(930000+i,k) for i,k in enumerate(kinds)]
previous=bank('dev')+bank('test')+json.loads((ROOT/'runs/round2_20261011/confirmation50/bank.json').read_text())['scenarios']
previous.extend(scenario(s) for s in range(710000,711000))
for rdir in (ROOT/'runs/round2_20261011',run):
    for seed in (20261011,20261012):
        previous.extend(scenario(json.loads(line)['scene_seed']) for line in (rdir/f'train_{seed}/learning.jsonl').read_text().splitlines())
assert not {s['seed'] for s in specs}&{s['seed'] for s in previous}
def signature(s,record=False):
    env=DynamicEnv();env.reset(s);raw=env.raw.tolist();sets=[env.segment.env.target_sail_angle,env.segment.env.target_rudder_angle];env.segment.close()
    result=json.dumps([raw,sets,{k:v for k,v in s.items() if k not in ('seed','kind','initial_raw','initial_setpoints')}],sort_keys=True)
    if record:s.update(initial_raw=raw,initial_setpoints=sets)
    return result
seen={signature(s) for s in previous}
for s in specs:
    key=signature(s,True);assert key not in seen;seen.add(key)
(out/'bank.json').write_text(json.dumps(dict(scenarios=specs,generated_after_freeze=True),indent=2))
jobs=[('normal',0,'normal',frozen['w0']),('w0',0,'avoid',frozen['w0'])]
for e in frozen['experts']:
    seed=e['train_seed']
    for method,mode,checkpoint in [('old_avoid','avoid',e['old_checkpoint']),('old_range','range',e['old_checkpoint']),
        ('guard_old_range','range',e['guard_old_checkpoint']),('final_avoid','avoid',e['checkpoint']),('final_range','range',e['checkpoint'])]:
        jobs.append((f'{seed}_{method}',seed,mode,checkpoint))
assert len(jobs)==12
(out/'matrix.json').write_text(json.dumps(jobs,indent=2))
pending=jobs.copy();active=[];receipts=[];started=time.perf_counter();environment=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
while pending or active:
    while pending and len(active)<4:
        label,seed,mode,checkpoint=pending.pop(0);log=(out/f'{label}.log').open('w')
        cmd=[sys.executable,'-u',str(ROOT/'scripts/round3_evaluate.py'),'--bank',str(out/'bank.json'),'--checkpoint',checkpoint,
            '--mode',mode,'--out',str(out/'parts'/label),'--train-seed',str(seed)]
        proc=subprocess.Popen(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env=environment)
        active.append((label,proc,log));receipts.append(dict(label=label,pid=proc.pid,command=cmd))
        (out/'processes.json').write_text(json.dumps(receipts,indent=2))
    for item in active[:]:
        label,proc,log=item;code=proc.poll()
        if code is not None:
            log.close();active.remove(item);print(label,code,flush=True)
            if code:raise RuntimeError('Evaluation failed; preserve partial results and inspect owned processes before retry')
    if active:time.sleep(1)
methods=('normal','w0','old_avoid','old_range','guard_old_range','final_avoid','final_range');summaries={}
for e in frozen['experts']:
    seed=e['train_seed'];dest=out/f'seed_{seed}';dest.mkdir();(dest/'trajectories').mkdir();rows=[]
    for method in methods:
        label=method if method in ('normal','w0') else f'{seed}_{method}';part=out/'parts'/label
        rr=[json.loads(x) for x in (part/'episodes.jsonl').read_text().splitlines()];assert len(rr)==50
        for r in rr:
            original_mode=r['mode'];r.update(mode=method,control_mode=original_mode,train_seed=seed,shared_control=method in ('normal','w0'))
            rows.append(r);shutil.copy2(part/f'trajectories/{r["seed"]}_{original_mode}.npz',dest/f'trajectories/{r["seed"]}_{method}.npz')
    rows.sort(key=lambda r:(r['seed'],r['mode']))
    (dest/'episodes.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows));(dest/'pairs.json').write_text(json.dumps(paired(rows,methods),indent=2))
    summary={}
    for method in methods:
        rr=[r for r in rows if r['mode']==method];dd=[r['min_distance'] for r in rr if r['min_distance'] is not None]
        summary[method]=dict(n=50,safe_complete=sum(r['safe_complete'] for r in rr),arrived=sum(r['arrived'] for r in rr),
            violations=sum(r['violated'] for r in rr),timeouts=sum(r['termination_reason']=='time_limit' for r in rr),
            other_failures=sum(r['termination_reason'] in ('boundary','other_truncation') for r in rr),
            by_kind={k:sum(r['safe_complete'] for r in rr if r['kind']==k) for k in KINDS},
            switches=sum(r['switches'] for r in rr),takeover_seconds_mean=float(np.mean([r['takeover_seconds'] for r in rr])),
            takeover_episodes=sum(bool(r['takeover_times']) for r in rr),handback_episodes=sum(bool(r['handback_times']) for r in rr),
            finished_normal_after_handback=sum(r['finished_normal_after_handback'] for r in rr),
            min_distance=min(dd,default=None),mean_min_distance=float(np.mean(dd)) if dd else None,
            decision_ms_per_step=1000*sum(r['decision_seconds'] for r in rr)/sum(r['time'] for r in rr),wall_seconds=sum(r['wall_seconds'] for r in rr))
    (dest/'summary.json').write_text(json.dumps(summary,indent=2));summaries[str(seed)]=summary
(out/'summary.json').write_text(json.dumps(dict(training_seeds=summaries,independent_scenarios=50,physical_rollouts=600,
    shared_controls=['normal','w0'],wall_seconds=time.perf_counter()-started,workers=4),indent=2));print(json.dumps(summaries,indent=2))
