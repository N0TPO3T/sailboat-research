import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
r=Path('/work/transfer_audit');d=json.loads((r/'demo_trajectory.json').read_text())['rows']
t=np.array([x['sim_time'] for x in d]);xy=np.array([x['position'][:2] for x in d]);a=np.array([x['action'] for x in d])
fig,axes=plt.subplots(2,1,figsize=(11,7),constrained_layout=True,gridspec_kw={'height_ratios':[1,1.3]})
ax=axes[0];ax.plot(xy[:,0],xy[:,1],'-o',ms=3,lw=2,color='#1565a8',label='Logged PPO trajectory')
ax.scatter([0],[0],marker='s',c='black',label='Reset position');ax.scatter([100],[0],marker='*',s=160,c='#d7453a',label='Waypoint')
ax.add_patch(plt.Circle((100,0),5.1,fill=False,ls='--',color='#d7453a',label='Arrival threshold (horizontal illustration)'))
ax.set_aspect('equal',adjustable='datalim');ax.set_xlabel('World x (m)');ax.set_ylabel('World y (m)');ax.legend(loc='upper left',fontsize=8,ncol=3);ax.grid(alpha=.2)
ax=axes[1];ax.plot(t,(a[:,0]+1)*45,label='Sail opening command (deg)');ax.plot(t,a[:,1]*60,label='Rudder command (deg)');ax.plot(t,np.trunc(a[:,2]*5),label='Propeller discrete command',ls='--');ax.set_xlabel('Simulation time (s)');ax.set_ylabel('Command value (units in legend)');ax.grid(alpha=.2);ax.legend()
fig.suptitle('Yara original PPO: one visualization rollout, not a benchmark',fontsize=14)
fig.savefig(r/'demo_trajectory.png',dpi=180);plt.close(fig)
