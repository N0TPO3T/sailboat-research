from pathlib import Path
import json,tarfile,gzip,io,hashlib,subprocess
R=Path('/home/ot/Students/hs/yara-env/docker');S=R/'server_layers';m=json.loads((R/'registry_manifest.json').read_text())
config=R/'image_layers'/m['config']['digest'][7:]
assert hashlib.file_digest(config.open('rb'),'sha256').hexdigest()==m['config']['digest'][7:]
archive=R/'verified-ros-image.tar';names=[]
with tarfile.open(archive,'w') as t:
 cname=config.name+'.json';t.add(config,arcname=cname)
 for d in m['layers']:
  p=S/d['digest'][7:];assert hashlib.file_digest(p.open('rb'),'sha256').hexdigest()==d['digest'][7:]
  unpacked=S/(p.name+'.tar')
  with gzip.open(p,'rb') as src,unpacked.open('wb') as dst:
   while True:
    b=src.read(1024*1024)
    if not b:break
    dst.write(b)
  name=p.name+'/layer.tar';t.add(unpacked,arcname=name);names.append(name)
 b=json.dumps([{'Config':cname,'RepoTags':['hs-yara:noetic-base'],'Layers':names}]).encode()
 item=tarfile.TarInfo('manifest.json');item.size=len(b);t.addfile(item,io.BytesIO(b))
print('official registry manifest sha256',hashlib.sha256((R/'registry_manifest.json').read_bytes()).hexdigest(),flush=True)
subprocess.run(['docker','load','--input',str(archive)],check=True)
subprocess.run(['python3',str(R/'verify_image.py')],check=True)
