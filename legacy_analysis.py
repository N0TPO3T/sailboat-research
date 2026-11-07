from legacy_validate import *
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
summary=json.loads((D/"summary.json").read_text());checks=[]
for scene in CONFIG["scenes"]:
 a=json.loads((D/("policy_original_"+scene["name"]+".json")).read_text());b=json.loads((D/("policy_yara_"+scene["name"]+".json")).read_text())
 n=min(len(a["rows"]),len(b["rows"]));x=np.array([v["raw"][:10] for v in a["rows"][:n]]);y=np.array([v["raw"][:10] for v in b["rows"][:n]])
 checks.append(dict(scene=scene["name"],same_reason=a["reason"]==b["reason"],same_length=len(a["rows"])==len(b["rows"]),max_state_error=np.max(np.abs(x-y),axis=0),max_position_difference=float(np.max(np.linalg.norm(x[:,:2]-y[:,:2],axis=1)))))
if not (D/"paired_comparison.json").exists():save("paired_comparison.json",checks)
else:assert json.loads((D/"paired_comparison.json").read_text())==clean(checks)
fig,ax=plt.subplots(2,2,figsize=(12,8))
for label,path in [("Original",D/"response_original.json"),("Yara signed small hull",R/"signed_20261107/response_signed.json"),("Gazebo legacy4dof",D/"response_yara.json")]:
 rows=json.loads(path.read_text())["rows"];t=np.array([v["time"] for v in rows]);x=np.array([v["raw"] for v in rows]);style="--" if label=="Gazebo legacy4dof" else "-"
 ax[0,0].plot(x[:,0],x[:,1],style,label=label);ax[0,1].plot(t,np.unwrap(x[:,3])*180/np.pi,style,label=label);ax[1,0].plot(t,x[:,4],style,label=label);ax[1,1].plot(t,x[:,8]*180/np.pi,style,label=label)
for a,title in zip(ax.flat,["49-step fixed action trajectory (m)","Heading (deg)","Surge speed (m/s)","Actual sail angle (deg)"]):a.set_title(title);a.grid(alpha=.25);a.legend(fontsize=8)
fig.tight_layout();fig.savefig(D/"response.png",dpi=160);plt.close(fig)
fig,axes=plt.subplots(1,3,figsize=(15,5));allxy=[]
for ax,scene in zip(axes,CONFIG["scenes"]):
 for name,path,style in [("Original",D/("policy_original_"+scene["name"]+".json"),"-"),("Yara signed small hull",R/"signed_20261107"/("policy_signed_"+scene["name"]+".json"),"-"),("Gazebo legacy4dof",D/("policy_yara_"+scene["name"]+".json"),"--")]:
  data=json.loads(path.read_text());xy=np.array([v["raw"][:2] for v in data["rows"]]);ax.plot(*xy.T,style,label=name);ax.plot(*xy[-1],"x");allxy.extend(xy.tolist())
 for o in scene["obstacles"]:
  radius=o["entity_radius"]+o["safety_buffer"];cx,cy=o["center_xy"];allxy.extend([[cx-radius,cy-radius],[cx+radius,cy+radius]]);ax.add_patch(Circle(o["center_xy"],radius,color="orange",alpha=.15));ax.add_patch(Circle(o["center_xy"],o["entity_radius"],color="red",alpha=.4))
 goals=np.array(scene["goals"]);ax.scatter(*goals.T,marker="*",s=70,c="green");allxy.extend(goals.tolist());ax.set_title(scene["name"]);ax.set_aspect("equal");ax.grid(alpha=.25);ax.legend(fontsize=8)
xy=np.array(allxy);lo=xy.min(0)-30;hi=xy.max(0)+30
for ax in axes:ax.set_xlim(lo[0],hi[0]);ax.set_ylim(lo[1],hi[1]);ax.set_xlabel("World x (m)")
axes[0].set_ylabel("World y (m)");fig.tight_layout();fig.savefig(D/"paired.png",dpi=160);plt.close(fig)
print(json.dumps(clean(checks),indent=2))
