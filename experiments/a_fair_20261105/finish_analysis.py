"""Reporting-only recovery of legacy null-as-unbounded static clearance.

Preserves the original frozen driver and failure receipt. Never runs a worker.
"""
from pathlib import Path
import sys,json,math,time,subprocess
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R))
import a_fair as experiment
experiment.integrity()
rawload=experiment.load
scene_map={j['scene']['id']:j['scene'] for j in rawload(R/'original_confirmation.json')['jobs']}
scene_map.update({s['id']:s for s in rawload(R/'new_scenes.json')['scenes']})
converted=[]
def normalize(obj,path):
    if isinstance(obj,dict):
        if obj.get('scene_id') in scene_map and 'min_static_margin' in obj and obj['min_static_margin'] is None:
            assert not scene_map[obj['scene_id']]['static'],('Null margin despite static obstacles',path)
            obj['min_static_margin']=math.inf;converted.append(str(path))
        return {k:normalize(v,path) for k,v in obj.items()}
    if isinstance(obj,list):return [normalize(v,path) for v in obj]
    return obj
def safe_load(path):return normalize(rawload(path),path)
experiment.load=safe_load
for stage,n in [('truth_branches',72),('grid_train',48),('old_Lstar',24),('new_paired',48)]:
    rec=rawload(R/(stage+'_complete.json'));assert rec['complete'] and rec['jobs']==n
experiment.summary()
subprocess.run([sys.executable,str(R/'audit_results.py'),str(R)],check=True)
assert rawload(R/'AUDIT.json')['pass']
recovery={'reporting_fix_only':True,'original_driver_preserved':True,'original_error_receipt':'failure.json','cause':'Legacy JSON maps unbounded static clearance to null. Interpret as +infinity only after checking the frozen scene has no static obstacles.','normalized_reads':converted,'scientific_sources_or_parameters_changed':False,'navigation_reruns':0,'finished':time.time()}
experiment.write(R/'ANALYSIS_RECOVERY.json',recovery)
beg=rawload(R/'execution.json')['started'];end=rawload(R/'new_paired_complete.json')['finished']
experiment.write(R/'completion.json',{'complete':True,'navigation_batches_complete':True,'navigation_finished':end,'navigation_wall_seconds':end-beg,'analysis_finished':time.time(),'branches':72,'grid':48,'old_episodes':24,'new_episodes':48,'original_driver_exit_code':1 if (R/'failure.json').exists() else 0,'analysis_recovery_exit_code':0,'analysis_recovery':'ANALYSIS_RECOVERY.json','audit_pass':True})
print('ANALYSIS RECOVERY COMPLETE; NO NAVIGATION RERUN')
