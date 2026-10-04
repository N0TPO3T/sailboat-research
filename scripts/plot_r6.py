"""R6 compact real-log figures, reusing R5 trace extraction and chart rendering."""
from pathlib import Path
import argparse,json,html
import numpy as np
from plot_r5 import ROOT,read,write,save,compact,chart,trace,plt,COL
from analyze_r1 import outcome
COL=["#0072B2","#D55E00","#009E73","#CC79A7","#E69F00","#56B4E9","#555555"]

def make(run):
    freeze=read(run/'freeze.json');main=freeze['main_variant'];rows=read(run/'final/analysis_rows.json')
    out=run/'figures';out.mkdir(exist_ok=True)
    ids=sorted({r['scene_id'] for r in rows});lookup={(r['scene_id'],r['variant']):r for r in rows}
    variants=['relay_m120','relay_m160',main]
    labels={'relay_m120':'Original + Relay120','relay_m160':'Original + Relay160',main:freeze['main_label']}
    labels.update(freeze.get('labels',{}));allv=variants+[v for v in sorted({r['variant'] for r in rows}) if v not in variants]
    routine=[s for s in ids if lookup[s,main]['evaluation_family']=='routine'];risk=[s for s in ids if lookup[s,main]['evaluation_family']=='risk']
    def get(s,v):return compact(run,lookup[s,v])
    def loss(s):return not lookup[s,main]['success'] and lookup[s,'relay_m160']['success']
    def gain(s):return lookup[s,main]['success'] and not lookup[s,'relay_m160']['success']
    def common(s):return lookup[s,main]['success'] and lookup[s,'relay_m160']['success']
    def ratio(s):return lookup[s,main]['time_s']/lookup[s,'relay_m160']['time_s']
    selected={}
    chosen=[]
    for distance in [1000,3000,5000]:
        ss=[s for s in routine if lookup[s,main]['distance_m']==distance]
        safe=[s for s in ss if common(s)]
        chosen.append(min(safe,key=lambda s:(ratio(s),s)) if safe else ss[0])
    selected['actual_1_3_5km']=dict(scene_ids=chosen,rule='Post-hoc illustrative largest proportional time gain among common-safe routine cases at each distance; fallback first sorted case. Not representative selection.')
    fig,axes=plt.subplots(1,3,figsize=(17,5.2))
    for ax,s in zip(axes,chosen):
        chart(ax,get(s,main))
        for j,v in enumerate(variants):trace(ax,get(s,v),COL[j],labels[v],ls='--' if v==main else '-')
        ax.set_title(s,fontsize=9);ax.legend(fontsize=7)
    fig.suptitle('Same-scene complete actual tracks: 1 / 3 / 5 km',fontsize=13)
    fig.text(.5,-.015,'Grey bodies; dashed circles = body + 60 m. Actual tracks only; star = final goal.',ha='center',fontsize=9)
    save(fig,out,'actual_1_3_5km')
    # Always show the adverse case alongside a favorable one.
    bad=next((s for s in ids if loss(s)),None)
    if bad is None:bad=max([s for s in ids if common(s)],key=lambda s:(ratio(s),s))
    good=next((s for s in ids if gain(s)),None)
    if good is None:good=min([s for s in ids if common(s)],key=lambda s:(ratio(s),s))
    selected['gain_and_cost']=dict(scene_ids=[good,bad],rule='First sorted safety gain and first sorted safety loss vs original160; if absent use best/worst common-safe time ratio. Post-hoc, both directions retained.')
    fig,axes=plt.subplots(2,2,figsize=(12,10))
    for col,s in enumerate([good,bad]):
        chart(axes[0,col],get(s,main))
        for j,v in enumerate(variants):
            d=get(s,v);trace(axes[0,col],d,COL[j],labels[v],ls='--' if v==main else '-')
            axes[1,col].plot([x['time'] for x in d['points']],[x['goal_distance'] for x in d['points']],c=COL[j],label=labels[v])
        axes[0,col].set_title(('Gain example: ' if col==0 else 'Adverse / cost example: ')+s,fontsize=8);axes[0,col].legend(fontsize=7)
        axes[1,col].axhline(10,c='black',ls=':',lw=1);axes[1,col].set_xlabel('Physical mission time (s)');axes[1,col].set_ylabel('Distance to final goal (m)');axes[1,col].grid(alpha=.2);axes[1,col].legend(fontsize=7)
    save(fig,out,'gain_and_cost')
    fig,axes=plt.subplots(2,2,figsize=(15,9.2))
    for k,(family,ss) in enumerate([('routine',routine),('risk',risk)]):
        rr=[r for r in rows if r['scene_id'] in ss];bottom=np.zeros(len(allv));cats=['safe_arrival','buffer_violation','time_limit']
        cats+=sorted({outcome(r) for r in rr}-set(cats))
        for j,cat in enumerate(cats):
            yy=np.array([sum(outcome(r)==cat for r in rr if r['variant']==v) for v in allv]);axes[k,0].bar(range(len(allv)),yy,bottom=bottom,color=['#009E73','#D55E00','#999999','#E69F00'][j%4],label=cat.replace('_',' '));bottom+=yy
        for i,v in enumerate(allv):
            n=sum(r['variant']==v for r in rr);ok=sum(r['success'] for r in rr if r['variant']==v);axes[k,0].text(i,n+.3,f'{ok}/{n}',ha='center',fontsize=8)
        axes[k,0].set_xticks(range(len(allv)),[labels.get(v,v) for v in allv],rotation=20,ha='right',fontsize=8);axes[k,0].set_ylabel('Complete episodes');axes[k,0].set_ylim(0,max(bottom)*1.3);axes[k,0].set_title(f'{family.capitalize()}: all outcomes');axes[k,0].legend(fontsize=7)
        for j,v in enumerate(variants[:2]):
            differences=sorted(lookup[s,main]['time_s']-lookup[s,v]['time_s'] for s in ss if lookup[s,main]['success'] and lookup[s,v]['success'])
            if differences:axes[k,1].step(differences,np.arange(1,len(differences)+1)/len(differences),where='post',color=COL[j],label=f'Main - {labels[v]}, n={len(differences)}')
        axes[k,1].axvline(0,c='black',ls='--',lw=1);axes[k,1].set_xlabel('Arrival-time difference (s); negative = faster');axes[k,1].set_ylabel('Common-safe empirical fraction');axes[k,1].legend(fontsize=7);axes[k,1].set_title('Conditional paired time; failures excluded here only')
    fig.suptitle('Frozen new instances: complete outcomes and conditional efficiency',fontsize=12);save(fig,out,'mission_outcomes')
    # Include failures in time-to-safe-completion curves using all episodes as denominator.
    fig,axes=plt.subplots(1,3,figsize=(16,4.6))
    for ax,dist in zip(axes,[1000,3000,5000]):
        ss=[s for s in routine if lookup[s,main]['distance_m']==dist]
        for j,v in enumerate(allv):
            times=sorted(lookup[s,v]['time_s']/(1.8*dist) for s in ss if lookup[s,v]['success']);xs=[0]+times+[1];ys=[0]+[i/len(ss) for i in range(1,len(times)+1)]+[len(times)/len(ss)]
            ax.step(xs,ys,where='post',c=COL[j%len(COL)],ls='--' if v==main else '-',label=labels.get(v,v))
        ax.set_title(f'{dist//1000} km, all {len(ss)} routine scenes');ax.set_xlabel('Fraction of task time limit');ax.set_ylabel('Fraction safely completed');ax.set_ylim(0,1.04);ax.grid(alpha=.2);ax.legend(fontsize=7)
    fig.suptitle('Whole-mission timeliness: failures remain in the denominator',fontsize=12);save(fig,out,'safe_completion_time')
    # A local safety view for the adverse case; straight targets are only annotations.
    s=bad;fig,axes=plt.subplots(1,2,figsize=(12,4.8));dmain=get(s,main);chart(axes[0],dmain)
    focus=None
    for j,v in enumerate(variants):
        d=get(s,v);trace(axes[0],d,COL[j],labels[v],ls='--' if v==main else '-')
        points=[x for x in d['points'] if x['clearance'] is not None and np.isfinite(x['clearance'])]
        if points:axes[1].plot([x['time'] for x in points],[x['clearance'] for x in points],c=COL[j],label=labels[v])
        if v==main and points:
            q=min(points,key=lambda x:x['clearance']);focus=(q['x'],q['y'])
    if focus and dmain['obstacles']:
        axes[0].set_xlim(focus[0]-400,focus[0]+400);axes[0].set_ylim(focus[1]-400,focus[1]+400);axes[0].set_aspect('equal',adjustable='box')
    axes[0].legend(fontsize=7);axes[0].set_title('Adverse-case local track (zoom if obstacles)',fontsize=10);axes[1].axhline(0,c='black',ls='--');axes[1].set_xlabel('Physical mission time (s)');axes[1].set_ylabel('Minimum clearance of each 1 s segment (m)');axes[1].legend(fontsize=7);axes[1].grid(alpha=.2)
    fig.suptitle(s,fontsize=10);save(fig,out,'adverse_safety_detail')
    selected['adverse_safety_detail']=dict(scene_id=s,rule='Same adverse case; zoom around main minimum-clearance endpoint. Segment metric, not swept hull.')
    write(out/'selection.json',selected)
    names=['actual_1_3_5km','gain_and_cost','mission_outcomes','safe_completion_time','adverse_safety_detail']
    body=''.join(f'<section><h2>{html.escape(n)}</h2><img src="figures/{n}.png" style="max-width:100%"></section>' for n in names)
    (run/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>R6 real-log results</title><h1>R6 research results</h1><p>Frozen new instances. All figures are derived from actual logs. Selection rules and source hashes: figures/selection.json and figure_data/*.json. This atlas includes adverse results.</p>'+body,encoding='utf-8')
    print('Saved',len(names),'figures and offline atlas',run)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('run');a=ap.parse_args();make(Path(a.run).resolve())
