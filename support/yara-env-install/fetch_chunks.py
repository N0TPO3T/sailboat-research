from pathlib import Path
import urllib.request,urllib.error,json,hashlib,concurrent.futures,time
R=Path(__file__).resolve().parent;S=R/'image_layers';m=json.loads((R/'registry_manifest.json').read_text())
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*a,**kw):return None
op=urllib.request.build_opener(NoRedirect)
token=json.load(urllib.request.urlopen('https://auth.docker.io/token?service=registry.docker.io&scope=repository:osrf/ros:pull',timeout=20))['token']
jobs=[];missing=[]
for d in m['layers']:
    h=d['digest'].split(':')[1];p=S/h
    if p.exists() and hashlib.file_digest(p.open('rb'),'sha256').hexdigest()==h:continue
    q=urllib.request.Request('https://registry-1.docker.io/v2/osrf/ros/blobs/'+d['digest'],headers={'Authorization':'Bearer '+token})
    try:op.open(q,timeout=20)
    except urllib.error.HTTPError as e:
        assert e.code in [302,307];url=e.headers['Location']
    folder=S/(h+'_chunks');folder.mkdir(exist_ok=True)
    missing.append((d,folder))
    for start in range(0,d['size'],1048576):
        end=min(start+1048576,d['size'])-1;target=folder/str(start)
        if target.exists() and target.stat().st_size==end-start+1:continue
        jobs.append((url,start,end,target))
def download(j):
    url,start,end,p=j
    for a in range(4):
        try:
            q=urllib.request.Request(url,headers={'Range':f'bytes={start}-{end}'})
            with urllib.request.urlopen(q,timeout=25) as r:
                b=r.read();assert r.status==206 and len(b)==end-start+1
                assert r.headers.get('Content-Range','').startswith(f'bytes {start}-{end}/')
            p.write_bytes(b);return len(b)
        except Exception:
            if a==3:raise
            time.sleep(1)
print('chunks needed',len(jobs),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    futures=[pool.submit(download,j) for j in jobs];n=0
    for f in concurrent.futures.as_completed(futures):
        f.result();n+=1
        if n%40==0: print('chunks complete',n,'/',len(jobs),flush=True)
for d,folder in missing:
    h=d['digest'].split(':')[1];p=S/h;sha=hashlib.sha256()
    with p.open('wb') as dst:
        for start in range(0,d['size'],1048576):
            b=(folder/str(start)).read_bytes();dst.write(b);sha.update(b)
    assert sha.hexdigest()==h
    print('verified',h[:12],p.stat().st_size,flush=True)
