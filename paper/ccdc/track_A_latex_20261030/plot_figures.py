"""Reproduce polished Figures 2–6 from portable frozen plot_data.json.
Run all: python plot_figures.py; one: python plot_figures.py figure3_guard
No model, simulator, weights, or machine-specific source directory is needed.
"""
from pathlib import Path
import json,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from matplotlib.lines import Line2D
P=Path(__file__).resolve().parent; D=json.loads((P/'plot_data.json').read_text()); O=P/'figures'
plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman','DejaVu Serif'],'font.size':8,'axes.labelsize':8,'xtick.labelsize':7.5,'ytick.labelsize':7.5,'legend.fontsize':7.5,'pdf.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.65,'lines.linewidth':1.2,'savefig.dpi':300,'path.simplify':False})
C={'reactive':'#397F79','simple':'#B78147','sampled':'#507DA5'}; L={'reactive':'R','simple':'L','sampled':'S15'}; M={'reactive':'s','simple':'^','sampled':'o'}; S={'reactive':':','simple':'--','sampled':'-'}
def save(f,n):
 for ext in ['png','pdf','svg']:f.savefig(O/(n+'.'+ext),dpi=300)
 plt.close(f)
def tidy(ax):
 for i,a in enumerate(np.atleast_1d(ax)):
  a.grid(axis='y',color='#DCE1E4',lw=.5,zorder=0);a.set_axisbelow(True)
  a.text(-.18,1.02,'('+chr(97+i)+')',transform=a.transAxes,fontsize=8,va='bottom')
def key(fig,methods=('reactive','simple','sampled'),y=.99):
 fig.legend([Line2D([],[],marker=M[v],ls='',color=C[v],ms=4) for v in methods],[L[v] for v in methods],loc='upper center',bbox_to_anchor=(.55,y),ncol=len(methods),frameon=False,handletextpad=.4,columnspacing=1.8)
def confirmation():
 ids=D['ids'];r={(x['scene_id'],x['variant']):x for x in D['confirmation']}
 f,ax=plt.subplots(3,1,figsize=(3.4,4.05),sharex=True,gridspec_kw={'height_ratios':[1.55,1.8,.65]});f.subplots_adjust(left=.19,right=.98,bottom=.12,top=.9,hspace=.30)
 for v,off in [('sampled',-.14),('simple',.14)]:
  pairs=[(i+1+off,float(r[s,v]['time_s'])-float(r[s,'reactive']['time_s'])) for i,s in enumerate(ids) if r[s,v]['success']=='True' and r[s,'reactive']['success']=='True']
  ax[0].scatter(*zip(*pairs),s=14,c=C[v],marker=M[v],zorder=3)
 for j,v in enumerate(C):
  ax[1].scatter(np.arange(1,25)+(j-1)*.2,[float(r[s,v]['min_dynamic_margin']) for s in ids],s=13,c=C[v],marker=M[v],zorder=3)
  for i,s in enumerate(ids):ax[2].scatter(i+1,j,marker='o' if r[s,v]['success']=='True' else 'x',s=12,c=C[v],linewidths=1,zorder=3)
 ax[0].set(ylabel='Δtime vs R (s)',ylim=(-35,330),yticks=[0,100,200,300]);ax[1].set_ylabel('Dynamic margin (m)');ax[1].set_yscale('symlog',linthresh=3);ax[1].set_yticks([-1,0,3,30,300]);ax[1].set_yticklabels(['−1','0','3','30','300'])
 ax[1].set_ylim(-3,420)
 ax[2].set(yticks=[0,1,2],yticklabels=['R','L','S15'],xlabel='Task index',ylim=(-.4,2.4),xticks=[1,8,12,16,20,24],xlim=(.45,24.55))
 for a in ax[:2]:a.axhline(0,c='#586168',lw=.65,zorder=1)
 tidy(ax);key(f);save(f,'figure2_confirmation')
def guard():
 g=[0,15,30,60];rr=[D['guard']['guard'+str(x)] for x in g];f,ax=plt.subplots(2,1,figsize=(3.4,2.8),sharex=True);f.subplots_adjust(left=.19,right=.98,bottom=.18,top=.93,hspace=.32)
 for k,label,style in [('mean','Mean','o-'),('max','Maximum','s--')]:ax[0].plot(g,[r['common_safe_time_delta_vs_R'][k] for r in rr],style,c=C['sampled'],mfc=C['sampled'] if k=='mean' else 'white',ms=3.5,label=label)
 ax[0].set_ylabel('Δtime vs R (s)');ax[0].legend(frameon=False,loc='center right',handlelength=2.2)
 ax[1].plot(g,[r['min_dynamic_margin'] for r in rr],'o-',c=C['sampled'],ms=3.5);ax[1].set(ylabel='Worst margin (m)',xlabel='Prediction guard ρ (m)',xticks=g);ax[1].axhline(0,c='#586168',lw=.65);tidy(ax);save(f,'figure3_guard')
