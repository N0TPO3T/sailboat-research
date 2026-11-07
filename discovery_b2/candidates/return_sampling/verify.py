import json
import numpy as np
from pilot import ROOT, posterior_catalog, edges, cost, maskof

rows=json.loads((ROOT/'results/episodes.json').read_text())
traces=json.loads((ROOT/'results/trajectories.json').read_text())
fields=json.loads((ROOT/'results/fields.json').read_text())
assert len(rows)==72 and len(traces)==72 and len(fields)==24
assert len({(r['seed'],r['true_lengthscale'],r['method']) for r in rows})==72
minimum_slack=min(r['budget_s']-r['duration_s']-r['plan_s'] for r in rows)
assert minimum_slack>=0, 'Including measured planning time violates deadline'
for r,tr in zip(rows,traces):
    assert (r['seed'],r['true_lengthscale'],r['method'])==(tr['seed'],tr['lengthscale'],tr['method'])
    assert len(r['route'])==len(set(r['route']))
    assert all(b['t']>=a['t']-1e-8 for a,b in zip(tr['rows'],tr['rows'][1:]))
    assert abs(tr['rows'][-1]['t']-r['duration_s'])<1e-7
    assert np.hypot(tr['rows'][-1]['x'],tr['rows'][-1]['y'])<1e-7
    assert sum(x['event']=='sample' for x in tr['rows'])==r['samples']
    assert np.isfinite(r['rmse']) and r['rmse']>=0
for d in fields[::2]:
    points=np.array(d['points']);grid=np.array(d['grid'])
    V,M=posterior_catalog(points,grid)
    assert min(V)>0
    for mask in range(256):
        for bit in range(8):
            assert V[mask|1<<bit]<=V[mask]+1e-10
        ids,W=M[mask]
        assert len(ids)==1+mask.bit_count()
        assert ids==[0]+[i+1 for i in range(8) if mask>>i&1]
        assert W.shape==(len(grid),len(ids))
    rr=[r for r in rows if r['seed']==d['seed']]
    # Changing unseen truth/kernel does not change selected route or expected information.
    for method in ['greedy','insertion','exact']:
        a,b=[r for r in rr if r['method']==method]
        assert a['route']==b['route'] and a['variance']==b['variance']
report={'status':'passed','episode_rows':72,'tasks':24,'minimum_deadline_slack_including_plan_s':minimum_slack,
        'checks':['no duplicate visits','trajectory time monotonic','returns to home','sample count matches point observations',
                  'all posterior subsets positive and monotone','posterior consumes only measured indices',
                  'route invariant to hidden truth/kernel','including measured planning latency still on time'],
        'limitations':['does not validate hydrodynamics or maneuver displacement','exactness limited to fixed edge trajectories']}
(ROOT/'results/verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
