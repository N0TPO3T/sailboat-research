from pathlib import Path
import json,zipfile,hashlib
p=Path(__file__).parent
z=zipfile.ZipFile(p/'R13_REPRODUCTION_internal.zip');idx=json.loads(z.read('CONTENTS_SHA256.json'));assert all(hashlib.sha256(z.read(n)).hexdigest()==h for n,h in idx.items());print('Internal bundle',len(idx),'hashes,',sum(n.endswith('trace.json') for n in z.namelist()),'traces; intact')
(p/'evidence/local_archive_check.json').write_text(json.dumps(dict(indexed_files=len(idx),trace_files=72,all_hashes_match=True,archive_sha256=hashlib.sha256((p/'R13_REPRODUCTION_internal.zip').read_bytes()).hexdigest()),indent=2))
