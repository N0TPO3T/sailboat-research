"""R13 targeted numeric sign check; imports existing observation-only R12 replay."""
from pathlib import Path
import sys,json,time
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'scripts'))
from check_r12_branches import physics_prefix
O=ROOT/'paper/ccdc/r13_revision/evidence';out=[];start=time.time()
for v in ['reactive','simple','sampled']:
 d=json.loads((ROOT/'runs/r12_revision_20261006/confirmation'/('r12new_mixed_pressure_1__'+v)/'trace.json').read_text())
 p,e,sub=physics_prefix(d,len(d['trajectory'])-1,True);p.close();x=dict(scene=d['scene']['id'],variant=v,endpoint_max_error=e,original_margin=d['row']['min_dynamic_margin'],substep_min=min(sub,key=lambda x:x['margin']),segments=len(sub),max_step=max(x['end_time']-x['time'] for x in sub));out.append(x);print(x,flush=True)
 (O/'new_case_substeps.json').write_text(json.dumps(dict(results=out,wall_s=time.time()-start,kind='same-command observation-only numerical replay; not new independent tasks'),indent=2))
