from pathlib import Path
import zipfile,json,hashlib
p=Path('/home/ot/Students/hs/sailboat-routing-v0/paper/ccdc/track_A_submit').resolve()
assert p.is_relative_to(Path('/home/ot/Students/hs').resolve())
z=zipfile.ZipFile(p/'A_SUBMISSION_READY_preview.zip')
for n in z.namelist():assert (p/n).resolve().is_relative_to(p),n
z.extractall(p)
m=json.loads((p/'DELIVERY.json').read_text())
for n,h in m['files'].items():assert hashlib.sha256((p/n).read_bytes()).hexdigest()==h,n
print('A synchronized: final source/DOCX/PDF/supplement/notes/check hashes verified')
print('PDF',m['files']['manuscript.pdf'])
