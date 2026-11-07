"""Fixed old50 screening; never opens the new confirmation scenarios."""
import sys,json,subprocess,os,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from round3_policy import *
run=ROOT/'runs/round3_20261011_2308';dest=run/'screen';dest.mkdir()
jobs=[]
for seed in (20261011,20261012):
    ck=torch.load(ROOT/f'checkpoints/round2/{seed}/resume.pt',weights_only=False,map_location='cpu')
    for mode in ('shrink','headon_guard'):
        path=dest/f'{seed}_{mode}.pt'
        torch.save(dict(actor=ck['actor'],normalizer=dict(ck['normalizer'],adaptation=mode),
            kind='development_only_existing_trained_actor_modified_input'),path)
        jobs.append((f'{seed}_{mode}',seed,path))
jobs.append(('w0_range',0,ROOT/'checkpoints/round3/w0/actor_init.pt'))
active=[];receipts=[];environment=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
while jobs or active:
    while jobs and len(active)<4:
        label,seed,path=jobs.pop(0);log=(dest/f'{label}.log').open('w')
        cmd=[sys.executable,'-u',str(ROOT/'scripts/round3_evaluate.py'),'--bank','runs/round2_20261011/confirmation50/bank.json',
            '--checkpoint',str(path),'--mode','range','--out',str(dest/label),'--train-seed',str(seed)]
        proc=subprocess.Popen(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env=environment)
        active.append((label,proc,log));receipts.append(dict(label=label,pid=proc.pid,command=cmd))
        (dest/'processes.json').write_text(json.dumps(receipts,indent=2))
    for item in active[:]:
        label,proc,log=item;code=proc.poll()
        if code is not None:
            log.close();active.remove(item);print(label,code,flush=True)
            if code:raise RuntimeError('Candidate failed; inspect existing owned workers before restarting')
    if active:time.sleep(1)
summary={}
for receipt in receipts:
    label=receipt['label'];rr=[json.loads(x) for x in (dest/label/'episodes.jsonl').read_text().splitlines()];assert len(rr)==50
    summary[label]=dict(safe=sum(r['safe_complete'] for r in rr),by_kind={k:sum(r['safe_complete'] for r in rr if r['kind']==k) for k in KINDS})
(dest/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
