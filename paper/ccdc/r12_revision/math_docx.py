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
 eq1=[row(sub(mi('c'),mi('t')),mo('='),norm(row(rt,mo('+'),alpha,mi('d'))),mo('−'),mn(85),text(' m')),
      row(alpha,mo('='),sub(mi('clip'),text('[0,1]')),par(row(mo('−'),frac(row(sup(rt,mi('T')),mi('d')),sup(norm(mi('d')),mn(2))))),text(' for d≠0.'))]
 residual=row(sub(mi('f'),mi('z')),par(row(sub(bar(mi('s')),mi('i')),mo(','),mi('w'))),mo('−'),frac(row(sub(mi('z'),row(mi('i'),mo('+'),mn(1))),mo('−'),sub(mi('z'),mi('i'))),dt))
 eq2=[row(sub(mi('ℒ'),mi('t')),par(mi('w')),mo('='),sub(mo('∑'),row(mi('i'),mo('∈'),sub(mi('I'),mi('t')))),sup(norm(row(mi('D'),par(sub(mi('e'),mi('i'))))),mn(2))),row(sub(mi('e'),mi('i')),mo('='),residual)]
 eq3=[row(mi('J'),par(mi('γ')),mo('='),sub(mi('d'),mi('G')),par(mi('γ')),mo('+'),mn(20),sub(mn(1),row(mi('γ'),mo('≠'),mi('n'))),mo('+'),mn(10),sub(mn(1),row(mi('γ'),mo('∈'),text('side')))),row(sub(mi('d'),mi('G')),par(mi('γ')),mo('='),norm(row(sup(hat(mi('p')),mi('γ')),par(sub(mi('K'),mi('γ'))),mo('−'),mi('G'))),text(' [m].'))]
 eq4=[row(mo('|'),sup(mi('m'),text('real')),mo('−'),hat(mi('m')),mo('|'),mo('≤'),mi('E'),mo(','),text('   '),sup(mi('m'),text('real')),mo('≥'),hat(mi('m')),mo('−'),mi('E'))]
 cmd=bar(rk);alphaweight=row(mn(1),mo('−'),sup(mi('e'),row(mo('−'),frac(dt,mi('τ')))))
 eq5=[row(cmd,mo('='),mi('clip'),par(row(mi('κ'),sub(mi('e'),mi('k')),mo(','),mo('−'),sub(mi('r'),text('max')),mo(','),sub(mi('r'),text('max'))))),row(rn,mo('='),rk,mo('+'),par(alphaweight),par(row(cmd,mo('−'),rk))),row(sub(mi('χ'),row(mi('k'),mo('+'),mn(1))),mo('='),sub(mi('χ'),mi('k')),mo('+'),dt,rn)]
 return {f'EQ{i+1}':x for i,x in enumerate([eq1,eq2,eq3,eq4,eq5])}
def to_omml(src):
 path='C:/Program Files/Microsoft Office/root/Office16/MML2OMML.XSL'
 transform=E.XSLT(E.parse(path))
 return transform(E.fromstring(('<math xmlns="http://www.w3.org/1998/Math/MathML">'+src+'</math>').encode())).getroot()
