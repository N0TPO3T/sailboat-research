"""Create and hash the lightweight publication package; never package weights."""
from pathlib import Path
import hashlib,json,zipfile
P=Path(__file__).resolve().parent
names='''manuscript.md manuscript.docx manuscript.pdf SUPPLEMENT.md SUPPLEMENT.docx SUPPLEMENT.pdf official_template.docx build_docx.py math_docx.py export_pdf.ps1 draw_interface.py plot_figures.py plot_data.json extract_figure_data.py FIGURE_DATA_CHECK.json FIGURE_POLISH_NOTES.md make_overview.py FIGURES.html check_paired_times.py PAIRED_TIME_CHECK.json check_visual_artifacts.py VISUAL_EDITION_CHECK.json CLOSEOUT_RESPONSE.md INDEPENDENT_VISUAL_CHECK.md README.md AUTHOR_CHECKLIST_ZH.md requirements-editorial.txt package_visual_edition.py'''.split()
files=[P/n for n in names]
for sub in ['evidence','provenance']:
 files += [p for p in (P/sub).rglob('*') if p.is_file()]
files += [p for p in (P/'figures').iterdir() if p.is_file() and not p.name.startswith('figure5_encounters')]
assert all(p.is_file() for p in files)
sha=lambda data:hashlib.sha256(data).hexdigest()
manifest={p.relative_to(P).as_posix():sha(p.read_bytes()) for p in sorted(files)}
(P/'CONTENTS_SHA256.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
archive=P/'CCDC2027_Track_A_closeout_package.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files+[P/'CONTENTS_SHA256.json']:z.write(p,p.relative_to(P).as_posix())
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for name,h in manifest.items():assert sha(z.read(name))==h
 assert not any(n.endswith(('.pth','.pt','.ckpt')) for n in z.namelist())
receipt={'archive':archive.name,'bytes':archive.stat().st_size,'sha256':sha(archive.read_bytes()),'files':len(manifest)+1,'all_manifest_hashes_verified':True,'complete_recovery_archive_included':False,'model_weights_included':False,'server_synced':False}
(P/'PACKAGE_RECEIPT.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
print(json.dumps(receipt,indent=2))
