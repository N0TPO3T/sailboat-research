from pathlib import Path
import sys,json,math
D=Path(__file__).resolve().parent;R=D.parents[1]
sys.path.insert(0,str(R))
from environment import np,segment_circle_clearance,CircleObstacle
from validate import clean
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
manifest=json.loads((D/"manifest.json").read_text());config=manifest["config"]
assert json.loads((D/"summary.json").read_text())["complete"]
checks=[];paired=[];fig,axes=plt.subplots(1,3,figsize=(15,6));bounds=[]
for ax,scene in zip(axes,config["scenes"]):
 name=scene["name"];data=json.loads((D/("policy_"+name+".json")).read_text());rows=data["rows"];s=data["summary"]
 ref=json.loads((R/"legacy4dof_20261108"/("policy_original_"+name+".json")).read_text())
 obstacles=tuple(CircleObstacle(tuple(o["center_xy"]),o["entity_radius"],o["safety_buffer"]) for o in scene["obstacles"])
 def margin(log):
  return min((segment_circle_clearance(np.array(a["raw"][:2],dtype=np.float32),np.array(b["raw"][:2],dtype=np.float32),obstacles)["safety_m"] for a,b in zip(log,log[1:])),default=math.inf)
 minimum=margin(rows);ref_minimum=margin(ref["rows"])
 if obstacles:assert abs(minimum-s["min_safety_m"])<=1e-9,(minimum,s["min_safety_m"])
 assert rows[-1]["time"]==s["time_s"]
 assert bool(s["success"])==(s["reason"]=="arrived" and minimum>0)
 clock_error=max(abs(x["diagnostics"]["clock"]-rows[0]["diagnostics"]["clock"]-x["time"]) for x in rows)
 assert clock_error<1e-8
 assert all(x["diagnostics"]["physics_mode"]=="native" and not x["diagnostics"]["body_static"] and not x["diagnostics"]["body_kinematic"] for x in rows)
 assert all(x["diagnostics"]["motor_command"]==0 and x["diagnostics"]["motor_applied_thrust"]==0 and not x["diagnostics"]["motor_plugin_present"] for x in rows)
 assert len(data["switches"])==(1 if "switch_at" in scene and s["time_s"]>scene["switch_at"] else 0)
 diagnostics=np.array([x["diagnostics"]["pose6"] for x in rows]);speed=np.array([np.hypot(x["raw"][4],x["raw"][5]) for x in rows])
 paired.append(dict(scene=name,original=dict(reason=ref["reason"],time_s=ref["rows"][-1]["time"],min_safety_m=ref_minimum,success=ref["reason"]=="arrived" and ref_minimum>0),yara=s,diagnostics=dict(sail_attack_range_deg=[min(x["diagnostics"]["sail_force"]["attack_deg"] for x in rows[1:]),max(x["diagnostics"]["sail_force"]["attack_deg"] for x in rows[1:])],last100_mean_speed_m_s=float(np.mean(speed[-100:])),max_abs_roll_deg=float(np.max(np.abs(diagnostics[:,3]))*180/np.pi),max_abs_pitch_deg=float(np.max(np.abs(diagnostics[:,4]))*180/np.pi),z_range_m=[float(np.min(diagnostics[:,2])),float(np.max(diagnostics[:,2]))],speed_range_m_s=[float(np.min(speed)),float(np.max(speed))],clock_error_s=clock_error)))
 checks.append(dict(scene=name,safety_recomputed=True,clock_and_native_body_checked=True,motor_off=True,score_matches_original_rules=True))
 for label,log,style in [("Original 4DOF",ref["rows"],"-"),("Yara original sail polar",rows,"--"),("Yara native sail",json.loads((R/"work/yara6dof_policy_20261108"/("policy_"+name+".json")).read_text())["rows"],":")]:
  xy=np.array([v["raw"][:2] for v in log]);ax.plot(xy[:,0],xy[:,1],style,label=label);ax.plot(*xy[-1],"x");bounds.extend(xy.tolist())
 for o in scene["obstacles"]:
  radius=o["entity_radius"]+o["safety_buffer"];cx,cy=o["center_xy"];bounds.extend([[cx-radius,cy-radius],[cx+radius,cy+radius]])
  ax.add_patch(Circle(o["center_xy"],radius,color="orange",alpha=.15));ax.add_patch(Circle(o["center_xy"],o["entity_radius"],color="red",alpha=.4))
 goals=np.array(scene["goals"]);ax.scatter(*goals.T,color="green",marker="*",s=65);bounds.extend(goals.tolist())
 ax.set_title(name+" | "+s["reason"]+" | "+str(int(s["time_s"]))+"s",fontsize=10);ax.set_aspect("equal");ax.grid(alpha=.25);ax.legend(fontsize=8);ax.set_xlabel("World x (m)")
bounds=np.array(bounds);lo=bounds.min(0)-30;hi=bounds.max(0)+30
for ax in axes:ax.set_xlim(lo[0],hi[0]);ax.set_ylim(lo[1],hi[1])
axes[0].set_ylabel("World y (m)");fig.tight_layout();fig.savefig(D/"paired.png",dpi=160);plt.close(fig)
with (D/"analysis.json").open("x") as f:json.dump(clean(dict(checks=checks,paired=paired)),f,indent=2)
print(json.dumps(clean(paired),indent=2))
