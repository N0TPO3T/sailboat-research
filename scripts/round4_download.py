"""Download this round's evidence without creating another remote archive."""
import subprocess,tarfile,hashlib,json
from pathlib import Path
ROOT=Path(r'C:\Users\74095\hs\SailBoat\sailboat-dynamic-routing-v0');run=ROOT/'runs/round4_20261025'
command="cd /home/ot/Students/hs/sailboat-dynamic-routing-v0 && tar -czf - --exclude='*/train_*/*.pt' --exclude='*/train_*/*.pt.gz' --exclude='*/train_*/*.pth' --exclude='*/train_*/*.tmp' runs/round4_20261025 scripts/round4_*.py scripts/train_round4.py REPORT_ROUND4_ZH.md"
archive=ROOT/'Round4_evidence.tar.gz'
with archive.open('wb') as out:subprocess.run(['ssh','donghai',command],stdout=out,check=True)
with tarfile.open(archive,'r:gz') as tar:
 for member in tar.getmembers():
  target=(ROOT/member.name).resolve();assert target.is_relative_to(ROOT.resolve())
 tar.extractall(ROOT,filter='data')
models=ROOT/'Round4_models.tar.gz'
with models.open('wb') as out:subprocess.run(['ssh','donghai','cd /home/ot/Students/hs/sailboat-dynamic-routing-v0 && tar -czf - checkpoints/round4'],stdout=out,check=True)
with tarfile.open(models,'r:gz') as tar:
 for member in tar.getmembers():assert (ROOT/member.name).resolve().is_relative_to(ROOT.resolve())
 tar.extractall(ROOT,filter='data')
receipts={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in (archive,models)}
(run/'download_receipts.json').write_text(json.dumps(receipts,indent=2));print(json.dumps(receipts))
