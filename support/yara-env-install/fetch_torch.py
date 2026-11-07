from pathlib import Path
import urllib.request,concurrent.futures,hashlib
R=Path('/home/ot/Students/hs/yara-env/docker/wheels');R.mkdir(exist_ok=True)
P=R/'torch_chunks';P.mkdir(exist_ok=True)
url='https://download-r2.pytorch.org/whl/cpu/torch-1.13.1%2Bcpu-cp38-cp38-linux_x86_64.whl'
size=199075931
def get(start):
 end=min(start+1048576,size)-1;p=P/str(start)
 if p.exists() and p.stat().st_size==end-start+1:return
 for i in range(3):
  try:
   with urllib.request.urlopen(urllib.request.Request(url,headers={'Range':f'bytes={start}-{end}'}),timeout=30) as r:
    b=r.read();assert r.status==206 and len(b)==end-start+1
   p.write_bytes(b);return
  except Exception:
   if i==2:raise
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(get,range(0,size,1048576)))
target=R/'torch-1.13.1+cpu-cp38-cp38-linux_x86_64.whl'
with target.open('wb') as f:
 for start in range(0,size,1048576):f.write((P/str(start)).read_bytes())
assert hashlib.file_digest(target.open('rb'),'sha256').hexdigest()=='4a8b84834eb12b3428c24e9f264c9bd6a2cf449fffc191374e7dbb2b950fc6d7'
print('CPU_TORCH_VERIFIED',flush=True)
