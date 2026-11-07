"""Reaggregate the supplied CSV only; no simulation or third-party packages."""
from pathlib import Path
from decimal import Decimal
import csv, hashlib, json, statistics

P = Path(__file__).resolve().parent
source = P / 'evidence/episodes.csv'
with source.open(newline='', encoding='utf-8-sig') as f:
    rows = [r for r in csv.DictReader(f) if r['stage'] == 'confirmation']
assert len(rows) == 72
index = {(r['scene_id'], r['variant']): r for r in rows}
scenes = sorted({r['scene_id'] for r in rows})
assert len(index) == 72 and len(scenes) == 24
assert all((s, v) in index for s in scenes for v in ('reactive', 'simple', 'sampled'))
assert all(r['success'] in ('True', 'False') for r in rows)
pairs, excluded = [], []
for scene in scenes:
    s15, low = index[scene, 'sampled'], index[scene, 'simple']
    if s15['success'] != 'True' or low['success'] != 'True':
        excluded.append({'scene_id': scene, 'S15_success': s15['success'],
                         'L_success': low['success'], 'L_arrived': low['arrived']})
        continue
    delta = Decimal(s15['time_s']) - Decimal(low['time_s'])
    pairs.append({'scene_id': scene, 'S15_time_s': s15['time_s'],
                  'L_time_s': low['time_s'], 'delta_s': str(delta)})
deltas = [Decimal(p['delta_s']) for p in pairs]
counts = [sum(x < 0 for x in deltas), sum(x == 0 for x in deltas), sum(x > 0 for x in deltas)]
assert len(pairs) == 23 and counts == [5, 13, 5]
assert (min(deltas), max(deltas), sum(deltas)/len(deltas), statistics.median(deltas)) == (-136, 308, 7, 0)
result = {'csv_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'filter': 'stage == confirmation; paired by scene_id; BOTH success == True',
          'precision': 'Decimal from original time_s strings; exact equality; no tolerance',
          'confirmation_rows': len(rows), 'confirmation_scenes': len(scenes),
          'safe_completions': {v: sum(r['success']=='True' for r in rows if r['variant']==v)
                               for v in ('reactive','simple','sampled')},
          'common_safe_pairs': len(pairs), 'S15_faster': counts[0],
          'equal_time': counts[1], 'S15_slower': counts[2],
          'min_delta_s': str(min(deltas)), 'max_delta_s': str(max(deltas)),
          'mean_delta_s': str(sum(deltas)/len(deltas)), 'median_delta_s': str(statistics.median(deltas)),
          'interpretation': 'Equal travel time does not establish equal trajectories. Failed arrivals and early stops excluded.',
          'pairs': pairs, 'excluded': excluded, 'new_navigation_experiments': 0}
(P/'PAIRED_TIME_CHECK.json').write_text(json.dumps(result, indent=2), encoding='utf8')
print(json.dumps({k:v for k,v in result.items() if k not in ('pairs','excluded')},indent=2))
