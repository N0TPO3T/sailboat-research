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
a=[dict(id='a',valid=True,position=[100,0],entity_radius=ENTITY,safety_buffer=60)]
b=[dict(id='a',valid=True,position=[120,0],entity_radius=ENTITY,safety_buffer=60)]
h=HistoricalFrame(frame,(),[a,b]);assert h.encode(raw)[14]==55 and h.encode(raw)[14]==75
assert np.array_equal(encode(frame,(stat,),[],raw),encode(frame,(),[dict(id='a',valid=True,position=[100,20],entity_radius=ENTITY,safety_buffer=60)],raw))
# IDs exchange nearest-slot rank; invalid observations never occupy a slot.
c0=[dict(id='a',time=0,valid=True,position=[100,0],entity_radius=ENTITY,safety_buffer=60),dict(id='b',time=0,valid=True,position=[130,20],entity_radius=ENTITY,safety_buffer=60)]
c1=[dict(id='a',time=1,valid=True,position=[120,0],entity_radius=ENTITY,safety_buffer=60),dict(id='b',time=1,valid=True,position=[80,20],entity_radius=ENTITY,safety_buffer=60)]
c2=[dict(c1[0],time=2),dict(c1[1],time=2,valid=False)]
h=HistoricalFrame(frame,(),[c0,c1,c2]);out=[h.encode(raw) for _ in range(3)]
assert out[0][14]==55 and np.isclose(out[1][14],np.hypot(80,20)-45) and out[2][14]==75 and out[2][16]==0
print('PASS: approaching/receding, simultaneous/asynchronous, stationary metric+encoding, historical positions, ID/rank exchange and validity')

# Same observed positions and own motion; only target speed changes goal-time gate.
from sailboat_routing.r7_goal import GoalRelaySupervisor
from sailboat_routing.planner import StaticMap
chart=StaticMap((-1000,2000,-1000,1000),(),grid_resolution=25)
for speed,expected in [(1.,True),(.5,False)]:
    sup=GoalRelaySupervisor(chart,dict(mode='current',goal_relay=True,goal_time_gate=True))
    obs=[dict(id='v1',valid=True,time=100,position=[800,0],velocity=[speed,0],entity_radius=ENTITY,safety_buffer=BUFFER)]
    sup.plan([500,200],0,[4,0],(900,200),(1000,0),100,obs)
    assert (sup.staging is not None)==expected
print('PASS: fixed-state goal occupancy time discrimination')
