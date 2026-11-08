"""Bounded CPU checks for the existing Yara hull and original task adapter."""
from environment import *
from validate import clean
import argparse,traceback,shutil

def run(output):
 output=output.resolve();output.mkdir(parents=True,exist_ok=True)
 if (output/"result.json").exists():raise FileExistsError("Existing check receipt preserved")
 c=json.loads((R/"config_yara6dof.json").read_text());checks=[];records={};tr=Transport(gazebo_args="--seed 61106")
 def save():
  (output/"result.json").write_text(json.dumps(clean(dict(passed=all(x["passed"] for x in checks),checks=checks,records=records,config=c)),indent=2))
 def checked(name,passed,**details):
  item=dict(name=name,passed=bool(passed),**details);checks.append(item);print(json.dumps(clean(item)),flush=True)
  assert passed,item
 try:
  # Zero-time reset checks expose incorrect world/body twist conversion.
  records["resets"]=[]
  for roll,pitch,yaw in [(0.,0.,0.),(.17,.12,1.1),(-.21,-.09,-1.4)]:
   cfg=copy.deepcopy(c);cfg["initial"][2:8]=[roll,yaw,.7,.12,.04,.06]
   cfg["initial_6dof"]=dict(z=.15,pitch=pitch,w=.12,q=.07)
   e=MigrationEnv("yara",tr,cfg)
   try:
    obs,_=e.reset();d=e.diag;records["resets"].append(dict(raw=e.raw.copy(),diagnostics=d))
    checked("reset_attitude_and_twist",np.allclose(e.raw[:10],cfg["initial"][:10],atol=2e-5,rtol=0) and np.allclose([d["pose6"][2],d["pose6"][4],d["body_twist6"][2],d["body_twist6"][4]],[.15,pitch,.12,.07],atol=2e-5,rtol=0),roll=roll,pitch=pitch,yaw=yaw)
   finally:e.close()
  e=MigrationEnv("yara",tr,c);obs,_=e.reset();rows=[];records["response"]=rows
  checked("fluid_density_buoyancy_and_foils",e.diag["fluid_density"]==dict(air_density=1.2,waterDensity=1025.,water_density=1025.),applied=e.diag["fluid_density"])
  prev=e.raw[8:10].astype(float);max_error=0.
  try:
   actions=[[1,1]]*12+[[0,0]]*5+[[-1,-1]]*22+[[0,0]]*5+[[1,1]]*5
   for action in actions:
    old_target=e.target.copy();before=e.raw.copy();obs,reward,_,_,info=e.step(action);d=info["diagnostics"]
    expected=prev+np.clip(e.target-prev,-np.pi/18,np.pi/18);error=float(np.max(np.abs(e.raw[8:10]-expected)));max_error=max(max_error,error);prev=e.raw[8:10].astype(float)
    assert d["physics_mode"]=="native" and not d["body_static"] and not d["body_kinematic"]
    assert obs.shape==(18,) and np.isfinite(obs).all()
    assert d["motor_command"]==0 and d["motor_applied_thrust"]==0 and not d["motor_plugin_present"]
    if action==[0,0]:np.testing.assert_array_equal(e.target,old_target)
    rows.append(dict(action=action,reward=reward,observation=obs,**info))
   checked("signed_actuator_rate_and_hold",max_error<=math.radians(.05),max_tracking_error_rad=max_error,tolerance_rad=math.radians(.05))
   checked("native_6dof_clock_and_information_boundary",all(abs(x["diagnostics"]["dt"]-1)<1e-8 for x in rows),steps=len(rows),policy_dimensions=18,heave_range=np.ptp([x["diagnostics"]["pose6"][2] for x in rows]),pitch_range=np.ptp([x["diagnostics"]["pose6"][4] for x in rows]))
  finally:e.close()
  # Check actual contact separately from the unchanged point-vessel score.
  cfg=copy.deepcopy(c);cfg["wind"]=[0.,0.,0.];cfg["initial"][4]=3.
  scene=dict(name="contact_probe",goals=[[500,0]],obstacles=[dict(center_xy=[3,0],entity_radius=.4,safety_buffer=0.)])
  e=MigrationEnv("yara",tr,cfg);e.reset(options=scene);records["contact"]=[]
  try:
   for k in range(5):
    _,_,_,_,info=e.step([0,0]);records["contact"].append(info)
   contacts=[x for x in records["contact"] if x["physical_contact"]]
   checked("actual_external_contact_recorded",bool(contacts),contact_steps=len(contacts),contact_pairs=[x["diagnostics"]["contact_pairs"] for x in contacts],original_entity_collision=[x["collision"] for x in records["contact"]])
  finally:e.close()
  # Same policy loader and actual history across a goal update, with no training.
  e=MigrationEnv("yara",tr,c);p=ObstacleController(mode="eval");obs,_=e.reset();p.reset(obs);records["policy_smoke"]=[]
  try:
   for k in range(5):
    if k==2:
     before=e.raw[:12].copy();target=e.target.copy();obs=e.set_goal([500,80],p)
     np.testing.assert_array_equal(e.raw[:12],before);np.testing.assert_array_equal(e.target,target)
    obs,_,_,_,info=e.step(p.act(obs).action);records["policy_smoke"].append(info)
   checked("same_18d_policy_and_causal_goal_change",len(e.history)==6 and len(e.commands)==5,policy_steps=5)
   e.reset();checked("reset_clears_target_history_and_6dof_state",len(e.history)==1 and not e.commands and not np.any(e.target) and np.allclose(e.raw[:10],c["initial"][:10],atol=2e-5,rtol=0))
  finally:p.close();e.close()
 except Exception:
  checks.append(dict(name="exception",passed=False,traceback=traceback.format_exc()));raise
 finally:
  save();tr.close()
  for name in ["bridge.log","gazebo.log","xvfb.log"]:
   if (R/"logs"/name).exists():shutil.copy2(R/"logs"/name,output/name)
if __name__=="__main__":
 a=argparse.ArgumentParser();a.add_argument("--output",required=True,type=Path);args=a.parse_args()
 if not args.output.resolve().is_relative_to(R/"work"):raise ValueError("check output must be inside migration18/work")
 run(args.output)
