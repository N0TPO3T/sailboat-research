"""Extract existing frozen plotting inputs, without running a scientific model.
Usage: python extract_figure_data.py PATH_TO_EXISTING_RECOVERY_ZIP
Normal figure regeneration needs only plot_data.json, not this archive.
"""
from pathlib import Path
import csv,json,hashlib,zipfile,sys
P=Path(__file__).resolve().parent; E=P/'evidence'
sha=lambda b:hashlib.sha256(b).hexdigest()
rows=[r for r in csv.DictReader((E/'episodes.csv').open()) if r['stage']=='confirmation']
ids=list(dict.fromkeys(j['scene']['id'] for j in json.loads((E/'confirmation.json').read_text())['jobs']))
lookup={(r['scene_id'],r['variant']):r for r in rows}
data={'ids':ids,'confirmation':rows,'guard':json.loads((E/'analysis.json').read_text())['guard'],'prediction':json.loads((E/'matched_prediction_quality.json').read_text()),'cases':{}}
checks={'scope':'Frozen figure data only; no experiments or weights included','sources':{n:sha((E/n).read_bytes()) for n in ['episodes.csv','confirmation.json','analysis.json','matched_prediction_quality.json']},'trace_sources':{},'case_row_checks':[]}
with zipfile.ZipFile(sys.argv[1]) as z:
 for sid in ['r12new_mixed_pressure_1','r12new_endpoint_3']:
  data['cases'][sid]={}
  for v in ['reactive','simple','sampled']:
   n=f'runs/r12_revision_20261006/confirmation/{sid}__{v}/trace.json'; b=z.read(n); d=json.loads(b); r=lookup[sid,v]
   for key in ['time_s','min_dynamic_margin','path_length_m']:
    assert float(d['row'][key])==float(r[key]),(sid,v,key)
   assert d['row']['success']==(r['success']=='True')
   t=d['trajectory']; slim={'row':d['row'],'scene':d['scene'],'time':[p['time'] for p in t],'xy':[p['raw'][:2] for p in t],'target':[p['targets'][0]['position'] for p in t],'margin':[p['dynamic'][0]['margin'] for p in t[1:]]}
   assert len(slim['xy'])==len(t)==int(d['row']['time_s'])+1
   data['cases'][sid][v]=slim;checks['trace_sources'][n]={'sha256':sha(b),'samples_preserved':len(t)};checks['case_row_checks'].append({'scene':sid,'method':v,'matches_current_episodes':True})
checks['confirmation_rows']=len(rows);assert len(rows)==72
checks['safe_counts']={v:sum(r['success']=='True' for r in rows if r['variant']==v) for v in ['reactive','simple','sampled']}
checks['common_safe_vs_R']={v:sum(lookup[s,v]['success']=='True' and lookup[s,'reactive']['success']=='True' for s in ids) for v in ['simple','sampled']}
checks['prediction_intervals']=[x['common_steps'] for x in data['prediction']]
checks['max_detailed_error_m']=max(x['detailed_max_error'] for x in data['prediction'])
a=data['cases']['r12new_endpoint_3'];checks['adverse_penalty_s']=a['sampled']['row']['time_s']-a['simple']['row']['time_s'];checks['adverse_R_L_tracks_identical']=a['reactive']['xy']==a['simple']['xy']
(P/'plot_data.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
checks['plot_data_sha256']=sha((P/'plot_data.json').read_bytes())
(P/'FIGURE_DATA_CHECK.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in checks.items() if k not in ['sources','trace_sources']},indent=2))
