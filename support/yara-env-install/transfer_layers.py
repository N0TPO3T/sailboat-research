from pathlib import Path
import json,hashlib,subprocess,concurrent.futures,time
R=Path(__file__).resolve().parent;S=R/'image_layers';T=R/'transfer_layers';T.mkdir(exist_ok=True)
m=json.loads((R/'registry_manifest.json').read_text());descs=[m['config']]+m['layers']
def transfer(d,p):
 h=d['digest'][7:]
 assert hashlib.file_digest(p.open('rb'),'sha256').hexdigest()==h
 subprocess.run(['scp','-q','-F','C:/Users/74095/.ssh/config',str(p),'donghai:/home/ot/Students/hs/yara-env/docker/image_layers/'+h],check=True)
 print('transferred verified layer',h[:12],d['size'],flush=True)
pending=descs.copy();futures=[];start=time.time()
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 while pending:
  assert time.time()-start<2400,'transfer readiness timeout'
  for d in pending[:]:
   h=d['digest'][7:];p=S/h;folder=S/(h+'_chunks')
   if not p.exists():
    chunks=[folder/str(k) for k in range(0,d['size'],1048576)]
    if all(x.exists() and x.stat().st_size==min(1048576,d['size']-int(x.name)) for x in chunks):
     p=T/h
     with p.open('wb') as out:
      for x in chunks:out.write(x.read_bytes())
   if p.exists() and p.stat().st_size==d['size']:
    futures.append(pool.submit(transfer,d,p));pending.remove(d)
  for f in futures:
   if f.done():f.result()
  if pending:time.sleep(3)
 for f in futures:f.result()
print('ALL_LAYERS_TRANSFERRED',flush=True)