def prediction():
 q=D['prediction'];f,ax=plt.subplots(2,1,figsize=(3.4,3.4),sharex=True);f.subplots_adjust(left=.19,right=.98,bottom=.18,top=.91,hspace=.23)
 for k,x in enumerate(q):
  for prefix,v,off in [('detailed','sampled',-.08),('simple','simple',.08)]:
   ix=k//2+1+(-.2 if k%2==0 else .2)+off;kw=dict(marker='o' if k%2==0 else '^',ls='',ms=4,c=C[v],mfc=C[v] if v=='sampled' else 'white',mew=.85)
   ax[0].plot(ix,x[prefix+'_max_error'],**kw);ax[1].plot(ix,x[prefix+'_margin_common']-x['actual_margin_common'],**kw)
 ax[0].set(yscale='log',ylabel='Max. position error (m)');ax[1].set(ylabel='Margin residual (m)',xlabel='Snapshot / protocols',xticks=range(1,7),xticklabels=['1\n−90/N','2\nC/N','3\n+45/N','4\nN/C','5\nN/C','6\n−90/N']);ax[1].axhline(0,c='#586168',lw=.65)
 for a in ax:
  for x in [1.5,2.5,3.5,4.5,5.5]:a.axvline(x,c='#E4E7E9',lw=.5,zorder=0)
 tidy(ax);f.legend([Line2D([],[],marker='o',ls='',c=C['sampled'],ms=4),Line2D([],[],marker='o',ls='',c=C['simple'],mfc='white',ms=4)],['S15','L'],loc='upper center',bbox_to_anchor=(.56,1),ncol=2,frameon=False);save(f,'figure4_prediction')
def case(sid,name,sync):
 ds=D['cases'][sid];f,ax=plt.subplots(2,1,figsize=(3.4,3.85),gridspec_kw={'height_ratios':[1.55,1]});f.subplots_adjust(left=.19,right=.98,bottom=.12,top=.87,hspace=.42)
 for o in ds['sampled']['scene']['static']:
  ax[0].add_patch(Circle(o['center_xy'],o['entity_radius']+60,fc='#F1F2F3',ec='#92999E',ls='--',lw=.6));ax[0].add_patch(Circle(o['center_xy'],o['entity_radius'],fc='#B4B9BD',ec='none'))
 handles=[]
 for v,d in ds.items():
  xy=np.asarray(d['xy']);width={'reactive':1.6,'simple':1.25,'sampled':1.0}[v];line,=ax[0].plot(*xy.T,c=C[v],ls=S[v],lw=width,label=L[v]);handles.append(line)
  ax[0].plot(*xy[sync],'o',ms=3,c=C[v]);ax[1].plot(d['time'][1:],d['margin'],c=C[v],ls=S[v],lw=width)
  mi=int(np.argmin(d['margin']));ax[0].plot(*xy[mi+1],marker='x' if d['margin'][mi]<=0 else '+',ms=5,c=C[v],mew=1)
 longest=max(ds.values(),key=lambda d:d['row']['time_s']);target=np.asarray(longest['target']);line,=ax[0].plot(*target.T,c='#555F66',ls='--',lw=.8,label='Target');handles.append(line);ax[0].plot(*target[sync],'s',ms=3,c='#555F66');ax[0].add_patch(Circle(target[sync],85,fill=False,ec='#555F66',ls=':',lw=.75));ax[0].plot(*ds['sampled']['scene']['goal'],'*',ms=5,c='#263640')
 ax[0].set(xlabel='World x (m)',ylabel='World y (m)',xticks=[0,250,500,750,1000]);ax[0].set_aspect('equal',adjustable='datalim');ax[1].set(xlabel='Time (s)',ylabel='Dynamic margin (m)');ax[1].axhline(0,c='#586168',ls='--',lw=.65)
 if sync==260:ax[1].set_ylim(-8,180);ax[1].set_xlim(240,460)
 tidy(ax);f.legend(handles,['R','L','S15','Target'],loc='upper center',bbox_to_anchor=(.57,.995),ncol=4,frameon=False,columnspacing=.85,handlelength=1.5,handletextpad=.4);save(f,name)
FUNCS={'figure2_confirmation':confirmation,'figure3_guard':guard,'figure4_prediction':prediction,'figure5_rescue':lambda:case('r12new_mixed_pressure_1','figure5_rescue',260),'figure6_adverse':lambda:case('r12new_endpoint_3','figure6_adverse',200)}
if __name__=='__main__':
 for name in (sys.argv[1:] or FUNCS):FUNCS[name]();print(name)
