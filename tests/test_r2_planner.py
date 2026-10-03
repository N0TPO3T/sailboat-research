import unittest, math
from dataclasses import replace
from sailboat_routing.planner import StaticMap,CircleObstacle,PlannerInput,LocalWindEstimate
from sailboat_routing.r1_planner import RouteWaypointPlanner,R1Config
from sailboat_routing.r2_planner import Radial500Planner,ForwardPlanner,RouteCostPlanner,RelayPlanner,RelayConfig
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

 def test_forecast_is_past_ten_seconds_and_duplicate_times_do_not_advance_it(self):
  chart=StaticMap((-1000,2000,-1000,1000),(CircleObstacle((300,0),55,70),),25)
  planner=RelayPlanner(chart,RelayConfig(prediction_horizon=20));current=None
  for t in range(11):
   v=PlannerInput((100+3*t,0),0,current,((100,0),(1000,0)),t,None)
   current=planner.plan(v).target_xy
   planner.plan(v)
   self.assertEqual(len(planner.motion),t+1)
   if t<10:self.assertTrue(all(x['forecast'] is None for x in planner.log))
  record=planner.log[-1]
  self.assertEqual(record['time'],10)
  self.assertEqual(record['velocity'],(3.,0.))
  self.assertEqual(record['forecast'],(190.,0.))
  self.assertTrue(record['predictive_risk'])
  self.assertEqual(chart.obstacles[0].safety_buffer,70)

 def test_route_cost_ablation_keeps_candidate_geometry_and_removes_only_two_costs(self):
  chart=StaticMap((-1500,2500,-1500,1500),(CircleObstacle((500,0),55,70),),25)
  v=PlannerInput((0,0),1.,(250,-200),((0,0),(1500,0)),30,None)
  a=ForwardPlanner(chart).plan(v);b=RouteCostPlanner(chart).plan(v)
  self.assertEqual([x.target_xy for x in a.candidates],[x.target_xy for x in b.candidates])
  for x in b.candidates:
   self.assertEqual(x.total,x.remaining_map_distance)
   self.assertEqual(x.turn_penalty,0.)
   self.assertEqual(x.change_penalty,0.)
