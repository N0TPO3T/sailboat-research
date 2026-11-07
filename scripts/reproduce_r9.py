"""Create a fresh output manifest, preserving original R9 evidence and deadlines."""
import argparse,json,time,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
a=argparse.ArgumentParser();a.add_argument('--manifest',required=True);a.add_argument('--out',required=True);a.add_argument('--scene');a.add_argument('--variant');a.add_argument('--hours',type=float,default=4);args=a.parse_args()
src=Path(args.manifest).resolve();out=Path(args.out).resolve()
assert out.is_relative_to((ROOT/'runs').resolve()) and 0<args.hours<=24
batch=json.loads(src.read_text());jobs=[j for j in batch['jobs'] if (not args.scene or j['scene']['id']==args.scene) and (not args.variant or j['variant']==args.variant)]
assert jobs,'No matching job';out.mkdir(exist_ok=False,parents=True)
(out/'plan.json').write_text(json.dumps(dict(deadline_epoch=time.time()+3600*args.hours,workers=4,threads=1,gpu=None,source_manifest=str(src))))
m=out/'reproduction.json';m.write_text(json.dumps(dict(run=str(out),jobs=jobs),indent=2))
subprocess.run([sys.executable,str(ROOT/'scripts/run_r9.py'),str(m)],check=True)
