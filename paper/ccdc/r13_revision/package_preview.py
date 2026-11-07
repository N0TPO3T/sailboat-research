from pathlib import Path
import zipfile,hashlib,json
p=Path(r'C:/Users/74095/hs/SailBoat/sailboat-routing-v0/paper/ccdc/r13_revision')
z=p/'R13_CCDC_REVIEW_preview.zip'
with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as a:
 for f in sorted(p.rglob('*')):
  if not f.is_file():continue
  r=f.relative_to(p)
  if '__pycache__' in r.parts or r.parts[0] in ('rendered','reproduction_check','server_state'):continue
  if f.name in ('R13_CCDC_REVIEW_preview.zip','R13_REPRODUCTION_internal.zip','thesis_final.txt','thesis_senior.txt','DELIVERY.json'):continue
  a.write(f,r.as_posix())
with zipfile.ZipFile(z) as a: assert a.testzip() is None
print(z.stat().st_size)
