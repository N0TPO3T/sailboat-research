#!/usr/bin/env python3
"""Small R1 batch runner using the unchanged continuous navigation loop."""
from pathlib import Path
import sys,os,time,json,argparse,copy,subprocess,hashlib,concurrent.futures,multiprocessing
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from sailboat_routing.runtime import configure_cpu
configure_cpu()
from sailboat_routing import navigation as nav
from sailboat_routing.r1_planner import RouteWaypointPlanner,R1Config
from sailboat_routing.planner import LocalWaypointPlanner
from sailboat_routing.wind_readout import RidgeWindReadout
from sailboat_routing.admission import file_hash

def read(p):return json.loads(Path(p).read_text())
class Budget:
    def __init__(self,deadline):self.deadline=deadline
    def check(self):
        if time.time()>self.deadline:raise TimeoutError('R1 shared 12h deadline reached')

def worker(job):
    start=time.time();cpu_start=time.process_time();out=Path(job['out']);out.mkdir(parents=True,exist_ok=False)
    nav._write_json(out/'job.json',job)
    admission=read(ROOT/'runs/navigation_admission.json')
    method=job.get('mode','geometry_only');model=None
    if method=='estimated_local':model=RidgeWindReadout.load(ROOT/'runs/v0_fit_20261002/model.npz',expected_source_identity=admission['source_identity'],expected_dimension=270)
    made=[]
    def factory(chart,unused,mode):
        planner=RouteWaypointPlanner(chart,R1Config(**job['config']),mode);made.append(planner);return planner
    nav.LocalWaypointPlanner=LocalWaypointPlanner if job['variant']=='anchor' else factory
    try:
        row=nav.run_episode(job['scene'],job['suite'],admission,out,Budget(job['deadline']),method=method,model=model)
        row.update(variant=job['variant'],round=job['round'],config=job['config'],distance_m=job['scene'].get('distance_m',1000),cpu_seconds=time.process_time()-cpu_start)
        nav._write_json(out/'row.json',row)
        if made:nav._write_json(out/'r1_decisions.json',made[0].log)
        nav._write_json(out/'exit.json',{'status':'completed','wall_seconds':time.time()-start,'pid':os.getpid()})
        return row
    except Exception as e:
        nav._write_json(out/'exit.json',{'status':'error','error':repr(e),'wall_seconds':time.time()-start,'pid':os.getpid()});raise

def main():
    ap=argparse.ArgumentParser();ap.add_argument('batch');ap.add_argument('--workers',type=int,default=4);args=ap.parse_args()
    batch=Path(args.batch).resolve();manifest=read(batch);run=Path(manifest['run']).resolve()
    assert run.is_relative_to((ROOT/'runs').resolve()) and 1<=args.workers<=4
    plan=read(run/'plan.json');Budget(plan['deadline_epoch']).check()
    assert 1<=manifest['round']<=plan['max_scientific_rounds']
    folder=batch.with_suffix('');folder.mkdir(exist_ok=False)
    sources={str(f.relative_to(ROOT)):file_hash(f) for f in (ROOT/'src/sailboat_routing').glob('*.py')}
    # Preserve exact scientific implementation for each development batch.
    (folder/'r1_planner.py').write_bytes((ROOT/'src/sailboat_routing/r1_planner.py').read_bytes())
    (folder/'run_r1.py').write_bytes(Path(__file__).read_bytes())
    nav._write_json(folder/'provenance.json',{'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'sources':sources,'command':sys.argv,'parent_pid':os.getpid(),'cpu_workers':args.workers,'threads_per_worker':1,'gpu_hours':0})
    jobs=[]
    for j in manifest['jobs']:
        j=copy.deepcopy(j);j.update(round=manifest['round'],deadline=plan['deadline_epoch'],out=str(folder/(j['scene']['id']+'__'+j['variant'])))
        jobs.append(j)
    rows=[];start=time.time()
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers,mp_context=multiprocessing.get_context('spawn')) as pool:
        pending={pool.submit(worker,j):j for j in jobs}
        for future in concurrent.futures.as_completed(pending):
            row=future.result();rows.append(row)
            nav._write_json(folder/'rows.json',rows)
            print('R1_PROGRESS',len(rows),'/',len(jobs),row['variant'],row['scene_id'],row['success'],row['reason'],flush=True)
    nav._write_json(folder/'completion.json',{'complete':True,'episodes':len(rows),'wall_seconds':time.time()-start,'episode_worker_seconds':sum(r['wall_seconds'] for r in rows)})
if __name__=='__main__':main()
