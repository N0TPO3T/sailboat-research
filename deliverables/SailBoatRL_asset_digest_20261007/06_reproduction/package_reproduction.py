"""Package existing exact execution inputs for internal reproducibility; no new scientific trial."""
from pathlib import Path
import json,hashlib,zipfile,shutil,subprocess,sys,time
r=Path.cwd();assert str(r.resolve()).startswith('/home/ot/Students/hs/')
o=r/'paper/ccdc/r13_revision';dst=o/'reproduction_check';assert not dst.exists();dst.mkdir()
files=[]
for folder in ['src','scripts','third_party']:
 files += [p for p in (r/folder).rglob('*.py') if '__pycache__' not in p.parts]
files += list((r/'checkpoints/obstacle_candidate').glob('*actor10800.pth'))+list((r/'checkpoints/obstacle_candidate').glob('*normalizer10800.pth'))
files += [r/'requirements.lock',r/'docs/obstacle_candidate_identity.json',r/'docs/UPSTREAM_MANIFEST.md']
for n in ['freeze.json','confirmation.json','analysis.json','calibration.json']:files.append(r/'runs/r12_revision_20261006'/n)
files += list((r/'runs/r12_revision_20261006/confirmation').glob('*/trace.json'))
hashes={}
for p in files:
 rel=p.relative_to(r);q=dst/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q);hashes[str(rel)]=hashlib.sha256(q.read_bytes()).hexdigest()
(dst/'CONTENTS_SHA256.json').write_text(json.dumps(hashes,indent=2))
check='''from pathlib import Path
import json,hashlib,sys
r=Path.cwd();sys.path[:0]=[str(r/'src'),str(r/'scripts')]
for n,h in json.loads((r/'CONTENTS_SHA256.json').read_text()).items():assert hashlib.sha256((r/n).read_bytes()).hexdigest()==h,n
from sailboat_routing.runtime import configure_cpu
configure_cpu()
from sailboat_routing.r8_model import CausalModel
m=CausalModel();m.close()
from run_r12 import worker
counts={};cpu={};rows={}
for p in (r/'runs/r12_revision_20261006/confirmation').glob('*/trace.json'):
 d=json.loads(p.read_text());x=d['row'];v=x['variant'];counts[v]=counts.get(v,0)+int(x['success']);cpu[v]=cpu.get(v,0)+x['cpu_seconds'];rows[x['scene_id'],v]=x
paired=[a['time_s']-rows[s,'simple']['time_s'] for (s,v),a in rows.items() if v=='sampled' and a['success'] and rows[s,'simple']['success']]
assert counts=={'reactive':19,'sampled':24,'simple':23} and len(paired)==23 and sum(paired)/23==7
print(json.dumps(dict(complete=True,model_load=True,worker_import=True,safe_counts=counts,episode_cpu=cpu,common_safe_n=len(paired),mean_time_S15_minus_L=sum(paired)/23,max_time_S15_minus_L=max(paired),source_root=str(r)),indent=2))
'''
(dst/'verify_recovery.py').write_text(check)
res=subprocess.run([str(r/'.venv/bin/python'),'verify_recovery.py'],cwd=dst,capture_output=True,text=True);(o/'evidence/recovery_check.log').write_text(res.stdout+res.stderr);assert res.returncode==0,res.stderr
(o/'evidence/recovery_check.json').write_text(res.stdout)
(dst/'README.md').write_text('# Internal reproduction package\n\nExact scientific source and learned assets plus all72 matched confirmation traces. Not an authorization to redistribute inherited assets publicly. Original copyright/author comments preserved. Training attribution/release permission remain pending.\n\nUse Python3.13 and requirements.lock in a user-owned environment. From extraction root: `python verify_recovery.py` validates hashes, loads actual18D weights, imports physical worker and reproduces all24 table counts and paired timing from logs. This is a recovery check, not a new full-voyage experiment. Current check used the existing project virtualenv without installing dependencies.\n')
with zipfile.ZipFile(o/'R13_REPRODUCTION_internal.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in dst.rglob('*'):
  if p.is_file() and '__pycache__' not in p.parts:z.write(p,p.relative_to(dst))
print(res.stdout)
