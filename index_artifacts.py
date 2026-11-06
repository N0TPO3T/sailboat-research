from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parent
skip={'.git','build','ipc','.cache','.tmp','__pycache__','archives'}
files={}
for p in sorted(R.rglob('*')):
 if not p.is_file() or any(x in skip for x in p.relative_to(R).parts) or p.name in ['ARTIFACT_INDEX.json','DELIVERY.json','run.lock']:continue
 assert not p.is_symlink(),p
 files[str(p.relative_to(R))]=dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
(R/'ARTIFACT_INDEX.json').write_text(json.dumps(dict(files=files,scope='Source, frozen assets, current raw outputs and logs; excludes generated build/cache/IPC and previous full-verification archives'),indent=2))
print('INDEX_FILES',len(files))
