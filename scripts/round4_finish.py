import sys,time,json,subprocess,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];run=ROOT/'runs/round4_20261025';env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
while not (run/'training_v2_done.json').exists():
 log=run/'training_v2_launcher.log'
 if log.exists() and 'Traceback' in log.read_text():raise RuntimeError('Training failed; do not proceed')
 time.sleep(10)
for script in ('round4_status.py','round4_select.py','round4_confirm.py','round4_verify.py','round4_report.py'):
 with (run/f'{script}.log').open('x') as log:subprocess.run([sys.executable,'-u',str(ROOT/'scripts'/script)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 print(script,'done',flush=True)
(run/'evaluation_done.json').write_text(json.dumps(dict(completed=True)))
