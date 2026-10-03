#!/usr/bin/env python3
"""R3 publication plots extending the existing trajectory plotter; all paths from raw logs."""
from pathlib import Path
import sys,json,argparse,math,html,csv
import plot_r2 as base
from analyze_r1 import outcome
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle,FancyBboxPatch
ROOT=Path(__file__).resolve().parents[1]
def save(fig,out,name):
    fig.savefig(out/(name+'.png'),dpi=300,bbox_inches='tight');fig.savefig(out/(name+'.svg'),bbox_inches='tight');plt.close(fig)
def additions(folder,main,simple,out,case=None,stage="frozen",case_name="intervention_case"):
    out.mkdir(parents=True,exist_ok=True)
    rows=json.loads((folder/'analysis_rows.json').read_text());variants=list(dict.fromkeys(['geom80',simple,main]+sorted({r['variant'] for r in rows})))
    fig,axes=plt.subplots(1,2,figsize=(12,4.6));cats=['safe_arrival','buffer_violation','entity_collision','timeout','other']
    colors=['#009E73','#D55E00','#882255','#E69F00','#777777']
    mapping={}
    for v in variants:
        rr=[r for r in rows if r['variant']==v];mapping[v]={}
        for r in rr:
            name=outcome(r);mapping[v][name]=mapping[v].get(name,0)+1
    # Preserve the canonical analyzer's categories verbatim.
    allcats=sorted({k for v in mapping.values() for k in v});bottom=np.zeros(len(variants))
    for i,c in enumerate(allcats):
        vals=np.array([mapping[v].get(c,0) for v in variants]);axes[0].bar(range(len(variants)),vals,bottom=bottom,label=c,color={'safe_arrival':'#009E73','buffer_violation':'#D55E00','entity_collision':'#882255','time_limit':'#E69F00'}.get(c,'#777777'))
        for j,val in enumerate(vals):
            if val:axes[0].text(j,bottom[j]+val/2,str(val),ha='center',va='center',fontsize=9)
        bottom+=vals
    axes[0].set_xticks(range(len(variants)),variants,rotation=30,ha='right',fontsize=8);axes[0].set_ylabel('Complete paired episodes');axes[0].legend(fontsize=8);axes[0].set_title('Full-task outcomes; no failure counted as faster')
    paired=json.loads((folder/'analysis.json').read_text())['pairs'];shown=[]
    for p in paired:
        if not p:continue
        # Detailed direction is read from the existing analyzer below.
    lookup={(r['scene_id'],r['variant']):r for r in rows}
    for control in variants:
        if control==main:continue
        ids=sorted(n for n,v in lookup if v==main and (n,control) in lookup and lookup[n,main]['success'] and lookup[n,control]['success'])
        dif=[lookup[n,main]['time_s']-lookup[n,control]['time_s'] for n in ids]
        if dif:shown.append((control,ids,dif))
    for i,(control,ids,dif) in enumerate(shown):
        axes[1].scatter(np.linspace(i-.12,i+.12,len(dif)),dif,s=13,alpha=.6,color='#0072B2')
        axes[1].plot([i-.2,i+.2],[float(np.median(dif))]*2,c='black',lw=2)
        axes[1].text(i,.98,'n='+str(len(ids)),ha='center',va='top',transform=axes[1].get_xaxis_transform(),fontsize=8)
    axes[1].set_xticks(range(len(shown)),[x[0] for x in shown],rotation=30,ha='right',fontsize=8);axes[1].axhline(0,c='gray',ls='--');axes[1].set_ylabel('Main minus control travel time (s)');axes[1].set_title('Common safe arrivals only; bar = median')
    fig.suptitle(('Frozen comparison: ' if stage=='frozen' else 'Seen-development comparison: ')+main);fig.tight_layout();save(fig,out,'outcomes_and_efficiency')
    (out/'statistical_plot_data.json').write_text(json.dumps(dict(outcomes=mapping,pairs=[dict(control=x[0],scene_ids=x[1],time_differences=x[2]) for x in shown]),indent=2))
    # Schematic names only inputs and rules actually used by the selected config.
    sample=next(r for r in rows if r['variant']==main)
    job=json.loads((ROOT/sample['evidence']).with_name('job.json').read_text())
    cfg=job['config'];kind=job.get('planner_kind','r1')
    if kind=='relay':
        visible='Known static map\nCurrent position\nCurrent and final targets'
        rule=f"Margin cap {cfg.get('margin',80):g} m; A* 25 m\nRoute lookahead {cfg.get('lookahead',500):g} m\nHandoff {cfg.get('handoff',40):g} m / chord risk"
    elif kind=='risk':
        visible='Known static map\nPosition / heading / clock\nCurrent and final targets'
        if cfg.get('closing_gate',False):visible+='\nPast 10 s positions'
        response='Retain 20 s / 15-point acceptance' if cfg.get('response')=='replan_only' else 'Bypass target acceptance gates'
        rule=f"Margin cap {cfg.get('margin',80):g} m; R1 base\nClearance request < {cfg.get('threshold',60):g} m\n{response}"
    else:
        visible='Known static map\nPosition / heading / clock\nCurrent and final targets'
        rule=f"Margin cap {cfg.get('margin',80):g} m; A* 25 m\nFeasible route / radial targets\nPeriod {cfg.get('period',10):g} s; hold {cfg.get('hold',20):g} s"
    fig,ax=plt.subplots(figsize=(12,3.5));ax.axis('off')
    boxes=[(.01,.42,.20,.38,visible),(.27,.42,.26,.38,rule),(.59,.42,.18,.38,'Rigid target frame\nFrozen SAC-LSTM\nReal-history re-encoding'),(.83,.42,.16,.38,'Sail / rudder action\nUnchanged physics\nOne-second step')]
    for x,y,w,h,txt in boxes:
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.008',fc='#eef3f8',ec='#3b5268'));ax.text(x+w/2,y+h/2,txt,ha='center',va='center',fontsize=9)
    for left,right in [(.22,.26),(.54,.58),(.78,.82)]:ax.annotate('',xy=(right,.61),xytext=(left,.61),arrowprops=dict(arrowstyle='->'))
    ax.text(.555,.85,'waypoint',ha='center',fontsize=8)
    ax.annotate('',xy=(.1,.4),xytext=(.91,.4),arrowprops=dict(arrowstyle='->',connectionstyle='bar,fraction=.16'))
    ax.plot([.91,.91,.68],[.4,.33,.33],c='#3b5268',lw=.9)
    ax.annotate('',xy=(.68,.4),xytext=(.68,.33),arrowprops=dict(arrowstyle='->',color='#3b5268'))
    ax.text(.8,.35,'Physical observation',ha='center',fontsize=8)
    ax.text(.5,.18,'Observed-state feedback; no direct / future wind supplied to the planner or actor',ha='center',fontsize=9)
    ax.text(.5,.04,'At t: actor uses current target. A new target selected at t is applied at t+1.',ha='center',fontsize=9)
    ax.set_title(main+' | Interface schematic, not an experimental result or safety certificate');save(fig,out,'method_framework')
    if case:
        c=json.loads(Path(case).read_text())
        if c:
            fig,axes=plt.subplots(2,2,figsize=(12,9));st=c['selected_at'];ap=c['applied_at'];p=np.array(c['common_input']['position_xy']);cs=['#0072B2','#D55E00'];details=[];window_clear=[];trace_rows=[]
            for k,row in enumerate(c['episode_rows']):
                raw=ROOT/row['evidence'];d=json.loads(raw.read_text());j=json.loads(raw.with_name('job.json').read_text());tr=d['trajectory'];xy=np.array([x['raw'][:2] for x in tr]);tt=np.array([x['time'] for x in tr]);label=row['variant']+' | '+outcome(row)+', '+str(int(row['time_s']))+' s'
                axes[0,0].plot(xy[:,0],xy[:,1],c=cs[k],lw=1.4,label=label)
                window_clear.extend(x['safety_clearance_m'] for x in tr if st-100<=x['time']<=st+250 and x.get('safety_clearance_m') is not None)
                axes[0,1].plot(tt,[np.nan if x.get('safety_clearance_m') is None else x['safety_clearance_m'] for x in tr],c=cs[k],label=row['variant'])
                axes[1,0].plot(tt,np.linalg.norm(xy-np.array(j['scene']['goal']),axis=1),c=cs[k],label=row['variant'])
                for ch in d['target_changes']:
                    if st-100<=ch['selected_at']<=st+100:axes[1,1].plot([ch['selected_at'],ch['applied_at']],[k,k],c=cs[k],marker='|',markersize=12)
                trace_rows.extend(dict(scene_id=c['scene_id'],variant=row['variant'],time_s=x['time'],x_m=x['raw'][0],y_m=x['raw'][1],safety_clearance_m=x.get('safety_clearance_m')) for x in tr)
                details.append(dict(row=row,job=j,events=[x for x in d['target_changes'] if st-100<=x['selected_at']<=st+100]))
                if k==1:
                    for o in j['suite']['maps'][j['scene']['map']]:
                        axes[0,0].add_patch(Circle(o['center_xy'],o['entity_radius'],fc='#777777',alpha=.4))
                        axes[0,0].add_patch(Circle(o['center_xy'],o['entity_radius']+o['safety_buffer'],fill=False,ls='--',ec='#777777'))
            axes[0,0].scatter(*p,c='black',marker='o',s=30,label='Shared state at t='+str(int(st)))
            for k,key in enumerate(['baseline','proposed']):
                q=np.array(c[key]['target_xy']);axes[0,0].plot([p[0],q[0]],[p[1],q[1]],':',c=cs[k],label='Proposed chord: '+key);axes[0,0].scatter(*q,c=cs[k],marker='D',s=25)
            targets=np.array([p,c['baseline']['target_xy'],c['proposed']['target_xy']]);lo=targets.min(axis=0)-100;hi=targets.max(axis=0)+100
            axes[0,0].set_xlim(lo[0],hi[0]);axes[0,0].set_ylim(lo[1],hi[1]);axes[0,0].set_aspect('equal',adjustable='box');axes[0,0].set_xlabel('World x (m)');axes[0,0].set_ylabel('World y (m)');axes[0,0].legend(fontsize=7);axes[0,0].set_title('Local executed paths and common-state targets')
            if window_clear:axes[0,1].set_ylim(min(-5,min(window_clear)-10),max(window_clear)+10)
            axes[0,1].axhline(0,c='black',ls='--');axes[0,1].axvline(st,c='gray',ls=':');axes[0,1].set_xlim(max(0,st-100),st+250);axes[0,1].set_ylabel('True per-step safety clearance (m)');axes[0,1].set_title('Shared decision time; request history in evidence')
            axes[1,0].set_ylabel('Distance to final goal (m)');axes[1,0].set_title('Complete episode; each curve ends at actual termination')
            axes[1,1].axvline(st,c='gray',ls=':');axes[1,1].set_yticks([0,1],[r['variant'] for r in c['episode_rows']]);axes[1,1].set_xlim(max(0,st-25),st+35);axes[1,1].set_ylim(-.5,1.5);axes[1,1].set_title('Actual target applications (selected t to applied t+1)')
            for a in [axes[0,1],axes[1,0],axes[1,1]]:a.set_xlabel('Physical time (s)');a.grid(alpha=.2)
            axes[0,1].legend(fontsize=8);axes[1,0].legend(fontsize=8);fig.suptitle(c['scene_id']+' | First target divergence; full outcomes retained');fig.tight_layout();save(fig,out,case_name)
            (out/(case_name+'_evidence.json')).write_text(json.dumps(dict(case=c,plot_details=details),indent=2))
            with (out/(case_name+'_trajectories.csv')).open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(trace_rows[0]));w.writeheader();w.writerows(trace_rows)
    images=sorted(p.stem for p in out.glob('*.png'));sections=''.join('<section><h2>'+html.escape(n)+'</h2><a href="'+n+'.svg">SVG</a><img src="'+n+'.png" loading="lazy"></section>' for n in images)
    (out/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>R3 CCDC evidence gallery</title><style>body{font:16px system-ui;max-width:1250px;margin:auto;padding:24px}img{width:100%}section{margin:32px 0}</style><h1>R3 CCDC evidence gallery</h1><p>Raw closed-loop paths, no smoothing, no extension after termination. Framework is a schematic. Selection rules and data are saved beside figures.</p>'+sections)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('folder');ap.add_argument('--main',required=True);ap.add_argument('--simple',required=True);ap.add_argument('--out',required=True);ap.add_argument('--case');ap.add_argument('--stage',choices=['development','frozen'],default='frozen');ap.add_argument('--case-name',default='intervention_case');ap.add_argument('--only-additions',action='store_true');a=ap.parse_args();folder=Path(a.folder).resolve();out=Path(a.out).resolve()
    if not a.only_additions:base.generate(folder,a.main,a.simple,out,a.stage,research_round='R3',reference_margin=80.)
    additions(folder,a.main,a.simple,out,a.case,a.stage,a.case_name)
