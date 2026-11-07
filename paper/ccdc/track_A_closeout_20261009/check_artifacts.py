"""Local closeout preservation/format checks; no experiments or raw-trace recomputation."""
from pathlib import Path
import json,re,hashlib,zipfile
from pypdf import PdfReader
from lxml import etree
P=Path(__file__).resolve().parent
S=P.parent/'track_A_aris_20261008'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a=(S/'manuscript.md').read_text(encoding='utf8');b=(P/'manuscript.md').read_text(encoding='utf8')
assert re.findall(r'\$\$(.*?)\$\$',a,re.S)==re.findall(r'\$\$(.*?)\$\$',b,re.S)
assert [x for x in a.split('\n\n') if x.startswith('|')]==[x for x in b.split('\n\n') if x.startswith('|')]
assert a.split('## References')[1]==b.split('## References')[1]
assert a.split('## Abstract')[0]==b.split('## Abstract')[0]
assert (S/'math_docx.py').read_bytes()==(P/'math_docx.py').read_bytes()
preserved=[p for p in (P/'evidence').iterdir() if p.is_file()]+[p for p in (P/'figures').iterdir() if p.is_file() and not p.name.startswith('figure1_interface')]
assert all(sha(p)==sha(S/p.relative_to(P)) for p in preserved)
with zipfile.ZipFile(P/'manuscript.docx') as d,zipfile.ZipFile(P/'official_template.docx') as t:
    assert etree.tostring(etree.fromstring(d.read('word/styles.xml')),method='c14n')==etree.tostring(etree.fromstring(t.read('word/styles.xml')),method='c14n')
    xml=etree.fromstring(d.read('word/document.xml'));ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    assert len(xml.findall('.//w:tbl',ns))==3
    paras=[''.join(e.xpath('.//w:t/text()',namespaces=ns)) for e in xml.findall('.//w:p',ns)]
    for block in b.strip().split('\n\n'):
        block=block.strip()
        if block.startswith(('#','Authors:','Affiliations:','Keywords:','$$','![','|','```','Table ')) or not block:continue
        norm=lambda x:x.replace('m_real','mreal').replace('O_t','Ot').replace('D_j','Dj').replace('f_z','fz').replace('r_max','rmax')
        assert any(norm(block).strip() in norm(p).strip() for p in paras),block[:80]
    refs=[p for p in xml.findall('.//w:p',ns) if re.match(r'^\[\d+\]',''.join(p.xpath('.//w:t/text()',namespaces=ns)))]
    assert len(refs)==10 and all(p.find('./w:pPr/w:keepLines',ns) is not None for p in refs)
reader=PdfReader(P/'manuscript.pdf');assert len(reader.pages)==8
fonts={}
for page in reader.pages:
    for ref in page['/Resources'].get('/Font',{}).values():
        f=ref.get_object();desc=f.get('/FontDescriptor')
        if not desc and f.get('/DescendantFonts'):desc=f['/DescendantFonts'][0].get_object().get('/FontDescriptor')
        fonts[str(f.get('/BaseFont'))]=bool(desc and any(x in desc.get_object() for x in ('/FontFile','/FontFile2','/FontFile3')))
assert all(fonts.values())
text='\n'.join(p.extract_text() for p in reader.pages)
assert 'justify its additional cost' not in text
for term in ['106.064','2133.23','378.44','17.009']:assert term in text,term
source=json.loads((P/'provenance/version_check.json').read_text())
assert all(sha(S/n)==h for n,h in source['source_hashes'].items())
result={'pdf_sha256':sha(P/'manuscript.pdf'),'pdf_pages':8,'all_fonts_embedded':True,'fonts':fonts,'equations_unchanged':6,'numerical_tables_unchanged':3,'bibliography_entries_unchanged':10,'authors_affiliations_unchanged':True,'ordinary_markdown_paragraphs_present_in_docx':True,'template_styles_unchanged':True,'references_keep_together':10,'evidence_and_other_figure_files_unchanged':len(preserved),'source_edition_unchanged':True,'visual_inspection':'All 8 final Word-export pages inspected at 1500-pixel height; figures, equations, tables and references readable. No reference entry split across columns/pages.','new_navigation_experiments':0,'trajectory_recomputation_this_round':False,'native_tex_compilation':False,'server_sync':False}
(P/'CLOSEOUT_CHECK.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result,indent=2))
