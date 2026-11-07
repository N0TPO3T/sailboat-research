from pathlib import Path
import json,numpy as np
p=Path('runs/r12_revision_20261006/confirmation'); ds={v:json.loads((p/('r12new_mixed_pressure_1__'+v)/'trace.json').read_text()) for v in ['reactive','simple','sampled']}
a,b=ds['sampled'],ds['simple']; first=next(i for i,(x,y) in enumerate(zip(a['trajectory'],b['trajectory'])) if x['target']!=y['target']);print('first refdiff boundary',first,'raw equal',a['trajectory'][first]['raw']==b['trajectory'][first]['raw'])
for v,d in ds.items():
 print(v,'firstchanges',[x for x in d['changes'] if first-16<=x['selected_at']<=first+1])
 for x in d['predictions']:
  if first-16<=x['time']<=first+1:print(v,str({k:y for k,y in x.items() if k!='candidates'}),str([{k:y for k,y in c.items() if k not in ['path','margins']} for c in x['candidates']])[:5000])
print('qualitykeys',json.loads(Path('runs/r12_revision_20261006/matched_prediction_quality.json').read_text())[0].keys())
