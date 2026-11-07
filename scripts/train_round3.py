"""Inherited SAC updater; causal, matched fixed-window sequences; own checkpoints."""
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from round3_policy import *
import argparse
import random
import shutil
import hashlib

p=argparse.ArgumentParser()
p.add_argument('--steps',type=int,default=CFG['train_steps'])
p.add_argument('--out',default='runs/train_v1')
p.add_argument('--resume')
p.add_argument('--hours',type=float,default=10)
p.add_argument('--dev-every',type=int,default=5000)
p.add_argument('--dynamic-columns-only',action='store_true')
p.add_argument('--mask-expired-metadata',action='store_true')
p.add_argument('--dev-at-start',action='store_true')
p.add_argument('--seed',type=int,default=CFG['seed'])
p.add_argument('--scene-base',type=int,default=710000)
p.add_argument('--handover-distribution',choices=['legacy','actual_routes'],default='legacy')
p.add_argument('--adaptation',choices=['original','shrink','headon_guard'],required=True)
args=p.parse_args()
out=ROOT/args.out
if out.exists():raise RuntimeError('Use a new training output directory; preserve all previous runs')
out.mkdir(parents=True)
for source in (Path(__file__),ROOT/'src/dynamic.py',ROOT/'src/round3_policy.py',ROOT/'configs/prototype.json'):
    shutil.copy2(source,out/('source_'+source.name))
random.seed(args.seed);np.random.seed(args.seed);torch.manual_seed(args.seed)
mods=CandidateModules()
learner=mods.original.SAC_lstm_countinuous(state_dim=26,action_dim=2,net_width=256,
    dvc=torch.device('cpu'),a_lr=CFG['actor_lr'],c_lr=CFG['critic_lr'],
    gamma=.99,alpha=.02,adaptive_alpha=False,batch_size=CFG['batch_size'])
actor,norm=make_expert(mods)
norm=AdaptNormalizer(dict(norm.state_dict(),adaptation=args.adaptation))
learner.actor.load_state_dict(actor.state_dict());learner.state_normalizer=norm
if args.dynamic_columns_only:
    constrain_dynamic_columns(learner.actor)
    learner.actor_optimizer=torch.optim.Adam([p for p in learner.actor.parameters() if p.requires_grad],lr=0.0003,weight_decay=0.)
learner.actor.eval();learner.q_critic.eval();learner.q_critic_target.eval()
learner.critic_warmup_steps=CFG['critic_warmup']
learner.replay_buffer=mods.original.ReplayBuffer(26,2,CFG['window'],20000,torch.device('cpu'))
steps=0;episode=0;actor_updates=0;elapsed_prior=0.
if args.resume:
    ck=torch.load(ROOT/args.resume,map_location='cpu',weights_only=False)
    if 'training_protocol' in ck:
        assert ck['training_protocol']==dict(seed=args.seed,scene_base=args.scene_base,handover_distribution=args.handover_distribution,adaptation=args.adaptation)
    assert ck.get('dynamic_columns_only',False)==args.dynamic_columns_only, 'Resume must preserve trainable parameter mode'
    for name in ('actor','q_critic','q_critic_target','actor_optimizer','q_critic_optimizer'):
        getattr(learner,name).load_state_dict(ck[name])
    learner.state_normalizer.load_state_dict(ck['normalizer'])
    learner.replay_buffer.__dict__.update(ck['replay'])
    if not ck.get('roll_projected_velocity',False):
        # Correct this prototype's earlier planar-velocity approximation in raw
        # replay: body relative vy gains v*(1-cos(roll)); missing slots stay zero.
        for key in ('s_seq','s_curr','s_next_seq','s_next_curr'):
            states=getattr(learner.replay_buffer,key)
            states[...,21]+=states[...,5]*(1-torch.cos(states[...,2]))*states[...,24]
    learner.training_step=ck['updates'];learner.critic_update_count=ck['critic_update_count']
    steps=ck['steps'];episode=ck['episode'];actor_updates=ck['actor_updates'];elapsed_prior=ck['wall_seconds']
    random.setstate(ck['python_rng']);np.random.set_state(ck['numpy_rng']);torch.set_rng_state(ck['torch_rng'])
started=time.perf_counter();last_dev=steps;last_save=steps
if args.mask_expired_metadata:
    norm.state['mask_expired_metadata']=True
(out/'config.json').write_text(json.dumps(dict(config=CFG,args=vars(args),initialization='actor hot start, new critic/optimizer/replay'),indent=2))
def parameter_hash(model):
    return hashlib.sha256(b''.join(v.detach().cpu().numpy().tobytes() for v in model.state_dict().values())).hexdigest()
(out/'initialization.json').write_text(json.dumps(dict(resume_source=args.resume,seed=args.seed,
    actor_sha256=parameter_hash(learner.actor),critic_sha256=parameter_hash(learner.q_critic),
    initial_replay_size=learner.replay_buffer.size,initial_steps=steps,
    mask_expired_metadata=norm.state.get('mask_expired_metadata',False),roll_projected_velocity=True),indent=2))

