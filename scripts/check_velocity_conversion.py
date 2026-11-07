"""Verify the one-time replay correction against the preserved pre-fix state."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from dynamic import *
old=torch.load(ROOT/'runs/train_masked/resume.pt',weights_only=False,map_location='cpu')
new=torch.load(ROOT/'runs/train_final/step_26082.pt',weights_only=False,map_location='cpu')
assert old['steps']==new['steps']==26082 and new['roll_projected_velocity']
result={}
for key in ('s_seq','s_curr','s_next_seq','s_next_curr'):
    x=old['replay'][key];y=new['replay'][key]
    correction=x[...,5]*(1-torch.cos(x[...,2]))*x[...,24]
    assert torch.allclose(y[...,21],x[...,21]+correction,atol=1e-7)
    columns=[i for i in range(26) if i!=21]
    assert torch.equal(x[...,columns],y[...,columns])
    result[key]=dict(max_abs_correction=float(correction.abs().max()),other_columns_unchanged=True)
assert all(torch.equal(v,new['actor'][k]) for k,v in old['actor'].items())
(ROOT/'runs/train_final/velocity_conversion_check.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
