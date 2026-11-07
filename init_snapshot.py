from pathlib import Path
import shutil,json,hashlib
src=Path('/home/ot/Students/hs/sailboat-routing-v0').resolve()
dst=Path('/home/ot/Students/hs/sailboat-track-b')
assert not dst.exists()
dst.mkdir();assert dst.resolve().is_relative_to(Path('/home/ot/Students/hs'))
for name in ['src','third_party','scripts','configs']:
 shutil.copytree(src/name,dst/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for name in ['requirements.lock','pyproject.toml']:
 if (src/name).exists():shutil.copy2(src/name,dst/name)
for name in ['runs','docs','literature','.cache','.tmp','figures']: (dst/name).mkdir()
manifest={str(p.relative_to(dst)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dst.rglob('*') if p.is_file()}
(dst/'docs/INITIAL_SNAPSHOT.json').write_text(json.dumps({'source':str(src),'source_code_head':'4c6a07878e7432da12dea50d42a3272dbce7a820','actual_working_files':manifest},indent=2))
print(len(manifest),sum(p.stat().st_size for p in dst.rglob('*') if p.is_file()))
