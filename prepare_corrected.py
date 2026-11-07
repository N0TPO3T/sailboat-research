import json
from pathlib import Path
r=Path('/home/ot/Students/hs/sailboat-track-b')
jobs=json.loads((r/'runs/pilot_scale.json').read_text())
for j in jobs:j['batch']='pilot_corrected'
(r/'runs/pilot_corrected.json').write_text(json.dumps(jobs))
