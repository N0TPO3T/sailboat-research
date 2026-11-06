from environment import *
from validate import save
from sailboat_routing.frames import LocalFrame
from sailboat_routing.r6_controller import ObstacleFrame
checks=[]
e=MigrationEnv('original');e.reset();g=e.modules.globals
g.current_action=np.zeros(2);g.current_state=np.zeros(12);g.state=np.zeros(14);g.state[12]=500
for x,expected in [(0,-.2),(125,2.8),(125,-.2),(250,4.8),(375,11.8),(490,39.8)]:
 g.current_state[0]=x
 reward=e.env.calculate_reward(np.zeros(12),False)
 np.testing.assert_allclose(reward,expected,rtol=0,atol=1e-12)
checks.append('milestone_once_and_arrival_reward')
g.current_state[0]=0
np.testing.assert_allclose(e.env.calculate_reward(np.zeros(12),True),-100.2,rtol=0,atol=1e-12)
checks.append('integration_failure_penalty')
for x,expected in [(489.999,False),(490,True),(510,True),(510.001,False)]:
 e.env.state[12:14]=[500,0];g.current_state[:2]=[x,0]
 assert bool(e.env.check_done())==expected
checks.append('goal_10m_closed_boundary')
high=e.high;plus=accumulate([0,0],high);minus=accumulate([0,0],-high)
np.testing.assert_allclose(plus,np.deg2rad([9,9]),atol=1e-12,rtol=0)
np.testing.assert_allclose(minus,np.deg2rad([-10,-10]),atol=1e-12,rtol=0)
checks.append('float32_high_asymmetric_floor_preserved')
f=LocalFrame.for_leg([0,0],[500,0]);raw=np.zeros(14,np.float32)
# equal-distance ordering, inclusion boundary, overlap clamping, missing sentinel
o=(CircleObstacle((0,100),30,60),CircleObstacle((100,0),30,60))
v=ObstacleFrame(f,o,'boundary40').encode(raw)
np.testing.assert_allclose(v[14:],[50,0,50,np.pi/2],atol=2e-5,rtol=0)
for center,expected in [(200,150),(200.001,0),(10,0)]:
 z=ObstacleFrame(f,(CircleObstacle((center,0),30,60),),'boundary40').encode(raw)
 np.testing.assert_allclose(z[14],expected,atol=2e-5,rtol=0)
checks.append('tie_sort_buffer60_visibility_and_overlap')
diag={'raw':[1,2,.3,.4,5,6,.7,.8,.9,1.,0,0,0,0]}
np.testing.assert_allclose(from_gazebo(diag),[1,2,-.3,.4,5,6,-.7,.8,-.9,-1.,0,0,0,0],atol=2e-5,rtol=0)
checks.append('explicit_gazebo_sign_conversion')
e.close();save('edge_checks.json',dict(passed=True,checks=checks,action_high=high.tolist(),positive_endpoint_deg=np.rad2deg(plus).tolist(),negative_endpoint_deg=np.rad2deg(minus).tolist()))
print('EDGE_CHECK_PASS',checks)
