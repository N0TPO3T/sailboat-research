"""Compact Fig.1 visual proposal. Scientific implementation is unchanged."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon

OUT = Path(__file__).resolve().parent / 'figures'
plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman','DejaVu Serif'],
                     'font.size':9,'pdf.fonttype':42,'svg.fonttype':'none'})
fig, ax = plt.subplots(figsize=(7.05, 3.85))
ax.set(xlim=(0,7.05),ylim=(0,3.85)); ax.axis('off')
INK='#293746'; BLUE='#507DA5'; TEAL='#397F79'; AMBER='#B78147'
def box(x,y,w,h,s,color=BLUE,fill='#EDF3F8',fs=9.5):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.012,rounding_size=0.055',
                              lw=.85,edgecolor=color,facecolor=fill,zorder=2))
    ax.text(x+w/2,y+h/2,s,ha='center',va='center',fontsize=fs,color=INK,linespacing=1.18,zorder=3)
def arrow(p,color=INK,dashed=False):
    x,y=zip(*p)
    ax.plot(x,y,color=color,lw=.85,ls=(0,(3,2)) if dashed else '-',zorder=1)
    ax.annotate('',xy=p[-1],xytext=p[-2],arrowprops=dict(arrowstyle='-|>',mutation_scale=8,lw=.85,color=color),zorder=1)

ax.text(.36,3.61,'(a) State reconstruction',fontsize=10.5,weight='bold',color=INK)
ax.text(3.52,3.61,'(b) Nominal-first selection',fontsize=10.5,weight='bold',color=INK)
box(.36,2.98,2.50,.40,'Observed state + real history')
box(.36,2.27,2.50,.40,'Eligibility check',color='#8995A0',fill='#F3F5F7')
arrow([(1.61,2.98),(1.61,2.68)])
arrow([(1.61,2.27),(1.61,1.91)],BLUE)
ax.text(1.70,2.06,'Eligible',fontsize=8.5,color=INK,va='center')
box(.36,1.50,2.50,.40,'Fit local wind')
box(.36,.83,1.13,.40,'Replay\nmemory',fs=9.5)
box(1.72,.83,1.14,.40,'Restore\nsetpoints',fs=9.5)
arrow([(1.61,1.50),(1.61,1.37),(.925,1.37),(.925,1.24)],BLUE)
arrow([(1.61,1.37),(2.29,1.37),(2.29,1.24)],BLUE)
arrow([(.925,.83),(.925,.69),(3.13,.69),(3.13,3.18),(3.52,3.18)],BLUE)
arrow([(2.29,.83),(2.29,.69)],BLUE)

box(3.52,2.98,3.16,.40,'Nominal rollout',fs=10)
arrow([(5.10,2.98),(5.10,2.77)],BLUE)
ax.add_patch(Polygon([(5.10,2.77),(6.45,2.34),(5.10,1.91),(3.75,2.34)],
                     facecolor='#EDF3F8',edgecolor=BLUE,lw=.85,zorder=2))
ax.text(5.10,2.34,'Valid & margin ≥ ρ?',ha='center',va='center',fontsize=10,color=INK)
arrow([(4.14,2.21),(4.14,1.51)],TEAL)
ax.text(4.23,1.77,'Pass',fontsize=9,color=INK)
arrow([(6.02,2.20),(6.02,1.51)],AMBER)
ax.text(6.11,1.77,'Fail',fontsize=9,color=INK)
box(3.52,.98,1.35,.52,'Return\nnominal',TEAL,'#E8F2EF',10)
box(5.21,.98,1.47,.52,'Predict alternatives\nRank / fallback',AMBER,'#FAF0E3',9.2)
ax.text(5.08,.77,'Isolated prediction histories',ha='center',fontsize=8.5,color=INK)
arrow([(4.195,.98),(4.195,.60),(4.80,.60),(4.80,.45)],TEAL)
arrow([(5.945,.98),(5.945,.60),(4.80,.60)],AMBER)

arrow([(.36,2.47),(.16,2.47),(.16,.25),(.36,.25)],'#8995A0',True)
ax.text(.40,.53,'Dashed: early return',fontsize=8,color=INK,ha='left',va='center')
box(.36,.06,6.32,.38,'t: old action  →  t+1: apply reference  →  [t+1, t+2]: first possible effect',
    '#8995A0','#F3F5F7',9.4)
fig.subplots_adjust(left=.01,right=.99,bottom=.025,top=.995)
for ext in ('png','svg','pdf'):
    fig.savefig(OUT/f'figure1_interface.{ext}',dpi=300)
plt.close(fig)
