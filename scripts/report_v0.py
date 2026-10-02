#!/usr/bin/env python3
"""Render fixed completed V0 runs, retaining failures and common-success denominators."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from sailboat_routing.runtime import configure_cpu
configure_cpu()
import argparse,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from sailboat_routing.metrics import METHODS

def main():
    p=argparse.ArgumentParser();p.add_argument('--comparison',required=True,type=Path);p.add_argument('--fit',required=True,type=Path);a=p.parse_args()
    out=a.comparison.resolve(strict=True)
    assert out.is_relative_to(ROOT/'runs')
    suite=json.loads((out/'suite.json').read_text());summary=json.loads((out/'result.json').read_text());fit=json.loads((a.fit/'result.json').read_text())
    colors={'geometry_only':'#2563eb','oracle_local':'#d97706','estimated_local':'#059669'}
    fig,axes=plt.subplots(3,4,figsize=(18,12))
    for scene,ax in zip(suite['comparison_scenarios'],axes.flat):
        for obs in suite['maps'][scene['map']]:
            ax.add_patch(Circle(obs['center_xy'],obs['entity_radius']+obs['safety_buffer'],color='gray',alpha=.12))
            ax.add_patch(Circle(obs['center_xy'],obs['entity_radius'],color='gray',alpha=.5))
        for method in METHODS:
            rec=json.loads((out/(scene['id']+'__'+method+'.json')).read_text());xy=np.array([v['raw'][:2] for v in rec['trajectory']])
            ax.plot(xy[:,0],xy[:,1],color=colors[method],label=method+(' OK' if rec['row']['success'] else ' FAIL'),linewidth=1.1)
            ax.scatter(*xy[-1],s=12,color=colors[method])
        ax.scatter(*scene['goal'],marker='*',s=70,color='black');ax.set_title(scene['id'],fontsize=10);ax.set_aspect('equal',adjustable='datalim');ax.grid(alpha=.2);ax.legend(fontsize=6)
    fig.suptitle('V0 fixed development scenarios: all successes and failures',fontsize=16)
    fig.tight_layout();fig.savefig(out/'trajectories.png',dpi=140);plt.close(fig)
    methods=list(METHODS);fig,ax=plt.subplots(figsize=(8,4))
    counts=[summary['methods'][m]['success_count'] for m in methods]
    ax.bar(methods,counts,color=[colors[m] for m in methods]);ax.set_ylim(0,summary['scene_count']);ax.set_ylabel('Safe arrivals / fixed scenarios');ax.set_title('Development set only; all failures retained')
    for i,c in enumerate(counts):ax.text(i,c+.15,f'{c}/{summary["scene_count"]}',ha='center')
    fig.tight_layout();fig.savefig(out/'success_counts.png',dpi=160);plt.close(fig)
    print(json.dumps({'summary':summary,'fit':fit['test'],'plots':['trajectories.png','success_counts.png']},allow_nan=False))
if __name__=='__main__':main()
