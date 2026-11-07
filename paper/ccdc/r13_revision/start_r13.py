from pathlib import Path
import datetime,json
p=Path.cwd();assert str(p.resolve()).startswith('/home/ot/Students/hs/')
(p/'CURRENT_PLAN.md').write_text('# Current Plan\n\nR13 full manuscript revision followed by three independent persistent A/B/C reviewers and evidence-based revision. Shared budget: 24h wall, four one-thread CPU workers, no GPU. Preserve R12 and old results. No push or submission.\n\nFirst readable manuscript and rendered PDF, then independent review; current entry docs/prompt/SailBoatRL_R13_ARIS_Three_Reviewer_Revision_Loop.md.\n')
(p/'paper/ccdc/r13_revision/budget.json').write_text(json.dumps(dict(start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),wall_hours=24,max_cpu_workers=4,gpu_authorized=False),indent=2))
r=p/'runs/r12_revision_20261006/confirmation'
for v in ['reactive','simple','sampled']:
 d=json.loads((r/('r12new_mixed_pressure_1__'+v)/'trace.json').read_text());print(v,list(d));print('decision sample',str(d.get('decisions',[])[:1])[:2500])
 for name in d:
  if name not in ['trajectory','scene','config','row']:print(name,str(d[name])[:150])
 t=min(d['trajectory'][1:],key=lambda x:x['dynamic'][0]['margin']);print('minimum',t['time'],t['dynamic'])
