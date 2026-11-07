"""Development-only counterfactual: is persistent expired metadata disrupting return?"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from dynamic import *
mods=CandidateModules();actor,norm=make_expert(mods)
ck=torch.load(ROOT/'runs/train_columns/step_10277.pt',weights_only=False,map_location='cpu')
actor.load_state_dict(ck['actor']);norm.load_state_dict(ck['normalizer'])
class AblatedNorm(FixedNormalizer):
    def normalize(self,x):
        y=super().normalize(x).clone()
        # DIAGNOSTIC ABLATION ONLY: not the deployed sensor or selected method.
        expired=(x[...,24]==0)
        for index in (23,25):y[...,index]=torch.where(expired,torch.zeros_like(y[...,index]),y[...,index])
        return y
out=ROOT/'runs/expiry_probe';out.mkdir(exist_ok=True)
results=[]
for seed in (810002,810008):
    for label,n in [('unchanged',norm),('zero_expired_metadata',AblatedNorm(norm.state_dict()))]:
        r=run_episode(scenario(seed,'late'),'avoid',actor,n,out/f'{seed}_{label}.npz')
        r['ablation']=label;results.append(r);print(json.dumps(r),flush=True)
(out/'results.json').write_text(json.dumps(results,indent=2))
