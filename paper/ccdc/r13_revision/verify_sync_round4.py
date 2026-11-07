from pathlib import Path
import json,zipfile,hashlib
r=Path('/home/ot/Students/hs/sailboat-routing-v0').resolve();assert r.is_relative_to(Path('/home/ot/Students/hs').resolve());p=r/'paper/ccdc/r13_revision';d=json.loads((p/'DELIVERY.json').read_text())
for name,meta in d['artifacts'].items():
 f=p/name;assert f.stat().st_size==meta['bytes'];assert hashlib.sha256(f.read_bytes()).hexdigest()==meta['sha256']
with zipfile.ZipFile(p/'R13_CCDC_REVIEW_preview.zip') as z:
 assert z.testzip() is None
 for n in z.namelist():assert (p/n).resolve().is_relative_to(p.resolve())
 z.extractall(p)
for n,h in d['reviewed_files'].items():assert hashlib.sha256((p/n).read_bytes()).hexdigest()==h
for role in 'ABC':assert 'Accept' in (p/f'review/round_04/{role}.md').read_text()
print('Server/local archive hashes matched; four reviewed files unchanged; 12 actual reviews delivered; internal recovery bundle unchanged.')
