#!/usr/bin/env python3
"""R3 publication plots extending the existing trajectory plotter; all paths from raw logs."""
from pathlib import Path
import sys,json,argparse,math,html
import plot_r2 as base
from analyze_r1 import outcome
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle,FancyBboxPatch
ROOT=Path(__file__).resolve().parents[1]
def save(fig,out,name):
    fig.savefig(out/(name+'.png'),dpi=300,bbox_inches='tight');fig.savefig(out/(name+'.svg'),bbox_inches='tight');plt.close(fig)
def additions(folder,main,simple,out,case=None):
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
    fig.suptitle('Frozen comparison: '+main);fig.tight_layout();save(fig,out,'outcomes_and_efficiency')
    (out/'statistical_plot_data.json').write_text(json.dumps(dict(outcomes=mapping,pairs=[dict(control=x[0],scene_ids=x[1],time_differences=x[2]) for x in shown]),indent=2))
    # A schematic is explicitly separate from experimental trajectory evidence.
    fig,ax=plt.subplots(figsize=(10,3.3));ax.axis('off')
    boxes=[(.02,.42,.22,.38,'Known static map\nCurrent position/heading\nCausal motion history'),(.34,.42,.27,.38,'High-level route / target\nEmpirical planning margin\nNormal holding / risk request'),(.73,.42,.24,.38,'Frozen SAC-LSTM@7200\nUnchanged sail/rudder\nOne-second physics step')]
    for x,y,w,h,text in boxes:
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.015',fc='#eef3f8',ec='#3b5268'));ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=10)
    ax.annotate('',xy=(.32,.62),xytext=(.25,.62),arrowprops=dict(arrowstyle='->'));ax.annotate('',xy=(.71,.62),xytext=(.62,.62),arrowprops=dict(arrowstyle='->'))
    ax.text(.67,.85,'waypoint\napplied at t+1',ha='center',fontsize=9)
    ax.annotate('',xy=(.12,.4),xytext=(.85,.4),arrowprops=dict(arrowstyle='->',connectionstyle='bar,fraction=.22'));ax.text(.5,.10,'Executed position/history feedback; no direct or future wind input',ha='center',fontsize=10)
    ax.set_title('Interface schematic, not a safety certificate or experimental result');save(fig,out,'method_framework')
    if case:
        c=json.loads(Path(case).read_text())
        if c:
            fig,axes=plt.subplots(2,2,figsize=(12,9));st=c['selected_at'];ap=c['applied_at'];p=np.array(c['common_input']['position_xy']);cs=['#0072B2','#D55E00'];details=[]
            for k,row in enumerate(c['episode_rows']):
                raw=ROOT/row['evidence'];d=json.loads(raw.read_text());j=json.loads(raw.with_name('job.json').read_text());tr=d['trajectory'];xy=np.array([x['raw'][:2] for x in tr]);tt=np.array([x['time'] for x in tr]);label=row['variant']+' | '+outcome(row)+', '+str(int(row['time_s']))+' s'
                axes[0,0].plot(xy[:,0],xy[:,1],c=cs[k],lw=1.4,label=label)
                axes[0,1].plot(tt,[np.nan if x.get('safety_clearance_m') is None else x['safety_clearance_m'] for x in tr],c=cs[k],label=row['variant'])
                axes[1,0].plot(tt,np.linalg.norm(xy-np.array(j['scene']['goal']),axis=1),c=cs[k],label=row['variant'])
                for ch in d['target_changes']:
                    if st-100<=ch['selected_at']<=st+100:axes[1,1].plot([ch['selected_at'],ch['applied_at']],[k,k],c=cs[k],marker='|',markersize=12)
                details.append(dict(row=row,events=[x for x in d['target_changes'] if st-100<=x['selected_at']<=st+100]))
                if k==1:
                    for o in j['suite']['maps'][j['scene']['map']]:
                        axes[0,0].add_patch(Circle(o['center_xy'],o['entity_radius'],fc='#777777',alpha=.4))
                        axes[0,0].add_patch(Circle(o['center_xy'],o['entity_radius']+o['safety_buffer'],fill=False,ls='--',ec='#777777'))
            axes[0,0].scatter(*p,c='black',marker='o',s=30,label='Shared state at t='+str(int(st)))
            for k,key in enumerate(['baseline','proposed']):
                q=np.array(c[key]['target_xy']);axes[0,0].plot([p[0],q[0]],[p[1],q[1]],':',c=cs[k],label='Proposed chord: '+key);axes[0,0].scatter(*q,c=cs[k],marker='D',s=25)
            targets=np.array([p,c['baseline']['target_xy'],c['proposed']['target_xy']]);lo=targets.min(axis=0)-100;hi=targets.max(axis=0)+100
            axes[0,0].set_xlim(lo[0],hi[0]);axes[0,0].set_ylim(lo[1],hi[1]);axes[0,0].set_aspect('equal',adjustable='box');axes[0,0].set_xlabel('World x (m)');axes[0,0].set_ylabel('World y (m)');axes[0,0].legend(fontsize=7);axes[0,0].set_title('Local executed paths and common-state targets')
            axes[0,1].axhline(0,c='black',ls='--');axes[0,1].axvline(st,c='gray',ls=':');axes[0,1].set_xlim(max(0,st-100),st+250);axes[0,1].set_ylabel('True per-step safety clearance (m)');axes[0,1].set_title('Shared decision time; request history in evidence')
            axes[1,0].set_ylabel('Distance to final goal (m)');axes[1,0].set_title('Complete episode; each curve ends at actual termination')
            axes[1,1].axvline(st,c='gray',ls=':');axes[1,1].set_yticks([0,1],[r['variant'] for r in c['episode_rows']]);axes[1,1].set_xlim(max(0,st-100),st+100);axes[1,1].set_ylim(-.5,1.5);axes[1,1].set_title('Actual target applications (selected t to applied t+1)')
            for a in [axes[0,1],axes[1,0],axes[1,1]]:a.set_xlabel('Physical time (s)');a.grid(alpha=.2)
            axes[0,1].legend(fontsize=8);axes[1,0].legend(fontsize=8);fig.suptitle(c['scene_id']+' | First target divergence; full outcomes retained');fig.tight_layout();save(fig,out,'intervention_case')
            (out/'intervention_evidence.json').write_text(json.dumps(dict(case=c,plot_details=details),indent=2))
    images=sorted(p.stem for p in out.glob('*.png'));sections=''.join('<section><h2>'+html.escape(n)+'</h2><a href="'+n+'.svg">SVG</a><img src="'+n+'.png" loading="lazy"></section>' for n in images)
    (out/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>R3 CCDC evidence gallery</title><style>body{font:16px system-ui;max-width:1250px;margin:auto;padding:24px}img{width:100%}section{margin:32px 0}</style><h1>R3 CCDC evidence gallery</h1><p>Raw closed-loop paths, no smoothing, no extension after termination. Framework is a schematic. Selection rules and data are saved beside figures.</p>'+sections)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('folder');ap.add_argument('--main',required=True);ap.add_argument('--simple',required=True);ap.add_argument('--out',required=True);ap.add_argument('--case');a=ap.parse_args();folder=Path(a.folder).resolve();out=Path(a.out).resolve()
    base.generate(folder,a.main,a.simple,out,'frozen',research_round='R3',reference_margin=80.)
    additions(folder,a.main,a.simple,out,a.case)
