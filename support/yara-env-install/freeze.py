from pathlib import Path
from importlib import metadata
import torch,gymnasium,stable_baselines3,rospy
p=Path('/work')
(p/'docker/requirements-installed.txt').write_text('\n'.join(sorted(d.metadata['Name']+'=='+d.version for d in metadata.distributions(path=['/work/python'])))+'\n')
print('IMPORT_PASS',torch.__version__,gymnasium.__version__,stable_baselines3.__version__)
