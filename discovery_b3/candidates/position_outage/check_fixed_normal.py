import pathlib,numpy as np,csv,json,time,datetime,os
p=pathlib.Path(__file__).resolve().parent;o=p/'results';t=time.perf_counter();d=np.load(o/'traces.npz');rows=[]
for start in range(40,521,60):
 key=str(start)+'_';ts=d[key+'t'];truth=d[key+'truth'];cv=d[key+'CV']
 # CV displacement retains exact initial horizontal velocity direction.
 u=cv[-1]-cv[0];u=u/np.linalg.norm(u);n=np.array([-u[1],u[0]])
 for m in ['CV','CTR','gyro_raw','gyro_bias']:
  pred=d[key+m];err=np.abs((pred-truth)@n)
  # Also report absolute departure of actual/reference from initial straight line.
  actual_departure=np.abs((truth-truth[0])@n)
  row={'start_s':start,'method':m,'fixed_normal_x':float(n[0]),'fixed_normal_y':float(n[1]),'fixed_normal_prediction_error_max_m':float(err.max()),'actual_initial_line_departure_max_m':float(actual_departure.max())}
  for budget in [2,5]:
   hit=np.flatnonzero(err>budget);row[f'crossed_{budget}m']=bool(len(hit));row[f'first_{budget}m_s']=float(ts[hit[0]]) if len(hit) else 60.
  rows.append(row)
with (o/'fixed_normal_scores.csv').open('w',newline='') as f:
 wr=csv.DictWriter(f,fieldnames=list(rows[0]));wr.writeheader();wr.writerows(rows)
summary={m:{f'crossed_{b}m':sum(x[f'crossed_{b}m'] for x in rows if x['method']==m) for b in [2,5]} for m in ['CV','CTR','gyro_raw','gyro_bias']}
summary['definition']='prediction-minus-reference position projected on initial ground-velocity normal; not absolute initial-line departure'
summary['windows']=9;summary['worker']=1;summary['gpu']=0;summary['wall_seconds']=time.perf_counter()-t;summary['utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();summary['pid']=os.getpid()
(o/'fixed_normal_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2));print([x for x in rows if x['method']=='CV' and x['crossed_2m']])
