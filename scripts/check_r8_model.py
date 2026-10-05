import sys,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from sailboat_routing.runtime import configure_cpu
configure_cpu()
import numpy as np
from sailboat_routing.r8_model import CausalModel
from sailboat_routing.frames import LocalFrame
from sailboat_routing.planner import CircleObstacle
R=ROOT/'runs/r7_dynamic_20261005T033700Z';model=CausalModel();out=[]
for batch,scene,t in [('confirmation85','confirm_mixed_3',150),('confirmation85','confirm_mixed_7',150),('goal_confirmation','final_overtaking_1',273)]:
 d=json.loads((R/batch/(scene+'__current')/'trace.json').read_text());tr=d['trajectory'];h=[np.array(x['raw'],np.float32) for x in tr[:t+1]];a=[np.array(x['command'],np.float32) for x in tr[1:t+1]];oh=[x['observations'] for x in tr[:t+1]]
 change=[c for c in d['changes'] if c['applied_at']<=t];start=change[-1]['applied_at'] if change else 0;target=change[-1]['target'] if change else tr[0]['target'];frame=LocalFrame.for_leg(tr[start]['raw'][:2],target);static=tuple(CircleObstacle(tuple(o['center_xy']),o['entity_radius'],60.) for o in d['scene']['static'])
 begin=time.time();fit=model.estimate(h);pred=model.rollout(h,a,oh,frame,target,np.array(tr[t+1]['command'],np.float32),30,static,np.array(d['scene']['goal']));actual=np.array([x['raw'][:2] for x in tr[t:t+31]]);p=np.array(pred['path']);errors=np.linalg.norm(p[:len(actual)]-actual[:len(p)],axis=1)
 out.append(dict(scene=scene,time=t,fit=fit,prediction=pred,actual=actual.tolist(),errors=errors.tolist(),seconds=time.time()-begin,target_changes_in_window=[c for c in d['changes'] if t<c['applied_at']<=t+30]));print(scene,fit,errors[-1],time.time()-begin,flush=True)
model.close();(ROOT/'runs/r8_closedloop_20261005T062543Z/predictor_witness.json').write_text(json.dumps(out,indent=2))
