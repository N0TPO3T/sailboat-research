import csv,json,math,hashlib
from pathlib import Path
import numpy as np
import sys
p=Path(__file__).parent/(sys.argv[1] if len(sys.argv)>1 else 'results')
read=lambda name:list(csv.DictReader((p/name).open()))
scores=read('scores.csv'); groups=read('groups.csv');pred=read('predictions.csv');split=read('splits.csv')
keys={(r['year'],r['budget'],r['seed'],r['gid']):r for r in split}
assert len(keys)==len(split)
assert all(not(int(r['visible']) and int(r['test'])) for r in split)
assert all(float(r['nearest_visible_km'])>=2-1e-9 for r in split if int(r['test']))
assert all(math.isfinite(float(r['prediction'])) and float(r['prediction'])>=0 for r in pred)
errs=[]
for s in scores:
 rr=[r for r in pred if all(r[k]==s[k] for k in ['year','budget','seed','method']) and int(r['test'])]
 y=np.array([float(r['truth']) for r in rr]);v=np.array([float(r['prediction']) for r in rr]);calc=np.mean(abs(y-v))/y.mean()
 errs.append(abs(calc-float(s['nmae'])))
assert max(errs)<1e-12
summary={}
for year in ['2020','2021','2022','2023']:
 ss=read('development_scores.csv') if year=='2020' else scores
 summary[year]={m:float(np.mean([float(r['nmae']) for r in ss if r['year']==year and r['method']==m])) for m in sorted(set(r['method'] for r in ss))}
feature_ranges={}
features=['X','Y','Depth','Month','Mean_thetao_SST','Chl_surf','Mean_NS_vo_Wclm','Mean_EW_uo_Wclm','SO_surf','Mean_current_speed','hour_sin','hour_cos']
for year in [2021,2022,2023]:
 h=[r for r in groups if int(r['year'])<year];t=[r for r in groups if int(r['year'])==year]
 feature_ranges[year]={}
 for f in features:
  lo=min(float(r[f]) for r in h);hi=max(float(r[f]) for r in h);v=[float(r[f]) for r in t]
  feature_ranges[year][f]={'history_min':lo,'history_max':hi,'target_min':min(v),'target_max':max(v),'out_of_history_range':sum(x<lo or x>hi for x in v)/len(v)}
 predh=[float(r['prediction']) for r in pred if r['year']==str(year) and r['method']=='history' and r['seed']=='3101' and r['budget']=='0.15']
 feature_ranges[year]['history_prediction_quantiles']=np.quantile(predh,[0,.5,.9,1]).tolist()
 feature_ranges[year]['truth_quantiles']=np.quantile([float(r['y']) for r in t],[0,.5,.9,1]).tolist()
report={'checks':'PASS','max_score_recompute_delta':max(errs),'groups':len(groups),'splits':len(split),'predictions':len(pred),'group_counts':{y:sum(r['year']==y for r in groups) for y in ['2019','2020','2021','2022','2023']},'method_nmae_diagnostic_only':summary,'feature_ranges':feature_ranges}
(p/'verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='feature_ranges'},indent=2))
