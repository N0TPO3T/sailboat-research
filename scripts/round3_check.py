"""Targeted invariants of the new input-only adaptation controls."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from round3_policy import *
run=ROOT/'runs/round3_20261011_2308'
ck=torch.load(ROOT/'checkpoints/round3/w0/actor_init.pt',weights_only=False,map_location='cpu')
base=FixedNormalizer(ck['normalizer']);guard=AdaptNormalizer(dict(ck['normalizer'],adaptation='headon_guard'))
shrink=AdaptNormalizer(dict(ck['normalizer'],adaptation='shrink'));original=AdaptNormalizer(ck['normalizer'])
for angle in (-2.,-.7,0.,1.3):
    for vt,suppress in [([-1.,.1],True),([0.,1.],False),([1.,.5],False)]:
        x=np.zeros(26,dtype=np.float32);x[2]=.2;x[3]=angle;x[4]=3.2;x[5]=.7;x[12]=500
        x[14:18]=[80.,.3,0.,0.];x[18:20]=[70.,20.];x[20:22]=body(np.array(vt)-velocity(x),angle)
        x[22]=1;x[24:26]=1;t=torch.tensor(x).repeat(2,10,1)
        a=base.normalize(t);b=guard.normalize(t)
        assert torch.equal(a,original.normalize(t));assert torch.equal(a[...,:18],b[...,:18])
        assert torch.count_nonzero(b[...,18:26])==0 if suppress else torch.equal(a,b)
        assert torch.equal(shrink.normalize(t)[...,18:26],a[...,18:26]*.5)
        t[...,24]=0;assert torch.equal(guard.normalize(t),base.normalize(t))
(run/'targeted_checks.json').write_text(json.dumps(dict(original_exact=True,inherited18_untouched=True,
    observed_velocity_rotation_checked=True,invalid_mask_preserved=True,batch_history_shapes=True),indent=2))
print('round3 targeted checks passed')
