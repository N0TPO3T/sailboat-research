"""Execution-interface schematic, drawn from the verified timing contract."""
from pathlib import Path
import sys
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P/'.tools/python'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
plt.rcParams.update({'font.family':'serif','font.size':7.4,'svg.fonttype':'none'})
fig,ax=plt.subplots(figsize=(3.4,3.65));ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
def box(x,y,w,h,text,color='#f4f6f8'):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.008',facecolor=color,edgecolor='#334b60',linewidth=.7))
    ax.text(x+w/2,y+h/2,text,ha='center',va='center',linespacing=1.2)
def arrow(a,b):ax.annotate('',xy=b,xytext=a,arrowprops={'arrowstyle':'->','lw':.8,'color':'black'})
box(.055,.875,.89,.105,'Observed state and causal history\nCurrent frame, manager and pending action')
box(.055,.685,.425,.13,'Reset and replay\ncontroller memory\nin the active frame')
box(.525,.685,.42,.13,'Accumulate issued\ncommands into setpoints;\nfit local wind')
arrow((.27,.875),(.27,.825));arrow((.73,.875),(.73,.825))
box(.055,.50,.89,.125,'Independent candidate rollouts\nSame pending action; reference hold,\nthen restore route feedback')
arrow((.27,.685),(.27,.63));arrow((.73,.685),(.73,.63))
box(.055,.335,.89,.105,'Test nominal clearance first\nIf rejected: rank alternatives / fallback')
arrow((.50,.50),(.50,.447))
box(.055,.165,.89,.11,'Deliver reference after the pending action\nRebuild physical controller memory; execute', '#eef6ef')
arrow((.50,.335),(.50,.282))
ax.plot([.055,.017,.017,.055],[.22,.22,.925,.925],color='black',lw=.7)
arrow((.017,.925),(.055,.925))
ax.text(-.017,.565,'executed observations only',rotation=90,ha='center',va='center',fontsize=6.4)
ax.plot([.12,.89],[.088,.088],color='black',lw=.7)
for x,label in [(.12,'t'),(.50,'t+1'),(.89,'t+2')]:
    ax.plot([x,x],[.074,.102],color='black',lw=.7);ax.text(x,.04,label,ha='center',fontsize=7)
ax.text(.31,.117,'pending old action',ha='center',fontsize=6.2)
ax.text(.70,.117,'first affected interval',ha='center',fontsize=6.2)
fig.subplots_adjust(left=.06,right=.99,top=.995,bottom=.015)
for ext in ['png','pdf','svg']:fig.savefig(P/'figures'/('figure1_interface.'+ext),dpi=300)
plt.close(fig)
