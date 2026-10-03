import unittest,math
from dataclasses import replace
from sailboat_routing.r1_planner import RouteWaypointPlanner,R1Config
from sailboat_routing.planner import StaticMap,CircleObstacle,PlannerInput,LocalWindEstimate

class R1Tests(unittest.TestCase):
 def test_wide_coverage_does_not_change_safety_map(self):
  chart=StaticMap((-1500,2000,-1500,1500),(CircleObstacle((500,0),55,70),),25)
  p=(380.,-180.);v=PlannerInput(p,0,None,((0,0),(1000,0)),165,None)
  planner=RouteWaypointPlanner(chart,R1Config(margin=80))
  decision=planner.plan(v)
  self.assertTrue(chart.segment_clear(p,decision.target_xy));self.assertEqual(chart.obstacles[0].exclusion_radius,125)
  self.assertGreater(len(decision.candidates),3)
 def test_geometry_cannot_read_wind(self):
  chart=StaticMap((-1000,2000,-1000,1000));v=PlannerInput((0,0),0,None,((0,0),(1000,0)),0,None)
  a=RouteWaypointPlanner(chart,R1Config(wind_weight=.3)).plan(v)
  b=RouteWaypointPlanner(chart,R1Config(wind_weight=.3)).plan(replace(v,wind=LocalWindEstimate(1.4,True)))
  self.assertEqual(a,b)
 def test_invalid_estimate_matches_geometry(self):
  chart=StaticMap((-1000,2000,-1000,1000));v=PlannerInput((0,0),0,None,((0,0),(1000,0)),0,LocalWindEstimate(math.nan,False))
  a=RouteWaypointPlanner(chart,R1Config(wind_weight=.3)).plan(v)
  b=RouteWaypointPlanner(chart,R1Config(wind_weight=.3),'estimated_local').plan(v)
  self.assertEqual(a,b)

 def test_final_goal_inside_fifteen_metres_is_retained(self):
  chart=StaticMap((-1000,2000,-1000,1000));v=PlannerInput((986,0),0,(1000,0),((0,0),(1000,0)),100,None)
  a=RouteWaypointPlanner(chart).plan(v);self.assertEqual(a.target_xy,(1000,0))
 def test_history_warmup_is_exact_geometry_and_same_candidates(self):
  chart=StaticMap((-1000,2000,-1000,1000));v=PlannerInput((0,0),0,None,((0,0),(1000,0)),0,None)
  a=RouteWaypointPlanner(chart).plan(v);b=RouteWaypointPlanner(chart,R1Config(history_gain=.5)).plan(v)
  self.assertEqual(a,b)

 def test_active_history_changes_scores_not_candidates(self):
  chart=StaticMap((-1000,2000,-1000,1000));v=PlannerInput((20,4),0,(500,0),((0,0),(1000,0)),20,None)
  geom=RouteWaypointPlanner(chart);hist=RouteWaypointPlanner(chart,R1Config(history_gain=.5))
  for planner in [geom,hist]:
   planner.history_target=(500,0);planner.previous.extend((float(t),(float(t),.2*t)) for t in range(20))
  a,b=geom.plan(v),hist.plan(v)
  self.assertEqual([x.target_xy for x in a.candidates],[x.target_xy for x in b.candidates])
  self.assertTrue(any(abs(x.total-y.total)>1e-6 for x,y in zip(a.candidates,b.candidates)))
 def test_history_estimator_resets_without_touching_controller(self):
  chart=StaticMap((-1000,2000,-1000,1000));planner=RouteWaypointPlanner(chart,R1Config(history_gain=.5))
  planner.history_target=(500,0);planner.previous.extend((float(t),(float(t),.2*t)) for t in range(20))
  planner.plan(PlannerInput((20,4),0,(500,100),((0,0),(1000,0)),20,None))
  self.assertEqual(len(planner.previous),1);self.assertEqual(planner.log[-1]['bias'],0)
