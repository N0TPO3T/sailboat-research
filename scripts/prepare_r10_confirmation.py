"""One fixed new R10 dynamic confirmation, generated only after provisional selection."""
import json,copy,time,random,hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];run=Path(sys.argv[1]).resolve();assert not (run/'confirmation.json').exists()
assert (run/'dynamic_development/completion.json').exists()
old=json.loads((ROOT/'runs/r8_closedloop_20261005T062543Z/confirmation.json').read_text())
methods={v:copy.deepcopy(next(j['config'] for j in old['jobs'] if j['variant']==v)) for v in ['reactive','sampled','hold60']};methods['nominal_hold']=dict(methods['sampled'],r10_nominal_hold=True)
files=[ROOT/'scripts/run_r10.py',ROOT/'scripts/run_r6.py',ROOT/'scripts/run_r8.py']+list((ROOT/'src/sailboat_routing').glob('*.py'))
freeze={'epoch':time.time(),'provisional_main':'sampled','method_family':'GVO-style candidate-conditioned position-reference closed-loop prediction; ideal-compute simulation only','methods':methods,'sources':{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},'generation_seed':202610507,'physical_seeds':'2026105070+i','n_scenes':12,'selection_rule':'4pressure+2crossing+2overtaking+2endpoint+2nonconflict; all kept irrespective of outcome','no_further_tuning':True}
(run/'freeze.json').write_text(json.dumps(freeze,indent=2));rng=random.Random(202610507);scenes=[]
for family,n in [('mixed_pressure',4),('underway_crossing',2),('underway_overtaking',2),('endpoint',2),('nonconflict',2)]:
 for k in range(n):
  i=len(scenes);s={'id':f'r10new_{family}_{k}','family':family,'distance_m':1000,'goal':[1000,0],'seed':2026105070+i,'profile':['stable','fast'][k%2],'base_direction_degrees':rng.uniform(45,80),'static':[]}
  speed=rng.uniform(.65,.95)
  if family=='mixed_pressure':
   crossing=rng.uniform(185,230);q=[rng.uniform(620,710),speed*crossing];v=[0,-speed];s.update(base_direction_degrees=rng.uniform(115,135),nominal_crossing_time=crossing,static=[{'center_xy':[850,300],'entity_radius':45}])
  elif family=='underway_crossing':q=[rng.uniform(420,540),-speed*rng.uniform(140,220)];v=[0,speed]
  elif family=='underway_overtaking':q=[rng.uniform(230,300),rng.uniform(-15,15)];v=[speed,0]
  elif family=='endpoint':q=[rng.uniform(610,650),rng.uniform(-15,15)];v=[rng.uniform(.8,1.),0]
  else:q=[rng.uniform(500,600),(-1 if k==0 else 1)*rng.uniform(340,390)];v=[speed,0]
  s['vessels']=[{'id':'ship0','position':q,'velocity':v}];scenes.append(s)
jobs=[{'domain':'dynamic','scene':s,'variant':v,'config':cfg} for s in scenes for v,cfg in methods.items()]
manifest={'run':str(run),'stage':'single_frozen_new_confirmation','generated_epoch':time.time(),'freeze_sha256':hashlib.sha256((run/'freeze.json').read_bytes()).hexdigest(),'jobs':jobs};(run/'confirmation.json').write_text(json.dumps(manifest,indent=2));print('frozen before generation;12instances48episodes; no outcome filtering')