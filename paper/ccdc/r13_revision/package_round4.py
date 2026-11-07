from pathlib import Path
import base64,json,zipfile,hashlib
p=Path(r'C:/Users/74095/hs/SailBoat/sailboat-routing-v0/paper/ccdc/r13_revision')
for n,v in json.loads((p/'server_state_transfer.json').read_text(encoding='utf-8-sig')).items():
 assert n in ['PROJECT_STATE.md','CURRENT_PLAN.md','HANDOFF.md'];(p/'server_state'/n).write_bytes(base64.b64decode(v))
z=p/'R13_CCDC_REVIEW_preview.zip'
with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as a:
 for f in sorted(p.rglob('*')):
  if not f.is_file():continue
  rel=f.relative_to(p)
  if any(k in rel.parts for k in ['__pycache__','rendered','reproduction_check']):continue
  if f.suffix=='.zip' and f.name!='R13_LaTeX.zip':continue
  if f.name in ['thesis_final.txt','thesis_senior.txt','server_state_transfer.json','DELIVERY.json','final_delivery_check.json']:continue
  a.write(f,rel.as_posix())
with zipfile.ZipFile(z) as a:
 assert a.testzip() is None
 for role in 'ABC':assert f'review/round_04/{role}.md' in a.namelist()
receipt={'reviewed_files':json.loads((p/'review_round_04_input/VERSION.json').read_text()),'total_review_rounds':4,'raw_reviews':12,'verdicts':dict.fromkeys('ABC','Accept'),'actual_conference_acceptance':False,'asset_use_and_reviewer_provision':'confirmed by explicit user report of provider permission','continuation_new_experiments':0,'artifacts':{}}
for n in ['R13_CCDC_REVIEW_preview.zip','R13_REPRODUCTION_internal.zip']:
 f=p/n;receipt['artifacts'][n]={'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size}
(p/'DELIVERY.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt['artifacts'],indent=2))
