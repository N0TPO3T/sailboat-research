"""Stage health/learning curves from completed evidence; never advances training."""
import argparse,json,math
from pathlib import Path
import numpy as np

def report(directory,plot=False):
    d=Path(directory);events=[]
    for p in sorted(d.glob('log_from_*.jsonl')):
        for line in p.read_text().splitlines():
            try:events.append(json.loads(line))
            except json.JSONDecodeError:pass # partial last line of an active writer
    updates=[r for r in events if r['type']=='update'];episodes=[r for r in events if r['type']=='episode']
    latest=json.loads((d/'latest.json').read_text()) if (d/'latest.json').exists() else {}
    progress=json.loads((d/'progress.json').read_text()) if (d/'progress.json').exists() else {}
    evals=[]
    for p in d.glob('eval_*/summary.json'):
        value=json.loads(p.read_text());evals.append(dict(step=int(p.parent.name.split('_')[1]),**value))
    evals.sort(key=lambda r:r['step']);recent=updates[-1000:]
    keys=['q_loss','a_loss','alpha_loss','alpha','q_abs_max','sample_entropy_estimate','action_saturation_fraction']
    metrics={k:dict(last=next((r[k] for r in reversed(recent) if k in r),None),mean=float(np.mean([r[k] for r in recent if k in r])) if any(k in r for r in recent) else None) for k in keys}
    broken=any(not math.isfinite(v) for r in updates for k,v in r.items() if isinstance(v,float))
    reasons=[]
    if recent:
        if max(r.get('q_abs_max',0) for r in recent)>1e5:reasons.append('Q absolute magnitude > 1e5; inspect scale')
        if not 1e-6<recent[-1]['alpha']<100:reasons.append('alpha outside [1e-6,100]')
        if np.mean([r.get('action_saturation_fraction',0) for r in recent])>.95:reasons.append('recent action saturation >95%')
    if not recent:reasons.append('No optimizer updates available')
    health='BROKEN' if broken else 'SUSPICIOUS' if reasons else 'HEALTHY'
    result=dict(TRAIN_HEALTH=health,STATIC_BASELINE_STATUS='IN_PROGRESS',step=latest.get('step',progress.get('training_step',0)),latest=latest,progress=progress,health_reasons=reasons,
        metrics_last1000_updates=metrics,actor_updates=sum(bool(r.get('policy_updated',False)) for r in updates),critic_updates=len(updates),
        return_first20_mean=float(np.mean([r['metrics']['reward'] for r in episodes[:20]])) if episodes else None,
        return_last20_mean=float(np.mean([r['metrics']['reward'] for r in episodes[-20:]])) if episodes else None,
        completed_evaluations=[dict(step=r['step'],metrics=r['metrics'],strata=r['strata']) for r in evals],
        continuation='Requires trajectory and health review; this script never launches 500k',thresholds='Nonfinite=BROKEN; |Q|>1e5,alpha outside(1e-6,100),saturation>.95=SUSPICIOUS; provisional engineering flags, not performance gates')
    (d/'training_health.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    if plot:
        import matplotlib;matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,axes=plt.subplots(3,2,figsize=(12,11));axes=axes.flat
        axes[0].plot([r['step'] for r in episodes],[r['metrics']['reward'] for r in episodes],alpha=.5)
        axes[0].set_title('Training episode return')
        fields=['no_obstacle_success_rate','static_safe_success_rate','static_safety_violation_rate','timeout_rate','minimum_separation_mean_m']
        for ax,key in zip(list(axes)[1:],fields):
            ax.plot([r['step'] for r in evals],[r['metrics'][key] for r in evals],marker='o');ax.set_title(key)
        for ax in fig.axes:
            ax.set_xlabel('Environment steps');ax.grid(alpha=.3)
            for x in [0,100000,500000,1000000,2000000]:
                if x<=max([r['step'] for r in evals]+[result['step']]):ax.axvline(x,color='gray',alpha=.2)
        fig.tight_layout();fig.savefig(d/'learning_curves.png',dpi=160);plt.close(fig)
    print(json.dumps(result,indent=2));return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--plot',action='store_true');a=p.parse_args();report(a.directory,a.plot)
