"""Fixed-bank rollout worker, reusing the original physical rollout implementation."""
import sys,json,hashlib,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from dynamic import *
p=argparse.ArgumentParser();p.add_argument('--bank',required=True);p.add_argument('--checkpoint',required=True)
p.add_argument('--mode',choices=['normal','avoid','range','risk'],required=True);p.add_argument('--out',required=True)
p.add_argument('--train-seed',type=int,required=True);args=p.parse_args()
out=ROOT/args.out
if out.exists():raise RuntimeError('Do not overwrite evaluations')
out.mkdir(parents=True);(out/'trajectories').mkdir()
actor,norm=make_expert(CandidateModules());ck=torch.load(ROOT/args.checkpoint,weights_only=False,map_location='cpu')
actor.load_state_dict(ck['actor']);norm.load_state_dict(ck['normalizer'])
specs=json.loads((ROOT/args.bank).read_text())['scenarios']
(out/'protocol.json').write_text(json.dumps(dict(bank=args.bank,checkpoint=args.checkpoint,train_seed=args.train_seed,
    mode=args.mode,checkpoint_sha256=hashlib.sha256((ROOT/args.checkpoint).read_bytes()).hexdigest(),config=CFG),indent=2))
for spec in specs:
    path=out/f'trajectories/{spec["seed"]}_{args.mode}.npz'
    r=run_episode(spec,args.mode,actor,norm,path);r['train_seed']=args.train_seed
    d=np.load(path);active=d['active'][:-1];changes=np.diff(np.r_[False,active].astype(int))
    entries=np.flatnonzero(changes==1).tolist();exits=np.flatnonzero(changes==-1).tolist()
    invisible=[]
    if spec['target_position'] is not None:
        for i in range(len(active)):
            dist=swept_distance(d['target'][i]-d['raw'][i,:2],d['target'][i+1]-d['raw'][i+1,:2])
            if dist<40 and not d['visible'][i]:invisible.append(i+1)
    r.update(takeover_times=entries if args.mode in ('range','risk') else [],
        handback_times=exits if args.mode in ('range','risk') else [],
        handback_and_safe_complete=bool(exits and r['safe_complete']),invisible_violation_times=invisible,
        finished_normal_after_handback=bool(exits and r['safe_complete'] and not active[-1]),
        last_executed_policy='avoid' if active[-1] else 'normal')
    with (out/'episodes.jsonl').open('a') as f:f.write(json.dumps(r)+'\n')
    print(json.dumps(r),flush=True)
