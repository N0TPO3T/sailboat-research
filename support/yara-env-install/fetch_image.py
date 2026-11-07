"""Fetch official Docker Registry content, verify digests, build docker-load archive."""
from pathlib import Path
import urllib.request,json,hashlib,time,gzip,tarfile,io,concurrent.futures
ROOT=Path(__file__).resolve().parent
STORE=ROOT/'image_layers'; STORE.mkdir(exist_ok=True)
REPO='osrf/ros'; TAG='noetic-desktop-full'
def token():
    return json.load(urllib.request.urlopen('https://auth.docker.io/token?service=registry.docker.io&scope=repository:'+REPO+':pull',timeout=30))['token']
def req(path):
    return urllib.request.Request('https://registry-1.docker.io/v2/'+REPO+'/'+path,headers={'Authorization':'Bearer '+token(),'Accept':'application/vnd.docker.distribution.manifest.v2+json'})
with urllib.request.urlopen(req('manifests/'+TAG),timeout=60) as r:
    raw=r.read(); manifest=json.loads(raw)
    digest=r.headers.get('Docker-Content-Digest')
assert manifest['mediaType']=='application/vnd.docker.distribution.manifest.v2+json'
(ROOT/'registry_manifest.json').write_bytes(raw)
def get_blob(desc):
    hexid=desc['digest'].split(':')[1]; p=STORE/hexid
    if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==hexid:
        return p
    for attempt in range(3):
        try:
            h=hashlib.sha256(); size=0
            with p.with_suffix('.part').open('wb') as f:
                for start in range(0,desc['size'],8*1024*1024):
                    end=min(start+8*1024*1024,desc['size'])-1
                    q=req('blobs/'+desc['digest']);q.add_header('Range',f'bytes={start}-{end}')
                    with urllib.request.urlopen(q,timeout=60) as r:
                        b=r.read()
                        assert len(b)==end-start+1,(r.status,len(b),start,end)
                    f.write(b);f.flush();h.update(b);size+=len(b)
            assert h.hexdigest()==hexid and size==desc['size']
            p.with_suffix('.part').replace(p)
            print('verified blob',hexid[:12],size,flush=True)
            return p
        except Exception as e:
            print('retry',hexid[:12],type(e).__name__,flush=True)
            if attempt==2:raise
            time.sleep(2)
config=get_blob(manifest['config'])
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    paths=list(pool.map(get_blob,manifest['layers']))
archive=ROOT/'ros-noetic-desktop-full.tar.gz'
def add_bytes(t,name,data):
    item=tarfile.TarInfo(name);item.size=len(data);t.addfile(item,io.BytesIO(data))
names=[]
with tarfile.open(archive,'w:gz',compresslevel=1) as t:
    cname=config.name+'.json'; t.add(config,arcname=cname)
    for p in paths:
        unpacked=p.with_suffix('.tar')
        with gzip.open(p,'rb') as src,unpacked.open('wb') as dst:
            while True:
                b=src.read(1024*1024)
                if not b:break
                dst.write(b)
        name=p.name+'/layer.tar';t.add(unpacked,arcname=name);names.append(name)
    add_bytes(t,'manifest.json',json.dumps([{'Config':cname,'RepoTags':[REPO+':'+TAG],'Layers':names}]).encode())
receipt={'source':REPO+':'+TAG,'registry_digest':digest,'compressed_bytes':sum(x['size'] for x in manifest['layers']),'archive_bytes':archive.stat().st_size,'archive_sha256':hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()}
(ROOT/'image_receipt.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt),flush=True)
