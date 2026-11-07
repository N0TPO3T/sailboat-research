from pathlib import Path
import hashlib,json,difflib,zipfile,re
p=Path(__file__).parent
old=(p.parent/'r12_revision/manuscript.md').read_text(encoding='utf8').splitlines(True);new=(p/'manuscript.md').read_text(encoding='utf8').splitlines(True)
(p/'R12_TO_R13.diff').write_text(''.join(difflib.unified_diff(old,new,fromfile='R12/manuscript.md',tofile='R13/manuscript.md')),encoding='utf8')
t=(p/'latex/main.tex').read_text(encoding='utf8');defined=set(re.findall(r'\\label\{([^}]+)\}',t));refs=set(re.findall(r'\\ref\{([^}]+)\}',t));assert refs<=defined,(refs-defined);assert t.count('\\begin{equation}')==6;assert '\\[2pt]' not in t.replace('\\\\[2pt]','')
meta=json.loads((p/'latex/conversion_check.json').read_text());assert meta['source_blocks']==meta['processed_blocks'];meta['unresolved_refs']=list(refs-defined);meta['latex_compiled']=False;meta['native_compile_error']='Unable to find standard directories for platform';(p/'latex/conversion_check.json').write_text(json.dumps(meta,indent=2))
with zipfile.ZipFile(p/'R13_LaTeX.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in (p/'latex').rglob('*'):
  if f.is_file():z.write(f,f.relative_to(p/'latex'))
(p/'LAYOUT_CHECK.json').write_text(json.dumps(dict(actual_pdf='manuscript.pdf',engine='Microsoft Word 2019',pages=8,all_pages_visually_inspected=True,template_font_not_reduced=True,math_fix='native OMML accents and minimum lower limits; restricted M/Mhat domain',pdf_sha256=hashlib.sha256((p/'manuscript.pdf').read_bytes()).hexdigest(),latex_compile_success=False),indent=2))
print('diff, static TeX checks and editable archive ready')
