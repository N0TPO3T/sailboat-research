from pathlib import Path
import json,hashlib,datetime
p=Path('/home/ot/Students/hs/sailboat-track-b')
f=p/'RESOURCE_LEDGER.json';d=json.loads(f.read_text());d.pop('max_workers',None);d.update(configured_workers_per_batch=4,global_process_peak='not verified; startup/cleanup overlap cannot be excluded',estimated_episode_compute_peak=4,estimated_new_start_after_old_last_write_seconds=1.8523,incident='docs/RESOURCE_SCHEDULING_INCIDENT.json',all_batches_exit_code=0);f.write_text(json.dumps(d,indent=2)+'\n')
files=['docs/B_METHOD_NOTE.md','docs/B_RESEARCH_REPORT.md','analysis_v2/all_results.csv','analysis_v2/group_summary.json','analysis_v2/paired_summary.json','scripts/station_recovery.py','scripts/station_luff_control.py','docs/FREEZE_V2.json','docs/CONFIRMATION_INTEGRITY_V2.json','RESOURCE_LEDGER.json']+[str(x.relative_to(p)) for x in sorted((p/'figures').glob('0[6-9]*.png'))]+['figures/10_recovery_scale.png']
m={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'same input for independent reviewers; no review outcome presumed','files':{s:hashlib.sha256((p/s).read_bytes()).hexdigest() for s in files}}
(p/'docs/REVIEW_INPUT_MANIFEST.json').write_text(json.dumps(m,indent=2)+'\n')
print(json.dumps(m,indent=2))
