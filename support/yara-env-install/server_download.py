from pathlib import Path
import json,urllib.request,concurrent.futures,hashlib,time
R=Path('/home/ot/Students/hs/yara-env/docker');S=R/'server_layers';S.mkdir(exist_ok=True)
ds=json.loads((R/'server_download.json').read_text());jobs=[]
for d in ds:
 h=d['digest'][7:];p=S/h
 old=R/'image_layers'/h
 if old.exists() and old.stat().st_size==d['size'] and hashlib.file_digest(old.open('rb'),'sha256').hexdigest()==h:
  if not p.exists():p.hardlink_to(old)
 if p.exists() and hashlib.file_digest(p.open('rb'),'sha256').hexdigest()==h:continue
 folder=S/(h+'_chunks');folder.mkdir(exist_ok=True)
 for start in range(0,d['size'],1048576):
  end=min(start+1048576,d['size'])-1;part=folder/str(start)
  if not part.exists() or part.stat().st_size!=end-start+1:jobs.append((d['url'],start,end,part))
def get(j):
 u,start,end,p=j
 for a in range(3):
  try:
   q=urllib.request.Request(u,headers={'Range':f'bytes={start}-{end}','Host':'production.cloudfront.docker.com'})
   with urllib.request.urlopen(q,timeout=35) as r:
    b=r.read();assert r.status==206 and len(b)==end-start+1
    assert r.headers.get('Content-Range','').startswith(f'bytes {start}-{end}/')
   p.write_bytes(b);return
  except Exception:
   if a==2:raise
   time.sleep(1)
print('remaining chunks',len(jobs),flush=True);s=time.time()
with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
 fs=[pool.submit(get,j) for j in jobs]
 for i,f in enumerate(concurrent.futures.as_completed(fs),1):
  f.result()
  if i%50==0: print('complete',i,'/',len(jobs),'wall_s',round(time.time()-s),flush=True)
for d in ds:
 h=d['digest'][7:];p=S/h
 if not p.exists():
  with p.open('wb') as out:
   for start in range(0,d['size'],1048576):out.write((S/(h+'_chunks')/str(start)).read_bytes())
 assert hashlib.file_digest(p.open('rb'),'sha256').hexdigest()==h
 print('verified',h[:12],flush=True)
print('DOWNLOAD_COMPLETE',flush=True)
