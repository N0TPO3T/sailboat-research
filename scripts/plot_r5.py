"""R5 real trajectory figures; redraw from compact figure_data without simulator."""
from pathlib import Path
import argparse,json,hashlib,csv,html,os
ROOT=Path(__file__).resolve().parents[1]
os.environ.update(MPLCONFIGDIR=str(ROOT/".cache/matplotlib"),XDG_CACHE_HOME=str(ROOT/".cache"),OMP_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1",MKL_NUM_THREADS="1")
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
ROOT=Path(__file__).resolve().parents[1]
COL=['#0072B2','#D55E00','#009E73','#CC79A7','#E69F00']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,d):p.write_text(json.dumps(d,indent=2),encoding='utf-8')
def save(fig,out,name):
    fig.tight_layout()
    for ext in ['png','svg','pdf']:fig.savefig(out/(name+'.'+ext),dpi=300,bbox_inches='tight')
    plt.close(fig)
def compact(run,row):
    dest=run/'figure_data'/(row['scene_id']+'__'+row['variant']+'.json');dest.parent.mkdir(exist_ok=True)
    if dest.exists():return read(dest)
    raw=ROOT/row['evidence'];data=read(raw);job=read(raw.with_name('job.json'));tr=data['trajectory']
    points=[dict(time=x['time'],x=x['raw'][0],y=x['raw'][1],clearance=x.get('safety_clearance_m'),goal_distance=float(np.linalg.norm(np.array(x['raw'][:2])-job['scene']['goal']))) for x in tr]
    d=dict(row=row,scene=job['scene'],obstacles=job['suite']['maps'][job['scene']['map']],points=points,changes=data['target_changes'],initial_target=next((x['target'] for x in tr if 'target' in x),None),source_sha256=hashlib.sha256(raw.read_bytes()).hexdigest())
    write(dest,d)
    with dest.with_suffix('.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(points[0]));w.writeheader();w.writerows(points)
    return d

def chart(ax,d):
    for o in d['obstacles']:
        ax.add_patch(Circle(o['center_xy'],o['entity_radius'],color='#888888',alpha=.55))
        ax.add_patch(Circle(o['center_xy'],o['entity_radius']+o['safety_buffer'],fill=False,ls='--',ec='#555555',lw=1))
    ax.scatter(*d['scene']['goal'],marker='*',s=80,c='black',label='Final goal');ax.scatter(0,0,c='black',s=16)
    ax.set_aspect('equal',adjustable='datalim');ax.set_xlabel('World x (m)');ax.set_ylabel('World y (m)');ax.grid(alpha=.16)

def trace(ax,d,color,label,ls='-'):
    xy=np.array([[x['x'],x['y']] for x in d['points']]);r=d['row'];from analyze_r1 import outcome
    status={'safe_arrival':'safe','buffer_violation':'buffer breach','time_limit':'timeout'}.get(outcome(r),outcome(r))
    ax.plot(xy[:,0],xy[:,1],c=color,lw=1.45,ls=ls,label=f'{label}: {r["time_s"]:.0f} s, {status}')
    bad=next((x for x in d['points'] if x['clearance'] is not None and x['clearance']<=0),None)
    if bad:ax.scatter(bad['x'],bad['y'],marker='x',s=60,c=color,zorder=8)
    return xy

def make(run,which,main_override=None):
    out=run/'figures';out.mkdir(exist_ok=True);main=main_override or read(run/'freeze.json')['main_variant']
    rows=read(run/('development' if which=='development' else 'final')/'analysis_rows.json');lookup={(r['scene_id'],r['variant']):r for r in rows}
    variants=['relay_m120','relay_m160',main];labels={'relay_m120':'Relay120','relay_m160':'Relay160','tangent_minimal':'Source-scale / 10 s','tangent_scaled':'90 m / 10 s','tangent_period60':'60 s / exit135','tangent_exit90':'60 s / exit90','tangent_fixed90':'Fixed target / 90 m',main:'Selected tangent'}
    selpath=out/'selection.json';selection=read(selpath) if selpath.exists() else {}
    def get(s,v):return compact(run,lookup[s,v])
    def family(s):return lookup[s,main]['evaluation_family']
    ids=sorted({r['scene_id'] for r in rows});routine=[s for s in ids if family(s)=='routine'];risk=[s for s in ids if family(s)=='risk']
    def delta(s):return lookup[s,main]['time_s']-lookup[s,'relay_m160']['time_s']
    def choose(ss):
        losses=[s for s in ss if not lookup[s,main]['success'] and lookup[s,'relay_m160']['success']]
        gains=[s for s in ss if lookup[s,main]['success'] and not lookup[s,'relay_m160']['success']]
        common=[s for s in ss if lookup[s,main]['success'] and lookup[s,'relay_m160']['success']]
        return (losses or gains or sorted(common,key=lambda s:(-delta(s),s)) or ss)[0]
    if which=='statistics':
        from analyze_r1 import outcome
        fig,axes=plt.subplots(2,2,figsize=(12,8.3));allv=variants+[v for v in sorted({r['variant'] for r in rows}) if v not in variants]
        for k,fam in enumerate(['routine','risk']):
            rr=[r for r in rows if r['evaluation_family']==fam];bottom=np.zeros(len(allv))
            cats=['safe_arrival','buffer_violation','time_limit'];cats+=sorted({outcome(x) for x in rr}-set(cats))
            for j,cat in enumerate(cats):
                yy=np.array([sum(outcome(x)==cat for x in rr if x['variant']==v) for v in allv]);axes[k,0].bar(range(len(allv)),yy,bottom=bottom,color=['#009E73','#D55E00','#999999','#E69F00'][j%4],label=cat.replace('_',' '));bottom+=yy
            for i,v in enumerate(allv):
                n=sum(x['variant']==v for x in rr);ok=sum(x['success'] for x in rr if x['variant']==v);axes[k,0].text(i,n+.35,f'{ok}/{n}',ha='center',fontsize=8)
            axes[k,0].set_xticks(range(len(allv)),[labels.get(v,v.replace('tangent_','')) for v in allv],rotation=18,ha='right');axes[k,0].set_ylabel('Episodes');axes[k,0].set_title(f'{fam.capitalize()}: complete mission outcomes');axes[k,0].legend(fontsize=7,loc='upper right');axes[k,0].set_ylim(0,max(bottom)*1.3)
            ss=routine if fam=='routine' else risk
            for j,v in enumerate(variants[:2]):
                diff=sorted(lookup[s,main]['time_s']-lookup[s,v]['time_s'] for s in ss if lookup[s,main]['success'] and lookup[s,v]['success'])
                if diff:axes[k,1].step(diff,np.arange(1,len(diff)+1)/len(diff),where='post',c=COL[j],label=f'Main - {labels[v]}; common safe n={len(diff)}')
            axes[k,1].axvline(0,c='black',ls='--',lw=1);axes[k,1].set_xlabel('Paired arrival-time difference (s); negative = faster');axes[k,1].set_ylabel('Empirical cumulative fraction');axes[k,1].set_title(f'{fam.capitalize()}: conditional time trade-off');axes[k,1].legend(fontsize=8)
        fig.suptitle('Frozen new instances; risk strata do not estimate natural failure frequency',fontsize=12);save(fig,out,'frozen_statistics')
    elif which=='trajectories':
        chosen=[choose([s for s in routine if lookup[s,main]['distance_m']==d]) for d in [1000,3000,5000]];selection['trajectories']=dict(scene_ids=chosen,rule='Per distance first sorted safety loss, else first gain, else largest common-safe time cost versus160; post-hoc illustration.')
        fig,axes=plt.subplots(1,3,figsize=(17,5.2))
        for ax,s in zip(axes,chosen):
            chart(ax,get(s,main))
            for j,v in enumerate(variants):trace(ax,get(s,v),COL[j],labels[v],ls='--' if j==2 else '-')
            ax.set_title(s,fontsize=9);ax.legend(fontsize=7,loc='best')
        fig.text(.5,-.025,'Complete actual tracks. Grey: obstacle body; dashed circles: body + 60 m; cross: first measured intrusion; star: goal.',ha='center',fontsize=9);save(fig,out,'complete_1_3_5km')
    elif which=='intervention':
        mm=read(run/'final/mechanisms.json');changed={r['scene_id'] for r in mm if r['variant']==main and (r['applied_recovery_targets'] or r['initial_recovery'])}
        gains=[s for s in risk if lookup[s,main]['success'] and not lookup[s,'relay_m160']['success']]
        s=(gains or [s for s in risk if s in changed] or risk)[0];selection['intervention']=dict(scene_id=s,rule='First sorted risk safety gain; else first risk intervention; else first risk case. Post-hoc.')
        fig,axes=plt.subplots(1,3,figsize=(17,5.1));dmain=get(s,main);chart(axes[0],dmain)
        for j,v in enumerate(variants):
            d=get(s,v);trace(axes[0],d,COL[j],labels[v],ls='--' if j==2 else '-')
            tt=[x['time'] for x in d['points']];axes[1].plot(tt,[x['clearance'] for x in d['points']],c=COL[j],label=labels[v]);axes[2].plot(tt,[x['goal_distance'] for x in d['points']],c=COL[j],label=labels[v])
        # Mark initial target separately and actual applications after recovery starts.
        mech=next(x for x in mm if x['scene_id']==s and x['variant']==main)
        first=0 if mech['initial_recovery'] else (mech['first_applied'] or 0)
        center=min(dmain['points'],key=lambda x:abs(x['time']-first))
        if mech['initial_recovery'] and dmain['initial_target'] is not None:
            q=dmain['initial_target'];axes[0].plot([0,q[0]],[0,q[1]],':',c=COL[2],lw=1);axes[0].scatter(*q,marker='D',c=COL[2],s=28,label='Initial main target')
        axes[0].set_aspect('equal',adjustable='box');axes[0].set_xlim(center['x']-500,center['x']+600);axes[0].set_ylim(center['y']-550,center['y']+550)
        for change in [x for x in dmain['changes'] if x.get('applied_at',0)>=first][:6]:
            t=change.get('applied_at',change.get('time'));q=change.get('target',change.get('new_target'))
            if t is None:continue
            pt=min(dmain['points'],key=lambda x:abs(x['time']-t));axes[0].scatter(pt['x'],pt['y'],marker='s',c=COL[2],s=20,zorder=7)
            for ax in axes[1:]:ax.axvline(t,c=COL[2],ls=':',lw=.6,alpha=.6)
            if q is not None:axes[0].plot([pt['x'],q[0]],[pt['y'],q[1]],':',c=COL[2],lw=.7);axes[0].scatter(*q,c=COL[2],marker='D',s=20)
        axes[1].axhline(0,c='black',ls='--');axes[1].set_ylabel('Measured step safety clearance (m)');axes[2].set_ylabel('Distance to final goal (m)')
        for ax in axes[1:]:ax.set_xlabel('Physical time (s)');ax.legend(fontsize=8)
        axes[0].legend(fontsize=7);fig.suptitle(s+' — local track crop and full outcome',fontsize=12)
        fig.text(.5,-.025,'Squares/vertical lines: first six target applications from recovery onward. Diamonds/chords: position references (initial target separately marked), not predicted tracks.',ha='center',fontsize=8);save(fig,out,'risk_intervention')
    elif which=='tradeoff':
        common=[s for s in ids if lookup[s,main]['success'] and lookup[s,'relay_m160']['success']];chosen=[min(common,key=lambda s:(delta(s),s)),max(common,key=lambda s:(delta(s),s))]
        selection['tradeoff']=dict(scene_ids=chosen,rule='Largest common-safe gain and cost versus160 over all frozen families; post-hoc, not typical frequencies.')
        fig,axes=plt.subplots(2,2,figsize=(12,10))
        for k,s in enumerate(chosen):
            chart(axes[k,0],get(s,main))
            for j,v in enumerate(variants):
                d=get(s,v);trace(axes[k,0],d,COL[j],labels[v],ls='--' if j==2 else '-')
                axes[k,1].plot([x['time'] for x in d['points']],[x['goal_distance'] for x in d['points']],c=COL[j],label=labels[v])
            axes[k,0].legend(fontsize=7);axes[k,0].set_title(s,fontsize=9);axes[k,1].set_title(f'{family(s)}; main minus Relay160: {delta(s):+.0f} s');axes[k,1].set_xlabel('Physical time (s)');axes[k,1].set_ylabel('Distance to final goal (m)');axes[k,1].legend(fontsize=8)
        save(fig,out,'gain_and_cost')
    elif which=='development':
        dev=read(run/'development/analysis_rows.json');ll={(r['scene_id'],r['variant']):r for r in dev};vv=['relay_m160','tangent_scaled','tangent_fixed90',main];vv=list(dict.fromkeys(vv));nn={'relay_m160':'Relay160','tangent_scaled':'Moving reference / 10 s','tangent_fixed90':'Fixed position',main:'Candidate: '+main.replace('tangent_','')}
        fig,axes=plt.subplots(2,2,figsize=(12,10));chosen=['s2271_046_staggered_fast_1000','s3271_037_channel_stable_1000']
        for k,s in enumerate(chosen):
            chart(axes[k,0],compact(run,ll[s,vv[0]]))
            for j,v in enumerate(vv):
                if (s,v) not in ll:continue
                d=compact(run,ll[s,v]);trace(axes[k,0],d,COL[j],nn[v]);axes[k,1].plot([x['time'] for x in d['points']],[x['clearance'] for x in d['points']],c=COL[j],label=nn[v])
            axes[k,0].legend(fontsize=7);axes[k,0].set_title(s,fontsize=9);axes[k,1].axhline(0,c='black',ls='--');axes[k,1].set_ylabel('Measured step safety clearance (m)');axes[k,1].set_xlabel('Physical time (s)');axes[k,1].legend(fontsize=8)
        fig.suptitle('Seen development cases: opposite effects of moving versus fixed references');save(fig,out,'development_response')
    write(selpath,selection)
    files=sorted(out.glob('*.png'));cards=''.join(f'<section><h2>{f.stem}</h2><a href="figures/{f.name}"><img src="figures/{f.name}"></a><p><a href="figures/{f.stem}.svg">SVG</a> · <a href="figures/{f.stem}.pdf">PDF</a></p></section>' for f in files)
    (run/'gallery.html').write_text('<!doctype html><html><meta charset="utf-8"><title>R5 real trajectory atlas</title><style>body{max-width:1500px;margin:auto;font:17px sans-serif;padding:24px}img{width:100%}section{margin:35px 0}</style><h1>R5 actual closed-loop evidence</h1><p>Frozen routine/risk tasks reported separately. Illustrative cases selected by the recorded rule; not population frequencies. Grey bodies and original +60 m safety boundaries. No simulated forecast is drawn as actual motion.</p>'+cards+'</html>',encoding='utf-8')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('run');ap.add_argument('--main');ap.add_argument('--figure',required=True,choices=['statistics','trajectories','intervention','tradeoff','development']);a=ap.parse_args();make(Path(a.run).resolve(),a.figure,a.main)
