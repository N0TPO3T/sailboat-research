from pathlib import Path
p=Path(__file__).parent;f=p/'math_docx.py';s=f.read_text(encoding='utf8').replace(' return root', ''' for lim in root.findall('.//m:limLow',ns):
  spacer=E.Element(Q('r'));t=E.SubElement(spacer,Q('t'));t.set('{http://www.w3.org/XML/1998/namespace}space','preserve');t.text='  ';lim.addnext(spacer)
 return root''');f.write_text(s,encoding='utf8')
