"""Three fixed episodes on native Yara 6DOF; no training or parameter search."""
from environment import *
from validate import clean
from sailboat_routing.obstacle_candidate import loading_paths
import argparse,traceback,shutil

def write(folder,name,value):
 with (folder/name).open("x") as f:json.dump(clean(value),f,indent=2)

def main(out,config_path=None,gate_path=None):
 out=out.resolve()
 if not out.is_relative_to(R/"work"):raise ValueError("output must be inside migration18/work")
 out.mkdir(parents=True,exist_ok=True)
 c=json.loads((config_path or R/"config_yara6dof.json").read_text())
 gate=json.loads((gate_path or R/"work/yara6dof_20261108/result.json").read_text())
 assert gate["passed"] and gate["config"]==c,"configuration differs from checked adapter"
 base=json.loads((R/"legacy4dof_20261108/source_final/config_legacy4dof.json").read_text())
 for key in ["policy_dt","limit_s","world_radius_m","goal_radius_m","seed","wind","initial","obstacle_input","scenes"]:assert c[key]==base[key],key
 assert c["physics_mode"]=="native" and c["actuator_mode"]=="signed"
 paths=loading_paths();original=Path("/home/ot/Students/hs/sailboat-routing-v0/checkpoints/obstacle_candidate")
 assets={key:Path(paths[key]).read_bytes()==(original/Path(paths[key]).name).read_bytes() for key in ["actor","normalizer"]};assert all(assets.values())
 sources=["environment.py","bridge.py","step.cc","config_yara6dof.json",str((config_path or R/"config_yara6dof.json").resolve().relative_to(R))]
 assert not subprocess.check_output(["git","diff","HEAD","--",*sources],cwd=R),"uncommitted runtime changes"
 references={scene["name"]:R/"legacy4dof_20261108"/("policy_original_"+scene["name"]+".json") for scene in c["scenes"]}
 for scene in c["scenes"]:assert json.loads(references[scene["name"]].read_text())["scene"]==scene
 write(out,"manifest.json",dict(config=c,scene_order=[s["name"] for s in c["scenes"]],max_episodes=3,max_steps_each=900,gazebo_seed=61106,fresh_world_per_scene=True,actor_mode="eval",loading_paths=paths,assets_equal_to_original_project=assets,existing_asset_index=str(R/"ASSET_HASHES.json"),code_commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=R,text=True).strip(),runner="runner.py",references={k:str(v) for k,v in references.items()},training=False))
 shutil.copy2(__file__,out/"runner.py")
 summaries=[]
 for scene in c["scenes"]:
  name=scene["name"];tr=None;e=None;p=None;rows=[];switches=[];reason="exception";arrived=False;captures={}
  try:
   tr=Transport(gazebo_args="--seed 61106");e=MigrationEnv("yara",tr,c);p=ObstacleController(mode="eval")
   obs,_=e.reset(options=scene);p.reset(obs);rows.append(dict(time=0,raw=e.raw.copy(),observation=obs,target_angles=[0,0],diagnostics=e.diag))
   reason="time_limit";max_angle_error=0.;previous=e.raw[8:10].astype(float)
   for k in range(c["limit_s"]):
    action=p.act(obs).action;obs,reward,_,truncated,info=e.step(action);rows.append(dict(action=action,reward=reward,observation=obs,**info))
    d=info["diagnostics"]
    assert d["physics_mode"]=="native" and not d["body_static"] and not d["body_kinematic"]
    assert d["fluid_density"]==dict(air_density=1.2,waterDensity=1025.,water_density=1025.)
    if c.get("sail_force_model")=="legacy_polar":
     f=d["sail_force"];assert f["source"]=="legacy_polar"
     assert abs(f["cl"]-float(e.env.sail_cl_interp(f["attack_deg"])))<1e-10
     assert abs(f["cd"]-float(e.env.sail_cd_interp(f["attack_deg"])))<1e-10
    assert d["motor_command"]==0 and d["motor_applied_thrust"]==0 and not d["motor_plugin_present"]
    expected=previous+np.clip(e.target-previous,-np.pi/18,np.pi/18)
    error=float(np.max(np.abs(e.raw[8:10]-expected)));max_angle_error=max(max_angle_error,error);previous=e.raw[8:10].astype(float)
    assert error<=math.radians(.05),(name,e.t,error,"actuator tracking")
    if k%100==0:print("STEP",name,e.t,e.raw[:2].tolist(),flush=True)
    if info["collision"]:reason="entity_collision";break
    if ("switch_at" not in scene or switches) and np.linalg.norm(e.raw[:2]-scene["goals"][-1])<=c["goal_radius_m"]:
     arrived=True;reason="arrived" if e.min_safety>0 else "arrived_with_buffer_violation";break
    if truncated:
     reason="time_limit" if e.t>=c["limit_s"] else "world_radius_limit";break
    if scene.get("switch_at")==e.t:
     before=e.raw[:12].copy();target=e.target.copy();obs=e.set_goal(scene["goals"][1],p)
     np.testing.assert_array_equal(e.raw[:12],before);np.testing.assert_array_equal(e.target,target)
     switches.append(dict(applied_at=e.t,history_count=len(e.commands)))
   summary=dict(scene=name,reason=reason,success=bool(arrived and e.min_safety>0),time_s=e.t,min_safety_m=e.min_safety,final_distance_m=float(np.linalg.norm(e.raw[:2]-scene["goals"][-1])),physical_contact_steps=sum(bool(x.get("physical_contact")) for x in rows),target_changes=len(switches),max_angle_error_rad=max_angle_error,max_clock_error_s=max(abs(x["diagnostics"]["dt"]-1) for x in rows[1:]))
   write(out,"policy_"+name+".json",dict(scene=scene,summary=summary,rows=rows,switches=switches));summaries.append(summary)
   print("RESULT",json.dumps(clean(summary)),flush=True)
   # Rendering advances the world only after the scored episode. The next episode starts a fresh world.
   try:
    trace=[x["raw"][:2].tolist() for x in rows];xy=np.array(trace+scene["goals"]);center=(xy.min(0)+xy.max(0))/2;span=max(80.,float(np.ptp(xy,axis=0).max()))
    prefix="../work/"+out.name+"/"+name
    captures["scene"]=tr.request("capture",filename=prefix+"_scene.png",trace=trace,xy=center.tolist(),offset=[0,-.7*span,.9*span],look_z=0.)
    captures["boat"]=tr.request("capture",filename=prefix+"_boat.png",trace=[],xy=e.raw[:2].tolist(),offset=[-7,-8,5],look_z=1.)
   except Exception:captures["error"]=traceback.format_exc()
   write(out,"capture_"+name+".json",dict(scored=False,**captures))
  except Exception:
   write(out,"error_"+name+".json",dict(error=traceback.format_exc(),reason=reason,scene=scene,rows=rows,switches=switches));raise
  finally:
   if p is not None:p.close()
   if e is not None:e.close()
   if tr is not None:tr.close()
   for log in ["bridge.log","gazebo.log","xvfb.log"]:
    if (R/"logs"/log).exists():shutil.copy2(R/"logs"/log,out/(name+"_"+log))
 write(out,"summary.json",dict(complete=True,episodes=summaries))
 print("COMPLETE",out,flush=True)
if __name__=="__main__":
 parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True);parser.add_argument("--config",type=Path);parser.add_argument("--gate",type=Path);args=parser.parse_args();main(args.output,args.config,args.gate)
