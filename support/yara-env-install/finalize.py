from pathlib import Path
import json,tarfile,hashlib
r=Path('/home/ot/Students/hs/yara-env').resolve()
assert str(r)=='/home/ot/Students/hs/yara-env'
p=r/'INSTALL_PREFLIGHT_ZH.md'
s=p.read_text()
note='> 2026-11-06：历史预检已被 README_ZH.md 的安装及实际步进 PASS 取代。用户已授权 Docker 写入，指定旧目录已删除。\n\n'
if not s.startswith(note):p.write_text(note+s)
report=json.loads((r/'logs/SMOKE_RESULT.json').read_text());assert report['status']=='PASS' and len(report['rows'])==8
changed=[];checked=0
with tarfile.open(r/'yara-source.tar.gz') as t:
    for m in t.getmembers():
        if not m.isfile():continue
        rel=Path(*Path(m.name).parts[1:]);p=r/'workspace/src/Yara_OVE'/rel
        if not p.exists() or hashlib.sha256(p.read_bytes()).digest()!=hashlib.sha256(t.extractfile(m).read()).digest():changed.append(str(rel))
        checked+=1
(r/'logs/SOURCE_CHECK.json').write_text(json.dumps({'archive_files_checked':checked,'changed_archive_files':changed},indent=2))
print('SOURCE_CHECK',checked,changed)
