"""Portable browser overview of final figures and unchanged table contents."""
from pathlib import Path
import html,re
P=Path(__file__).resolve().parent
cards=[]
for stem in ['manuscript','SUPPLEMENT']:
 text=(P/(stem+'.md')).read_text(encoding='utf8')
 for cap,path in re.findall(r'!\[(.*?)\]\((.*?)\)',text):
  cards.append(f'<section><a href="{path}"><img src="{path}" alt="{html.escape(cap)}"></a><p>{html.escape(cap)}</p><p><a href="{path[:-3]}svg">SVG</a> · <a href="{path[:-3]}pdf">PDF</a></p></section>')
 for cap,rows in re.findall(r'(Table [^\n]+)\n\n(\|.*?)(?=\n\n|$)',text,re.S):
  content=[]
  for i,row in enumerate(rows.splitlines()):
   if re.match(r'^\|[-:| ]+\|$',row):continue
   tag='th' if i==0 else 'td'
   content.append('<tr>'+''.join(f'<{tag}>{html.escape(x.strip())}</{tag}>' for x in row.strip('|').split('|'))+'</tr>')
  cards.append('<section class="table"><h2>'+html.escape(cap)+'</h2><table>'+''.join(content)+'</table></section>')
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CCDC Track A — figures and tables</title><style>
body{font-family:Georgia,serif;color:#293746;background:#fafbfc;max-width:1200px;margin:40px auto;padding:0 24px;line-height:1.5}h1{font-size:28px}h2{font-size:18px}main{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}section{background:white;border:1px solid #dce1e4;padding:20px}section:first-child,.table{grid-column:1/-1}img{display:block;max-width:100%;max-height:800px;margin:auto}table{width:100%;border-collapse:collapse;font-size:15px}td,th{border:1px solid #d9d9d9;padding:8px;text-align:left}th{background:#edf3f8}a{color:#396c93}p{font-size:15px}@media(max-width:700px){main{display:block}section{margin:20px 0;overflow:auto}}
</style><h1>CCDC Track A — figures and tables</h1><p>Visual edition: 13 October 2026. Six figures and seven tables. Click each figure to view its full-resolution PNG. Numerical results are unchanged.</p><p><a href="manuscript.pdf">Main paper</a> · <a href="SUPPLEMENT.pdf">Supplement</a></p><main>'''+''.join(cards)+'</main></html>'
(P/'FIGURES.html').write_text(page,encoding='utf8')
assert len(cards)==13
