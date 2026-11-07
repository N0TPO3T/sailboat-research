import os
os.environ['OPENBLAS_NUM_THREADS']='1'
from pathlib import Path
import numpy as np
import pilot
p=Path(__file__).parent;g=pilot.groups(p/'input/xdat.Full.csv');out={}
for y in [2020,2021,2022,2023]:
 tr=[r for r in g if r['year']<y];te=[r for r in g if r['year']==y];m=pilot.History(tr,1);x=pilot.arrays(te);a=m.design(x);ly=a@m.beta;z=(x-m.mu)/m.sd
 contrib=a[:,1:]*m.beta[1:];fmax=np.max(abs(contrib),axis=0);idx=np.argsort(fmax)[-5:][::-1]
 names=[]
 for typ in ['linear','square','cube','hinge_q10','hinge_q50','hinge_q90']:
  names.extend([typ+':'+f for f in pilot.RAW+['hour_sin','hour_cos']])
 names.extend(['spatial_rbf_'+str(i) for i in range(16)])
 out[y]={'raw_log_prediction_quantiles':np.quantile(ly,[0,.5,.9,1]).tolist(),'training_log_bounds':m.bounds,'clipping_fraction':float(np.mean((ly<m.bounds[0])|(ly>m.bounds[1]))),'smear':m.smear,'top_terms':[{ 'term':names[i], 'max_absolute_log_contribution':float(fmax[i])} for i in idx],'max_abs_z':{f:float(v) for f,v in zip(pilot.RAW+['hour_sin','hour_cos'],abs(z).max(0))}}
pilot.dump(p/'results/trend_diagnosis.json',out);print(__import__('json').dumps(out,indent=2))
