"""Pair W0 with existing identity-matched old50 results; no new rollouts."""
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from dynamic import *
from round2_metrics import paired
run=ROOT/'runs/round3_20261011_2308';out=run/'diagnosis'
frozen=json.loads((ROOT/'runs/round2_20261011/freeze.json').read_text())
assert frozen['config']==CFG and frozen['dynamic_sha256']==hashlib.sha256((ROOT/'src/dynamic.py').read_bytes()).hexdigest()
rows=[]
for e in frozen['experts']:
    assert e['sha256']==hashlib.sha256((ROOT/e['checkpoint']).read_bytes()).hexdigest()
    ts=e['train_seed'];old=ROOT/f'runs/round2_20261011/confirmation50/seed_{ts}/episodes.jsonl'
    for line in old.read_text().splitlines():
        r=json.loads(line)
        if r['mode']=='risk' or (r['mode']=='normal' and ts!=20261011):continue
        r['mode']=r['mode'] if r['mode']=='normal' else r['mode']+'_'+str(ts)
        r['source']='reused_round2';rows.append(r)
w0=[json.loads(x) for x in (out/'w0_old50/episodes.jsonl').read_text().splitlines()];assert len(w0)==50
rows.extend(dict(r,mode='w0',source='new_W0_on_seen50') for r in w0)
methods=('normal','w0','avoid_20261011','avoid_20261012','range_20261011','range_20261012')
summary={m:dict(n=sum(r['mode']==m for r in rows),safe=sum(r['safe_complete'] for r in rows if r['mode']==m),
    by_kind={k:sum(r['safe_complete'] for r in rows if r['mode']==m and r['kind']==k) for k in KINDS}) for m in methods}
assert all(v['n']==50 for v in summary.values())
(out/'old50_episodes.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
(out/'old50_pairs.json').write_text(json.dumps(paired(rows,methods),indent=2))
(out/'old50_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
branches=[json.loads(x) for x in (out/'branches/results.jsonl').read_text().splitlines()];assert len(branches)==12
for key in {(r['train_seed'],r['seed']) for r in branches}:
    rr=[r for r in branches if (r['train_seed'],r['seed'])==key]
    assert len({r['fingerprint'] for r in rr})==1
print(json.dumps([dict(scene=r['seed'],method=r['continuation'],safe=r['safe_complete'],time=r['time']) for r in branches]))
