"""One prespecified post-calibration confirmation; every generated task is retained."""
import json,random,hashlib,time,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'runs/r12_revision_20261006'
assert not (R/'confirmation.json').exists()
cal=json.loads((R/'calibration.json').read_text());params=cal['parameters_tau_gain_ratecap'];cfg={'sampled':True,'period':15,'horizon':60,'guard':30}
methods={'reactive':{'availability':True},'sampled':cfg,'simple':dict(cfg,low_order_params=params)}
files=[ROOT/'scripts/run_r12.py',ROOT/'src/sailboat_routing/r12_model.py',ROOT/'src/sailboat_routing/r8_model.py',ROOT/'src/sailboat_routing/r8_planner.py',ROOT/'scripts/run_r8.py']
freeze={'epoch':time.time(),'generation_seed':202610612,'count':24,'families':{'mixed_pressure':8,'underway_crossing':4,'underway_overtaking':4,'endpoint':4,'nonconflict':4},'methods':methods,'sources':{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},'no_outcome_filtering':True,'no_post_confirmation_tuning':True,'cost_basis':'12 low-order development tasks completed within minutes; original parity benchmark under same single-thread runtime;24 tasks fixed within12h budget'}
(R/'freeze.json').write_text(json.dumps(freeze,indent=2));rng=random.Random(202610612);scenes=[]
for family,n in freeze['families'].items():
 for k in range(n):
  i=len(scenes);s={'id':f'r12new_{family}_{k}','family':family,'distance_m':1000,'goal':[1000,0],'seed':2026106120+i,'profile':['stable','fast'][k%2],'base_direction_degrees':rng.uniform(45,80),'static':[]};speed=rng.uniform(.65,.95)
  if family=='mixed_pressure':
   crossing=rng.uniform(185,230);q=[rng.uniform(620,710),speed*crossing];v=[0,-speed];s.update(base_direction_degrees=rng.uniform(115,135),nominal_crossing_time=crossing,static=[{'center_xy':[850,300],'entity_radius':45}])
  elif family=='underway_crossing':q=[rng.uniform(420,540),-speed*rng.uniform(140,220)];v=[0,speed]
  elif family=='underway_overtaking':q=[rng.uniform(230,300),rng.uniform(-15,15)];v=[speed,0]
  elif family=='endpoint':q=[rng.uniform(610,650),rng.uniform(-15,15)];v=[rng.uniform(.8,1.),0]
  else:q=[rng.uniform(500,600),(-1 if k%2==0 else 1)*rng.uniform(340,390)];v=[speed,0]
  s['vessels']=[{'id':'ship0','position':q,'velocity':v}];scenes.append(s)
(R/'confirmation.json').write_text(json.dumps({'run':str(R),'workers':4,'jobs':[{'scene':s,'variant':v,'config':cfg} for s in scenes for v,cfg in methods.items()]},indent=2));print('Frozen24tasks72episodes; no outcome filtering')
