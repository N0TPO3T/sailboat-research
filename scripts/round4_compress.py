"""Losslessly compress only this run's immutable step snapshots, preserving bytes."""
import gzip,hashlib,json,time,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];run=ROOT/'runs/round4_20261025';assert str(run.resolve()).startswith('/home/ot/Students/hs/')
receipts=run/'compression.jsonl'
while True:
 for p in run.glob('train_*/step_*.pt'):
  assert p.resolve().is_relative_to(run.resolve()) and not p.is_symlink()
  target=p.with_suffix('.pt.gz')
  if target.exists():continue
  raw=p.read_bytes();digest=hashlib.sha256(raw).hexdigest();temp=target.with_suffix('.tmp')
  with gzip.open(temp,'wb',compresslevel=3) as f:f.write(raw)
  with gzip.open(temp,'rb') as f:assert hashlib.sha256(f.read()).hexdigest()==digest
  temp.replace(target)
  with receipts.open('a') as f:f.write(json.dumps(dict(source=str(p.relative_to(ROOT)),compressed=str(target.relative_to(ROOT)),sha256_uncompressed=digest,raw_bytes=len(raw),compressed_bytes=target.stat().st_size))+'\n')
  p.unlink() # Only this task's verified, immutable snapshot, retained byte-for-byte in gzip.
 if (run/'training_v2_done.json').exists():break
 time.sleep(15)
(run/'compression_done.json').write_text(json.dumps(dict(completed=True)))
