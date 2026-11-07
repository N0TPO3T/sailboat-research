import sys,json,subprocess,shutil,hashlib,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from dynamic import *
ROOT=Path(__file__).resolve().parents[1];run=ROOT/'runs/round4_20261025';f=json.loads((run/'freeze.json').read_text());checks=[]
for r in f['selections']:
 dest=(ROOT/r['checkpoint']).parent
 ck=torch.load(dest/'resume.pt',weights_only=False,map_location='cpu')
 source=torch.load(ROOT/f'checkpoints/round2/{r["source"]}/resume.pt',weights_only=False,map_location='cpu')
 assert ck['training_protocol']['takeover_copies']==(1 if r['arm']=='control' else 4)
 if ck['steps']==0:
  assert all(torch.equal(v,source['actor'][k]) for k,v in ck['actor'].items()) and ck['replay']['size']==0
  selected_check='step0 equals source actor; fresh empty training state; no learned updates selected'
 else:
  subprocess.run([sys.executable,str(ROOT/'scripts/verify_checkpoint.py'),str(dest/'resume.pt')],check=True)
  shutil.copy2(dest/'checkpoint_verification.json',dest/'selected_verification.json')
  selected_check='selected restored four SAC updates identically'
 terminal=run/f'train_v2_{r["source"]}_{r["arm"]}/resume.pt'
 # Preserve a genuinely trained recovery state even when selection rejects training.
 os.link(terminal,dest/'terminal_resume.pt')
 subprocess.run([sys.executable,str(ROOT/'scripts/verify_checkpoint.py'),str(dest/'terminal_resume.pt')],check=True)
 # verifier writes checkpoint_verification.json; make the terminal role explicit.
 shutil.copy2(dest/'checkpoint_verification.json',dest/'terminal_verification.json')
 terminal_state=torch.load(terminal,weights_only=False,map_location='cpu')
 delta=sum(float(torch.sum((v-source['actor'][k])**2)) for k,v in terminal_state['actor'].items())**.5
 assert delta>0 and terminal_state['actor_updates']>0
 checks.append(dict(source=r['source'],arm=r['arm'],terminal_actor_l2_change_from_round2=delta,selected_check=selected_check,terminal_sha256=hashlib.sha256(terminal.read_bytes()).hexdigest(),terminal_four_updates_verified=True))
for source in (20261011,20261012):subprocess.run([sys.executable,str(ROOT/'scripts/check_round3_trajectories.py'),str(run/f'confirmation50/seed_{source}')],check=True)
(run/'verification.json').write_text(json.dumps(checks,indent=2));print(json.dumps(checks))



