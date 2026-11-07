import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];run=ROOT/'runs/round4_20261025';conf=run/'confirmation50'
if conf.exists():
 rows=[]
 for part in sorted((conf/'parts').glob('*')):
  p=part/'episodes.jsonl';n=len(p.read_text().splitlines()) if p.exists() else 0;rows.append(dict(part=part.name,completed=n))
 print(json.dumps(dict(parts=rows,unique_completed=sum(r['completed'] for r in rows),evaluation_done=(run/'evaluation_done.json').exists())))
for name in ['finish.log','round4_confirm.py.log','round4_verify.py.log','round4_report.py.log']:
 p=run/name
 if p.exists() and 'Traceback' in p.read_text():print(name,p.read_text()[-1500:])
