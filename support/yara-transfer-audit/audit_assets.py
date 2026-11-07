from pathlib import Path
import hashlib,json,torch,zipfile,io
from stable_baselines3 import PPO,SAC
r=Path('/senior');out=[]
for rel in ['checkpoints/actor.pth','checkpoints/normalizer.pth','checkpoints/obstacle_candidate/saclstm_s14obst_noise_0204_actor10800.pth']:
 p=r/rel;d=torch.load(p,map_location='cpu')
 out.append({'file':rel,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'keys':{k:list(v.shape) if hasattr(v,'shape') else str(type(v)) for k,v in d.items()}})
checks=[]
for cls in [PPO,SAC]:
 p=Path('/work/workspace/src/Yara_OVE/esailor/policy')/f'esailor_{cls.__name__}_53_A3232_C3232.zip'
 m=cls.load(str(p),device='cpu')
 with zipfile.ZipFile(p) as z:d=torch.load(io.BytesIO(z.read('policy.pth')),map_location='cpu')
 checks.append({'model':p.name,'all_saved_policy_tensors_equal':all(torch.equal(v,m.policy.state_dict()[k]) for k,v in d.items()),'num_tensors':len(d)})
assert all(c['all_saved_policy_tensors_equal'] for c in checks)
Path('/work/transfer_audit/asset_tensor_audit.json').write_text(json.dumps({'senior':out,'yara':checks},indent=2))
print(json.dumps({'senior_shapes':[{k:v for k,v in d['keys'].items() if k.endswith('0.weight') or k=='mean'} for d in out],'yara':checks}))
