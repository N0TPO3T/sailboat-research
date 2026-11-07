from environment import *
from validate import clean
import argparse,traceback,shutil
D=R/os.environ.get("MIGRATION18_RUN","legacy4dof_20261108")
if D.parent!=R or not D.name.startswith("legacy4dof_"):raise ValueError("run name must be a legacy4dof_ child")
D.mkdir(exist_ok=True)
def save(n,v):
 p=D/n
 if p.exists():raise FileExistsError(p)
 p.write_text(json.dumps(clean(v),indent=2))
def config():return json.loads((R/"config_legacy4dof.json").read_text())
def kernel():
 import legacy_reference
 m=SeniorModules();e=m.environment.Sailboat_nowind_last();legacy_reference.globals=m.globals
 m.globals.w_change_v=8.;m.globals.w_change_d=np.pi/2
 rng=np.random.default_rng(61106);cases=[];expected=[]
 for i in range(64):
  state=np.array([10.,-5.,rng.uniform(-.5,.5),rng.uniform(-np.pi,np.pi),rng.uniform(-1,5),rng.uniform(-1,1),rng.uniform(-.2,.2),rng.uniform(-.2,.2)])
  sail=rng.uniform(-np.pi/2,np.pi/2);rudder=rng.uniform(-np.pi/6,np.pi/6)
  cases.append([*state,sail,rudder,0.,8.]);expected.append(legacy_reference.state_derivatives(e,state,np.zeros(2),0.,sail,rudder,0.,0.))
 data="\n".join(" ".join(map(str,row)) for row in cases)+"\n"
 p=subprocess.run([str(R/"build/legacy_probe")],input=data,capture_output=True,text=True,check=True)
 actual=np.array([[float(v) for v in row.split()] for row in p.stdout.splitlines()]);err=np.max(np.abs(actual-expected),axis=0)
 save("kernel_gate.json",dict(passed=bool(max(err)<=1e-9),tolerance=1e-9,max_derivative_error=err,cases=cases,expected=expected,actual=actual))
 assert max(err)<=1e-9,err
 print("KERNEL",err,flush=True)
def response():
 assert json.loads((D/"kernel_gate.json").read_text())["passed"]
 actions=[[1,1]]*12+[[0,0]]*5+[[-1,-1]]*22+[[0,0]]*5+[[1,1]]*5
 reference=[];tr=Transport()
 try:
  for backend in ["original","yara"]:
   e=MigrationEnv(backend,tr,config());e.reset();rows=[]
   for action in actions:
    obs,reward,_,_,info=e.step(action);rows.append(dict(action=action,observation=obs,reward=reward,**info))
   save("response_"+backend+".json",dict(rows=rows))
   if backend=="original":reference=rows
   else:
    a=np.array([r["raw"][:10] for r in reference]);b=np.array([r["raw"][:10] for r in rows]);err=np.max(np.abs(a-b),axis=0)
    limits=np.array([.1,.1,.01,.01,.01,.01,.01,.01,1e-6,1e-6])
    save("response_gate.json",dict(passed=bool(np.all(err<=limits)),max_error=err,limits=limits,clock_error=max(abs(r["diagnostics"]["dt"]-1) for r in rows)))
    assert np.all(err<=limits),(err,limits)
    print("RESPONSE",err,flush=True)
   e.close()
 finally:tr.close()
def policy():
 assert json.loads((D/"response_gate.json").read_text())["passed"]
 summaries=[]
 tr=Transport()
 try:
  for backend in ["original","yara"]:
   for scene in CONFIG["scenes"]:
    e=MigrationEnv(backend,tr,config());p=ObstacleController(mode="eval");obs,_=e.reset(options=scene);p.reset(obs)
    rows=[dict(time=0,raw=e.raw.copy(),target_angles=[0,0])];switches=[];reason="time_limit";arrived=False
    try:
     for k in range(CONFIG["limit_s"]):
      action=p.act(obs).action;obs,reward,_,truncated,info=e.step(action);rows.append(dict(action=action,reward=reward,observation=obs,**info))
      if info["collision"]:reason="entity_collision";break
      if ("switch_at" not in scene or switches) and np.linalg.norm(e.raw[:2]-scene["goals"][-1])<=CONFIG["goal_radius_m"]:
       arrived=True;reason="arrived" if e.min_safety>0 else "arrived_with_buffer_violation";break
      if truncated:break
      if scene.get("switch_at")==e.t:
       before=e.raw[:12].copy();target=e.target.copy();obs=e.set_goal(scene["goals"][1],p)
       np.testing.assert_array_equal(before,e.raw[:12]);np.testing.assert_array_equal(target,e.target);switches.append(dict(applied_at=e.t,history_count=len(e.commands)))
    except Exception:reason="exception";save("error_"+backend+"_"+scene["name"]+".json",dict(error=traceback.format_exc()));raise
    finally:
     save("policy_"+backend+"_"+scene["name"]+".json",dict(backend=backend,scene=scene,reason=reason,success=arrived and e.min_safety>0,rows=rows,switches=switches));p.close();e.close()
    result=dict(backend=backend,scene=scene["name"],reason=reason,time=e.t,success=arrived and e.min_safety>0,min_safety=e.min_safety,final_distance=float(np.linalg.norm(e.raw[:2]-scene["goals"][-1])))
    summaries.append(result);print("RESULT",result,flush=True)
  save("summary.json",summaries)
 finally:tr.close()
