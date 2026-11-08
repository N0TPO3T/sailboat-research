from pathlib import Path
import json,numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
D=Path(__file__).resolve().parent;R=D.parents[1]
fig,axs=plt.subplots(2,2,figsize=(11,7))
logs=[]
for label,path in [("Native sail",R/"work/yara6dof_20261108/result.json"),("Original sail polar",D/"result.json")]:
 rows=json.loads(path.read_text())["records"]["response"];logs.append(rows)
 t=np.array([x["time"] for x in rows]);raw=np.array([x["raw"] for x in rows]);target=np.array([x["target_angles"] for x in rows])
 axs[0,0].plot(t,np.hypot(raw[:,4],raw[:,5]),label=label)
 axs[0,1].plot(t,np.unwrap(raw[:,3])*180/np.pi,label=label)
 axs[1,0].plot(t,raw[:,8]*180/np.pi,label=label+" sail")
 axs[1,0].plot(t,raw[:,9]*180/np.pi,":",label=label+" rudder")
 if label=="Original sail polar":
  axs[1,1].plot(t,[x["diagnostics"]["sail_force"]["attack_deg"] for x in rows],label="Measured attack angle")
assert [x["action"] for x in logs[0]]==[x["action"] for x in logs[1]]
for ax,title,unit in zip(axs.flat,["Body speed","Yaw (unwrapped)","Actual actuator angles","Sail angle of attack"],["m/s","deg","deg","deg"]):
 ax.set_title(title);ax.set_xlabel("Simulation time (s)");ax.set_ylabel(unit);ax.grid(alpha=.25);ax.legend(fontsize=8)
fig.tight_layout();fig.savefig(D/"response.png",dpi=160)
