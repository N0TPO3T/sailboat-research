"""Prespecified joint avoid/range development selection, before new confirmation."""
import sys,json,hashlib,shutil,gzip,os,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from dynamic import *
run=ROOT/'runs/round4_20261025';assert not (run/'freeze.json').exists()
while not (run/'compression_done.json').exists():time.sleep(10)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old_freeze=json.loads((ROOT/'runs/round2_20261011/freeze.json').read_text())
for e in old_freeze['experts']:assert sha(ROOT/e['checkpoint'])==e['sha256']
w0=torch.load(ROOT/'checkpoints/round3/w0/actor_init.pt',weights_only=False,map_location='cpu')
assert hashlib.sha256(b''.join(v.detach().cpu().numpy().tobytes() for v in w0['actor'].values())).hexdigest()=='c76911bfec7847f405bb6a8f31606580dcb49f54529c06d229597720c17b1a23'
experts=[];records=[]
def counts(d):return {m:sum(r['safe_complete'] for r in d['results'] if r['mode']==m) for m in ('avoid','range')}
def score(d):
 c=counts(d);return (min(c.values()),sum(c.values()),-sum(r['time'] if r['safe_complete'] else 700 for r in d['results']),-d['steps'])
for source in (20261011,20261012):
 e=dict(train_seed=source,old_checkpoint=f'checkpoints/round2/{source}/resume.pt');arms={}
 for arm in ('control','takeover4'):
  folder=run/f'train_v2_{source}_{arm}';complete=json.loads((folder/'complete.json').read_text());assert complete['steps']>=20000
  init=json.loads((folder/'initialization.json').read_text());assert init['initial_steps']==0 and init['initial_replay_size']==0 and init['resume_source'] is None
  dev=[json.loads(x) for x in (folder/'development.jsonl').read_text().splitlines()];chosen=max(dev,key=score)
  avoid_only=max(dev,key=lambda d:(counts(d)['avoid'],-sum(r['time'] if r['safe_complete'] else 700 for r in d['results'] if r['mode']=='avoid'),-d['steps']))
  dest=ROOT/f'checkpoints/round4/{source}/{arm}';assert not dest.exists();dest.mkdir(parents=True)
  ckpath=folder/f'step_{chosen["steps"]}.pt'
  if ckpath.exists():os.link(ckpath,dest/'resume.pt')
  else:
   with gzip.open(ckpath.with_suffix('.pt.gz'),'rb') as src,(dest/'resume.pt').open('wb') as dst:shutil.copyfileobj(src,dst)
  ck=torch.load(dest/'resume.pt',weights_only=False,map_location='cpu')
  for key in ('actor','normalizer'):torch.save(ck[key],dest/f'{key}.pth')
  receipt=dict(source=source,arm=arm,checkpoint=str((dest/'resume.pt').relative_to(ROOT)),sha256=sha(dest/'resume.pt'),selected_steps=chosen['steps'],avoid_only_choice=dict(steps=avoid_only['steps'],counts=counts(avoid_only),joint_score=score(avoid_only)),counts=counts(chosen),score=score(chosen),initialization=init,complete=complete,candidates=[dict(steps=d['steps'],counts=counts(d),score=score(d)) for d in dev])
  (dest/'selection.json').write_text(json.dumps(receipt,indent=2));records.append(receipt);arms[arm]=receipt
  e[f'{arm}_checkpoint']=receipt['checkpoint'];e[f'{arm}_sha256']=receipt['sha256']
 assert arms['control']['initialization']['actor_sha256']==arms['takeover4']['initialization']['actor_sha256']
 assert arms['control']['initialization']['critic_sha256']==arms['takeover4']['initialization']['critic_sha256']
 experts.append(e)
weighted=[r for r in records if r['arm']=='takeover4'];controls=[r for r in records if r['arm']=='control']
adopt=all(w['counts']['avoid']>=c['counts']['avoid'] for w,c in zip(weighted,controls)) and sum(w['counts']['range'] for w in weighted)>sum(c['counts']['range'] for c in controls)
final_arm='takeover4' if adopt else 'control'
for e in experts:e['checkpoint']=e[f'{final_arm}_checkpoint']
freeze=dict(experts=experts,selections=records,final_arm=final_arm,adopt_takeover_weighting=adopt,config=CFG,w0='checkpoints/round3/w0/actor_init.pt',w0_sha256=sha(ROOT/'checkpoints/round3/w0/actor_init.pt'),sources={f:sha(ROOT/f) for f in ('src/dynamic.py','scripts/train_round4.py','scripts/round4_select.py','scripts/round4_confirm.py','scripts/round2_evaluate.py')},confirmation='not generated or evaluated at freeze',matrix='normal/W0 shared + old/control/takeover4 each avoid/range x two source experts; 700 unique full rollouts')
(run/'freeze.json').write_text(json.dumps(freeze,indent=2));print(json.dumps(freeze,indent=2))