def regression():
 actions=[[1,1]]*12+[[0,0]]*5+[[-1,-1]]*22+[[0,0]]*5+[[1,1]]*5
 tr=Transport();checks=[]
 try:
  for mode in ["native","signed"]:
   c=copy.deepcopy(CONFIG);c["actuator_mode"]=mode;e=MigrationEnv("yara",tr,c);e.reset();ref=json.loads((R/"signed_20261107"/("response_"+mode+".json")).read_text())["rows"]
   for i,a in enumerate(actions):
    e.step(a);np.testing.assert_array_equal(e.raw[:10],np.array(ref[i]["raw"][:10],dtype=np.float32))
   e.close();checks.append(dict(mode=mode,steps=49,physical_states_bitwise_equal=True))
  save("native_signed_regression.json",dict(passed=True,checks=checks))
 finally:tr.close()
def wind():
 c=json.loads((R/"config_legacy_dryden.json").read_text());tr=Transport();allrows={}
 try:
  for backend in ["original","yara"]:
   e=MigrationEnv(backend,tr,c);obs,_=e.reset();rows=[]
   for k in range(30):
    obs,reward,_,_,info=e.step([.2,-.2] if k<15 else [0,0]);assert obs.shape==(18,);rows.append(info)
   allrows[backend]=rows;save("dryden_"+backend+".json",dict(rows=rows));e.close()
  a=allrows["original"];b=allrows["yara"]
  np.testing.assert_array_equal([v["wind_next"] for v in a],[v["wind_next"] for v in b])
  err=np.max(np.abs(np.array([v["raw"][:10] for v in a])-np.array([v["raw"][:10] for v in b])),axis=0)
  limits=np.array([.1,.1,.01,.01,.01,.01,.01,.01,1e-6,1e-6]);save("dryden_gate.json",dict(passed=bool(np.all(err<=limits)),wind_sequence_bitwise_equal=True,max_error=err,limits=limits,steps=30))
  assert np.all(err<=limits),err
 finally:tr.close()
def resets():
 tr=Transport();checks=[]
 try:
  for k,mode in enumerate(["legacy4dof","native","legacy4dof","signed","legacy4dof"]):
   c=config() if mode=="legacy4dof" else copy.deepcopy(CONFIG)
   if mode!="legacy4dof":c["actuator_mode"]=mode
   e=MigrationEnv("yara",tr,c);obs,info=e.reset();np.testing.assert_array_equal(e.target,[0,0]);assert len(e.history)==1 and not e.commands
   for i in range(3):e.step([.5,-.5])
   e.reset();np.testing.assert_allclose(e.raw[:10],c["initial"][:10],atol=2e-5,rtol=0);np.testing.assert_array_equal(e.target,[0,0]);assert len(e.history)==1 and not e.commands
   checks.append(dict(mode=mode,reset_count=2,passed=True));e.close()
  save("reset_gate.json",dict(passed=True,checks=checks))
 finally:tr.close()
def capture():
 tr=Transport();e=MigrationEnv("yara",tr,config());p=ObstacleController(mode="eval")
 try:
  scene=CONFIG["scenes"][1];obs,_=e.reset(options=scene);p.reset(obs);rows=[dict(time=0,raw=e.raw.copy())]
  for k in range(60):
   obs,_,_,truncated,info=e.step(p.act(obs).action);rows.append(info)
   if info["collision"] or truncated:break
  trace=[v["raw"][:2].tolist() for v in rows];xy=e.raw[:2].tolist()
  overview=tr.request("capture",filename="../"+D.name+"/gazebo_scene.png",trace=trace,xy=[250,0],offset=[0,-330,360],look_z=0)
  close=tr.request("capture",filename="../"+D.name+"/gazebo_boat.png",trace=[],xy=xy,offset=[-7,-8,5],look_z=1)
  save("capture_receipt.json",dict(scored=False,description="Fresh actual 60-step policy demonstration; camera advances excluded from scored episodes; Yara geometry visual proxy",rows=rows,overview=overview,close=close))
 finally:p.close();e.close();tr.close()
if __name__=="__main__":
 stage=sys.argv[1]
 sentinels={"kernel":"kernel_gate.json","response":"response_original.json","policy":"policy_original_clear.json","wind":"dryden_original.json","regression":"native_signed_regression.json","reset":"reset_gate.json","capture":"capture_receipt.json"}
 if stage in sentinels and (D/sentinels[stage]).exists():raise FileExistsError("Existing results preserved; set MIGRATION18_RUN to a fresh legacy4dof_ name")
 stages=dict(kernel=kernel,response=response,policy=policy,regression=regression,wind=wind,reset=resets,capture=capture)
 stages[stage]()
