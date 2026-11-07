import json
from pathlib import Path
root=Path(__file__).parent
jobs=[dict(id='cal'+str(i),method='heading',seed=1,desired=a,wind=90,heading=a,horizon=180,batch='calibration') for i,a in enumerate([0,40,140,-90])]
(root/'calibration.json').write_text(json.dumps(jobs))
