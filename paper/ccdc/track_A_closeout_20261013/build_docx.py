"""Populate the supplied CCDC Word template; export PDF with Microsoft Word."""
from pathlib import Path
from copy import deepcopy
import re, hashlib, sys
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_TAB_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION_START
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from math_docx import mathparts,to_omml
P=Path(__file__).resolve().parent
SUPP = '--supplement' in sys.argv
STEM = 'SUPPLEMENT' if SUPP else 'manuscript'
d=Document(P/'official_template.docx')
title_section=deepcopy(d.sections[0]._sectPr)
main_section=deepcopy(d.sections[3]._sectPr)
body=d._element.body
for x in list(body): body.remove(x)
body.append(main_section)
if SUPP:
 main_section.find(qn('w:cols')).set(qn('w:num'),'1')

def columns(n):
 section=d.add_section(WD_SECTION_START.CONTINUOUS)
 cols=section._sectPr.find(qn('w:cols'))
 for child in list(cols):cols.remove(child)
 cols.set(qn('w:num'),str(n));cols.set(qn('w:equalWidth'),'1')

def format_table(table):
 pr=table._tbl.tblPr
 borders=OxmlElement('w:tblBorders')
 for name in ['top','left','bottom','right','insideH','insideV']:
  el=OxmlElement('w:'+name);el.set(qn('w:val'),'single');el.set(qn('w:sz'),'4');el.set(qn('w:color'),'D9D9D9');borders.append(el)
 pr.append(borders)
 for ri,row in enumerate(table.rows):
  if ri==0:
   repeat=OxmlElement('w:tblHeader');row._tr.get_or_add_trPr().append(repeat)
  no_split=OxmlElement('w:cantSplit');row._tr.get_or_add_trPr().append(no_split)
  for ci,c in enumerate(row.cells):
   c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
   if ri==0:
    fill=OxmlElement('w:shd');fill.set(qn('w:fill'),'EDF3F8');c._tc.get_or_add_tcPr().append(fill)
   for p in c.paragraphs:
    p.paragraph_format.first_line_indent=Inches(0)
    p.alignment=WD_ALIGN_PARAGRAPH.LEFT if (ci==0 or SUPP) else WD_ALIGN_PARAGRAPH.CENTER
def nonum(p):
 n=OxmlElement('w:numPr'); i=OxmlElement('w:numId'); i.set(qn('w:val'),'0'); n.append(i);p._p.get_or_add_pPr().append(n)
def para(txt,style='Body Text',keep=False):
 p=d.add_paragraph(style=style);nonum(p)
 for i,t in enumerate(re.split(r'(\*\*.*?\*\*)',txt)):
  bold=t.startswith('**');t=t[2:-2] if bold else t
  symbols={'m_real':('m','real'),'O_t':('O','t'),'D_j':('D','j'),'f_z':('f','z'),'r_max':('r','max'),'Kγ':('K','γ')}
  for piece in re.split('('+'|'.join(map(re.escape,symbols))+')',t):
   if piece in symbols:
    a,b=symbols[piece];r=p.add_run(a);r.italic=True;r=p.add_run(b);r.font.subscript=True
   else:r=p.add_run(piece)
   if bold:r.bold=True
 p.paragraph_format.keep_with_next=keep
 return p
def eq(key):
 for i,line in enumerate(mathparts()[key]):
  p=para('',keep=i<len(mathparts()[key])-1);p.paragraph_format.first_line_indent=Inches(0);p.paragraph_format.space_before=Pt(3);p.paragraph_format.space_after=Pt(3)
  p._p.append(to_omml(line))
  if i==len(mathparts()[key])-1:
   p.paragraph_format.tab_stops.add_tab_stop(Inches(3.36),WD_TAB_ALIGNMENT.RIGHT)
   p.add_run('\t('+key[2:]+')')
blocks=(P/(STEM+'.md')).read_text(encoding='utf8').strip().split('\n\n');eidx=0;next_abstract=False
if not SUPP:
 # Place the full-width method overview immediately before Section III.
 # Markdown retains its logical position within III-A; text and caption are identical.
 fig1=next(b for b in blocks if b.startswith('![Fig. 1.'))
 blocks.remove(fig1)
 blocks.insert(next(i for i,b in enumerate(blocks) if b.startswith('## III.')),fig1)
