"""Prepare, but do not run, an isolated exact-design repeat from this archive."""
from pathlib import Path
import argparse,shutil,json,sys
p=argparse.ArgumentParser();p.add_argument('--output',required=True);args=p.parse_args()
src=Path(__file__).resolve().parent;dst=Path(args.output).resolve()
if dst.exists():raise SystemExit('Output already exists; use a NEW directory to preserve previous results.')
dst.mkdir(parents=True)
for name in ['frozen','inputs']:shutil.copytree(src/name,dst/name)
for name in ['.tmp','.cache']:(dst/'frozen'/name).mkdir(exist_ok=True)
for name in ['a_fair.py','audit_results.py','finish_analysis.py','EXPERIMENT_PLAN.md','FREEZE.json','SOURCE_HASHES.json','INPUT_HASHES.json','new_scenes.json','original_calibration.json','original_confirmation.json']:
    shutil.copy2(src/name,dst/name)
env=json.loads((src/'environment.json').read_text())
(dst/'original_environment.json').write_text(json.dumps(env,indent=2))
env.update(origin=str(dst/'inputs'),source_root=str(dst/'frozen'),run_root=str(dst),interpreter=sys.executable,smoke_command=f'{sys.executable} {dst / "a_fair.py"} smoke')
(dst/'environment.json').write_text(json.dumps(env,indent=2))
(dst/'REPRODUCTION_OF.json').write_text(json.dumps({'source':str(src),'same_frozen_design':True,'not_new_independent_evidence':True,'paths_relocated_only':True},indent=2))
print('Prepared:',dst)
print('Activate a compatible environment from frozen/requirements.lock; run smoke before any complete repeat:')
print(sys.executable, str(dst/'a_fair.py'), 'smoke')
print('A full repeat is a separate compute action and is NOT launched by this utility.')
