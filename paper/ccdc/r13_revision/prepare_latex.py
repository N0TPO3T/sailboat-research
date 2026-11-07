from pathlib import Path
p=Path(__file__).parent
f=p/'convert_to_latex.py';s=f.read_text(encoding='utf8')
s=s.replace("s=(P/'manuscript.md')", "(O/'figures').mkdir(parents=True,exist_ok=True)\ns=(P/'manuscript.md')")
s=s.replace('R12 content-preserving','R13 content-preserving').replace("elif eq==3:e=", "elif eq==4:e=").replace("elif eq==5:e=", "elif eq==6:e=")
s=s.replace('c_t&=', 'c_{j,t}&=').replace(r'\|-85\,\mathrm{m}',r'\|-D_j')
s=s.replace('assert eq==5 and tc==3 and bib','assert eq==6 and tc==2 and bib').replace("'figures':5", "'figures':6")
s=s.replace("('m̂',", "('m_real',r'$m^{\\rm real}$'),('Dⱼ',r'$D_j$'),('cⱼ,ₜ',r'$c_{j,t}$'),('ĉ',r'$\\hat c$'),('r̄',r'$\\bar r$'),('Kγ',r'$K_\\gamma$'),('O_t',r'$\\mathcal O_t$'),('D_j',r'$D_j$'),('⁹',r'$^9$'),('∞',r'$\\infty$'),('○','o'),('×',r'$\\times$'),('m̂',")
s=s.replace("('⁻¹²',", "('⁻⁹',r'$^{-9}$'),('⁻¹²',")
s=s.replace("else [.15,.17,.30,.38]", "else [.34,.22,.22,.22]")
s=s.replace("out.append('\\\\\\n'.join(txt(x) for x in lines[1:])+ '\\n'+r'\\end{quote}')", "out.append((' '+chr(92)*2+'\\n').join(txt(x) for x in lines[1:])+ '\\n'+r'\\end{quote}')")
f.write_text(s,encoding='utf8')
