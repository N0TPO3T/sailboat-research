"""Read-only reaggregation from stored trajectories. No simulator execution."""
from pathlib import Path
import sys,json,math,csv,hashlib,statistics
R=Path(sys.argv[1]).resolve();F=R/'frozen'
sys.dont_write_bytecode=True
sys.path.insert(0,str(F/'src'))
from sailboat_routing.runtime import configure_cpu
configure_cpu()
import numpy as np
from sailboat_routing.r7_dynamic import relative_minimum,target_truth
from sailboat_routing.metrics import segment_circle_clearance
from sailboat_routing.planner import CircleObstacle

def load(p):return json.loads(Path(p).read_text())
def close(a,b):return a==b or math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-8)
for stage in ['truth_branches','grid_train','old_Lstar','new_paired']:
    assert load(R/(stage+'_complete.json'))['complete']
checks=[];rows=[]
for stage,expected in [('old_Lstar',24),('new_paired',48)]:
    paths=sorted((R/stage).glob('*/trace.json'));assert len(paths)==expected,(stage,len(paths))
    for path in paths:
        d=load(path);tr=d['trajectory'];s=d['scene'];row=d['row'];assert row['complete']
        static=tuple(CircleObstacle(tuple(o['center_xy']),o['entity_radius'],60.) for o in s.get('static',[]))
        if row['min_static_margin'] is None:
            assert not static,'Null static margin with actual static obstacles'
            row['min_static_margin']=math.inf
        initial=np.array(tr[0]['raw'][:2],dtype=np.float32)
        sm=segment_circle_clearance(initial,initial,static)['safety_m'];dm=math.inf;em=math.inf;length=0.
        for k,(a,b) in enumerate(zip(tr[:-1],tr[1:])):
            assert a['time']==k and b['time']==k+1
            p,q=np.array(a['raw'][:2],dtype=np.float32),np.array(b['raw'][:2],dtype=np.float32);length+=float(np.linalg.norm(q-p))
            c=segment_circle_clearance(p,q,static);sm=min(sm,c['safety_m']);em=min(em,c['entity_m'])
            for target in s['vessels']:
                distance,_=relative_minimum(p,q,target_truth(target,k)[0],target_truth(target,k+1)[0]);dm=min(dm,distance-85);em=min(em,distance-25)
        reached=float(np.linalg.norm(np.array(tr[-1]['raw'][:2])-s['goal']))<=10
        success=row['arrived'] and sm>0 and dm>0
        assert not row['arrived'] or reached
        assert len(tr)-1==row['time_s']
        for a,b in [(length,row['path_length_m']),(sm,row['min_static_margin']),(dm,row['min_dynamic_margin']),(em,row['min_entity_margin'])]:assert close(a,b),(path,a,b)
        assert success==row['success']
        checks.append({'stage':stage,'scene_id':s['id'],'variant':row['variant'],'steps':len(tr)-1,'trajectory_hash':hashlib.sha256(path.read_bytes()).hexdigest(),'metrics_match':True})
        rows.append(dict(stage=stage,geometry_id=s.get('geometry_id',s['id']),wind_repeat=s.get('wind_repeat',''),**row))
new={}
for p in (R/'new_paired').glob('*/trace.json'):
    d=load(p);sid=d['scene']['id'];new.setdefault(sid,[]).append(d)
for sid,ds in new.items():
    assert len(ds)==3
    assert all(d['scene']==ds[0]['scene'] for d in ds)
    assert all(d['trajectory'][0]['raw']==ds[0]['trajectory'][0]['raw'] for d in ds),'Initial state mismatch'
for geom in {d[0]['scene']['geometry_id'] for d in new.values()}:
    ds=[d[0]['scene'] for d in new.values() if d[0]['scene']['geometry_id']==geom];assert len(ds)==2
    stripped=[{k:v for k,v in d.items() if k not in ['id','seed','wind_repeat']} for d in ds];assert stripped[0]==stripped[1]
    assert ds[0]['seed']!=ds[1]['seed']
cal=load(R/'calibration.json');grid=cal['all_training_grid'];assert len(grid)==48
best=min(grid,key=lambda x:(x['score_m'],x['id']));assert best['params']==cal['selected_params']
branches=list((R/'branches').glob('*.json'));assert len(branches)==72
assert all(load(p)['prefix_state_max_error']==0 for p in branches)
assert all(load(p)['selected15s_position_parity'] in [None,0] for p in branches)
with (R/'episodes.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
receipt={'pass':True,'episodes_recomputed':len(checks),'new_scene_matching':True,'geometry_wind_pairing':True,'train_grid_selection_exact':True,'real_prefixes_exact':72,'selected15s_prefixes_exact':sum(load(p)['selected15s_position_parity']==0 for p in branches),'episode_checks':checks,'no_new_simulations':True}
(R/'AUDIT.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in receipt.items() if k!='episode_checks'},indent=2))
