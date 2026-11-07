"""Regenerate scientific plots from frozen data, with grayscale-safe encodings."""
from pathlib import Path
P=Path(__file__).resolve().parent
s=(P.parent/'r13_revision/plot_r13.py').read_text(encoding='utf8')
s=s.replace('import json,csv,numpy as np','import sys,zipfile\nsys.path.insert(0,str(Path(__file__).resolve().parent/".tools/python"))\nimport json,csv,numpy as np')
s=s.replace("ROOT=Path.cwd(); R=ROOT/'runs/r12_revision_20261006'; O=ROOT/'paper/ccdc/r13_revision'; (O/'figures').mkdir(exist_ok=True,parents=True);(O/'evidence').mkdir(exist_ok=True)","O=Path(__file__).resolve().parent; R=O/'evidence'; (O/'figures').mkdir(exist_ok=True,parents=True)")
s=s.replace("data={(s,v):json.loads((R/'confirmation'/(s+'__'+v)/'trace.json').read_text()) for s in ids for v in C}","with zipfile.ZipFile(O.parent/'r13_revision/R13_REPRODUCTION_internal.zip') as z:\n traces=[json.loads(z.read(n)) for n in z.namelist() if n.endswith('trace.json')]\ndata={(d['row']['scene_id'],d['row']['variant']):d for d in traces}\nMARK={'reactive':'s','simple':'^','sampled':'o'}\nSTYLE={'reactive':':','simple':'--','sampled':'-'}")
s=s.replace("s=12,c=C[v],label=L[v]","s=16,c=C[v],marker=MARK[v],label=L[v]")
s=s.replace("s=11,c=C[v],label=L[v]","s=15,c=C[v],marker=MARK[v],label=L[v]")
s=s.replace("ms=4,c=C[v],label=L[v] if k==0 else None","ms=4,c=C[v],mfc=C[v] if v=='sampled' else 'white',mew=.8,label=L[v] if k==0 else None")
s=s.replace("ms=4,c=C[v])","ms=4,c=C[v],mfc=C[v] if v=='sampled' else 'white',mew=.8)")
s=s.replace("xlabel='Snapshot ID (protocols in supplement)',xticks=range(1,7)","xlabel='Snapshot and circle / triangle protocols',xticks=range(1,7),xticklabels=['1\\n-90/N','2\\nC/N','3\\n+45/N','4\\nN/C','5\\nN/C','6\\n-90/N']")
s=s.replace("ax[0].set(yscale='log'","ax[1].tick_params(axis='x',labelsize=6.2)\nax[0].set(yscale='log'")
s=s.replace("c=C[v],lw=.9,label=", "c=C[v],ls=STYLE[v],lw=1.15,label=")
s=s.replace("ax[1].plot(tt,mm,c=C[v],lw=.85)","ax[1].plot(tt,mm,c=C[v],ls=STYLE[v],lw=1.15)")
s=s.split('# Same physical/history state')[0]
s+='\nprint("Regenerated five data figures from frozen traces; no experiments.")\n'
(P/'plot_revision.py').write_text(s,encoding='utf8')
