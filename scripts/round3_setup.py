"""Establish the untrained window control without suppressing its 18D slots."""
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from dynamic import *
run=ROOT/'runs/round3_20261011_2308';dest=ROOT/'checkpoints/round3/w0'
assert not dest.exists();dest.mkdir(parents=True)
mods=CandidateModules();actor,norm=make_expert(mods)
checkpoints=[torch.load(ROOT/f'checkpoints/round2/{s}/resume.pt',weights_only=False,map_location='cpu') for s in (20261011,20261012)]
for key,value in checkpoints[0]['normalizer'].items():
    other=checkpoints[1]['normalizer'][key]
    assert torch.equal(value,other) if isinstance(value,torch.Tensor) else value==other
norm.load_state_dict(checkpoints[0]['normalizer']);assert norm.state['mask_expired_metadata']
for key,value in actor.state_dict().items():
    if key in ('fc_input.0.weight','current_state_fc.0.weight'):
        assert torch.count_nonzero(value[:,18:26])==0
        for c in checkpoints:
            assert torch.equal(value[:,:18],c['actor'][key][:,:18])
            assert torch.equal(value[:,26:],c['actor'][key][:,26:])
    else:
        for c in checkpoints:assert torch.equal(value,c['actor'][key]),key
torch.save(dict(actor=actor.state_dict(),normalizer=norm.state_dict(),kind='untrained_control_no_optimizer'),dest/'actor_init.pt')
e=DynamicEnv();spec=scenario(920033,'headon');o18,o26,m=e.reset(spec)
# A legal visible target must populate original obstacle slots for W0 too.
e.target=e.raw[:2]+80*np.array([math.cos(e.raw[3]),math.sin(e.raw[3])]);o18,o26,m=e.observe()
assert m['visible'] and abs(float(o18[14])-80)<1e-3 and torch.count_nonzero(norm.normalize(torch.from_numpy(o26))[14:18])>0
e.segment.close()
receipt=dict(round2_selected_steps=[c['steps'] for c in checkpoints],identical_normalizers=True,
    inherited_actor_unchanged=True,new_columns_zero=True,original_obstacle_slots_retained=True,
    window=CFG['window'],mask=True,checkpoint='checkpoints/round3/w0/actor_init.pt',
    actor_sha256=hashlib.sha256(b''.join(v.numpy().tobytes() for v in actor.state_dict().values())).hexdigest(),
    config=CFG,scope='W0 is a baseline Actor, not a trained or resumable SAC state')
(run/'w0_identity.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
