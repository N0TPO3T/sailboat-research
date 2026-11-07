"""Validate completed artifacts and package the current round locally."""
import json,hashlib,tarfile,zipfile,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];run=ROOT/'runs/round4_20261025'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
f=json.loads((run/'freeze.json').read_text());checks=json.loads((run/'verification.json').read_text());summary=json.loads((run/'confirmation50/summary.json').read_text())
assert summary['physical_rollouts']==400 and summary['independent_scenarios']==50
assert len(list((run/'confirmation50/parts').glob('*/trajectories/*.npz')))==400
for source in (20261011,20261012):
 c=json.loads((run/f'confirmation50/seed_{source}/trajectory_checks.json').read_text());assert c['all_metric_checks_passed'] and c['episodes_checked']==400
for r in f['selections']:
 p=ROOT/r['checkpoint'];assert sha(p)==r['sha256']
 verification=next(v for v in checks if v['source']==r['source'] and v['arm']==r['arm'])
 assert sha(p.parent/'terminal_resume.pt')==verification['terminal_sha256']
 log=run/f'train_v2_{r["source"]}_{r["arm"]}/learning.jsonl'
 for line in log.read_text().splitlines():
  e=json.loads(line);assert e['updates']==max(0,e['steps']//4-63)
  assert e['extra_replay']==e['early_takeover_steps']*(3 if r['arm']=='takeover4' else 0)
  assert all(math.isfinite(float(v)) for v in e['loss'].values())
for seed,expected in [(20261011,'13a9477db7f15e0c5cdc5bcc4484ea232fe9675077ccbbd6e82dca0c7c97a0b7'),(20261012,'e17860f29b984b5bd6e5a26b3e46ae1f3ca338c9c20326835f2af78bb188d523')]:assert sha(ROOT/f'checkpoints/round2/{seed}/resume.pt')==expected
assert sha(ROOT/'src/dynamic.py')=='58b4320ffe212b3eea8d172c96f210c8084ed1034974a2911c635bcd3d6d6224'
assert sha(ROOT/'scripts/train.py')=='918be886897bfeb3800486d768d1a1f5d6eb5a9bf688348593efb0ac7fb916d8'
receipt=dict(unique_confirmations=400,independent_scenes=50,combined_rows=800,checkpoint_download_hashes_match=True,all_four_terminal_states_present=True,old_round2_assets_and_core_unchanged=True,physical_clock_and_duplicate_counts_checked=True,all_losses_finite=True,figures=['01_development.png','02_confirmation.png','03_paired_cost.png','04_cases.gif'])
(run/'delivery_checks.json').write_text(json.dumps(receipt,indent=2))
# Explicitly distinguish a compact preview from the full evidence and checkpoint bundle.
preview=ROOT/'DualPolicy_Round4_preview.zip'
files=[ROOT/'REPORT_ROUND4_ZH.md',ROOT/'HANDOFF.md',run/'COMMANDS.md',run/'PROTOCOL.md',run/'CONCLUSIONS_ZH.md',run/'freeze.json',run/'metadata_errata.json',run/'implementation_check.json',run/'delivery_checks.json',run/'diagnosis/DIAGNOSIS_ZH.md',run/'diagnosis/paired_branches.json',run/'diagnosis/final_attribution.json',run/'confirmation50/summary.json',run/'confirmation50/aliases.json',run/'confirmation50/bank.json']
files+=list((run/'figures').glob('*'))
for s in (20261011,20261012):files.extend(p for p in (run/f'confirmation50/seed_{s}').glob('*') if p.is_file())
with zipfile.ZipFile(preview,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in files:z.write(p,p.relative_to(ROOT).as_posix())
with zipfile.ZipFile(preview) as z:assert z.testzip() is None
# Rebuild evidence after final narrative and figure updates; the streamed download receipt is historical.
evidence=ROOT/'Round4_evidence.tar.gz'
files=list(run.rglob('*'))+[ROOT/'REPORT_ROUND4_ZH.md',ROOT/'HANDOFF.md',ROOT/'README.md',ROOT/'PROJECT_STATE.md',ROOT/'CURRENT_PLAN.md',ROOT/'PROJECT_MEMORY.md']+list((ROOT/'scripts').glob('round4_*.py'))+[ROOT/'scripts/train_round4.py']
with tarfile.open(evidence,'w:gz',compresslevel=5) as tar:
 for p in files:
  if not p.is_file() or p.name=='final_packages.json':continue
  rel=p.relative_to(ROOT)
  if any(part.startswith('train_') for part in rel.parts) and ('.pt' in p.suffixes or p.suffix in ('.pth','.tmp')):continue
  tar.add(p,arcname=rel.as_posix(),recursive=False)
receipts={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in (preview,evidence,ROOT/'Round4_models.tar.gz')}
(run/'final_packages.json').write_text(json.dumps(receipts,indent=2));print(json.dumps(receipts))

