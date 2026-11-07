import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from dynamic import *
import argparse
p=argparse.ArgumentParser()
p.add_argument('--split',choices=['dev','test'],default='dev')
p.add_argument('--checkpoint')
p.add_argument('--out',required=True)
p.add_argument('--modes',nargs='+',default=['normal','avoid','range','risk'])
args=p.parse_args()
out=ROOT/args.out;out.mkdir(parents=True,exist_ok=True)
if (out/'episodes.jsonl').exists():raise RuntimeError('Use a new output directory; never overwrite results')
mods=CandidateModules();actor,norm=make_expert(mods)
if args.checkpoint:
    ck=torch.load(ROOT/args.checkpoint,weights_only=False,map_location='cpu')
    actor.load_state_dict(ck['actor']);norm.load_state_dict(ck['normalizer'])
else: ck=None
specs=bank(args.split)
(out/'protocol.json').write_text(json.dumps(dict(split=args.split,scenarios=specs,modes=args.modes,
    checkpoint=args.checkpoint,train_steps=ck['steps'] if ck else 0,config=CFG),indent=2))
results=[]
for spec in specs:
    for mode in args.modes:
        r=run_episode(spec,mode,actor,norm,out/f'trajectories/{spec["seed"]}_{mode}.npz')
        results.append(r)
        with (out/'episodes.jsonl').open('a') as f:f.write(json.dumps(r)+'\n')
        print(json.dumps(r),flush=True)
common=[s['seed'] for s in specs if all(next(r for r in results if r['seed']==s['seed'] and r['mode']==mode)['safe_complete'] for mode in args.modes)]
summary={}
for mode in args.modes:
    rr=[r for r in results if r['mode']==mode]
    cc=[r for r in rr if r['seed'] in common]
    distances=[r['min_distance'] for r in rr if r['min_distance'] is not None]
    summary[mode]=dict(n=len(rr),safe_complete=sum(r['safe_complete'] for r in rr),arrived=sum(r['arrived'] for r in rr),
        violations=sum(r['violated'] for r in rr),common_safe_n=len(cc),
        common_safe_time_mean=float(np.mean([r['time'] for r in cc])) if cc else None,
        min_distance=min(distances,default=None),mean_switches=float(np.mean([r['switches'] for r in rr])),
        mean_takeover_seconds=float(np.mean([r['takeover_seconds'] for r in rr])),
        decision_ms_per_step=1000*sum(r['decision_seconds'] for r in rr)/sum(r['time'] for r in rr),
        wall_seconds=sum(r['wall_seconds'] for r in rr))
(out/'summary.json').write_text(json.dumps(dict(methods=summary,common_safe_seeds=common),indent=2))
print(json.dumps(summary,indent=2))
