#!/usr/bin/env python3
"""R2 figures from saved raw traces only; no rollout, smoothing or wind query."""
from pathlib import Path
import os,json,csv,math,argparse,statistics,html
ROOT=Path(__file__).resolve().parents[1]
os.environ['MPLCONFIGDIR']=str(ROOT/'.cache/matplotlib')
os.environ['XDG_CACHE_HOME']=str(ROOT/'.cache');os.environ['TMPDIR']=str(ROOT/'.tmp')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle,Rectangle
from matplotlib.lines import Line2D
from analyze_r1 import outcome,interval
from analyze_r2 import quantile
plt.rcParams.update({'font.size':10,'svg.fonttype':'none','path.simplify':False,'axes.spines.top':False,'axes.spines.right':False})
PALETTE=['#0072B2','#D55E00','#009E73','#CC79A7','#555555']
def generate(folder,main,simple,out=None,stage="development"):
    folder=Path(folder).resolve();out=Path(out).resolve() if out else folder.parent/'figures';out.mkdir(parents=True,exist_ok=True)
    rows=json.loads((folder/'analysis_rows.json').read_text());lookup={(r['scene_id'],r['variant']):r for r in rows}
    variants=list(dict.fromkeys(['geom80',simple,main]));allvars=variants+sorted({r['variant'] for r in rows}-set(variants))
    labels={'geom80':'R1 geom80',simple:'Simple baseline ('+simple+')',main:('R2 main (' if stage=='frozen' else 'Candidate (')+main+')'}
    if main==simple:labels[main]='Simple baseline / R2 main ('+main+')'
    colors={v:PALETTE[i%len(PALETTE)] for i,v in enumerate(allvars)}
    names=sorted({r['scene_id'] for r in rows});cache={}
    def data(name,v):
        key=(name,v)
        if key not in cache:
            row=lookup[key];f=ROOT/row['evidence'];cache[key]=(json.loads(f.read_text()),json.loads(f.with_name('job.json').read_text()))
        return cache[key]
    def xy(d):return np.array([a['raw'][:2] for a in d['trajectory']])
    def save(fig,name):
        fig.savefig(out/(name+'.png'),dpi=300,bbox_inches='tight')
        fig.savefig(out/(name+'.svg'),bbox_inches='tight');plt.close(fig)
    def geography(ax,job):
        goal=job['scene']['goal']
        for o in job['suite']['maps'][job['scene']['map']]:
            ax.add_patch(Circle(o['center_xy'],o['entity_radius'],facecolor='#777777',edgecolor='#333333',alpha=.5,zorder=1))
            ax.add_patch(Circle(o['center_xy'],o['entity_radius']+o['safety_buffer'],fill=False,edgecolor='#777777',linestyle='--',linewidth=1,zorder=1))
        ax.add_patch(Circle(goal,job['suite']['goal_radius_m'],fill=False,edgecolor='black',linewidth=1.5))
        ax.scatter(*goal,marker='*',s=150,facecolors='none',edgecolors='black',linewidths=1.2,zorder=6,label='Goal (10 m arrival radius)')
        ax.scatter(0,0,marker='o',s=45,facecolor='white',edgecolor='black',zorder=6,label='Start')
        ax.set_aspect('equal',adjustable='datalim');ax.set_xlabel('World x (m)');ax.set_ylabel('World y (m)');ax.grid(alpha=.18)
    def track(ax,name,v,mark=True):
        d,job=data(name,v);a=xy(d);r=lookup[name,v]
        ax.plot(a[:,0],a[:,1],c=colors[v],lw=1.45,label=labels.get(v,v)+' | '+outcome(r)+', '+str(int(r['time_s']))+' s',zorder=3)
        if mark:
            times={t['time']:t['raw'][:2] for t in d['trajectory']}
            changes=d['target_changes'];stride=max(1,math.ceil(len(changes)/12))
            q=[times[c['applied_at']] for c in changes[::stride] if c['applied_at'] in times]
            if q:ax.scatter(np.array(q)[:,0],np.array(q)[:,1],s=16,marker='|',c=colors[v],zorder=5)
            for fraction in [.2,.4,.6,.8]:
                k=int((len(a)-1)*fraction);j=min(k+10,len(a)-1)
                if j>k:ax.annotate('',xy=a[j],xytext=a[k],arrowprops=dict(arrowstyle='->',color=colors[v],lw=1))
        if not r['success']:ax.scatter(*a[-1],marker='x',s=55,c=colors[v],zorder=6)
    selections=[]
    for dist,family in [(1000,'open'),(3000,'channel'),(5000,'staggered')]:
        available=[n for n in names if all((n,v) in lookup for v in variants) and lookup[n,main]['distance_m']==dist]
        common=[n for n in available if all(lookup[n,v]['success'] for v in variants)]
        pool=[n for n in common if lookup[n,main]['layout']==family] or common or available
        assert pool
        if common:
            deltas={n:lookup[n,main]['time_s']-lookup[n,'geom80']['time_s'] for n in pool}
            median=statistics.median(deltas.values());chosen=min(pool,key=lambda n:(abs(deltas[n]-median),n))
            reason='Common success: prefer '+family+' layout; closest to within-pool median main-minus-R1 time difference; scene ID breaks ties'
        else:chosen=sorted(pool)[0];reason='No all-method common success; first scene ID at this distance'
        selections.append({'figure':'trajectory_'+str(dist//1000)+'km','scene_id':chosen,'reason':reason,'distance_m':dist})
        d,job=data(chosen,main);fig,ax=plt.subplots(figsize=(9,6));geography(ax,job)
        for v in variants:track(ax,chosen,v)
        ax.set_title(str(dist//1000)+' km actual trajectories\n'+chosen)
        ax.legend(fontsize=8,loc='best')
        fig.text(.5,.005,'Solid: raw executed paths. Ticks: sparse actual target applications. Gray disks: entities; dashed circles: true safety boundary. No smoothing.',ha='center',fontsize=8)
        save(fig,'trajectory_'+str(dist//1000)+'km')
    available=[n for n in names if all((n,v) in lookup for v in variants)]
    gains=[n for n in available if lookup[n,main]['success'] and lookup[n,'geom80']['success'] and lookup[n,main]['time_s']<lookup[n,'geom80']['time_s']]
    if gains:
        pool=[n for n in gains if lookup[n,main]['distance_m']==5000] or gains
        benefit=min(pool,key=lambda n:(lookup[n,main]['time_s']-lookup[n,'geom80']['time_s'],n))
        selections.append({'figure':'efficiency_example','scene_id':benefit,'reason':'Largest main/R1 common-success time reduction; third displayed method may fail; prefer 5km, then scene ID. Deliberately extreme mechanism illustration, not typical benefit.'})
        dd,jj=data(benefit,main);fig,ax=plt.subplots(figsize=(9,6));geography(ax,jj)
        for v in variants:track(ax,benefit,v)
        ax.set_title(str(lookup[benefit,main]['distance_m']//1000)+' km: largest paired gain vs R1 (not typical)\n'+benefit);ax.legend(fontsize=8,loc='best')
        fig.text(.5,.005,'Complete raw paths. An extreme selected example; use paired statistics for overall inference.',ha='center',fontsize=8)
        save(fig,'efficiency_example')
    regression=[n for n in available if not lookup[n,main]['success'] and lookup[n,'geom80']['success']]
    failures=[n for n in available if not lookup[n,main]['success']]
    if regression:chosen=sorted(regression)[0];reason='First scene ID with main failure and R1 safe arrival'
    elif failures:chosen=sorted(failures)[0];reason='First main failure by scene ID'
    else:
        chosen=min(available,key=lambda n:(lookup[n,main]['min_safety_clearance_m'] if lookup[n,main]['min_safety_clearance_m'] is not None else math.inf,n))
        reason='No main failure: smallest logged main safety clearance'
    d,job=data(chosen,main);trace=d['trajectory']
    dangerous=[x for x in trace if x.get('safety_clearance_m') is not None and x['safety_clearance_m']<=0]
    finite=[x for x in trace if x.get('safety_clearance_m') is not None]
    focus=dangerous[0] if dangerous else min(finite,key=lambda x:x['safety_clearance_m']) if finite else trace[-1]
    ft=focus['time'];pos=np.array(focus['raw'][:2])
    selections.append({'figure':'failure_local','scene_id':chosen,'reason':reason,'focus_time_s':ft,'focus':'end of first violating 1 s segment' if dangerous else 'minimum clearance or terminal state'})
    fig=plt.figure(figsize=(10,7));ax=fig.add_axes([.08,.13,.62,.75]);geography(ax,job)
    for v in variants:track(ax,chosen,v,mark=False)
    ax.scatter(*pos,marker='X',s=100,color=colors[main],edgecolor='black',zorder=8,label=('First unsafe step ends at t=' if dangerous else 'Focus at t=')+str(int(ft))+' s')
    # Issued target at decision time is reconstructed from *applied* changes,
    # not trajectory[t].target (which belongs to the preceding action interval).
    pre=max(0,int(ft)-1);state=next((a for a in trace if a['time']==pre),trace[-1])
    target=trace[1].get('target') if len(trace)>1 else None
    for change in d['target_changes']:
        if change['applied_at']<=pre:target=change['target']
    if target is not None:
        a=np.array(state['raw'][:2]);b=np.array(target)
        ax.plot([a[0],b[0]],[a[1],b[1]],':',c=colors[main],lw=1.7,label='Issued-target chord at t='+str(pre)+' (not predicted path)')
        ax.scatter(*b,marker='D',s=30,c=colors[main])
    ax.set_xlim(pos[0]-170,pos[0]+170);ax.set_ylim(pos[1]-170,pos[1]+170)
    context=fig.add_axes([.74,.57,.25,.30]);geography(context,job)
    for v in variants:track(context,chosen,v,mark=False)
    context.add_patch(Rectangle((pos[0]-170,pos[1]-170),340,340,fill=False,edgecolor='black',lw=1.2))
    context.set_xlabel('');context.set_ylabel('');context.tick_params(labelsize=6)
    context.set_title('Whole episode; box = zoom',fontsize=8)
    fig.text(.75,.48,'Start: open circle\nGoal: black star (10 m)\nDashed circles: true safety\nSolid lines: actual paths',fontsize=8,va='top')
    ax.set_aspect('equal',adjustable='box');ax.legend(fontsize=8,loc='best')
    ax.set_title('Local failure / minimum-clearance case\n'+chosen)
    fig.text(.5,.005,'Local window; complete paths remain in raw logs. Safety uses 1 s step segments, not continuous integration curves.',ha='center',fontsize=8)
    save(fig,'failure_local')
    for key,ylabel,name in [('clearance','Per-step safety clearance (m)','safety_clearance'),('progress','Distance to final goal (m)','goal_distance')]:
        fig,ax=plt.subplots(figsize=(9,4.5))
        for v in variants:
            dd,jj=data(chosen,v);tt=np.array([z['time'] for z in dd['trajectory']])
            yy=np.linalg.norm(xy(dd)-np.array(jj['scene']['goal']),axis=1) if key=='progress' else np.array([z.get('safety_clearance_m') if z.get('safety_clearance_m') is not None else np.nan for z in dd['trajectory']])
            ax.plot(tt,yy,color=colors[v],label=labels.get(v,v),lw=1)
        if key=='clearance':ax.axhline(0,color='black',ls='--',label='True safety boundary')
        ax.axvline(ft,color='gray',ls=':',lw=1);ax.set_xlabel('Physical time (s)');ax.set_ylabel(ylabel)
        ax.set_title(chosen+'\nRaw time series; each method stops at its own actual end')
        ax.legend(fontsize=8);ax.grid(alpha=.2);save(fig,name)
    changes=d['target_changes'];near=[c for c in changes if ft-120<=c['applied_at']<=ft+15]
    if not near and changes:near=[min(changes,key=lambda c:abs(c['applied_at']-ft))]
    fig,ax=plt.subplots(figsize=(9,3.5))
    if near:
        for i,c in enumerate(near[-12:]):
            ax.plot([c['selected_at'],c['applied_at']],[i,i],color=colors[main],lw=2)
            ax.scatter(c['selected_at'],i,marker='o',facecolor='white',edgecolor=colors[main],s=40)
            ax.scatter(c['applied_at'],i,marker='|',color=colors[main],s=150)
        ax.set_yticks(range(len(near[-12:])),[str(tuple(round(z,1) for z in c['target'])) for c in near[-12:]])
    else:ax.text(.5,.5,'No actual target change in this episode',ha='center',transform=ax.transAxes)
    applied_times={c['selected_at'] for c in changes}
    pending=[a for a in d['planner_decisions'] if a['decision']['target_xy']!=a['input']['current_goal_xy'] and a['decision_time'] not in applied_times]
    ax.set_title('Up to 12 actual changes near focus: '+chosen+'\nOpen circle: selected; tick: applied. Unapplied proposals in full episode: '+str(len(pending)))
    ax.set_xlabel('Physical time (s)');ax.set_ylabel('Applied target (world m)');ax.grid(alpha=.2);save(fig,'target_timing')
    fig,axes=plt.subplots(1,3,figsize=(13,4.5))
    for ax,dist in zip(axes,[1000,3000,5000]):
        shown=[v for v in allvars if any(r['variant']==v and r['distance_m']==dist for r in rows)]
        for i,v in enumerate(shown):
            rr=[r for r in rows if r['variant']==v and r['distance_m']==dist];n=len(rr);k=sum(r['success'] for r in rr);lo,hi=interval(k,n)
            ax.bar(i,k/n,color=colors[v],alpha=.9);ax.errorbar(i,k/n,yerr=[[k/n-lo],[hi-k/n]],color='black',capsize=3,fmt='none')
            ax.text(i,hi+.025,str(k)+'/'+str(n),ha='center',fontsize=8)
        ax.set_xticks(range(len(shown)),[labels.get(v,v) for v in shown],rotation=30,ha='right',fontsize=8)
        ax.set_ylim(0,1.15);ax.set_title(str(dist//1000)+' km');ax.grid(axis='y',alpha=.2)
    axes[0].set_ylabel('Safe-arrival fraction');fig.suptitle('Same-scene evaluation: Wilson 95% intervals (not safety guarantees)')
    fig.tight_layout();save(fig,'success_by_distance')
    controls=[v for v in variants if v!=main];fig,axes=plt.subplots(1,len(controls),figsize=(6*len(controls),4.8),squeeze=False)
    for ax,control in zip(axes[0],controls):
        for i,dist in enumerate([1000,3000,5000]):
            common=[n for n in names if (n,control) in lookup and (n,main) in lookup and lookup[n,main]['distance_m']==dist and lookup[n,main]['success'] and lookup[n,control]['success']]
            diff=[lookup[n,main]['time_s']-lookup[n,control]['time_s'] for n in common]
            if diff:
                offsets=np.linspace(-.11,.11,len(diff));ax.scatter(i+offsets,diff,color=colors[main],s=18,alpha=.65)
                ax.plot([i-.2,i+.2],[statistics.median(diff)]*2,color='black',lw=2)
                ax.text(i,.97,'n='+str(len(diff)),ha='center',transform=ax.get_xaxis_transform(),fontsize=9)
        ax.axhline(0,color='gray',ls='--');ax.set_xticks([0,1,2],['1 km','3 km','5 km']);ax.set_title('Main minus '+labels.get(control,control))
        ax.set_ylabel('Paired travel-time difference (s)');ax.grid(axis='y',alpha=.2)
    fig.suptitle('Common safe arrivals only; dots = scenes, black bar = median; negative is faster')
    fig.tight_layout();save(fig,'paired_efficiency')
    (out/'figure_selection.json').write_text(json.dumps({'stage':stage,'rule':'predeclared family/median rule plus first regression or minimum clearance; no smoothing; no rollouts','main':main,'simple':simple,'display_variants':variants,'labels':labels,'cases':selections},indent=2))
    # A small offline evidence slice: exact plotted positions and actual target events.
    plotted=[];events=[]
    for n in sorted({x['scene_id'] for x in selections}):
        for v in variants:
            dd,jj=data(n,v)
            for x in dd['trajectory']:
                plotted.append(dict(scene_id=n,variant=v,time_s=x['time'],x_m=x['raw'][0],y_m=x['raw'][1],safety_clearance_m=x.get('safety_clearance_m')))
            for x in dd['target_changes']:
                events.append(dict(scene_id=n,variant=v,selected_at=x['selected_at'],applied_at=x['applied_at'],target_x_m=x['target'][0],target_y_m=x['target'][1]))
    for filename,items in [('plotted_trajectories.csv',plotted),('plotted_target_events.csv',events)]:
        if items:
            with (out/filename).open('w',newline='') as ff:
                writer=csv.DictWriter(ff,fieldnames=list(items[0]));writer.writeheader();writer.writerows(items)
    selected_names=sorted({x['scene_id'] for x in selections})
    scene_evidence=[]
    for n in selected_names:
        dd,jj=data(n,main)
        scene_evidence.append({'scene':jj['scene'],'suite':jj['suite'],
            'rows':[lookup[n,v] for v in variants]})
    (out/'plotted_scenes.json').write_text(json.dumps(scene_evidence,indent=2))
    figures=['trajectory_1km','trajectory_3km','trajectory_5km','failure_local','safety_clearance','goal_distance','target_timing','success_by_distance','paired_efficiency']
    if gains:figures.insert(3,'efficiency_example')
    sections=''.join('<section><h2>'+html.escape(n)+'</h2><a href="'+n+'.svg">SVG</a><img loading="lazy" src="'+n+'.png" alt="'+n+'"></section>' for n in figures)
    (out/'index.html').write_text('<!doctype html><html><meta charset="utf-8"><title>R2 actual trajectories and results</title><style>body{font:16px system-ui;max-width:1200px;margin:30px auto;padding:0 20px;background:#fafafa;color:#222}img{width:100%;height:auto}section{background:white;padding:18px;margin:24px 0}h1,h2{font-weight:600}</style><h1>R2 actual trajectories and results</h1><p>Saved simulation logs only. No path smoothing or extension beyond termination. Dashed obstacle circles show the true safety boundary; no fixed tracking guarantee is implied. See figure_selection.json and the report for selection rules and limitations.</p>'+sections+'</html>',encoding='utf-8')
    print(json.dumps(selections,indent=2))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('folder');ap.add_argument('--main',required=True);ap.add_argument('--simple',required=True);ap.add_argument('--out');ap.add_argument('--stage',choices=['development','frozen'],default='development');a=ap.parse_args();generate(a.folder,a.main,a.simple,a.out,a.stage)
