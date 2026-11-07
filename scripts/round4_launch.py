import os,sys,json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];run=ROOT/'runs/round4_20261025'
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',CUDA_VISIBLE_DEVICES='')
jobs=[]
for source,seed,base in [(20261011,20261025,740000),(20261012,20261026,750000)]:
 for copies,label in [(1,'control'),(4,'takeover4')]:
  name=f'train_v2_{source}_{label}';log=(run/f'{name}.log').open('x')
  cmd=[sys.executable,'-u',str(ROOT/'scripts/train_round4.py'),'--actor-start',f'checkpoints/round2/{source}/resume.pt','--takeover-copies',str(copies),'--seed',str(seed),'--scene-base',str(base),'--steps','20000','--out',str(run/name),'--dynamic-columns-only','--mask-expired-metadata','--handover-distribution','actual_routes','--dev-every','5000','--dev-at-start','--hours','3']
  p=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT);jobs.append((p,log,cmd,name))
(run/'training_v2_processes.json').write_text(json.dumps([dict(pid=p.pid,name=n,command=c) for p,l,c,n in jobs],indent=2))
for p,l,c,n in jobs:
 code=p.wait();l.close();print(n,code,flush=True)
 if code:raise RuntimeError(f'{n} failed; inspect other owned processes before retry')
(run/'training_v2_done.json').write_text(json.dumps(dict(completed=True)))

