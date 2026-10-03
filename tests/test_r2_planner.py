import unittest, math
from dataclasses import replace
from sailboat_routing.planner import StaticMap,CircleObstacle,PlannerInput,LocalWindEstimate
from sailboat_routing.r1_planner import RouteWaypointPlanner,R1Config
from sailboat_routing.r2_planner import Radial500Planner,RelayPlanner,RelayConfig
from sailboat_routing.metrics import segment_circle_clearance

class R2Tests(unittest.TestCase):
 def test_radial_ablation_preserves_narrow_control(self):
  chart=StaticMap((-1500,2500,-1500,1500),(CircleObstacle((500,0),55,70),),25)
  a=RouteWaypointPlanner(chart,R1Config(wide_candidates=False));b=Radial500Planner(chart,R1Config(wide_candidates=False))
  current=None
  for t,p in [(0,(0,0)),(10,(15,-2)),(30,(65,-30)),(50,(110,-90))]:
   v=PlannerInput(p,.3,current,((0,0),(1500,0)),t,None)
   x,y=a.plan(v),b.plan(v);self.assertEqual(x,y);current=x.target_xy
 def test_relay_does_not_cut_obstacle_turn(self):
  chart=StaticMap((-1000,2000,-1000,1000),(CircleObstacle((300,0),55,70),),25)
  planner=RelayPlanner(chart);v=PlannerInput((0,0),0,None,((0,0),(1000,0)),0,None)
  d=planner.plan(v)
  self.assertGreater(segment_circle_clearance(v.position_xy,d.target_xy,chart.obstacles)['safety_m'],79.99)
  self.assertEqual(chart.obstacles[0].safety_buffer,70)
  self.assertLessEqual(math.dist(v.position_xy,d.target_xy),500.0001)
 def test_relay_holds_during_heading_change_and_ignores_wind(self):
  chart=StaticMap((-1000,2000,-1000,1000));planner=RelayPlanner(chart)
  d=planner.plan(PlannerInput((0,0),0,None,((0,0),(1000,0)),0,None))
  v=PlannerInput((200,80),math.pi,d.target_xy,((0,0),(1000,0)),80,LocalWindEstimate(1.2,True))
  self.assertEqual(planner.plan(v).target_xy,d.target_xy)
  self.assertFalse(planner.plan(v).wind_used)
 def test_final_goal_retained_at_fourteen_metres(self):
  chart=StaticMap((-1000,2000,-1000,1000));planner=RelayPlanner(chart)
  v=PlannerInput((986,0),0,(1000,0),((0,0),(1000,0)),100,None)
  self.assertEqual(planner.plan(v).target_xy,(1000,0))
 def test_visible_target_advances_after_handoff(self):
  chart=StaticMap((-1000,2000,-1000,1000));planner=RelayPlanner(chart)
  v=PlannerInput((465,0),0,(500,0),((0,0),(1000,0)),100,None)
  self.assertEqual(planner.plan(v).target_xy,(965,0))
