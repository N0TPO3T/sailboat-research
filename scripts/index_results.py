import json,hashlib,datetime,sys,platform,importlib.metadata
from pathlib import Path
R=Path(__file__).resolve().parents[1]
status={'calibration':'obsolete rudder sign; admission only','calibration_signfix':'valid steady-heading admission, not stationkeeping','pilot_station':'prototype: phase reverse sail incomplete; all shuttle invalid shared leg/q; no final claims','pilot_scale':'prototype: phase reverse sail incomplete; all shuttle invalid shared leg/q; no final claims','pilot_corrected':'prototype: all shuttle invalid shared leg/q; phase small circle not full literature assumptions','turn_admission':'valid response admission; not a task benchmark','fair_development':'center and phase development valid; ALL shuttle results invalid shared leg/q','fair_adaptation':'development after independent leg/q fix; before explicit final-step failure flag, not formal confirmation','phase_footprint':'valid development, larger internal circles, common low-level adaptation','ablation_development':'valid development ablation','accounting_fault_check':'artificial fault injection only; NEVER navigation performance','confirmation':'frozen new-instance confirmation','scale_check':'v1 frozen scale check; later development context, never pool with v2 as unseen','recovery_diagnosis':'same-history causal branches at one old task state; not independent tasks','recovery_sail_check':'additional same-history sail branches at the same state; not independent tasks','recovery_development':'8 old tasks, method development','recovery_simplification':'same8old tasks, mechanism alternatives; do not pool as new','recovery_minimal':'same8old tasks, deletion of speed-build stage','recovery_confirmation':'v2 frozen24new physical instances,5original variants','recovery_scale':'v2 frozen8new scale instances,3original variants','recovery_luff_control':'same24v2instances, preregistered structural matched comparator; not24additionaltasks','recovery_luff_scale':'same8v2scaleinstances, matched comparator; not8additionaltasks'}
items=[];cpu=0;wall=0;episodes=0
for d in sorted((R/'runs').iterdir()):
 if not d.is_dir():continue
 entries=[]
 for f in sorted(d.glob('*.json')):
  z=json.loads(f.read_text());x=z['result'];entries.append(dict(path=str(f.relative_to(R)),sha256=hashlib.sha256(f.read_bytes()).hexdigest(),method=x['method'],completed=x.get('completed'),integration_failed=x.get('integration_failed','not recorded in prototype'),cpu_s=x['cpu_s'],wall_s=x['wall_s']))
  cpu+=x['cpu_s'];wall+=x['wall_s'];episodes+=1
 runner=d/'runner_source.py';items.append(dict(batch=d.name,interpretation=status.get(d.name,'unknown'),n=len(entries),runner_sha256=hashlib.sha256(runner.read_bytes()).hexdigest() if runner.exists() else 'not captured for early prototype',files=entries))
(R/'RESULTS_INDEX.json').write_text(json.dumps(items,indent=2))
ledger=dict(start_utc='2026-10-07T15:13:40Z',deadline_utc='2026-10-08T15:13:40Z',indexed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),episodes_including_fault_and_obsolete=episodes,sum_worker_process_cpu_seconds=cpu,sum_episode_wall_seconds_not_elapsed=wall,max_workers=4,numerical_threads_per_worker=1,gpu_hours=0,training='none; mature conventional controller route',note='CPU totals from worker process_time; exclude startup imports and report tooling; accumulated episode wall is NOT elapsed wall.')
(R/'RESOURCE_LEDGER.json').write_text(json.dumps(ledger,indent=2))
versions={}
for p in ['numpy','scipy','torch','gymnasium','matplotlib']:
 try:versions[p]=importlib.metadata.version(p)
 except importlib.metadata.PackageNotFoundError:versions[p]='missing'
(R/'docs/ENVIRONMENT.json').write_text(json.dumps(dict(python=sys.version,platform=platform.platform(),packages=versions),indent=2))
source=[]
for sub in ['src','third_party','scripts','configs']:
 for p in sorted((R/sub).rglob('*')):
  if p.is_file() and '__pycache__' not in str(p):source.append(dict(path=str(p.relative_to(R)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
(R/'docs/FINAL_SOURCE_MANIFEST.json').write_text(json.dumps(source,indent=2))
print(json.dumps(ledger,indent=2))
