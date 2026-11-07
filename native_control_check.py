from legacy_validate import *
import shlex
if (D/"native_control_gate.json").exists():raise FileExistsError("control results already exist")
build=D/"baseline_build";src=D/"baseline_buildsrc";build.mkdir(exist_ok=True);src.mkdir(exist_ok=True)
if not (D/"baseline_step.cc").exists():(D/"baseline_step.cc").write_bytes(subprocess.check_output(["git","show","3d2f468:step.cc"],cwd=R))
(src/"CMakeLists.txt").write_text((R/"CMakeLists.txt").read_text().replace("MigrationStep","MigrationStepBaseline").replace("SHARED step.cc","SHARED ../baseline_step.cc"))
container_path="/work/migration18/"+D.name
(D/"ocean_baseline.world").write_text((R/"ocean.world").read_text().replace("libMigrationStep.so",container_path+"/baseline_build/libMigrationStepBaseline.so"))
if not (build/"libMigrationStepBaseline.so").exists():
 with (D/"build_baseline.log").open("w") as log:
  subprocess.run([str(R.parent/"run-yara.sh"),"bash","-c","cd "+shlex.quote(container_path+"/baseline_build")+" && cmake ../baseline_buildsrc && make -j2"],stdout=log,stderr=subprocess.STDOUT,check=True)

# Paired old/new compiled plugin under the same explicit Gazebo solver seed.
actions=[[1,1]]*12+[[0,0]]*5+[[-1,-1]]*22+[[0,0]]*5+[[1,1]]*5
runs={}
for version,world in [("baseline",container_path+"/ocean_baseline.world"),("current","/work/migration18/ocean.world")]:
 tr=Transport(world=world,gazebo_args="--seed 61106")
 try:
  for mode in ["native","signed"]:
   c=copy.deepcopy(CONFIG);c["actuator_mode"]=mode;e=MigrationEnv("yara",tr,c);e.reset();rows=[]
   for a in actions:
    obs,reward,_,_,info=e.step(a);rows.append(info)
   save("control_"+version+"_"+mode+".json",dict(rows=rows));runs[version+mode]=np.array([v["raw"][:10] for v in rows]);e.close()
 finally:tr.close()
checks=[]
for mode in ["native","signed"]:
 a=runs["baseline"+mode];b=runs["current"+mode];checks.append(dict(mode=mode,max_state_difference=np.max(np.abs(a-b),axis=0),bitwise_equal=bool(np.array_equal(a,b))))
save("native_control_gate.json",dict(passed=all(v["bitwise_equal"] for v in checks),gazebo_seed=61106,steps=49,checks=checks,baseline_commit="3d2f468",historical_unseeded_bitwise_check="failed; preserved in regression.log; no relaxed numerical tolerance used"))
assert all(v["bitwise_equal"] for v in checks),checks
