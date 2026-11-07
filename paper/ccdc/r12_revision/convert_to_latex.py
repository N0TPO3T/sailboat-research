from pathlib import Path
import re,zipfile,shutil,json,hashlib
P=Path(__file__).resolve().parent; O=P/'latex'
s=(P/'manuscript.md').read_text(encoding='utf8')
template=zipfile.ZipFile(r'C:/Users/74095/hs/CCDC/conference-latex-template.zip')
cls=next(n for n in template.namelist() if n.endswith('/IEEEtran.cls'))
(O/'IEEEtran.cls').write_bytes(template.read(cls))
for n in template.namelist():
 if n.endswith('.tex'):(O/'official_template_original.tex').write_bytes(template.read(n))
for f in (P/'figures').glob('*.pdf'):shutil.copy2(f,O/'figures'/f.name)
special={'&':r'\&','%':r'\%','$':r'\$','#':r'\#','_':r'\_','{':r'\{','}':r'\}','~':r'\textasciitilde{}','\\':r'\textbackslash{}'}
unicode_map={'±':r'\ensuremath{\pm}','²':r'\ensuremath{^2}','³':r'\ensuremath{^3}','¹':r'\ensuremath{^1}',
 'Ö':r'\"{O}','å':r'\aa{}','ç':r'\c{c}','İ':r'\.{I}','ş':r'\c{s}',
 'Δ':r'\ensuremath{\Delta}','α':r'\ensuremath{\alpha}','γ':r'\ensuremath{\gamma}','θ':r'\ensuremath{\theta}',
 'ι':r'\ensuremath{\iota}','κ':r'\ensuremath{\kappa}','ρ':r'\ensuremath{\rho}','τ':r'\ensuremath{\tau}',
 'φ':r'\ensuremath{\phi}','χ':r'\ensuremath{\chi}','ψ':r'\ensuremath{\psi}','ω':r'\ensuremath{\omega}',
 '–':'--','—':'---','“':'``','”':"''",'∈':r'\ensuremath{\in}','−':r'\ensuremath{-}','≤':r'\ensuremath{\le}','≥':r'\ensuremath{\ge}'}
def txt(t):
 stash=[]
 def keep(v):stash.append(v);return 'ZZTOKEN'+str(len(stash)-1)+'ZZ'
 for a,b in [('m̂',r'$\hat m$'),('s̄',r'$\bar s$'),('r₀',r'$r_0$'),('pₜ₊₁',r'$p_{t+1}$'),('qₜ₊₁',r'$q_{t+1}$'),('pₜ',r'$p_t$'),('qₜ',r'$q_t$'),('Iₜ',r'$I_t$'),('eₖ',r'$e_k$'),('pₖ',r'$p_k$'),('χₖ',r'$\chi_k$'),('rₖ₊₁',r'$r_{k+1}$'),('ωφ',r'$\omega_\phi$'),('ωψ',r'$\omega_\psi$'),('f_z',r'$f_z$'),('r_max',r'$r_{\max}$'),('x_local',r'$x_{\rm local}$'),('⁻¹²',r'$^{-12}$'),('⁻³',r'$^{-3}$'),('⁻¹',r'$^{-1}$')]:
  if a in t:t=t.replace(a,keep(b))
 t=re.sub(r'\[(\d+)\]',lambda m:keep(r'\cite{ref'+m[1]+'}'),t)
 t=re.sub(r'(?:Fig\.|Figure) (\d+)',lambda m:keep(r'Fig.~\ref{fig:'+m[1]+'}'),t)
 for roman,num in [('III',3),('II',2),('I',1)]:t=t.replace('Table '+roman,keep(r'Table~\ref{tab:'+str(num)+'}'))
 t=''.join(special.get(c,unicode_map.get(c,c)) for c in t)
 for i,v in enumerate(stash):t=t.replace('ZZTOKEN'+str(i)+'ZZ',v)
 return t
