"""Paired efficiency on each pair's own common-safe set; no failed-stop speedup."""
import numpy as np

def paired(rows, methods=('normal','avoid','range','risk')):
    by={(r['seed'],r['mode']):r for r in rows}; seeds=sorted({r['seed'] for r in rows})
    out={}
    for ia,a in enumerate(methods):
        for b in methods[ia+1:]:
            common=[s for s in seeds if by[s,a]['safe_complete'] and by[s,b]['safe_complete']]
            wins=[s for s in seeds if not by[s,a]['safe_complete'] and by[s,b]['safe_complete']]
            losses=[s for s in seeds if by[s,a]['safe_complete'] and not by[s,b]['safe_complete']]
            result=dict(a=a,b=b,common_safe=common,rescued=wins,lost=losses,
                both_failed=[s for s in seeds if not by[s,a]['safe_complete'] and not by[s,b]['safe_complete']])
            for key in ('time','path_length'):
                x=np.array([by[s,a][key] for s in common]);y=np.array([by[s,b][key] for s in common]);d=y-x
                result[key]=dict(a_mean=float(x.mean()) if len(x) else None,b_mean=float(y.mean()) if len(y) else None,
                    a_median=float(np.median(x)) if len(x) else None,b_median=float(np.median(y)) if len(y) else None,
                    delta_mean=float(d.mean()) if len(d) else None,delta_median=float(np.median(d)) if len(d) else None,
                    max_degradation=float(d.max()) if len(d) else None,
                    faster=int((d<-1e-6).sum()),equal=int((abs(d)<=1e-6).sum()),slower=int((d>1e-6).sum()),
                    per_scene=[dict(seed=s,a=float(xx),b=float(yy),delta=float(dd)) for s,xx,yy,dd in zip(common,x,y,d)])
            out[f'{b}-minus-{a}']=result
    return out
