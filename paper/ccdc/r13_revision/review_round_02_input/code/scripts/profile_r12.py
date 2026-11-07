"""Fixed causal decision inputs, one numerical thread; no physical episodes."""
import sys,json,math,copy,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from sailboat_routing.runtime import configure_cpu
configure_cpu()
import numpy as np
from sailboat_routing.r8_model import CausalModel
from sailboat_routing.r12_model import LowOrderModel
from sailboat_routing.navigation import _write_json
from check_r12_branches import parts,frame_at,reconstructed_base
R=ROOT/'runs/r12_revision_20261006';params=json.loads((R/'calibration.json').read_text())['parameters_tau_gain_ratecap'];branches=json.loads((R/'fixed_branches.json').read_text());rows=[];tables=[]
for item in [branches[0],branches[4],branches[8]]:
 d=json.loads(Path(item['source']).read_text());t=item['time'];s,static,chart=parts(d);base,nom=reconstructed_base(d,t,chart);frame=frame_at(d,t);tr=d['trajectory'];history=[np.array(x['raw'],np.float32) for x in tr[:t+1]];commands=[np.array(x['command'],np.float32) for x in tr[1:t+1]];oh=[x['observations'] for x in tr[:t+1]];old=np.array(tr[t+1]['command'],np.float32);p=np.array(tr[t]['raw'][:2]);angle=math.atan2(nom[1]-p[1],nom[0]-p[0]);options=[('nominal',nom,0),('continue',frame.goal_world,15)]+[(f'turn{deg}',p+350*np.array([math.cos(angle+math.radians(deg)),math.sin(angle+math.radians(deg))]),15) for deg in [-90,-45,45,90]]
 for typ in ['detailed','simple']:
  model=CausalModel() if typ=='detailed' else LowOrderModel(params)
  for repeat in range(3):
   previous=[x for x in d['predictions'] if x['time']<t]
   if typ=='detailed':model.wind=np.array(previous[-1]['wind_estimate']) if previous else np.array([0.,8.]);model.fitted=bool(previous)
   begin=time.perf_counter();cpu=time.process_time();model.estimate(history);evals=[]
   for name,q,hold in options:
    pred=model.rollout(history,commands,oh,frame,q,old,60,static,np.array(s['goal']),copy.deepcopy(base),hold)
    feasible=pred['valid'] and not pred['integration_failed'] and pred['min_margin']>=30;cost=pred['terminal_distance']+(0 if name=='nominal' else 20)+(10 if name.startswith('turn') else 0)
    evals.append(dict(name=name,target=list(q),margin=pred['min_margin'],cost=cost,feasible=feasible,valid=pred['valid'],path=pred['path']))
    if name=='nominal' and feasible:break
   feasible=[x for x in evals if x['feasible']];valid=[x for x in evals if x['valid']]
   selected=evals[0] if evals[0]['feasible'] else min(feasible,key=lambda x:x['cost']) if feasible else max(valid,key=lambda x:(x['margin'],-x['cost'])) if valid else evals[1]
   rows.append(dict(scene=s['id'],time=t,model=typ,repeat=repeat,wall=time.perf_counter()-begin,cpu=time.process_time()-cpu,candidates=len(evals),selected=selected['name']))
   if repeat==0:tables.append(dict(scene=s['id'],time=t,model=typ,candidates=evals,selected=selected['name']))
   _write_json(R/'planning_profile.json',rows);_write_json(R/'matched_decisions.json',tables)
  model.close()
print('profile18 calls complete',flush=True)
