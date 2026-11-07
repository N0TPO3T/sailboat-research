import json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];run=ROOT/'runs/round4_20261025'
read=lambda p:[json.loads(x) for x in p.read_text(encoding='utf-8-sig').splitlines()]
rows=read(run/'confirmation50/seed_20261011/episodes.jsonl');by={(r['seed'],r['mode']):r for r in rows};details=[]
for seed in (940038,940040,940045):
 a=np.load(run/f'confirmation50/seed_20261011/trajectories/{seed}_old_range.npz');b=np.load(run/f'confirmation50/seed_20261011/trajectories/{seed}_weighted_range.npz');cut=by[seed,'old_range']['takeover_times'][0]
 assert cut==by[seed,'weighted_range']['takeover_times'][0]
 for key in ('raw','setpoints','wind'):np.testing.assert_array_equal(a[key][:cut+1],b[key][:cut+1])
 np.testing.assert_array_equal(a['action'][:cut],b['action'][:cut])
 details.append(dict(seed=seed,first_takeover=cut,identical_real_prefix=True,old=by[seed,'old_range'],new=by[seed,'weighted_range']))
# The worst routing delay is a no-target interface difference, not an avoidance detour.
for s in (20261011,20261012):
 ds={m:np.load(run/f'confirmation50/seed_{s}/trajectories/940007_{m}.npz') for m in ('normal','w0','old_avoid','weighted_avoid','weighted_range')}
 assert not ds['weighted_range']['active'][:-1].any()
 np.testing.assert_array_equal(ds['normal']['raw'],ds['weighted_range']['raw'])
 for m in ('old_avoid','weighted_avoid'):np.testing.assert_array_equal(ds['w0']['raw'],ds[m]['raw'])
original=read(ROOT/'runs/round3_20261011_2308/diagnosis/branches/results.jsonl');new=read(run/'diagnosis/selected_branches/results.jsonl')
for r in new:
 old=next(x for x in original if x['train_seed']==r['train_seed'] and x['seed']==r['seed'] and x['continuation']=='trained');assert old['fingerprint']==r['fingerprint']
result=dict(new_rescues=details,selected_branches=new,no_target_940007_equivalence_verified=True)
(run/'diagnosis/final_attribution.json').write_text(json.dumps(result,indent=2))
print(json.dumps(dict(prefix_checks=len(details),selected_branch_checks=len(new),no_target_equivalence=True)))