def save(name):
    payload={key:getattr(learner,key).state_dict() for key in ('actor','q_critic','q_critic_target','actor_optimizer','q_critic_optimizer')}
    payload.update(normalizer=norm.state_dict(),replay=learner.replay_buffer.__dict__,
        steps=steps,episode=episode,updates=learner.training_step,actor_updates=actor_updates,
        critic_update_count=learner.critic_update_count,python_rng=random.getstate(),
        numpy_rng=np.random.get_state(),torch_rng=torch.get_rng_state(),
        wall_seconds=elapsed_prior+time.perf_counter()-started,
        dynamic_columns_only=args.dynamic_columns_only,mask_expired_metadata=norm.state.get('mask_expired_metadata',False),
        roll_projected_velocity=True,
        training_protocol=dict(seed=args.seed,scene_base=args.scene_base,handover_distribution=args.handover_distribution,adaptation=args.adaptation),
        resume_boundary='episode boundary; next episode seed=scene_base+episode',config=CFG)
    dest=out/name;temp=dest.with_suffix('.tmp');torch.save(payload,temp);temp.replace(dest)
    torch.save(learner.actor.state_dict(),out/'actor.pth')
    torch.save(norm.state_dict(),out/'normalizer.pth')

if args.dev_at_start:
    save(f'step_{steps}.pt')
    results=[run_episode(s,'avoid',learner.actor,norm) for s in bank('dev')]
    with (out/'development.jsonl').open('a') as f:f.write(json.dumps(dict(steps=steps,results=results))+'\n')
    print(json.dumps(dict(development_step=steps,safe=sum(r['safe_complete'] for r in results),count=len(results))),flush=True)

while steps<args.steps and time.perf_counter()-started<args.hours*3600:
    env=DynamicEnv();spec=scenario(args.scene_base+episode)
    o18,o26,m=env.reset(spec)
    normal=ObstacleController(mods,mode='eval');normal.reset(o18)
    window=Window(o26)
    prefix=int(np.random.randint(10,46)) if args.handover_distribution=='legacy' else None
    # Fixed episode mixture: one third initial expert, one third actual range
    # takeover, one third actual risk takeover. The complete normal prefix is
    # executed, preserving real actuator state, sensor, wind and both histories.
    start_mode=('avoid','range','risk')[episode%3] if args.handover_distribution=='actual_routes' else 'legacy'
    handover_router=Router(start_mode) if start_mode!='legacy' else None
    total_reward=0.;loss={};takeover=False;takeover_time=None;expert_steps=0
    while True:
        an=normal.act(o18).action
        # Prefix is a real normal-policy trajectory; switch early if target enters FOV.
        enter=(env.t>=prefix or m['visible']) if start_mode=='legacy' else handover_router.choose(m)
        takeover=takeover or enter
        if takeover and takeover_time is None:takeover_time=env.t
        use_normal=not takeover
        command=an if use_normal else expert_action(learner.actor,norm,window,o26,deterministic=False)
        ss,aa=window.arrays()
        (n18,n26,nm),reward,done,info=env.step(command)
        window.append(o26,command);ns,na=window.arrays()
        # Time limits bootstrap; arrival, boundary and true safety failure terminate.
        terminal=info['arrived'] or info['violated'] or np.linalg.norm(env.raw[:2])>=750
        learner.replay_buffer.add(ss,aa,o26,command,reward,ns,na,n26,terminal)
        normal.previous_action=command.copy()
        steps+=1;total_reward+=reward;expert_steps+=int(takeover)
        if learner.replay_buffer.size>=256 and steps%CFG['update_every']==0:
            loss=learner.train()
            actor_updates+=int(loss.get('policy_updated',False))
            if not all(math.isfinite(float(v)) for v in loss.values()):raise FloatingPointError(loss)
        o18,o26,m=n18,n26,nm
        if done:break
    episode+=1
    record=dict(episode=episode,steps=steps,updates=learner.training_step,actor_updates=actor_updates,
        kind=spec['kind'],reward=total_reward,arrived=info['arrived'],violated=info['violated'],
        time=env.t,scene_seed=spec['seed'],start_mode=start_mode,takeover_time=takeover_time,expert_steps=expert_steps,
        loss=loss,wall_seconds=elapsed_prior+time.perf_counter()-started)
    with (out/'learning.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
    print(json.dumps(record),flush=True)
    normal.close();env.segment.close()
    if (out/'STOP_AFTER_EPISODE').exists():
        save('resume.pt')
        break
    if steps-last_save>=1000:
        save('resume.pt');last_save=steps
    if steps-last_dev>=args.dev_every:
        save(f'step_{steps}.pt');last_dev=steps
        results=[run_episode(s,'avoid',learner.actor,norm) for s in bank('dev')]
        with (out/'development.jsonl').open('a') as f:f.write(json.dumps(dict(steps=steps,results=results))+'\n')
        print(json.dumps(dict(development_step=steps,safe=sum(r['safe_complete'] for r in results),count=len(results))),flush=True)
if args.handover_distribution=='actual_routes' and steps!=last_dev:
    save(f'step_{steps}.pt')
    results=[run_episode(s,'avoid',learner.actor,norm) for s in bank('dev')]
    with (out/'development.jsonl').open('a') as f:f.write(json.dumps(dict(steps=steps,results=results))+'\n')
    print(json.dumps(dict(development_step=steps,safe=sum(r['safe_complete'] for r in results),count=len(results))),flush=True)
save('resume.pt')
(out/'complete.json').write_text(json.dumps(dict(steps=steps,updates=learner.training_step,actor_updates=actor_updates,
    episodes=episode,wall_seconds=elapsed_prior+time.perf_counter()-started,
    stopped_by='requested_steps' if steps>=args.steps else ('stop_marker' if (out/'STOP_AFTER_EPISODE').exists() else 'wall_budget')),indent=2))
