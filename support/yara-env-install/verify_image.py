from pathlib import Path
import json,subprocess,hashlib
r=Path('/home/ot/Students/hs/yara-env/docker')
m=json.loads((r/'registry_manifest.json').read_text())
p=r/'image_layers'/m['config']['digest'][7:]
assert hashlib.sha256(p.read_bytes()).hexdigest()==m['config']['digest'][7:]
c=json.loads(p.read_text())
i=json.loads(subprocess.check_output(['docker','image','inspect','hs-yara:noetic-base']))[0]
assert i['RootFS']['Layers']==c['rootfs']['diff_ids']
assert i['Config']==c['config'], (i['Config'],c['config'])
assert i['Architecture']==c['architecture'] and i['Os']==c['os']
receipt={'tag':'hs-yara:noetic-base','source':'osrf/ros:noetic-desktop-full','official_manifest_sha256':hashlib.sha256((r/'registry_manifest.json').read_bytes()).hexdigest(),'official_config_digest':m['config']['digest'],'docker_image_id':i['Id'],'rootfs_and_config_equal':True,'note':'Docker 29 containerd image identifier differs from config digest; verified actual config and all uncompressed rootfs digests against official config. Compressed blobs verified before load.'}
(r/'IMAGE_RECEIPT.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt))
