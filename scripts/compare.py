"""Four single-thread CPU workers, one fixed method each, same frozen expert."""
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from dynamic import *
import argparse
import subprocess
import shutil
p=argparse.ArgumentParser();p.add_argument('--checkpoint',default='checkpoints/selected/resume.pt')
p.add_argument('--out',default='runs/confirmation');p.add_argument('--split',choices=['dev','test'],default='test')
args=p.parse_args();out=ROOT/args.out
if out.exists():raise RuntimeError('Refusing to overwrite comparison')
out.mkdir(parents=True);parts=out/'parts';parts.mkdir();(out/'trajectories').mkdir()
methods=['normal','avoid','range','risk'];processes=[]
comparison_started=time.perf_counter()
for mode in methods:
    log=(out/f'{mode}.log').open('w')
    command=[sys.executable,'-u',str(ROOT/'scripts/evaluate.py'),'--split',args.split,
             '--checkpoint',args.checkpoint,'--out',str(parts/mode),'--modes',mode]
    proc=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    processes.append((mode,proc,log))
(out/'processes.json').write_text(json.dumps([dict(mode=m,pid=p.pid) for m,p,_ in processes],indent=2))
for mode,proc,log in processes:
    code=proc.wait();log.close()
    print(json.dumps(dict(mode=mode,returncode=code)),flush=True)
    if code:raise RuntimeError(f'{mode} failed; preserve logs and completed workers')
rows=[];protocol=None
for mode in methods:
    part=parts/mode;current=json.loads((part/'protocol.json').read_text())
    if protocol:
        for field in ('scenarios','checkpoint','train_steps','config'):assert current[field]==protocol[field]
    else:protocol=current
    rows.extend(json.loads(line) for line in (part/'episodes.jsonl').read_text().splitlines())
    for trajectory in (part/'trajectories').glob('*.npz'):shutil.copy2(trajectory,out/'trajectories'/trajectory.name)
rows.sort(key=lambda r:(r['seed'],methods.index(r['mode'])))
(out/'episodes.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
protocol['modes']=methods;protocol['workers']=4
(out/'protocol.json').write_text(json.dumps(protocol,indent=2))
common=[s['seed'] for s in protocol['scenarios'] if all(next(r for r in rows if r['seed']==s['seed'] and r['mode']==m)['safe_complete'] for m in methods)]
summary={}
for mode in methods:
    rr=[r for r in rows if r['mode']==mode];cc=[r for r in rr if r['seed'] in common]
    distances=[r['min_distance'] for r in rr if r['min_distance'] is not None]
    summary[mode]=dict(n=len(rr),safe_complete=sum(r['safe_complete'] for r in rr),arrived=sum(r['arrived'] for r in rr),
        violations=sum(r['violated'] for r in rr),common_safe_n=len(cc),
        common_safe_time_mean=float(np.mean([r['time'] for r in cc])) if cc else None,
        min_distance=min(distances,default=None),mean_switches=float(np.mean([r['switches'] for r in rr])),
        mean_takeover_seconds=float(np.mean([r['takeover_seconds'] for r in rr])),
        decision_ms_per_step=1000*sum(r['decision_seconds'] for r in rr)/sum(r['time'] for r in rr),
        wall_seconds=sum(r['wall_seconds'] for r in rr))
(out/'summary.json').write_text(json.dumps(dict(methods=summary,common_safe_seeds=common,
    comparison_wall_seconds=time.perf_counter()-comparison_started,workers=4),indent=2))
print(json.dumps(summary,indent=2))
