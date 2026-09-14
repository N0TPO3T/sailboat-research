"""Bounded CPU smoke check using unmodified reference files; not paper evaluation."""
from pathlib import Path
import argparse,os,sys,json,hashlib,importlib.util,random,time
p=argparse.ArgumentParser();p.add_argument('--steps',type=int,default=50);p.add_argument('--output',required=True);args=p.parse_args()
assert 1<=args.steps<=1000
root=Path(__file__).resolve().parents[1]
if sys.platform.startswith('linux'):
    allowed=Path('/home/ot/Students/hs').resolve()
    assert root.is_relative_to(allowed)
    assert Path(args.output).resolve().is_relative_to(allowed)
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
os.environ['OMP_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1'
sys.dont_write_bytecode=True
import numpy as np,torch,scipy,gymnasium,pygame
torch.set_num_threads(1)
sys.path.insert(0,str(root/'sailboat_RL/PART4/SAC'))
import utils_fc,utils_lstm
used=[]
def module(rel):
    f=root/rel;used.append(f)
    spec=importlib.util.spec_from_file_location('hs_env_'+str(len(used)),f)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
result={'purpose':'CPU engineering smoke; not a benchmark or paper reproduction','steps_limit':args.steps,'noise':'no additional sensor/actuator wrapper; environment wind retained','versions':{'python':sys.version,'torch':torch.__version__,'numpy':np.__version__,'scipy':scipy.__version__,'gymnasium':gymnasium.__version__},'cases':[]}
for prefix,dim,envfile,cls,mod in [
 ('sac_s14nowind_buf1e6_seed100',14,'sailboat_s14.py','Sailboat_nowind_last',utils_fc),
 ('sac_s14wind_buf1e6_seed100',16,'sailboat_s14_wind.py','Sailboat_wind_last',utils_fc),
 ('saclstm_s14nowind_buf1e6_seed100',14,'sailboat_s14.py','Sailboat_nowind_last',utils_lstm)]:
    random.seed(0);np.random.seed(0);torch.manual_seed(0)
    env=getattr(module('sailboat_RL/gymnasium/envs/sailboat/'+envfile),cls)(render_mode=None)
    lstm=mod is utils_lstm;actor=mod.Actor(dim,2,(256,256) if lstm else (1024,512,256))
    ap=root/'model'/f'{prefix}_actor7200.pth';npth=root/'model'/f'{prefix}_normalizer7200.pth';used.extend([ap,npth,Path(mod.__file__)])
    actor.load_state_dict(torch.load(ap,map_location='cpu',weights_only=True),strict=True);actor.eval()
    normalizer=mod.ZScoreNormalizer(dim,torch.device('cpu'));normalizer.load_state_dict(torch.load(npth,map_location='cpu',weights_only=True))
    obs,_=env.reset(seed=0);assert obs.shape==(dim,)
    prev=obs.copy();prev_a=np.zeros(2,dtype=np.float32);reward_sum=0.;start=time.monotonic();terminated=truncated=False
    for step in range(args.steps):
        with torch.no_grad():
            kw={'current_state':normalizer.normalize(torch.tensor(obs,dtype=torch.float32).unsqueeze(0)),'deterministic':True}
            if lstm:kw.update(single_step_mode=True,prev_state=normalizer.normalize(torch.tensor(prev,dtype=torch.float32).unsqueeze(0)),prev_action=torch.tensor(prev_a).unsqueeze(0),env_ids=['smoke'])
            a,_=actor(**kw);a=a[0].numpy()
        old=obs.copy();obs,reward,terminated,truncated,info=env.step(a*env.action_space.high)
        assert np.isfinite(obs).all() and np.isfinite(reward) and np.isfinite(a).all()
        prev=old;prev_a=a.copy();reward_sum+=float(reward)
        if terminated or truncated:break
    case={'model':prefix,'steps':step+1,'finite':True,'terminated':bool(terminated),'truncated':bool(truncated),'reward':reward_sum,'final_distance':float(np.linalg.norm(obs[:2]-obs[12:14])),'seconds':time.monotonic()-start}
    result['cases'].append(case);print(json.dumps(case),flush=True);env.close()
# Check that the obstacle environment can reset/step, without claiming an obstacle policy.
env=module('sailboat_RL/gymnasium/envs/sailboat/sailboat_s14_obst_V3.py').Sailboat_obst_v3(render_mode=None)
random.seed(0);np.random.seed(0);o,_=env.reset(seed=0)
for _ in range(5):
    o,reward,term,trunc,_=env.step(np.zeros(2,dtype=np.float32));assert o.shape==(18,) and np.isfinite(o).all() and np.isfinite(reward)
    if term or trunc:break
result['obstacle_environment']='reset + up to 5 zero-action steps passed; no policy tested';env.close()
result['source_sha256']={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in used}
out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2));print('PASS',out)
