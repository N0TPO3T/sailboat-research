from pathlib import Path
import hashlib,json,zipfile,datetime
p=Path(r'C:/Users/74095/hs/SailBoat/sailboat-track-b')
roots=['scripts','src','third_party','configs','runs','docs','analysis','analysis_v2','figures','reviews','.aris/traces/research-review/2026-10-08_ab']
files=[]
for name in roots:
    for f in (p/name).rglob('*'):
        if f.is_file() and '__pycache__' not in f.parts and f.suffix!='.pyc':files.append(f)
for name in ['README.md','STATUS.md','RESOURCE_LEDGER.json','RESULTS_INDEX.json','requirements.lock','EARLY_PROBLEM_REVIEW.md']:
    if (p/name).is_file():files.append(p/name)
files=sorted(set(files))
manifest={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':{str(f.relative_to(p)).replace('\\','/'):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}}
m=p/'PACKAGE_MANIFEST.json';m.write_text(json.dumps(manifest,indent=2),encoding='utf-8');files.append(m)
z=p/'B_RESEARCH_preview.zip'
with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as a:
    for f in files:a.write(f,str(f.relative_to(p)))
with zipfile.ZipFile(z) as a:
    bad=a.testzip();assert bad is None,bad
receipt={'zip':z.name,'bytes':z.stat().st_size,'sha256':hashlib.sha256(z.read_bytes()).hexdigest(),'entries':len(files),'testzip':'pass'}
(p/'PACKAGE_RECEIPT.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps(receipt,indent=2))
