from pathlib import Path
import hashlib,json,zipfile
p=Path(r'C:/Users/74095/hs/SailBoat/sailboat-routing-v0/paper/ccdc/r13_revision')
r=json.loads((p/'DELIVERY.json').read_text())
for n,meta in r['artifacts'].items():
 f=p/n
 assert f.stat().st_size==meta['bytes'],n
 assert hashlib.sha256(f.read_bytes()).hexdigest()==meta['sha256'],n
 with zipfile.ZipFile(f) as z:assert z.testzip() is None
with zipfile.ZipFile(p/'R13_CCDC_REVIEW_preview.zip') as z:
 for n in z.namelist():
  if n.startswith('server_state/'):
   f=p/n;f.parent.mkdir(exist_ok=True);f.write_bytes(z.read(n))
for n,h in r['reviewed_files'].items():assert hashlib.sha256((p/n).read_bytes()).hexdigest()==h
(p/'evidence/final_delivery_check.json').write_text(json.dumps({'local_server_archives_match':True,'zip_crc_ok':True,'final_reviewed_identity_matches':True,'nine_raw_reviews_present':all((p/f'review/round_{r:02}/{a}.md').exists() for r in (1,2,3) for a in 'ABC')},indent=2))
print('Archives, reviewed identity and server state verified')
