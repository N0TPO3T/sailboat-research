"""Package verified publication artifacts and lightweight evidence only."""
from pathlib import Path
import hashlib,json,zipfile,tempfile,subprocess,sys
P=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
check=json.loads((P/'CLOSEOUT_CHECK.json').read_text())
assert check['pdf_sha256']==sha(P/'manuscript.pdf')
assert sha(P/'manuscript.pdf') in (P/'INDEPENDENT_CLOSEOUT_CHECK.md').read_text(encoding='utf8')
names=['manuscript.md','manuscript.docx','manuscript.pdf','SUPPLEMENT.md',
       'CLOSEOUT_RESPONSE.md','INDEPENDENT_CLOSEOUT_CHECK.md','CLOSEOUT_CHECK.json',
       'PAIRED_TIME_CHECK.json','check_paired_times.py','AUTHOR_CHECKLIST_ZH.md','README.md',
       'build_docx.py','math_docx.py','export_pdf.ps1','draw_interface.py','convert_to_latex.py',
       'official_template.docx','requirements-editorial.txt','VENUE_CHECK.md','REFERENCE_METADATA_CHECK.json']
files=[P/n for n in names]
for folder in ['figures','evidence','latex','provenance']:
    files += [p for p in (P/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
assert all(p.exists() for p in files)
assert not any(p.suffix.lower() in ['.pth','.pt','.ttf','.otf','.woff','.woff2'] for p in files)
manifest={'execution_date':'2026-10-09 Asia/Shanghai','status':'content closeout completed; submission metadata pending',
          'pdf_sha256':sha(P/'manuscript.pdf'),'package_scope':'lightweight publication and evidence; not full recovery',
          'full_recovery_included':False,'weights_included':False,'all_raw_trajectories_included':False,
          'new_experiments':0,'server_synced':False,'pushed':False,'submitted':False,
          'pending_metadata':['corresponding author','email','applicable funding'],
          'files':{p.relative_to(P).as_posix():sha(p) for p in sorted(files)}}
(P/'DELIVERY.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
dest=P/'CCDC2027_Track_A_closeout_package.zip'
with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
    for p in files+[P/'DELIVERY.json']:z.write(p,p.relative_to(P).as_posix())
with zipfile.ZipFile(dest) as z:
    assert z.testzip() is None
    assert all(hashlib.sha256(z.read(n)).hexdigest()==h for n,h in manifest['files'].items())
    # Standalone CSV-check smoke test after extraction elsewhere, without sibling archives.
    with tempfile.TemporaryDirectory(prefix='closeout-package-') as tmp:
        tmp=Path(tmp)
        for name in ['check_paired_times.py','evidence/episodes.csv']:z.extract(name,tmp)
        subprocess.run([sys.executable,str(tmp/'check_paired_times.py')],cwd=tmp,check=True,stdout=subprocess.PIPE)
        actual=json.loads((tmp/'PAIRED_TIME_CHECK.json').read_text())
        assert actual==json.loads((P/'PAIRED_TIME_CHECK.json').read_text())
receipt={'zip':dest.name,'bytes':dest.stat().st_size,'sha256':sha(dest),'zip_crc_ok':True,
         'all_manifest_hashes_ok':True,'standalone_csv_reaggregation_ok':True,'member_count':len(files)+1}
(P/'PACKAGE_RECEIPT.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
print(json.dumps(receipt,indent=2))
