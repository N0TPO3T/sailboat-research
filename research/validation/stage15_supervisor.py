import subprocess,json,time
from pathlib import Path
root=Path('/home/ot/Students/hs/sailboat-research')
start=time.time()
command=['.venv/bin/python','-B','research/chapter5_static.py','train','--config','configs/chapter5_static_aligned.json','--history-protocol','aligned','--through-stage','100000','--output','research/outputs/chapter5_static_aligned_seed101']
result=subprocess.run(command,cwd=root)
(root/'research/validation/stage15_exit.json').write_text(json.dumps(dict(returncode=result.returncode,wall_seconds=time.time()-start,started_unix=start,ended_unix=time.time())))
if result.returncode==0:
 subprocess.run(['.venv/bin/python','-B','research/static_training_report.py','research/outputs/chapter5_static_aligned_seed101'],cwd=root,check=True)
