"""Package this local editorial edition without modifying frozen research assets."""
from pathlib import Path
import json,hashlib,difflib,zipfile,re,datetime
from pypdf import PdfReader
from lxml import etree
P=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
orig=P.parent/'track_A_submit'
doc=(P/'manuscript.md').read_text(encoding='utf8')
(P/'REVISION.diff').write_text(''.join(difflib.unified_diff((orig/'manuscript.md').read_text(encoding='utf8').splitlines(True),doc.splitlines(True),fromfile='track_A_submit/manuscript.md',tofile='track_A_aris_20261008/manuscript.md')),encoding='utf8')
reader=PdfReader(P/'manuscript.pdf');assert len(reader.pages)<=8
fonts={}
for page in reader.pages:
    for item in page['/Resources'].get('/Font',{}).values():
        font=item.get_object();desc=font.get('/FontDescriptor')
        if not desc and font.get('/DescendantFonts'):desc=font['/DescendantFonts'][0].get_object().get('/FontDescriptor')
        fonts[str(font.get('/BaseFont'))]=bool(desc and any(k in desc.get_object() for k in ['/FontFile','/FontFile2','/FontFile3']))
assert all(fonts.values()),fonts
tex=(P/'latex/main.tex').read_text(encoding='utf8')
labels=re.findall(r'\\label\{([^}]+)\}',tex)
assert len(labels)==len(set(labels))
assert set(re.findall(r'\\ref\{([^}]+)\}',tex))<=set(labels)
assert set(re.findall(r'\\cite\{([^}]+)\}',tex))<=set(re.findall(r'\\bibitem\{([^}]+)\}',tex))
assert len(re.findall(r'\\begin\{equation\}',tex))==6
with zipfile.ZipFile(P/'manuscript.docx') as d,zipfile.ZipFile(P/'official_template.docx') as t:
    assert etree.tostring(etree.fromstring(d.read('word/styles.xml')),method='c14n')==etree.tostring(etree.fromstring(t.read('word/styles.xml')),method='c14n')
    xml=d.read('word/document.xml').decode();assert xml.count('<w:tbl>')==3
    assert '<m:oMath' in xml
verification=json.loads((P/'REVISION_VERIFICATION.json').read_text(encoding='utf8'))
verification.update({'timestamp':now,'pdf_pages':len(reader.pages),'fonts':fonts,'all_fonts_embedded':True,'template_styles_unchanged':True,'native_word_math':True,'duplicate_tex_labels':0,'undefined_tex_references':0,'undefined_tex_citations':0,'latex_compile_verified':False,'primary_pdf_renderer':'Microsoft Word 2019, ISO 19005-1 export option; PDF/A conformance not independently certified','visual_check':'See PAPER_IMPROVEMENT_LOG.md for inspected final page set.'})
(P/'REVISION_VERIFICATION.json').write_text(json.dumps(verification,indent=2),encoding='utf8')
with zipfile.ZipFile(P/'LaTeX_source.zip','w',zipfile.ZIP_DEFLATED) as z:
    for f in (P/'latex').rglob('*'):
        if f.is_file() and f.suffix in ['.tex','.cls','.pdf','.md','.json']:z.write(f,f.relative_to(P/'latex'))
files=['manuscript.pdf','manuscript.docx','manuscript.md','SUPPLEMENT.md','AUTHOR_NOTES_ZH.md','PAPER_IMPROVEMENT_LOG.md','REVISION_VERIFICATION.json','REVISION.diff','LaTeX_source.zip','VENUE_CHECK.md','EVIDENCE_INDEX.md','README.md','STATUS.md','review_round1.md','review_round2.md','manuscript_round0_original.pdf','manuscript_round1.pdf','manuscript_round2.pdf','REFERENCE_METADATA_CHECK.json']
manifest={'created_at':now,'scope':'local editorial revision of the user-named draft; server research state not queried or superseded','source_pdf':str(orig/'manuscript.pdf'),'source_pdf_sha256':sha(orig/'manuscript.pdf'),'recovery_archive_sha256':verification['archive_sha256'],'new_navigation_experiments':0,'training':False,'authors_source':'user message in current chat','files':{n:sha(P/n) for n in files if (P/n).exists()},'submission_uploaded':False,'push_or_server_sync':False}
(P/'DELIVERY.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
with zipfile.ZipFile(P/'CCDC2027_revised_package.zip','w',zipfile.ZIP_DEFLATED) as z:
    for n in files+['DELIVERY.json','build_docx.py','math_docx.py','export_pdf.ps1','convert_to_latex.py','official_template.docx','verify_revision.py','plot_revision.py','draw_interface.py']:
        f=P/n
        if f.exists():z.write(f,n)
    for f in (P/'figures').iterdir():
        if f.is_file():z.write(f,f.relative_to(P))
    for f in (P/'evidence').iterdir():
        if f.is_file():z.write(f,f.relative_to(P))
with zipfile.ZipFile(P/'CCDC2027_revised_package.zip') as z:assert z.testzip() is None
print(json.dumps({'pages':len(reader.pages),'all_fonts_embedded':True,'package':str(P/'CCDC2027_revised_package.zip'),'bytes':(P/'CCDC2027_revised_package.zip').stat().st_size},indent=2))
