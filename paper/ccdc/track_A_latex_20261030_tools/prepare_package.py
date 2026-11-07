from pathlib import Path
import shutil, re, runpy, json, hashlib

ROOT=Path(__file__).resolve().parent
SRC=ROOT.parent/'track_A_closeout_20261013'
STAGE=ROOT/'source_markdown'
STAGE.mkdir(exist_ok=True)
for name in ['manuscript.md','SUPPLEMENT.md']:
    shutil.copy2(SRC/name,STAGE/name)
(STAGE/'latex').mkdir(exist_ok=True)
shutil.copy2(ROOT.parent/'track_A_closeout_20261009/latex/IEEEtran.cls',STAGE/'latex/IEEEtran.cls')
shutil.copytree(SRC/'figures',STAGE/'figures',dirs_exist_ok=True)
converter=(SRC/'convert_to_latex.py').read_text(encoding='utf-8').replace('R13 content-preserving','20261013 closeout content-preserving')
(STAGE/'convert_to_latex.py').write_text(converter,encoding='utf-8')
ns=runpy.run_path(str(STAGE/'convert_to_latex.py'))
for name in ['main.tex','IEEEtran.cls','conversion_check.json']:
    shutil.copy2(STAGE/'latex'/name,ROOT/name)
shutil.copytree(SRC/'figures',ROOT/'figures',dirs_exist_ok=True)
main=(ROOT/'main.tex').read_text(encoding='utf-8')
# Preserve visible indentation in the original pseudocode.
algorithm=re.search(r'```text\n(.*?)\n```',(SRC/'manuscript.md').read_text(encoding='utf-8'),re.S).group(1).splitlines()
body=[]
for line in algorithm:
    indent=len(line)-len(line.lstrip())
    body.append(r'\noindent\hspace*{'+str(indent*.38)+r'em}'+ns['txt'](line.lstrip())+r'\par')
replacement='\\begin{quote}\\small\n'+'\n'.join(body)+'\n\\end{quote}'
main=re.sub(r'\\begin\{quote\}.*?\\end\{quote\}',lambda _:replacement,main,flags=re.S)
(ROOT/'main.tex').write_text(main,encoding='utf-8')

# Supplement references refer to the main paper; keep their literal numbering.
special=ns['special']; umap=ns['unicode_map']
umap.update({'·':r'\ensuremath{\cdot}','τ':r'\ensuremath{\tau}','ᵀ':r'\ensuremath{^{\mathsf T}}','≠':r'\ensuremath{\ne}',
             '→':r'\ensuremath{\to}','π':r'\ensuremath{\pi}',
             '⁻':r'\ensuremath{^{-}}','⁹':r'\ensuremath{^9}',
             '₂':r'\ensuremath{_2}','₊':r'\ensuremath{_+}',
             '₁':r'\ensuremath{_1}'})
def txt(s):
    stash=[]
    def keep(value):
        stash.append(value); return 'ZZKEEP'+str(len(stash)-1)+'ZZ'
    s=re.sub(r'`([^`]+)`',lambda m:keep(r'\path|'+m[1]+'|'),s)
    replacements=[('p̂',r'\ensuremath{\hat p}'),('q̂',r'\ensuremath{\hat q}'),('M̂',r'\ensuremath{\widehat M}'),('m̂',r'\ensuremath{\hat m}'),('s̄',r'\ensuremath{\bar s}'),('⁻¹²',r'\ensuremath{^{-12}}'),('⁻³',r'\ensuremath{^{-3}}'),('⁻¹',r'\ensuremath{^{-1}}')]
    for a,b in replacements:s=s.replace(a,keep(b))
    # Long source paths may wrap while their exact identifiers remain unchanged.
    s=re.sub(r'(?<![\w/])(?:[\w.-]+/)+[\w.()-]+',lambda m:keep(r'\path|'+m[0]+'|'),s,flags=re.ASCII)
    s=''.join(special.get(c,umap.get(c,c)) for c in s)
    for i,v in enumerate(stash):s=s.replace('ZZKEEP'+str(i)+'ZZ',v)
    return s
out=[r'''% Supplement accompanying the unchanged 20261013 closeout manuscript.
\documentclass[11pt,a4paper]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[margin=22mm]{geometry}
\usepackage{amsmath,amssymb,textcomp,array,longtable,url}
\urlstyle{tt}
\setlength{\emergencystretch}{3em}
\setlength{\parindent}{0pt}
\setlength{\parskip}{6pt}
\renewcommand{\thetable}{S\arabic{table}}
\begin{document}
''']
caption=''; tables=0; sections=0
for b in (SRC/'SUPPLEMENT.md').read_text(encoding='utf-8').strip().split('\n\n'):
    b=b.strip()
    if not b:continue
    if b.startswith('# '):out.append(r'\begin{center}\Large\bfseries '+txt(b[2:])+r'\end{center}')
    elif b.startswith('### '):out.append(r'\subsection*{'+txt(b[4:])+'}')
    elif b.startswith('## '):sections+=1;out.append(r'\section*{'+txt(b[3:])+'}')
    elif re.match(r'Table S\d+\.',b):caption=re.sub(r'^Table S\d+\.\s*','',b)
    elif b.startswith('|'):
        rows=[[c.strip() for c in l.strip('|').split('|')] for l in b.splitlines() if not re.match(r'^\|[-: |]+\|$',l)]
        n=len(rows[0]); widths={3:[.12,.55,.33],6:[.38,.10,.13,.13,.13,.13],5:[.10,.34,.19,.20,.17],4:[.16,.43,.15,.26]}[n]
        spec='@{}'+''.join(r'>{\raggedright\arraybackslash}p{\dimexpr '+str(w)+r'\linewidth-'+str((n-1)*8/n)+r'pt\relax}' for w in widths)+'@{}'
        lines=[' & '.join(txt(c) for c in row)+r' \\' for row in rows]
        out.append(r'\begingroup\small\setlength{\tabcolsep}{4pt}'+ '\n'+r'\begin{longtable}{'+spec+'}\n'+r'\caption{'+txt(caption)+r'}\\'+'\n\\hline\n'+lines[0]+'\n\\hline\\endfirsthead\n'+lines[0]+'\n\\hline\\endhead\n'+'\n'.join(lines[1:])+'\n\\hline\n'+r'\end{longtable}\endgroup')
        tables+=1
    else:out.append(txt(b))
out.append(r'\end{document}')
supp='\n\n'.join(out)
unknown=sorted(set(c for c in supp if ord(c)>127))
assert not unknown,repr(unknown)
assert tables==4 and sections==14
(ROOT/'supplement.tex').write_text(supp,encoding='utf-8')
for directory in ['evidence','provenance']:
    shutil.copytree(SRC/directory,ROOT/directory,dirs_exist_ok=True)
for name in ['check_paired_times.py','PAIRED_TIME_CHECK.json','plot_data.json','plot_figures.py','draw_interface.py','requirements-editorial.txt','AUTHOR_CHECKLIST_ZH.md','CLOSEOUT_RESPONSE.md']:
    shutil.copy2(SRC/name,ROOT/name)
(ROOT/'reference_word_edition').mkdir(exist_ok=True)
for name in ['manuscript.pdf','SUPPLEMENT.pdf','manuscript.docx','SUPPLEMENT.docx']:
    shutil.copy2(SRC/name,ROOT/'reference_word_edition'/name)
# Remove only generated duplicate staging folders inside this new package.
shutil.rmtree(STAGE/'latex');shutil.rmtree(STAGE/'figures')
(STAGE/'convert_to_latex.py').unlink()
print('Prepared',ROOT)


