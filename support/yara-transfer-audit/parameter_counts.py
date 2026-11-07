import json,torch
from pathlib import Path
from stable_baselines3 import SAC,PPO
r=Path('/work/workspace/src/Yara_OVE/esailor/policy');out={}
for cls in [PPO,SAC]:
 m=cls.load(str(r/f'esailor_{cls.__name__}_53_A3232_C3232.zip'),device='cpu')
 out[cls.__name__]={'all_policy_parameters':sum(p.numel() for p in m.policy.parameters())}
 if cls==SAC:out[cls.__name__]['actor_parameters']=sum(p.numel() for p in m.actor.parameters())
 else:out[cls.__name__]['actor_parameters']=sum(p.numel() for p in m.policy.mlp_extractor.policy_net.parameters())+sum(p.numel() for p in m.policy.action_net.parameters())+m.policy.log_std.numel()
 out[cls.__name__]['details']={k:str(getattr(m,k,'absent')) for k in ['gae_lambda','clip_range','normalize_advantage','vf_coef','max_grad_norm','target_update_interval','train_freq','target_entropy']}
Path('/work/transfer_audit/parameter_counts.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
