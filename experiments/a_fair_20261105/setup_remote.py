from pathlib import Path
import json,hashlib,shutil,random,time,subprocess

ORIGIN=Path('/home/ot/Students/hs/sailboat-routing-v0').resolve(strict=True)
assert ORIGIN.is_relative_to(Path('/home/ot/Students/hs').resolve(strict=True))
RUN=ORIGIN/'runs/a_fair_20261105'
RUN.mkdir(exist_ok=False)
F=RUN/'frozen';F.mkdir()
for name in ['src','scripts','third_party','checkpoints']:
    assert (ORIGIN/name).resolve(strict=True).is_relative_to(Path('/home/ot/Students/hs'))
    shutil.copytree(ORIGIN/name,F/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for name in ['.tmp','.cache']: (F/name).mkdir()
shutil.copy2(ORIGIN/'requirements.lock',F/'requirements.lock')
for name in ['EXPERIMENT_PLAN.md','a_fair.py']:
    shutil.copy2(Path(__file__).parent/name,RUN/name)
cal=json.loads((ORIGIN/'runs/r12_revision_20261006/calibration.json').read_text())
oldfreeze=json.loads((ORIGIN/'runs/r12_revision_20261006/freeze.json').read_text())
hashes={str(p.relative_to(F)):hashlib.sha256(p.read_bytes()).hexdigest() for p in F.rglob('*') if p.is_file()}
for path in ['src/sailboat_routing/r12_model.py','src/sailboat_routing/r8_model.py','src/sailboat_routing/r8_planner.py','scripts/run_r8.py']:
    assert hashes[path]==oldfreeze['sources'][path],('Frozen science mismatch',path)
def write(name,data): (RUN/name).write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
write('SOURCE_HASHES.json',hashes)
write('original_calibration.json',cal)
shutil.copy2(ORIGIN/'runs/r12_revision_20261006/confirmation.json',RUN/'original_confirmation.json')
rng=random.Random(2026110501);scenes=[];geoms=[]
for family,n in [('mixed_pressure',4),('underway_crossing',1),('underway_overtaking',1),('endpoint',1),('nonconflict',1)]:
    for k in range(n):
        g=len(geoms);s={'id':f'a26_{family}_{k}','geometry_id':f'g{g:02d}','family':family,'distance_m':1000,'goal':[1000,0],'profile':['stable','fast'][g%2],'base_direction_degrees':rng.uniform(45,80),'static':[]}
        speed=rng.uniform(.65,.95)
        if family=='mixed_pressure':
            cross=rng.uniform(185,230);q=[rng.uniform(620,710),speed*cross];v=[0,-speed]
            s.update(base_direction_degrees=rng.uniform(115,135),nominal_crossing_time=cross,static=[{'center_xy':[850,300],'entity_radius':45}])
        elif family=='underway_crossing':q=[rng.uniform(420,540),-speed*rng.uniform(140,220)];v=[0,speed]
        elif family=='underway_overtaking':q=[rng.uniform(230,300),rng.uniform(-15,15)];v=[speed,0]
        elif family=='endpoint':q=[rng.uniform(610,650),rng.uniform(-15,15)];v=[rng.uniform(.8,1.),0]
        else:q=[rng.uniform(500,600),(-1 if k%2==0 else 1)*rng.uniform(340,390)];v=[speed,0]
        s['vessels']=[{'id':'ship0','position':q,'velocity':v}];geoms.append(s)
        for r in range(2):scenes.append(dict(s,id=s['id']+f'_wind{r}',wind_repeat=r,seed=2026110500+2*g+r))
write('new_scenes.json',{'generation_seed':2026110501,'geometries':geoms,'scenes':scenes,'created_before_calibration':True})
write('environment.json',{'interpreter':str(ORIGIN/'.venv/bin/python'),'reuse_existing_environment':True,'workers':4,'threads_per_worker':1,'gpu':0,'origin':str(ORIGIN),'source_root':str(F),'run_root':str(RUN),'required_versions':{'python':'3.13.11','torch':'2.13.0+cpu','numpy':'2.4.6','scipy':'1.18.1'},'smoke_command':f'PYTHONDONTWRITEBYTECODE=1 {ORIGIN}/.venv/bin/python {RUN}/a_fair.py smoke'})
write('FREEZE.json',{'epoch':time.time(),'origin':str(ORIGIN),'server_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ORIGIN,text=True).strip(),'max_wall_seconds':21600,'sources_sha256':hashlib.sha256((RUN/'SOURCE_HASHES.json').read_bytes()).hexdigest(),'protocol_sha256':hashlib.sha256((RUN/'EXPERIMENT_PLAN.md').read_bytes()).hexdigest(),'new_scenes_sha256':hashlib.sha256((RUN/'new_scenes.json').read_bytes()).hexdigest(),'driver_sha256':hashlib.sha256((RUN/'a_fair.py').read_bytes()).hexdigest(),'training_ids':cal['train_scene_ids'],'validation_ids':cal['validation_scene_ids'],'no_post_test_tuning':True})
print('FROZEN',RUN,flush=True)
