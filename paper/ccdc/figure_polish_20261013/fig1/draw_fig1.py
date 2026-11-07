"""Fig.1 visual draft; no scientific/data changes. Matplotlib vector source."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon
P=Path(__file__).resolve().parent
plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman','DejaVu Serif'],'font.size':9,'pdf.fonttype':42,'svg.fonttype':'none'})
fig,ax=plt.subplots(figsize=(7.05,4.7));ax.set(xlim=(0,7.05),ylim=(0,4.7));ax.axis('off')
ink='#253746';blue='#28658A';green='#3C705E';orange='#986331'
def node(x,y,w,h,label,color=ink,fill='white',fs=9):
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.015,rounding_size=0.055',linewidth=.85,edgecolor=color,facecolor=fill,zorder=2))
 ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=fs,linespacing=1.14,zorder=3)
def edge(points,color=ink,dash=False):
 xs,ys=zip(*points);ax.plot(xs,ys,color=color,lw=.9,ls=(0,(3,2)) if dash else '-',zorder=1)
 ax.annotate('',xy=points[-1],xytext=points[-2],arrowprops={'arrowstyle':'-|>','mutation_scale':8,'lw':.9,'color':color},zorder=1)
ax.text(.4,4.48,'(a) Eligibility and reconstruction',fontsize=10,color=ink,weight='bold')
ax.text(3.65,4.48,'(b) Nominal-first selection',fontsize=10,color=ink,weight='bold')
node(.4,3.85,2.65,.43,'Observed state and real history\nPending old-reference action',fs=9)
node(.4,2.95,2.65,.63,'Active hold: return held reference\nOtherwise call nominal manager*\nReview not due / no nearby target: return nominal',fs=8.2)
edge([(1.72,3.85),(1.72,3.58)])
edge([(1.72,2.95),(1.72,2.65)])
ax.text(1.80,2.78,'Eligible',fontsize=8.4,va='center',color=blue)
node(.4,2.25,2.65,.40,'Fit local wind from observed motion',color=blue,fs=9)
node(.4,1.43,1.23,.54,'Reset and replay\ncontroller memory\nin active frame',color=blue,fs=8.5)
node(1.80,1.43,1.25,.54,'Accumulate issued\ncommands into\nactuator setpoints',color=blue,fs=8.5)
edge([(1.72,2.25),(1.72,2.10),(1.01,2.10),(1.01,1.97)],blue)
edge([(1.72,2.10),(2.42,2.10),(2.42,1.97)],blue)
edge([(1.01,1.43),(1.01,1.22),(3.35,1.22),(3.35,4.06),(3.65,4.06)],blue)
edge([(2.42,1.43),(2.42,1.22)],blue)
node(3.65,3.85,2.95,.43,'Predict nominal to horizon H\nSame pending action; cloned manager',color=blue,fs=9)
edge([(5.125,3.85),(5.125,3.54)],blue)
ax.add_patch(Polygon([(5.125,3.54),(6.55,3.10),(5.125,2.66),(3.70,3.10)],facecolor='#F8FAFC',edgecolor=blue,lw=.9,zorder=2))
ax.text(5.125,3.10,'Valid, integration successful\nand minimum margin ≥ ρ?',ha='center',va='center',fontsize=9)
edge([(4.13,2.97),(4.13,2.48)],green);ax.text(4.20,2.62,'Pass',color=green,fontsize=8.5)
edge([(6.06,2.96),(6.06,2.48)],orange);ax.text(6.13,2.62,'Fail',color=orange,fontsize=8.5)
node(3.65,1.78,1.20,.68,'Select nominal\nSkip alternative\npredictions',color=green,fs=9)
node(5.08,1.53,1.78,.93,'Restore separate branches\nPredict available continuation\nand four side protocols\nHold P; restore nominal\nRank / original fallback',color=orange,fs=8.3)
edge([(4.25,1.78),(4.25,1.27),(5.12,1.27),(5.12,.97)],green)
edge([(5.97,1.53),(5.97,1.27),(5.12,1.27)],orange)
ax.text(3.65,1.08,'Isolated prediction histories',ha='left',fontsize=8,color=ink)
ax.text(.4,1.04,'Dashed bypass: early return, no prediction',fontsize=8,color=ink)
edge([(.4,3.25),(.23,3.25),(.23,.75),(.4,.75)],ink,True)
node(.4,.42,6.45,.55,'Return selected reference → execute the pending old action → apply any changed reference at t+1\nRebuild physical memory after a reference change; only executed feedback updates real history',fs=9)
ax.text(.4,.13,'* Clear incumbent after an expired hold, before calling the manager.',fontsize=8,color=ink)
ax.text(3.63,.13,'t  ── old action ──  t+1  ── first possible effect ──  t+2',fontsize=8,color=ink)
fig.subplots_adjust(left=.01,right=.99,bottom=.02,top=.995)
for ext in ['png','pdf','svg']:fig.savefig(P/('figure1_v1.'+ext),dpi=300)
plt.close(fig)
