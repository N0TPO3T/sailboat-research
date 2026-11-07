"""Compare both predictors to already executed fixed protocols; no new truth branches."""
import sys,json,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from sailboat_routing.runtime import configure_cpu
configure_cpu()
import numpy as np
from sailboat_routing.r12_model import LowOrderModel
from sailboat_routing.navigation import _write_json
from check_r12_branches import parts,frame_at,reconstructed_base
R=ROOT/'runs/r12_revision_20261006';params=json.loads((R/'calibration.json').read_text())['parameters_tau_gain_ratecap'];out=[];model=LowOrderModel(params)
for b in json.loads((R/'fixed_branches.json').read_text()):
 d=json.loads(Path(b['source']).read_text());t=b['time'];s,st,ch=parts(d);base,nom=reconstructed_base(d,t,ch);pre=next(p for p in d['predictions'] if p['time']==t);cs=[c for c in pre['candidates'] if c['name']==b['candidate']];c=cs[0] if cs else {'target':list(frame_at(d,t).goal_world),'hold':15}
 tr=d['trajectory'];h=[np.array(x['raw'],np.float32) for x in tr[:t+1]];a=[np.array(x['command'],np.float32) for x in tr[1:t+1]];oh=[x['observations'] for x in tr[:t+1]]
 low=model.rollout(h,a,oh,frame_at(d,t),c['target'],np.array(tr[t+1]['command'],np.float32),60,st,np.array(s['goal']),copy.deepcopy(base),c['hold']);k=min(len(low['path'])-1,b['common_steps']);truth=np.array(b['actual']['path'][:k+1]);detail=np.array(b['prediction']['path'][:k+1]);simple=np.array(low['path'][:k+1]);am=min(b['actual']['margins'][:k])
 out.append({'scene':b['scene'],'time':t,'candidate':b['candidate'],'common_steps':k,'simple_valid':low['valid'],'simple_failure':low['prediction_failure'],'simple_prediction':low,'actual_margin_common':am,'detailed_margin_common':min(b['prediction']['margins'][:k]),'simple_margin_common':min(low['margins'][:k]),'detailed_max_error':float(max(np.linalg.norm(detail-truth,axis=1))),'simple_max_error':float(max(np.linalg.norm(simple-truth,axis=1)))})
_write_json(R/'matched_prediction_quality.json',out)
print('matched fixed protocols',len(out),'full60',sum(x['common_steps']==60 for x in out),'median max errors',np.median([x['detailed_max_error'] for x in out]),np.median([x['simple_max_error'] for x in out]))
