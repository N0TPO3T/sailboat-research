"""Editable Office Math from explicit MathML; no rasterized formulas."""
from lxml import etree as E
from xml.sax.saxutils import escape
def mi(t):return '<mi>'+escape(t)+'</mi>'
def mo(t):return '<mo>'+escape(t)+'</mo>'
def mn(t):return '<mn>'+str(t)+'</mn>'
def row(*x):return '<mrow>'+''.join(x)+'</mrow>'
def sub(a,b):return '<msub>'+a+b+'</msub>'
def sup(a,b):return '<msup>'+a+b+'</msup>'
def frac(a,b):return '<mfrac>'+a+b+'</mfrac>'
def bar(a):return '<mover>'+a+mo('¯')+'</mover>'
def hat(a):return '<mover>'+a+mo('ˆ')+'</mover>'
def norm(a):return row(mo('‖'),a,mo('‖'))
def par(a):return row(mo('('),a,mo(')'))
def text(t):return '<mtext>'+escape(t)+'</mtext>'
def mathparts():
 rt=sub(mi('r'),mn(0));alpha=sup(mi('α'),mo('*'));dt=mi('Δt');rk=sub(mi('r'),mi('k'));rn=sub(mi('r'),row(mi('k'),mo('+'),mn(1)))
 eq1=[row(sub(mi('c'),row(mi('j'),mo(','),mi('t'))),mo('='),norm(row(rt,mo('+'),alpha,mi('d'))),mo('−'),sub(mi('D'),mi('j'))),
      row(alpha,mo('='),sub(mi('clip'),text('[0,1]')),par(row(mo('−'),frac(row(sup(rt,mi('T')),mi('d')),sup(norm(mi('d')),mn(2))))),text(' for d≠0.'))]
 residual=row(sub(mi('f'),mi('z')),par(row(sub(bar(mi('s')),mi('i')),mo(','),mi('w'))),mo('−'),frac(row(sub(mi('z'),row(mi('i'),mo('+'),mn(1))),mo('−'),sub(mi('z'),mi('i'))),dt))
 eq2=[row(sub(mi('ℒ'),mi('t')),par(mi('w')),mo('='),sub(mo('∑'),row(mi('i'),mo('∈'),sub(mi('I'),mi('t')))),sup(norm(row(mi('D'),par(row(sub(mi('e'),mi('i')),par(mi('w')))))),mn(2))),row(sub(mi('e'),mi('i')),par(mi('w')),mo('='),residual)]
 eq3=[row(mi('J'),par(mi('γ')),mo('='),sub(mi('d'),mi('G')),par(mi('γ')),mo('+'),mn(20),sub(mn(1),row(mi('γ'),mo('≠'),mi('n'))),mo('+'),mn(10),sub(mn(1),row(mi('γ'),mo('∈'),text('side')))),row(sub(mi('d'),mi('G')),par(mi('γ')),mo('='),norm(row(sup(hat(mi('p')),mi('γ')),par(sub(mi('K'),mi('γ'))),mo('−'),mi('G'))),text(' [m].'))]
 eq4=[row(mo('|'),mi('M'),mo('−'),hat(mi('M')),mo('|'),mo('≤'),mi('E'),mo(','),text('   '),mi('M'),mo('≥'),hat(mi('M')),mo('−'),mi('E'))]
 cmd=bar(rk);alphaweight=row(mn(1),mo('−'),sup(mi('e'),row(mo('−'),frac(dt,mi('τ')))))
 eq5=[row(cmd,mo('='),mi('clip'),par(row(mi('κ'),sub(mi('e'),mi('k')),mo(','),mo('−'),sub(mi('r'),text('max')),mo(','),sub(mi('r'),text('max'))))),row(rn,mo('='),rk,mo('+'),par(alphaweight),par(row(cmd,mo('−'),rk))),row(sub(mi('χ'),row(mi('k'),mo('+'),mn(1))),mo('='),sub(mi('χ'),mi('k')),mo('+'),dt,rn)]
 eqmin=[row(hat(mi('m')),par(mi('γ')),mo('='),sub(mi('min'),row(mi('j'),mo('∈'),sub(mi('O'),mi('t')))),sub(mi('min'),row(mn(0),mo('≤'),mi('k'),mo('<'),sub(mi('K'),mi('γ')))),sub(hat(mi('c')),row(mi('j'),mo(','),mi('k'))),par(mi('γ')))]
 return {f'EQ{i+1}':x for i,x in enumerate([eq1,eq2,eqmin,eq3,eq4,eq5])}
def to_omml(src):
 path='C:/Program Files/Microsoft Office/root/Office16/MML2OMML.XSL'
 transform=E.XSLT(E.parse(path))
 root=transform(E.fromstring(('<math xmlns="http://www.w3.org/1998/Math/MathML">'+src+'</math>').encode())).getroot()
 ns={'m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}; Q=lambda x:'{'+ns['m']+'}'+x
 for node in list(root.findall('.//m:limUpp',ns)):
  if ''.join(node.find('m:lim',ns).itertext())=='ˆ':
   acc=E.Element(Q('acc'));pr=E.SubElement(acc,Q('accPr'));ch=E.SubElement(pr,Q('chr'));ch.set(Q('val'),'̂');acc.append(node.find('m:e',ns));node.getparent().replace(node,acc)
 for node in list(root.findall('.//m:sSub',ns)):
  base=node.find('m:e',ns)
  if ''.join(base.itertext())=='min':
   lim=E.Element(Q('limLow'));lim.append(base);b=node.find('m:sub',ns);b.tag=Q('lim');lim.append(b);node.getparent().replace(node,lim)
 for lim in root.findall('.//m:limLow',ns):
  spacer=E.Element(Q('r'));t=E.SubElement(spacer,Q('t'));t.set('{http://www.w3.org/XML/1998/namespace}space','preserve');t.text='  ';lim.addnext(spacer)
 return root
