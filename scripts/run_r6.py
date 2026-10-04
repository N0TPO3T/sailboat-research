#!/usr/bin/env python3
"""R6 bounded evaluation reuses R1 runner and original physics/evaluation."""
import os,sys,json,time,copy,subprocess,multiprocessing,concurrent.futures
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
import run_r1 as base
from sailboat_routing import navigation as nav
from sailboat_routing.runtime import SeniorModules,FrozenController
from sailboat_routing.continuous import ContinuousPhysics
from sailboat_routing.frames import LocalFrame
from sailboat_routing.r6_controller import WindowController,FeedforwardController,ObstacleController,ObstacleFrameFactory,change_reference
from sailboat_routing.admission import file_hash
ORIGINAL_STACK=nav.build_stack;ORIGINAL_RUN=nav.run_episode;ORIGINAL_REENCODE=nav.reencode_controller

def worker(job):
    cfg=job.get("controller",{"kind":"legacy"});kind=cfg["kind"]
    def stack(protocol,limit,radius):
        if kind=="legacy":return ORIGINAL_STACK(protocol,limit,radius)
        modules=SeniorModules();frame=LocalFrame
        if kind=="window":policy=WindowController(modules,ROOT/protocol["actor"],ROOT/protocol["normalizer"],alignment=cfg.get("alignment","training"),window=cfg.get("window",10))
        elif kind=="reset":
            policy=FrozenController(modules,ROOT/protocol["actor"],ROOT/protocol["normalizer"]);policy.reset_on_switch=True
        elif kind=="fc":policy=FeedforwardController(modules)
        elif kind=="obstacle":
            policy=ObstacleController(mode="eval");policy.reset_on_switch=cfg.get("reset_on_switch",False)
            frame=ObstacleFrameFactory(nav.chart_for(job["scene"],job["suite"]).obstacles,cfg.get("obstacle_input","center"))
        else:raise ValueError(kind)
        return modules,policy,ContinuousPhysics(modules,total_time_limit=limit,world_radius_limit=radius),frame
    def run(scene,suite,admission,out,budget,**kwargs):
        admission=copy.deepcopy(admission)
        admission["source_identity"]={"original_admission_reference":admission["source_identity"],"r6_controller":cfg,"original_equivalence_claimed":kind=="legacy"}
        kwargs["record_features"]=False
        if job.get("max_steps"):kwargs["max_steps"]=job["max_steps"]
        return ORIGINAL_RUN(scene,suite,admission,out,budget,**kwargs)
    nav.build_stack=stack;nav.run_episode=run;nav.reencode_controller=change_reference
    try:
        row=base.worker(job);row["controller"]=cfg;nav._write_json(Path(job["out"])/"row.json",row);return row
    finally:nav.build_stack=ORIGINAL_STACK;nav.run_episode=ORIGINAL_RUN;nav.reencode_controller=ORIGINAL_REENCODE

def main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument("batch");ap.add_argument("--workers",type=int,default=4);a=ap.parse_args()
    manifest=json.loads(Path(a.batch).read_text());run=Path(manifest["run"]).resolve();assert run.is_relative_to((ROOT/"runs").resolve()) and 1<=a.workers<=4
    plan=json.loads((run/"plan.json").read_text());base.Budget(plan["deadline_epoch"]).check()
    folder=Path(a.batch).resolve().with_suffix("");folder.mkdir(exist_ok=False)
    files=list((ROOT/"src/sailboat_routing").glob("*.py"))+[Path(__file__),ROOT/"scripts/run_r1.py"]
    src=folder/"source";src.mkdir()
    for f in files:(src/f.name).write_bytes(f.read_bytes())
    nav._write_json(folder/"provenance.json",{"commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),"sources":{str(f.relative_to(ROOT)):file_hash(f) for f in files},"command":sys.argv,"parent_pid":os.getpid(),"cpu_workers":a.workers,"gpu_hours":0})
    jobs=[]
    for j in manifest["jobs"]:
        j=copy.deepcopy(j);j.update(round=manifest.get("round",0),deadline=plan["deadline_epoch"],out=str(folder/(j["scene"]["id"]+"__"+j["variant"])));jobs.append(j)
    rows=[];start=time.time()
    with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers,mp_context=multiprocessing.get_context("spawn")) as pool:
        pending=[pool.submit(worker,j) for j in jobs]
        for future in concurrent.futures.as_completed(pending):
            row=future.result();rows.append(row);nav._write_json(folder/"rows.json",rows)
            print("R6_PROGRESS",len(rows),"/",len(jobs),row["variant"],row["scene_id"],row["success"],row["time_s"],flush=True)
    nav._write_json(folder/"completion.json",{"complete":True,"episodes":len(rows),"wall_seconds":time.time()-start,"episode_cpu_seconds":sum(r["cpu_seconds"] for r in rows)})
if __name__=="__main__":main()
