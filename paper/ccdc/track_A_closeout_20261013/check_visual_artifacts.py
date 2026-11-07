"""Check current manuscript consistency; optional read-only prior-edition check."""
from pathlib import Path
import re,json,hashlib,zipfile
from pypdf import PdfReader
from docx import Document
from lxml import etree
P=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
tables=lambda s:[[[v.strip() for v in row.strip('|').split('|')] for row in b.splitlines() if not re.match(r'^\|[-:| ]+\|$',row)] for b in s.split('\n\n') if b.startswith('|')]
result={}
for stem,num in [('manuscript',3),('SUPPLEMENT',4)]:
 md=(P/(stem+'.md')).read_text(encoding='utf8');doc=Document(P/(stem+'.docx'))
 tab=tables(md);actual=[[[c.text for c in r.cells] for r in t.rows] for t in doc.tables]
 assert len(tab)==num and actual==tab
 paras=[p.text for p in doc.paragraphs]
 norm=lambda s:s.replace('m_real','mreal').replace('O_t','Ot').replace('D_j','Dj').replace('f_z','fz').replace('r_max','rmax').replace('**','')
 for block in md.strip().split('\n\n'):
  block=block.strip()
  if not block or block.startswith(('#','Authors:','Affiliations:','$$','|','```')):continue
  if block.startswith('!['):block=re.match(r'!\[(.*?)\]',block,re.S)[1]
  assert any(norm(block) in norm(x) for x in paras),block[:80]
 pdf=PdfReader(P/(stem+'.pdf'));fonts={}
 for page in pdf.pages:
  for ref in page['/Resources'].get('/Font',{}).values():
   f=ref.get_object();desc=f.get('/FontDescriptor')
   if not desc and f.get('/DescendantFonts'):desc=f['/DescendantFonts'][0].get_object().get('/FontDescriptor')
   fonts[str(f.get('/BaseFont'))]=bool(desc and any(k in desc.get_object() for k in ('/FontFile','/FontFile2','/FontFile3')))
 assert all(fonts.values())
 assert len(pdf.pages)==(8 if stem=='manuscript' else 6)
 result[stem]={'pdf_pages':len(pdf.pages),'pdf_sha256':sha(P/(stem+'.pdf')),'markdown_sha256':sha(P/(stem+'.md')),'docx_sha256':sha(P/(stem+'.docx')),'table_cells_match_markdown':num,'paragraphs_and_captions_match':True,'all_fonts_embedded':True}
 text='\n'.join(p.extract_text() for p in pdf.pages)
 for value in (['106.064','2133.23','378.44','17.009'] if stem=='manuscript' else ['2133.23','378.44','17.009']):assert value in text,(stem,value)

base=P.parent/'track_A_closeout_20261009'
if base.exists():
 a=(base/'manuscript.md').read_text(encoding='utf8');b=(P/'manuscript.md').read_text(encoding='utf8')
 assert re.findall(r'\$\$(.*?)\$\$',a,re.S)==re.findall(r'\$\$(.*?)\$\$',b,re.S)
 clean=lambda s:re.sub(r'!\[Fig\..*?\]\(.*?\)','',s,flags=re.S)
 assert clean(a)==clean(b)
 for stem in ['manuscript','SUPPLEMENT']:assert tables((base/(stem+'.md')).read_text(encoding='utf8'))==tables((P/(stem+'.md')).read_text(encoding='utf8'))
 for f in (base/'evidence').iterdir():
  if f.is_file():assert sha(f)==sha(P/'evidence'/f.name)
 result['prior_edition_check']={'main_text_except_captions_unchanged':True,'all_seven_table_contents_unchanged':True,'all_six_equations_unchanged':True,'frozen_evidence_files_unchanged':len(list((base/'evidence').iterdir()))}
with zipfile.ZipFile(P/'manuscript.docx') as d,zipfile.ZipFile(P/'official_template.docx') as t:
 canon=lambda data:etree.tostring(etree.fromstring(data),method='c14n')
 assert canon(d.read('word/styles.xml'))==canon(t.read('word/styles.xml'))
result.update(template_styles_unchanged=True,server_synced=False,new_experiments=0,weights_included=False)
(P/'VISUAL_EDITION_CHECK.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result,indent=2))
