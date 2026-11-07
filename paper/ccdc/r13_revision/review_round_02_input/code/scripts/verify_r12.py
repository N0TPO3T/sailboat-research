"""Finite delivery checks; no physics execution."""
from pathlib import Path
import json,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'runs/r12_revision_20261006'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out={'old_hashes_unchanged':{},'freeze_hashes_match':{},'coverage':{},'assets_match':{}}
for p,h in json.loads((ROOT/'paper/ccdc/r11_draft/evidence/ASSET_HASHES.json').read_text()).items():
 out['assets_match'][p]=sha(ROOT/p)==h
 assert out['assets_match'][p],p
for p,h in json.loads((R/'original_hashes.json').read_text()).items():
 out['old_hashes_unchanged'][p]=sha(ROOT/p)==h
 assert out['old_hashes_unchanged'][p],p
for p,h in json.loads((R/'freeze.json').read_text())['sources'].items():
 out['freeze_hashes_match'][p]=sha(ROOT/p)==h
 assert out['freeze_hashes_match'][p],p
for stage in ['development','guard','confirmation']:
 m=json.loads((R/(stage+'.json')).read_text())
 expected={(j['scene']['id'],j['variant']) for j in m['jobs']}
 actual={}
 for f in (R/stage).glob('*/trace.json'):
  d=json.loads(f.read_text());row=d['row'];key=row['scene_id'],row['variant']
  assert key not in actual
  assert row['complete'],(key,row['reason'])
  actual[key]=row
 assert set(actual)==expected,(stage,expected-set(actual),set(actual)-expected)
 out['coverage'][stage]={'expected':len(expected),'actual':len(actual),'safe':sum(x['success'] for x in actual.values()),'failures_retained':[{'scene':x['scene_id'],'variant':x['variant'],'reason':x['reason'],'min_dynamic_margin':x['min_dynamic_margin']} for x in actual.values() if not x['success']]}
 assert (R/stage/'completion.json').exists()
b=json.loads((R/'branches_complete.json').read_text());out['branches_completion']=b
out['execution']=json.loads((R/'execution_complete.json').read_text())
assert out['execution']['guard_return']==0 and out['execution']['confirmation_return']==0
out['branch_retry_explanation']='Initial nonconflict t=10 was not an eligible prediction state. No branch executed there. Documented retry uses first actual eligible t=56; branches_complete.json is authoritative.'
out['source_head']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
(R/'verification.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