for b in blocks:
 b=b.strip()
 if not b:continue
 if b.startswith('# '):para(b[2:],'paper title',True)
 elif b.startswith('Authors:'):
  p=para('','Author',True)
  for i,(name,n) in enumerate([('Sheng Huang','1'),('Chao Yang','1'),('Buyu Guo','2')]):
   if i:p.add_run(', ')
   p.add_run(name);p.add_run(n).font.superscript=True
 elif b.startswith('Affiliations:'):
  for text in ['1. Institute of Physical Oceanography and Remote Sensing,','Ocean College, Zhejiang University, Zhoushan, China','2. Donghai Laboratory, Zhoushan, China']:
   para(text,'Affiliation',True)
  p=d.add_paragraph();p._p.get_or_add_pPr().append(title_section)
 elif b=='## Abstract':next_abstract=True;continue
 elif next_abstract:para('Abstract—'+b,'Abstract');next_abstract=False
 elif b.startswith('Keywords:'):para(b,'Keywords')
 elif b.startswith('### '):para(b[4:],'Heading 2',True)
 elif b.startswith('## '):para(b[3:],'Heading 1',True)
 elif b.startswith('$$'):eidx+=1;eq('EQ'+str(eidx))
 elif b.startswith('!['):
  cap,fn=re.match(r'!\[(.*?)\]\((.*?)\)',b,re.S).groups()
  wide='figure1_interface' in fn
  if wide:columns(1)
  p=d.add_paragraph();p.paragraph_format.keep_with_next=True;p.paragraph_format.first_line_indent=Inches(0);p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.add_run().add_picture(str(P/fn),width=Inches(6.98 if wide else 3.37))
  para(cap,'figure caption')
  if wide:columns(2)
 elif re.match(r'^Table (?:[IVX]+|S\d+)\.',b):para(b,'table head',True)
 elif b.startswith('|'):
  rows=[x for x in b.splitlines() if not re.match(r'^\|[-:| ]+\|$',x)]
  vals=[[z.strip() for z in row.strip('|').split('|')] for row in rows]
  table=d.add_table(rows=0,cols=len(vals[0]));table.autofit=False
  widths=([1.18,.48,.4,.4,.4,.4] if len(vals[0])==6 else ([1.48,.4,.48,.48,.48] if len(vals[0])==5 else ([.45,.60,1.10,1.17] if vals[0][0].startswith('ρ') else [1.20,.70,.70,.72])))
  if SUPP:
   widths={3:[.55,3.75,2.68],4:[1.0,3.1,1.1,1.78],5:[.65,2.75,1.25,1.3,1.03],6:[2.4,.8,.9,.96,.96,.96]}[len(vals[0])]
  for col,w in zip(table.columns,widths):col.width=Inches(w)
  for ri,row in enumerate(vals):
   cells=table.add_row().cells
   for c,w,txt in zip(cells,widths,row):
    c.width=Inches(w);p=c.paragraphs[0];p.paragraph_format.space_after=Pt(2);p.paragraph_format.space_before=Pt(2)
    p.paragraph_format.keep_with_next=ri<len(vals)-1
    r=p.add_run(txt);r.font.name='Times New Roman';r.font.size=Pt(9 if SUPP else 8);r.bold=ri==0
  format_table(table)
  d.add_paragraph().paragraph_format.space_after=Pt(0)
 elif b.startswith('```'):
  for line in b.splitlines()[1:-1]:
   indent=len(line)-len(line.lstrip()); p=para(line.lstrip(),keep=True); p.paragraph_format.first_line_indent=Inches(0); p.paragraph_format.left_indent=Inches(.12 if indent else 0); p.paragraph_format.space_after=Pt(1); p.paragraph_format.keep_together=True
   if line.startswith('Algorithm'):p.runs[0].bold=True
 elif re.match(r'^\[\d+\]',b):
  p=para(b,'references');p.paragraph_format.keep_together=True
 else:para(b)
d.core_properties.title=blocks[0][2:]
d.core_properties.author='Sheng Huang; Chao Yang; Buyu Guo'
d.core_properties.subject='CCDC 2027 Track A closeout manuscript'
d.core_properties.keywords='autonomous sailing; reference protocol; closed-loop prediction'
d.save(P/(STEM+'.docx'))
print('Saved',P/(STEM+'.docx'))
