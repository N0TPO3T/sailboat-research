"""R12 wrapper; original science sources unchanged. Max four single-thread CPU workers."""
import os,sys,json,time,copy,concurrent.futures,multiprocessing,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import run_r8
from sailboat_routing.r8_planner import SampledSupervisor
from sailboat_routing.r12_model import LowOrderModel
from sailboat_routing.navigation import _write_json

class SimpleSupervisor(SampledSupervisor):
    def __init__(self,chart,config):
        super().__init__(chart,config);self.model.close();self.model=LowOrderModel(config['low_order_params'])

def worker(job):
    old=run_r8.SampledSupervisor
    if job['config'].get('low_order_params'):run_r8.SampledSupervisor=SimpleSupervisor
    try:return run_r8.worker(job)
    finally:run_r8.SampledSupervisor=old

def main():
    manifest=Path(sys.argv[1]).resolve();batch=json.loads(manifest.read_text());run=Path(batch['run']).resolve()
    assert run.is_relative_to(ROOT/'runs')
    plan=json.loads((run/'plan.json').read_text());assert time.time()<plan['deadline_epoch']
    folder=manifest.with_suffix('');folder.mkdir(exist_ok=False)
    files=[Path(__file__),ROOT/'scripts/run_r8.py']+list((ROOT/'src/sailboat_routing').glob('*.py'))
    _write_json(folder/'provenance.json',dict(started=time.time(),pid=os.getpid(),workers=4,threads=1,gpu=0,sources={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}))
    jobs=[]
    for j in batch['jobs']:
        j=copy.deepcopy(j);j.update(out=str(folder/(j['scene']['id']+'__'+j['variant'])),deadline=plan['deadline_epoch']);jobs.append(j)
    rows=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context('spawn')) as pool:
        for f in concurrent.futures.as_completed([pool.submit(worker,j) for j in jobs]):
            row=f.result();rows.append(row);_write_json(folder/'rows.json',rows);print(len(rows),len(jobs),row['scene_id'],row['variant'],row['success'],row['reason'],row['time_s'],flush=True)
    _write_json(folder/'completion.json',dict(complete=True,episodes=len(rows),finished=time.time()))
if __name__=='__main__':main()
