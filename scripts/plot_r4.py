"""R4 real-log figures. Each --figure invocation is independently reproducible."""
from pathlib import Path
import argparse, json, csv, math, html
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
ROOT=Path(__file__).resolve().parents[1]
COLORS=['#0072B2','#D55E00','#009E73','#CC79A7','#E69F00']
plt.rcParams.update({'font.size':10,'font.family':'DejaVu Sans','axes.spines.top':False,
    'axes.spines.right':False,'svg.fonttype':'none'})
def read(p):return json.loads(p.read_text())
def save(fig,out,name):
    fig.tight_layout()
    for ext in ['png','svg','pdf']:fig.savefig(out/(name+'.'+ext),dpi=300,bbox_inches='tight')
    plt.close(fig)
def mapdraw(ax,job):
    for o in job['suite']['maps'][job['scene']['map']]:
        ax.add_patch(Circle(o['center_xy'],o['entity_radius'],color='#888888',alpha=.5))
        ax.add_patch(Circle(o['center_xy'],o['entity_radius']+o['safety_buffer'],fill=False,ls='--',ec='#555555',lw=1))
    ax.set_aspect('equal',adjustable='box');ax.set_xlabel('World x (m)');ax.set_ylabel('World y (m)')
def branch_figure(run,out):
    cases=[('s2271_046_staggered_fast_1000',600,'branches1','branch_away_t600'),
           ('s3271_037_channel_stable_1000',400,'branches_short','branch_away_t400_250')]
    controls={r['scene_id']:r for r in read(run/'replay_check/rows.json')}
    fig,axes=plt.subplots(2,2,figsize=(12,10));indices=[];points=[]
    for k,(sid,t,batch,variant) in enumerate(cases):
        route=next(x for x in read(run/'branches1/rows.json') if x['scene_id']==sid and x['variant']==f'branch_route_t{t}')
        away=next(x for x in read(run/batch/'rows.json') if x['scene_id']==sid and x['variant']==variant)
        rows=[controls[sid],route,away];names=['Continue Relay160','Fresh route','Outward target']
        for j,(row,label) in enumerate(zip(rows,names)):
            raw=ROOT/row['evidence'];d=read(raw);job=read(raw.with_name('job.json'));tr=d['trajectory']
            xy=np.array([x['raw'][:2] for x in tr]);tt=np.array([x['time'] for x in tr]);clear=[x.get('safety_clearance_m') for x in tr]
            status='safe arrival' if row['success'] else 'buffer failure'
            axes[k,0].plot(xy[:,0],xy[:,1],color=COLORS[j],lw=1.5,label=f'{label}: {status}, {int(row["time_s"])} s')
            axes[k,1].plot(tt,clear,color=COLORS[j],lw=1.4,label=label)
            if j==0:
                control_xy=xy.copy()
                mapdraw(axes[k,0],job);p=xy[int(t)];axes[k,0].scatter(*p,c='black',s=28,zorder=6)
                q=tr[int(t)]['target'];axes[k,0].plot([p[0],q[0]],[p[1],q[1]],':',c=COLORS[j]);axes[k,0].scatter(*q,marker='D',c=COLORS[j],s=26)
                bad=next((x for x in tr if x.get('safety_clearance_m') is not None and x['safety_clearance_m']<=0),None)
                if bad:axes[k,0].scatter(*bad['raw'][:2],marker='x',c='black',s=65,zorder=8)
            else:
                event=read(raw.with_name('branch_state.json'))['events'][0];q=event['alternative']
                axes[k,0].plot([p[0],q[0]],[p[1],q[1]],':',c=COLORS[j]);axes[k,0].scatter(*q,marker='D',c=COLORS[j],s=26)
                if j==2:
                    stop=min(len(xy),len(control_xy))
                    response=next((z for z in range(t+1,stop) if np.linalg.norm(xy[z]-control_xy[z])>=5),None)
                    if response is not None:
                        axes[k,1].axvline(response,color=COLORS[j],ls='--',lw=1,label=f'5 m path separation at {response} s')
                        axes[k,0].scatter(*xy[response],marker='s',c=COLORS[j],s=24)
                        indices.append(dict(scene_id=sid,response_definition='First 5 m actual position separation from continue branch; diagnostic, not a tracking bound',response_time_s=response))
            indices.append(dict(scene_id=sid,label=label,row=row))
            points.extend(dict(scene_id=sid,label=label,time_s=x['time'],x_m=x['raw'][0],y_m=x['raw'][1],clearance_m=x.get('safety_clearance_m')) for x in tr)
        axes[k,0].legend(fontsize=7,loc='lower left',bbox_to_anchor=(0,1.01));axes[k,0].text(.01,-.18,f'({chr(97+2*k)}) {sid}; branch at {t} s',transform=axes[k,0].transAxes,fontsize=9)
        axes[k,1].axhline(0,c='black',ls='--');axes[k,1].axvline(t+1,c='gray',ls=':')
        axes[k,1].set_xlim(t-100,t+240);axes[k,1].set_xlabel('Physical time (s)');axes[k,1].set_ylabel('Step safety clearance (m)');axes[k,1].legend(fontsize=8,loc='lower left',bbox_to_anchor=(0,1.01))
        axes[k,1].text(.01,-.18,f'({chr(98+2*k)}) Same prefix; changed target applied at {t+1} s',transform=axes[k,1].transAxes,fontsize=9)
    fig.text(.5,-.035,'Grey discs: obstacle bodies; dashed circles: 60 m safety boundary; dotted lines: target chords; diamonds: targets.\nBlack dot: branch state; black cross: first intrusion of continue branch; green square: first 5 m separation.',ha='center',fontsize=8)
    save(fig,out,'same_state_branches');(out/'same_state_branches_index.json').write_text(json.dumps(indices,indent=2))
    with (out/'same_state_branches_data.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(points[0]));w.writeheader();w.writerows(points)

def response_figure(run,out):
    with (run/'response_segments.csv').open() as f:rows=list(csv.DictReader(f))
    fig,axes=plt.subplots(1,2,figsize=(12,5.2))
    bins=[('<=150 m',lambda d:d<=150),('150-350 m',lambda d:150<d<=350),('>350 m',lambda d:d>350)]
    status=['not_required_small_heading_difference','responded','censored_by_target_change','not_observed_full_window','episode_ended_without_response']
    labels=['Small initial heading error','Observed heading response','Censored: target changed','No response in full window','Episode ended']
    totals=[]
    for i,(name,cond) in enumerate(bins):
        rr=[r for r in rows if cond(float(r['target_distance_m']))];totals.append(len(rr));bottom=0
        for j,s in enumerate(status):
            n=sum(r['response_status']==s for r in rr)
            axes[0].bar(i,n,bottom=bottom,color=COLORS[j],label=labels[j] if i==0 else None);bottom+=n
        axes[0].text(i,bottom+10,'n='+str(len(rr)),ha='center',fontsize=9)
        times=sorted(float(r['heading_response_s']) for r in rr if r['response_status']=='responded')
        if times:axes[1].step(times,np.arange(1,len(times)+1)/len(times),where='post',color=COLORS[i],label=name+f' (n={len(times)})')
    axes[0].set_xticks(range(3),[x[0] for x in bins]);axes[0].set_xlabel('Target distance at application');axes[0].set_ylabel('Target segments (not independent scenes)')
    axes[0].legend(fontsize=7,loc='lower left',bbox_to_anchor=(0,1.05),ncol=2);axes[1].axvline(60,c='black',ls='--',label='60 s working response scale')
    axes[1].set_xlabel('Observed heading-response proxy (s)');axes[1].set_ylabel('Conditional empirical fraction');axes[1].legend(fontsize=8)
    episodes=len({(x['scene_id'],x['variant']) for x in rows})
    axes[0].text(0,-.23,f'(a) All {len(rows):,} segments from {episodes} seen episodes; failures retained',transform=axes[0].transAxes,fontsize=9)
    axes[1].text(0,-.23,'(b) Responders only; censoring prevents a tracking guarantee',transform=axes[1].transAxes,fontsize=9)
    save(fig,out,'response_calibration')

def grace_figure(run,out):
    cases=['s2271_005_channel_slow_1000','s2271_013_channel_stable_3000']
    refs=read(run/'baseline_references.json');rr=read(run/'development2/rows.json')
    names=['Relay160','Without response grace','With response grace']
    fig,axes=plt.subplots(2,2,figsize=(12,10));indices=[];points=[]
    for panel,sid in enumerate(cases):
        baseline=next(x for x in refs if x['scene_id']==sid and x['variant']=='relay_m160')
        rows=[baseline]+[next(x for x in rr if x['scene_id']==sid and x['variant']==v) for v in ['no_grace','response_away']]
        for k,(row,label) in enumerate(zip(rows,names)):
            raw=ROOT/row['evidence'];d=read(raw);job=read(raw.with_name('job.json'));tr=d['trajectory'];xy=np.array([x['raw'][:2] for x in tr]);tt=np.array([x['time'] for x in tr]);ls='--' if k==2 else '-'
            axes[panel,0].plot(xy[:,0],xy[:,1],c=COLORS[k],ls=ls,lw=1.5,label=label+f' ({int(row["time_s"])} s)')
            if k==0:mapdraw(axes[panel,0],job);baseline_trace=tr
            if k==2:assert tr==baseline_trace,'Caption requires identical baseline trace'
            final_distance=np.linalg.norm(xy-np.array(job['scene']['goal']),axis=1)
            axes[panel,1].plot(tt,final_distance,c=COLORS[k],ls=ls,lw=1.4,label=label)
            points.extend(dict(scene_id=sid,label=label,time_s=x['time'],x_m=x['raw'][0],y_m=x['raw'][1],final_distance_m=float(final_distance[i])) for i,x in enumerate(tr))
            indices.append(dict(scene_id=sid,label=label,row=row))
        logs=read((ROOT/rows[-1]['evidence']).with_name('r2_decisions.json'));ev=next(x for x in logs if x.get('event')=='response_grace')
        axes[panel,1].axvline(ev['time'],c='gray',ls=':',label=f'Request at {ev["time"]:g} s; target age {ev["target_age"]:g} s')
        axes[panel,0].legend(fontsize=8,loc='lower left',bbox_to_anchor=(0,1.01));axes[panel,1].legend(fontsize=8,loc='lower left',bbox_to_anchor=(0,1.01))
        axes[panel,1].set_xlabel('Physical time (s)');axes[panel,1].set_ylabel('Distance to final goal (m)')
        delta=rows[2]['time_s']-rows[1]['time_s']
        axes[panel,0].text(0,-.19,sid+'; seen illustrative case',transform=axes[panel,0].transAxes,fontsize=9)
        axes[panel,1].text(0,-.19,f'Grace minus no-grace: {delta:+.0f} s; all three safely arrive',transform=axes[panel,1].transAxes,fontsize=9)
    save(fig,out,'normal_response_case');(out/'normal_response_case_index.json').write_text(json.dumps(dict(selection='005 identified as normal-success diagnostic;013 added to show the opposing effect of grace. Both seen, not a frequency estimate.',records=indices),indent=2))
    with (out/'normal_response_case_data.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(points[0]));w.writeheader();w.writerows(points)

def final_figures(run,out,which):
    from analyze_r1 import outcome
    rows=read(run/'final/analysis_rows.json');main=read(run/'freeze.json')['main_variant']
    variants=['relay_m120','relay_m160',main]+[v for v in sorted({x['variant'] for x in rows}) if v not in ['relay_m120','relay_m160',main]]
    names={'relay_m120':'Relay120','relay_m160':'Relay160','commit_away':'Outward + commitment','no_commit':'Without commitment','commit_route':'Route + commitment'}
    lookup={(x['scene_id'],x['variant']):x for x in rows};ids=sorted({x['scene_id'] for x in rows})
    if which=='statistics':
        fig,axes=plt.subplots(1,2,figsize=(13,4.8));bottom=np.zeros(len(variants));counts={}
        cats=['safe_arrival','buffer_violation','entity_collision','time_limit','region_exit','NoRouteError','NoLocalTargetError']
        cats+=sorted({outcome(x) for x in rows}-set(cats))
        for j,cat in enumerate(cats):
            values=[sum(x['variant']==v and outcome(x)==cat for x in rows) for v in variants]
            if not sum(values):continue
            counts[cat]=values;axes[0].bar(range(len(variants)),values,bottom=bottom,label=cat.replace('_',' '),color=['#009E73','#D55E00','#882255','#E69F00','#777777','#CC79A7','#333333'][min(j,6)])
            for i,n in enumerate(values):
                if n:axes[0].text(i,bottom[i]+n/2,str(n),ha='center',va='center',fontsize=9)
            bottom+=values
        assert all(x==len(ids) for x in bottom),'Every frozen scene must enter each outcome bar'
        axes[0].set_xticks(range(len(variants)),[names.get(v,v) for v in variants],rotation=25,ha='right',fontsize=8);axes[0].set_ylabel('Complete paired missions');axes[0].legend(fontsize=8,loc='lower left',bbox_to_anchor=(0,1.01),ncol=3)
        contrasts=[]
        for c in [v for v in variants if v!=main]:
            common=[n for n in ids if lookup[n,c]['success'] and lookup[n,main]['success']]
            delta=[lookup[n,main]['time_s']-lookup[n,c]['time_s'] for n in common]
            gains=sum(lookup[n,main]['success'] and not lookup[n,c]['success'] for n in ids);losses=sum(lookup[n,c]['success'] and not lookup[n,main]['success'] for n in ids)
            contrasts.append(dict(control=c,common_scene_ids=common,time_differences_s=delta,wins=gains,losses=losses))
            i=len(contrasts)-1
            if delta:
                axes[1].scatter(np.linspace(i-.15,i+.15,len(delta)),delta,s=15,alpha=.6,c=COLORS[i%len(COLORS)])
                axes[1].plot([i-.23,i+.23],[np.median(delta)]*2,c='black',lw=2)
            axes[1].text(i,1.03,f'+{gains}/-{losses}; n={len(common)}',transform=axes[1].get_xaxis_transform(),ha='center',va='bottom',fontsize=8)
        axes[1].set_xticks(range(len(contrasts)),[names.get(x['control'],x['control']) for x in contrasts],rotation=25,ha='right',fontsize=8)
        axes[1].axhline(0,c='gray',ls='--');axes[1].set_ylabel('Main minus control travel time (s)')
        axes[0].text(0,-.38,f'(a) {len(ids)} new instances per method; every failure retained',transform=axes[0].transAxes,fontsize=9)
        axes[1].text(0,-.38,'(b) Common safe arrivals only; line = median; +wins / -losses',transform=axes[1].transAxes,fontsize=9)
        save(fig,out,'frozen_outcomes');(out/'frozen_outcomes_data.json').write_text(json.dumps(dict(variants=variants,outcomes=counts,contrasts=contrasts),indent=2))
    else:
        fig,axes=plt.subplots(1,3,figsize=(15,6));selection=[];points=[]
        for ax,distance_m in zip(axes,[1000,3000,5000]):
            eligible=[n for n in ids if lookup[n,main]['distance_m']==distance_m and lookup[n,main]['layout']!='open']
            lost=[n for n in eligible if not lookup[n,main]['success'] and lookup[n,'relay_m160']['success']]
            won=[n for n in eligible if lookup[n,main]['success'] and not lookup[n,'relay_m160']['success']]
            common=[n for n in eligible if lookup[n,main]['success'] and lookup[n,'relay_m160']['success']]
            sid=lost[0] if lost else won[0] if won else max(common,key=lambda n:lookup[n,main]['time_s']-lookup[n,'relay_m160']['time_s']) if common else eligible[0]
            rule='first safe-arrival loss' if lost else 'first safe-arrival gain' if won else 'largest common-success time cost' if common else 'first non-open case'
            for k,v in enumerate(['relay_m120','relay_m160',main]):
                row=lookup[sid,v];raw=ROOT/row['evidence'];data=read(raw);job=read(raw.with_name('job.json'));xy=np.array([x['raw'][:2] for x in data['trajectory']]);status=outcome(row).replace('_',' ')
                ax.plot(xy[:,0],xy[:,1],c=COLORS[k],lw=1.3,label=names.get(v,v)+f': {status}, {int(row["time_s"])} s')
                ax.scatter(*xy[-1],marker='o' if row['success'] else 'x',c=COLORS[k],s=30)
                if k==0:mapdraw(ax,job);ax.scatter(*job['scene']['goal'],marker='*',c='black',s=65)
                selection.append(dict(scene_id=sid,distance_m=distance_m,selection_rule=rule,row=row))
                points.extend(dict(scene_id=sid,variant=v,time_s=x['time'],x_m=x['raw'][0],y_m=x['raw'][1],clearance_m=x.get('safety_clearance_m')) for x in data['trajectory'])
            ax.legend(fontsize=7,loc='lower left',bbox_to_anchor=(0,1.01));fig.text(({1000:0,3000:1,5000:2}[distance_m]+.5)/3,-.035,sid+'\nPosthoc: '+rule,ha='center',fontsize=8)
        fig.text(.5,-.115,'Grey discs: obstacle bodies; dashed circles: 60 m safety boundary; solid curves: actual paths.\nStar: final goal; circle: safe endpoint; cross: failed endpoint (not necessarily first intrusion).',ha='center',fontsize=8)
        save(fig,out,'frozen_actual_paths');(out/'frozen_actual_paths_index.json').write_text(json.dumps(selection,indent=2))
        with (out/'frozen_actual_paths_data.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(points[0]));w.writeheader();w.writerows(points)

def commitment_figure(run,out):
    sid='s3271_037_channel_stable_1000';allrows=read(run/'confirmation/rows.json')
    rows=[next(x for x in allrows if x['scene_id']==sid and x['variant']==v) for v in ['commit_away','no_commit']]
    fig,axes=plt.subplots(2,2,figsize=(12,9));points=[];indices=[]
    for k,row in enumerate(rows):
        raw=ROOT/row['evidence'];d=read(raw);job=read(raw.with_name('job.json'));tr=d['trajectory'];xy=np.array([x['raw'][:2] for x in tr]);tt=np.array([x['time'] for x in tr]);color=COLORS[2] if k==0 else COLORS[1];label='With commitment' if k==0 else 'Without commitment'
        axes[0,0].plot(xy[:,0],xy[:,1],c=color,lw=1.5,label=label+f' ({int(row["time_s"])} s)')
        axes[0,1].plot(tt,[x.get('safety_clearance_m') for x in tr],c=color,lw=1.5,label=label)
        axes[1,1].plot(tt,np.linalg.norm(xy-np.array(job['scene']['goal']),axis=1),c=color,label=label)
        applied=[x['applied_at'] for x in d['target_changes']];axes[1,0].scatter(applied,[k]*len(applied),c=color,marker='|',s=180,label=label)
        if k==0:
            mapdraw(axes[0,0],job);p=xy[587];axes[0,0].scatter(*p,c='black',s=30)
            escape=next(x['target'] for x in d['target_changes'] if x['selected_at']==586)
            axes[0,0].plot([p[0],escape[0]],[p[1],escape[1]],':',c=color);axes[0,0].scatter(*escape,c=color,marker='D',s=30)
        else:
            replacement=next(x['target'] for x in d['target_changes'] if x['selected_at']==587)
            axes[0,0].plot([p[0],replacement[0]],[p[1],replacement[1]],':',c=color);axes[0,0].scatter(*replacement,c=color,marker='D',s=30)
            bad=next(x for x in tr if x.get('safety_clearance_m') is not None and x['safety_clearance_m']<=0);axes[0,0].scatter(*bad['raw'][:2],marker='x',c='black',s=60)
        indices.append(row);points.extend(dict(variant=row['variant'],time_s=x['time'],x_m=x['raw'][0],y_m=x['raw'][1],clearance_m=x.get('safety_clearance_m')) for x in tr)
    axes[0,0].set_xlim(200,940);axes[0,0].set_ylim(-600,-150);axes[0,0].legend(fontsize=8)
    axes[0,1].set_xlim(540,800);axes[0,1].set_ylim(-5,max(x['clearance_m'] for x in points if 540<=x['time_s']<=800)+10);axes[0,1].axhline(0,c='black',ls='--');axes[0,1].axvline(587,c='gray',ls=':');axes[0,1].set_xlabel('Physical time (s)');axes[0,1].set_ylabel('Step safety clearance (m)');axes[0,1].legend(fontsize=8,loc='upper left')
    axes[1,0].set_xlim(570,700);axes[1,0].set_ylim(-.5,1.5);axes[1,0].set_yticks([0,1],['With commitment','Without commitment']);axes[1,0].set_xlabel('Actual target application time (s)');axes[1,0].axvspan(587,647,color=COLORS[2],alpha=.1);axes[1,0].text(617,.5,'Conditional 60 s\ncommitment window',ha='center',va='center',fontsize=9)
    axes[1,1].set_xlabel('Physical time (s)');axes[1,1].set_ylabel('Distance to final goal (m)');axes[1,1].legend(fontsize=8)
    captions=['(a) s3271_037_channel_stable_1000 (local)\nDotted lines are target chords','(b) Positions/actions diverge at 589 s;\nseparation reaches 5 m at 604 s','(c) Escape applied at 587 s; no-commit replaces it at 588 s','(d) Full missions; failure is not counted as faster']
    for i,(ax,c) in enumerate(zip(axes.flat,captions)):ax.text(0,-.36 if i==0 else -.2,c,transform=ax.transAxes,fontsize=9)
    fig.text(.5,-.035,'Grey discs: obstacle bodies; dashed circles: 60 m safety boundary; dotted lines: target chords; diamonds: targets.\nBlack dot: state at 587 s; black cross: first intrusion without commitment. Actual paths are solid curves.',ha='center',fontsize=8)
    save(fig,out,'commitment_case');(out/'commitment_case_index.json').write_text(json.dumps(dict(scene_id=sid,scope='Seen paired ablation, full task; first later difference selected posthoc to explain observed failure',rows=indices),indent=2))
    with (out/'commitment_case_data.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(points[0]));w.writeheader();w.writerows(points)

def effect_figure(run,out):
    cases=['s4271_025_channel_stable_5000','s5271_001_channel_stable_1000']
    rr=read(run/'final/analysis_rows.json');fig,axes=plt.subplots(2,2,figsize=(12,10));indices=[];points=[]
    names={'relay_m120':'Relay120','relay_m160':'Relay160','commit_away':'Outward + commitment'}
    for panel,sid in enumerate(cases):
        for k,v in enumerate(['relay_m120','relay_m160','commit_away']):
            row=next(x for x in rr if x['scene_id']==sid and x['variant']==v)
            raw=ROOT/row['evidence'];d=read(raw);job=read(raw.with_name('job.json'));tr=d['trajectory']
            xy=np.array([x['raw'][:2] for x in tr]);tt=np.array([x['time'] for x in tr]);dist=np.linalg.norm(xy-np.array(job['scene']['goal']),axis=1)
            local=tt<=600
            axes[panel,0].plot(xy[local,0],xy[local,1],c=COLORS[k],lw=1.4,label=names[v])
            axes[panel,1].plot(tt,dist,c=COLORS[k],lw=1.4,label=names[v]+f' ({int(row["time_s"])} s)')
            if k==0:mapdraw(axes[panel,0],job)
            if k==2:
                ev=read(raw.with_name('r2_decisions.json'))[0];p=ev['position'];q=ev['target']
                axes[panel,0].plot([p[0],q[0]],[p[1],q[1]],':',c=COLORS[k]);axes[panel,0].scatter(*p,c='black',s=28);axes[panel,0].scatter(*q,marker='D',c=COLORS[k],s=28)
                axes[panel,1].axvline(ev['time']+1,c='grey',ls=':',label=f'Target applied at {ev["time"]+1:g} s')
            indices.append(dict(scene_id=sid,row=row,selection='Posthoc largest time gain and largest time loss relative to Relay160 among four changed frozen scenes. Relay120 retained as a strong comparator.'))
            points.extend(dict(scene_id=sid,variant=v,time_s=x['time'],x_m=x['raw'][0],y_m=x['raw'][1],final_distance_m=float(dist[i])) for i,x in enumerate(tr))
        if panel==0:axes[panel,0].set_xlim(-550,750);axes[panel,0].set_ylim(-100,800)
        else:axes[panel,0].set_xlim(100,650);axes[panel,0].set_ylim(-650,120)
        axes[panel,0].legend(fontsize=8,loc='lower left',bbox_to_anchor=(0,1.01),ncol=2)
        axes[panel,1].legend(fontsize=8,loc='lower left',bbox_to_anchor=(0,1.01),ncol=2)
        axes[panel,1].set_xlabel('Physical time (s)');axes[panel,1].set_ylabel('Distance to final goal (m)')
        axes[panel,0].text(0,-.19,sid+'\nLocal view; first 600 s of actual traces only',transform=axes[panel,0].transAxes,fontsize=8)
        axes[panel,1].text(0,-.19,'Full missions; all three safely arrive\nNo-commit trace equals main and is omitted here',transform=axes[panel,1].transAxes,fontsize=8)
    fig.text(.5,-.035,'Grey discs: obstacle bodies; dashed circles: 60 m safety boundary; solid curves: actual paths.\nDotted chord and diamond: intervention target; black dot: decision state. No smoothing or extension.\nPosthoc largest gain / largest slowdown versus Relay160.',ha='center',fontsize=8)
    save(fig,out,'frozen_intervention_cases');(out/'frozen_intervention_cases_index.json').write_text(json.dumps(indices,indent=2))
    with (out/'frozen_intervention_cases_data.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(points[0]));w.writeheader();w.writerows(points)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('run');ap.add_argument('--figure',choices=['branches','response','grace','commitment','statistics','paths','effects'],required=True);a=ap.parse_args()
    run=Path(a.run).resolve();out=run/'figures';out.mkdir(exist_ok=True)
    if a.figure in ['statistics','paths']:final_figures(run,out,a.figure)
    else:{'branches':branch_figure,'response':response_figure,'grace':grace_figure,'commitment':commitment_figure,'effects':effect_figure}[a.figure](run,out)
