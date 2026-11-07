from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from sailboat_routing.runtime import SeniorModules, OriginalSegment
from sailboat_routing.obstacle_candidate import ObstacleController
import numpy as np
root = Path(__file__).resolve().parents[1]
env = OriginalSegment(SeniorModules(), noise_enabled=False)
policy = ObstacleController(mode='eval')
obs = env.reset(100, 90)
policy.reset(np.r_[obs, np.zeros(4)].astype(np.float32))
rows = [obs.copy()]
for _ in range(50):
    act = policy.act(np.r_[obs, np.zeros(4)].astype(np.float32)).action
    obs, _, done, trunc, _ = env.step(act)
    rows.append(obs.copy())
    if done or trunc:
        break
assert np.isfinite(rows).all() and np.linalg.norm(rows[-1][:2]-rows[0][:2]) > 0
np.savez(root/'runs/f0_smoke.npz', states=np.array(rows))
print({'steps':len(rows)-1, 'position':obs[:2].tolist(), 'artifact':'runs/f0_smoke.npz'})
