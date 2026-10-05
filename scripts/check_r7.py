"""Small dynamic contracts; no physics rollout or new dependency."""
from pathlib import Path
import sys,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from sailboat_routing.r7_dynamic import *
from sailboat_routing.metrics import segment_circle_clearance
assert cpa(np.zeros(2),np.array([1,0]),np.array([100,0]),np.zeros(2))==(100.,0.)
assert cpa(np.zeros(2),np.array([-1,0]),np.array([100,0]),np.zeros(2))[0]<0
assert relative_minimum([0,0],[10,0],[5,-5],[5,5])[0]==0
assert relative_minimum([0,0],[10,0],[5,-15],[5,-5])[0]>0
stat=CircleObstacle((100,20),ENTITY,BUFFER)
assert segment_circle_clearance([0,0],[200,0],[stat])['safety_m']==relative_minimum([0,0],[200,0],[100,20],[100,20])[0]-SAFE
raw=np.zeros(14);frame=LocalFrame.for_leg([0,0],[500,0])
a=[dict(id='a',valid=True,position=[100,0],entity_radius=20,safety_buffer=60)]
b=[dict(id='a',valid=True,position=[120,0],entity_radius=20,safety_buffer=60)]
h=HistoricalFrame(frame,(),[a,b]);assert h.encode(raw)[14]==60 and h.encode(raw)[14]==80
assert np.array_equal(encode(frame,(stat,),[],raw),encode(frame,(),[dict(id='a',valid=True,position=[100,20],entity_radius=20,safety_buffer=60)],raw))
print('PASS: approaching/receding, simultaneous/asynchronous, stationary metric+encoding, historical positions')
