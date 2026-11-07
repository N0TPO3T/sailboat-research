import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from round3_policy import *
import argparse
import random
p=argparse.ArgumentParser();p.add_argument('checkpoint');args=p.parse_args()
ck=torch.load(ROOT/args.checkpoint,weights_only=False,map_location='cpu')
mods=CandidateModules();initial,norm=make_expert(mods)
changes={k:float(torch.linalg.vector_norm(ck['actor'][k]-v)) for k,v in initial.state_dict().items()}
assert ck['actor_updates']>0 and max(changes.values())>0
assert all(torch.isfinite(v).all() for v in ck['actor'].values())
assert ck['normalizer']['mean'].shape==(26,)
assert ck['replay']['size']>0 and ck['updates']>0
def resume_and_update():
    learner=mods.original.SAC_lstm_countinuous(state_dim=26,action_dim=2,net_width=256,dvc=torch.device('cpu'),
        a_lr=CFG['actor_lr'],c_lr=CFG['critic_lr'],gamma=.99,alpha=.02,adaptive_alpha=False,batch_size=CFG['batch_size'])
    # Load a fresh checkpoint for each comparison: replay update_priorities mutates tensors.
    saved=torch.load(ROOT/args.checkpoint,weights_only=False,map_location='cpu')
    if saved.get('dynamic_columns_only',False):
        constrain_dynamic_columns(learner.actor)
        learner.actor_optimizer=torch.optim.Adam([p for p in learner.actor.parameters() if p.requires_grad],lr=.0003,weight_decay=0.)
    for key in ('actor','q_critic','q_critic_target','actor_optimizer','q_critic_optimizer'):
        getattr(learner,key).load_state_dict(saved[key])
    learner.state_normalizer=AdaptNormalizer(saved['normalizer'])
    learner.replay_buffer.__dict__.update(saved['replay'])
    learner.training_step=saved['updates'];learner.critic_update_count=saved['critic_update_count']
    learner.critic_warmup_steps=CFG['critic_warmup']
    learner.actor.eval();learner.q_critic.eval();learner.q_critic_target.eval()
    random.setstate(saved['python_rng']);np.random.set_state(saved['numpy_rng']);torch.set_rng_state(saved['torch_rng'])
    losses=[learner.train() for _ in range(4)]
    return losses,{k:v.detach().clone() for k,v in learner.actor.state_dict().items()}
a,wa=resume_and_update();b,wb=resume_and_update()
assert a==b and all(torch.equal(wa[k],wb[k]) for k in wa)
if ck.get('dynamic_columns_only',False):
    for key,value in initial.state_dict().items():
        if key in ('fc_input.0.weight','current_state_fc.0.weight'):
            assert torch.equal(ck['actor'][key][:,:18],value[:,:18])
            if key=='fc_input.0.weight':assert torch.equal(ck['actor'][key][:,26:],value[:,26:])
        else:assert torch.equal(ck['actor'][key],value),key
result=dict(checkpoint=args.checkpoint,steps=ck['steps'],updates=ck['updates'],actor_updates=ck['actor_updates'],
            actor_tensor_change_norms=changes,restored_four_updates_identical=True,
            scope='Two restores from same saved state; not a historical upstream exact continuation')
dest=(ROOT/args.checkpoint).parent/'checkpoint_verification.json';dest.write_text(json.dumps(result,indent=2))
print(json.dumps(dict(steps=ck['steps'],actor_updates=ck['actor_updates'],max_change=max(changes.values()),restored_four_updates_identical=True)))