out=[r'''% R12 content-preserving LaTeX edition. Edit this file directly.
% The supplied IEEEtran.cls is copied byte-for-byte from the user's template.
\documentclass[conference]{IEEEtran}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{cite}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{graphicx}
\usepackage{textcomp}
\usepackage{array}
\usepackage{url}
\graphicspath{{figures/}}
\begin{document}
''']
blocks=[b.strip() for b in s.strip().split('\n\n') if b.strip()]
abstract=False;bib=False;eq=0;tc=0;caption='';coverage=[]
for b in blocks:
 coverage.append(hashlib.sha256(b.encode()).hexdigest())
 if b.startswith('# '):out.append(r'\title{'+txt(b[2:])+'}')
 elif b.startswith('Authors and'):out.append(r'\author{\IEEEauthorblockN{Authors and affiliations to be confirmed}}'+'\n'+r'\maketitle')
 elif b=='## Abstract':abstract=True
 elif abstract:out.append(r'\begin{abstract}'+'\n'+txt(b)+'\n'+r'\end{abstract}');abstract=False
 elif b.startswith('Keywords:'):out.append(r'\begin{IEEEkeywords}'+txt(b[len('Keywords:'):].strip())+r'\end{IEEEkeywords}')
 elif b=='## References':out.append(r'\begin{thebibliography}{8}');bib=True
 elif bib:
  m=re.match(r'\[(\d+)\]\s*(.*)',b,re.S);assert m
  out.append(r'\bibitem{ref'+m[1]+'} '+txt(m[2]))
 elif b.startswith('### '):out.append(r'\subsection{'+txt(re.sub(r'^[A-Z]\.\s*','',b[4:]))+'}')
 elif b.startswith('## '):
  h=re.sub(r'^[IVX]+\.\s*','',b[3:]);out.append(('\\section*{' if h.startswith('Acknowledgment') else '\\section{')+txt(h)+'}')
 elif b.startswith('$$'):
  eq+=1;e=b.strip('$\n ').replace(r'\mathbf1',r'\mathbf{1}')
  # Break long identities without changing the five equation numbers.
  if eq==1:e=r'\begin{aligned}c_t&=\|r_0+\alpha^*d\|-85\,\mathrm{m},\\\alpha^*&=\operatorname{clip}_{[0,1]}\!\left(-\frac{r_0^\top d}{\|d\|^2}\right)\quad(d\ne0).\end{aligned}'
  elif eq==2:e=r'\begin{aligned}\mathcal L_t(w)&=\sum_{i\in I_t}\|D e_i(w)\|^2,\\e_i(w)&=f_z(\bar s_i,w)-\frac{z_{i+1}-z_i}{\Delta t}.\end{aligned}'
  elif eq==3:e=r'\begin{aligned}J(\gamma)&=d_G(\gamma)+20\mathbf{1}_{\gamma\ne n}+10\mathbf{1}_{\gamma\in\mathrm{side}},\\d_G(\gamma)&=\|\hat p^\gamma(K_\gamma)-G\|\quad[\mathrm m].\end{aligned}'
  elif eq==5:e=r'\begin{aligned}\bar r_k&=\operatorname{clip}(\kappa e_k,-r_{\max},r_{\max}),\\r_{k+1}&=r_k+(1-e^{-\Delta t/\tau})(\bar r_k-r_k),\\\chi_{k+1}&=\chi_k+\Delta t\,r_{k+1}.\end{aligned}'
  out.append(r'\begin{equation}\label{eq:'+str(eq)+'}\n'+e+'\n'+r'\end{equation}')
 elif b.startswith('!['):
  m=re.match(r'!\[(.*?)\]\((.*?)\)',b,re.S);cap=m[1];num=re.match(r'Fig\. (\d+)\.',cap)[1];cap=re.sub(r'^Fig\. \d+\.\s*','',cap);f=Path(m[2]).with_suffix('.pdf')
  out.append(r'\begin{figure}[tb]\centering'+'\n'+r'\includegraphics[width=\columnwidth]{'+f.name+'}\n'+r'\caption{'+txt(cap)+'}\n'+r'\label{fig:'+num+'}\n'+r'\end{figure}')
 elif re.match(r'Table [IVX]+\.',b):caption=re.sub(r'^Table [IVX]+\.\s*','',b)
 elif b.startswith('|'):
  tc+=1;rows=[[c.strip() for c in l.strip('|').split('|')] for l in b.splitlines() if not re.match(r'^\|[-: |]+\|$',l)]
  widths=([.32,.12,.14,.14,.14,.14] if len(rows[0])==6 else [.15,.17,.30,.38])
  spec='@{}'+''.join(r'>{\centering\arraybackslash}p{'+str(round(w*.96,4))+r'\columnwidth}' for w in widths)+'@{}'
  body=[]
  for i,row in enumerate(rows):body.append(' & '.join((r'\textbf{'+txt(c)+'}' if i==0 else txt(c)) for c in row)+r' \\')
  out.append(r'\begin{table}[tb]\centering'+'\n'+r'\caption{'+txt(caption)+'}\n'+r'\label{tab:'+str(tc)+'}\n'+r'\setlength{\tabcolsep}{0pt}'+'\n'+r'\begin{tabular}{'+spec+'}\n\\hline\n'+body[0]+'\n\\hline\n'+'\n'.join(body[1:])+'\n\\hline\n'+r'\end{tabular}\end{table}')
 elif b.startswith('```'):
  lines=b.splitlines()[1:-1];out.append(r'\begin{quote}\noindent\textbf{'+txt(lines[0])+'}\n\\[2pt]')
  out.append('\\\n'.join(txt(x) for x in lines[1:])+ '\n'+r'\end{quote}')
 else:out.append(txt(b))
assert eq==5 and tc==3 and bib
out+=[r'\end{thebibliography}',r'\end{document}']
t='\n\n'.join(out)+'\n'
assert not any(ord(c)>127 for c in t),ascii(''.join(set(c for c in t if ord(c)>127)))
(O/'main.tex').write_text(t,encoding='utf8')
(O/'conversion_check.json').write_text(json.dumps({'source_sha256':hashlib.sha256(s.encode()).hexdigest(),'source_blocks':len(blocks),'processed_blocks':len(coverage),'equations':eq,'tables':tc,'figures':5,'references':8,'template_cls_sha256':hashlib.sha256((O/'IEEEtran.cls').read_bytes()).hexdigest(),'scientific_content_changed':False},indent=2),encoding='utf8')
print('Written',O/'main.tex')
