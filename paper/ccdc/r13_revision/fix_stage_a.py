from pathlib import Path
p=Path(__file__).parent
s=(p/'plot_r13.py').read_text(encoding='utf8').replace("title=f'(a) {\"Unique L failure\" if \"pressure\" in sid else \"Adverse: S15 adds 308 s\"}; circles/square at {sync}s'", "title=f'(a) {\"Unique L failure\" if \"pressure\" in sid else \"S15 adds 308 s\"} — markers: {sync}s'")
s=s.replace("'font.size':8", "'font.size':8,'axes.titlesize':8")
(p/'plot_r13.py').write_text(s,encoding='utf8')
s=(p/'manuscript.md').read_text(encoding='utf8')
# Printed numbering follows first appearance, filenames remain stable.
for a,b in [('Fig. 5.','Fig. @3.'),('Fig. 6.','Fig. @4.'),('Fig. 3.','Fig. @5.'),('Fig. 4.','Fig. @6.'),('Fig. 6','Fig. @4'),('Figs. 5–6','Figs. 3–4'),('Figure 3','Figure @5'),('Figure 4','Figure @6')]:s=s.replace(a,b)
s=s.replace('@','').replace('c_{j,t} over','cⱼ,ₜ over').replace('D_j=','Dⱼ=').replace('D_j is','Dⱼ is').replace('K_γ','Kγ').replace('m_real','m_real')
s=s.replace(' Figure 5 shows the navigation-cost tail and actual worst dynamic margin without a redundant constant-completion panel.', ' Figure 5 shows the cost tail and worst actual margin.')
(p/'manuscript.md').write_text(s,encoding='utf8')
m=(p/'math_docx.py').read_text(encoding='utf8').replace("par(sub(mi('e'),mi('i')))","par(row(sub(mi('e'),mi('i')),par(mi('w'))))")
(p/'math_docx.py').write_text(m,encoding='utf8')
(p/'VENUE_CHECK.md').write_text('# Official requirements checked 2026-10-07\n\nhttps://www.ccdc.neu.edu.cn/firstSubmit/list.htm official CCDC2027 page retrieved via web search: initial submission allows8pages including figures. Final wording mentions6pages plus excess-page charges; confirm final rules separately. Earlier CCDC2026 final pages not silently applied. Anonymity/AI-specific policy not established from this page. Supplied Word template retained.\n',encoding='utf8')
