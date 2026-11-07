"""One bounded seven-job confirmation: 50 normal + 2 experts x 3 modes x 50."""
import sys,json,hashlib,subprocess,time,shutil,argparse,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from dynamic import *
from round2_metrics import paired
p=argparse.ArgumentParser();p.add_argument('--key-cases',action='store_true');args=p.parse_args()
run=ROOT/'runs/round2_20261011';frozen=json.loads((run/'freeze.json').read_text())
assert frozen['config']==CFG
assert frozen['dynamic_sha256']==hashlib.sha256((ROOT/'src/dynamic.py').read_bytes()).hexdigest()
out=run/('retrained_key_cases' if args.key_cases else 'confirmation50')
if out.exists():raise RuntimeError('Refuse to overwrite a confirmation')
out.mkdir()
if args.key_cases:
    keys=json.loads((run/'diagnosis/key_cases.json').read_text())
    specs=[json.loads(str(np.load(ROOT/f'runs/confirmation/trajectories/{c["seed"]}_normal.npz')['spec'])) for c in keys['cases']]
else:
    # Generation happens only after both experts and all controls have frozen.
    kinds=sum(([k]*n for k,n in [('none',8),('away',8),('late',8),('cross',9),('headon',9),('edge_static',8)]),[])
    specs=[scenario(920000+i,k) for i,k in enumerate(kinds)]
    previous=bank('dev')+bank('test')+[scenario(s) for s in range(710000,711000)]
    for expert in frozen['experts']:
        train=run/f'train_{expert["train_seed"]}'
        previous.extend(scenario(r['scene_seed']) for r in map(json.loads,(train/'learning.jsonl').read_text().splitlines()))
    assert not {s['seed'] for s in specs}&{s['seed'] for s in previous}
    def physical_signature(s):return json.dumps({k:v for k,v in s.items() if k not in ('seed','kind','initial_raw','initial_setpoints')},sort_keys=True)
    # None cases have identical absent-target metadata; their actual random
    # initial physical states must also be checked, not rejected as duplicates.
    def initialized_signature(s,record=False):
        e=DynamicEnv();e.reset(s);raw=e.raw.tolist()
        setpoints=[e.segment.env.target_sail_angle,e.segment.env.target_rudder_angle];e.segment.close()
        if record:s.update(initial_raw=raw,initial_setpoints=setpoints)
        return json.dumps([physical_signature(s),raw,setpoints],sort_keys=True)
    old_signatures={initialized_signature(s) for s in previous}
    signatures=[]
    for s in specs:
        signature=initialized_signature(s,record=True);assert signature not in old_signatures and signature not in signatures
        signatures.append(signature)
(out/'bank.json').write_text(json.dumps(dict(scenarios=specs,generated_after_freeze=True,
    freeze_sha256=hashlib.sha256((run/'freeze.json').read_bytes()).hexdigest()),indent=2))
jobs=[(0,'normal',frozen['experts'][0])]+[(e['train_seed'],m,e) for e in frozen['experts'] for m in ('avoid','range','risk')]
pending=jobs.copy();active=[];receipts=[];started=time.perf_counter();environment=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
while pending or active:
    while pending and len(active)<4:
        seed,mode,expert=pending.pop(0);part=out/f'parts/{seed}_{mode}';log=(out/f'{seed}_{mode}.log').open('w')
        command=[sys.executable,'-u',str(ROOT/'scripts/round2_evaluate.py'),'--bank',str(out/'bank.json'),
            '--checkpoint',expert['checkpoint'],'--mode',mode,'--out',str(part),'--train-seed',str(seed)]
        proc=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env=environment)
        active.append((seed,mode,proc,log));receipts.append(dict(seed=seed,mode=mode,pid=proc.pid,command=command))
        (out/'processes.json').write_text(json.dumps(receipts,indent=2))
    for item in active[:]:
        seed,mode,proc,log=item;code=proc.poll()
        if code is not None:
            log.close();active.remove(item);print(json.dumps(dict(seed=seed,mode=mode,exit_code=code)),flush=True)
            if code:raise RuntimeError('Evaluation failed; preserve partial results and inspect other owned jobs before restarting')
    if active:time.sleep(1)
normal=[json.loads(l) for l in (out/'parts/0_normal/episodes.jsonl').read_text().splitlines()]
all_summaries={}
for expert in frozen['experts']:
    seed=expert['train_seed'];dest=out/f'seed_{seed}';dest.mkdir();(dest/'trajectories').mkdir()
    rows=[dict(r,train_seed=seed,normal_reused=True) for r in normal]
    for mode in ('avoid','range','risk'):
        part=out/f'parts/{seed}_{mode}'
        assert json.loads((part/'protocol.json').read_text())['checkpoint_sha256']==expert['sha256']
        rows.extend(json.loads(l) for l in (part/'episodes.jsonl').read_text().splitlines())
    for mode in ('normal','avoid','range','risk'):
        part=out/f'parts/{0 if mode=="normal" else seed}_{mode}'
        for file in (part/'trajectories').glob('*.npz'):shutil.copy2(file,dest/'trajectories'/file.name)
    rows.sort(key=lambda r:(r['seed'],r['mode']))
    (dest/'episodes.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    (dest/'pairs.json').write_text(json.dumps(paired(rows),indent=2))
    summary={}
    for mode in ('normal','avoid','range','risk'):
        rr=[r for r in rows if r['mode']==mode];dd=[r['min_distance'] for r in rr if r['min_distance'] is not None]
        summary[mode]=dict(n=len(rr),safe_complete=sum(r['safe_complete'] for r in rr),arrived=sum(r['arrived'] for r in rr),
            violations=sum(r['violated'] for r in rr),timeouts=sum(r['termination_reason']=='time_limit' for r in rr),
            other_failures=sum(r['termination_reason'] in ('boundary','other_truncation') for r in rr),
            by_kind={k:sum(r['safe_complete'] for r in rr if r['kind']==k) for k in KINDS},
            switches=sum(r['switches'] for r in rr),takeover_seconds_mean=float(np.mean([r['takeover_seconds'] for r in rr])),
            takeover_episodes=sum(bool(r['takeover_times']) for r in rr),
            handback_episodes=sum(bool(r['handback_times']) for r in rr),
            handback_safe_episodes=sum(r['handback_and_safe_complete'] for r in rr),
            finished_normal_after_handback=sum(r['finished_normal_after_handback'] for r in rr),
            invisible_violation_episodes=sum(bool(r['invisible_violation_times']) for r in rr),
            min_distance=min(dd,default=None),mean_min_distance=float(np.mean(dd)) if dd else None,
            decision_ms_per_step=1000*sum(r['decision_seconds'] for r in rr)/sum(r['time'] for r in rr),
            wall_seconds=sum(r['wall_seconds'] for r in rr))
    (dest/'summary.json').write_text(json.dumps(summary,indent=2));all_summaries[str(seed)]=summary
(out/'summary.json').write_text(json.dumps(dict(training_seeds=all_summaries,independent_scenarios=len(specs),
    physical_rollouts=7*len(specs),normal_reused=True,wall_seconds=time.perf_counter()-started,workers=4),indent=2))
print(json.dumps(all_summaries,indent=2))
