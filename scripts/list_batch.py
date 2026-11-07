import json,sys
from pathlib import Path
r=Path('/home/ot/Students/hs/sailboat-track-b')
for p in sorted((r/'runs'/sys.argv[1]).glob('*.json')):
 x=json.loads(p.read_text())['result'];print(p.name,round(x['inside_fraction'],4),x['max_outside_s'],round(x['actuator_variation_rad'],1))
