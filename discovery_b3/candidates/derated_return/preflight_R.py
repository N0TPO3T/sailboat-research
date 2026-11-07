import json,hashlib
from pathlib import Path
import numpy as np
from pilot import allocation,otter,force_bounds,shaft_to_force,forces_to_wrench
p=Path(__file__).resolve().parent;v=otter();lo,hi=force_bounds(v);n=0;err=0.
for rho in [.25,.5,1.]:
 for side in [0,1]:
  factor=np.ones(2);factor[side]=rho;lows=lo*factor;highs=hi*factor
  for X in [-500,-80,0,80,500]:
   for N in [-500,-80,0,80,500]:
    cmd,ach,upper=allocation(v,X,N,lows,highs);f=shaft_to_force(v,cmd)
    assert np.all(f>=lows-1e-8) and np.all(f<=highs+1e-8)
    err=max(err,float(np.max(abs(ach-forces_to_wrench(v,f)))))
    assert np.all(cmd>=v.n_min*np.sqrt(factor)-1e-8) and np.all(cmd<=v.n_max*np.sqrt(factor)+1e-8)
    n+=1
r=dict(status='pass',allocation_checks=n,max_wrench_roundtrip_error=err,force_limits_original=[lo,hi],Dsurge=float(v.D[0,0]),fixed_speed_caps={str(rho):.9*2*hi*rho/float(v.D[0,0]) for rho in [.25,.5]},config_sha256=hashlib.sha256((p/'FROZEN_CONFIG.json').read_bytes()).hexdigest())
(p/'preflight.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
