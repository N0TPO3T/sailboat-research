import unittest
from sailboat_routing.planner import StaticMap,CircleObstacle,PlannerInput,PlannerDecision
from sailboat_routing.r1_planner import RouteWaypointPlanner,R1Config
from sailboat_routing.r2_planner import RelayPlanner,RelayConfig
from sailboat_routing.r3_planner import RiskManagedPlanner,RiskConfig

class R3Tests(unittest.TestCase):
 def test_disabled_intervention_matches_original_planners(self):
  chart=StaticMap((-1500,2500,-1500,1500),(CircleObstacle((500,0),55,70),),25)
  for kind in ['r1','relay']:
   old=RouteWaypointPlanner(chart) if kind=='r1' else RelayPlanner(chart,RelayConfig(handoff=100,trigger_clearance=80))
   new=RiskManagedPlanner(chart,RiskConfig(base=kind,threshold=0))
   current=None
   for t,p in [(0,(0,0)),(10,(15,-2)),(30,(65,-30)),(50,(110,-90))]:
    v=PlannerInput(p,.3,current,((0,0),(1500,0)),t,None)
    x,y=old.plan(v),new.plan(v);self.assertEqual(x,y);current=x.target_xy
 def test_closing_gate_uses_past_positions_and_does_not_trigger_on_receding(self):
  chart=StaticMap((-1000,2000,-1000,1000),(CircleObstacle((300,0),55,70),),25)
  for closing,start,step,expected in [(True,130,-2,False),(True,100,3,True),(False,130,-2,True)]:
   obj=RiskManagedPlanner(chart,RiskConfig(threshold=80,closing_gate=closing))
   class Probe:
    config=R1Config()
    def plan(self,v):return PlannerDecision(v.current_goal_xy,(),'probe',False)
   obj.base=Probe()
   for t in range(11):
    v=PlannerInput((start+step*t,0),0,(500,200),((0,0),(1000,0)),t,None)
    obj.plan(v);obj.plan(v)
   self.assertEqual(len(obj.motion),11)
   self.assertEqual(obj.log[-1]['risk_detected'],expected)
   if closing and expected:
                self.assertTrue(any(x['attempt'] for x in obj.log if x['time']==10))
                self.assertFalse(obj.log[-1]['attempt'])
 def test_risk_bypasses_holding_temporarily_and_cooldown_is_physical_time(self):
  chart=StaticMap((-1000,2000,-1000,1000),(CircleObstacle((300,0),55,70),),25)
  obj=RiskManagedPlanner(chart,RiskConfig(threshold=80,cooldown=20))
  class Probe:
   config=R1Config()
   calls=[]
   def plan(self,v):
    self.calls.append(self.config)
    return PlannerDecision(v.current_goal_xy,(),'probe',False)
  obj.base=Probe();original=obj.base.config
  for t in [0,1,19,20]:
   obj.plan(PlannerInput((130,0),0,(500,200),((0,0),(1000,0)),t,None))
  self.assertEqual([x.improvement for x in obj.base.calls],[0,15,15,0])
  self.assertEqual([x.hold for x in obj.base.calls],[0,20,20,0])
  self.assertEqual(obj.base.config,original)
 def test_open_water_has_no_finite_risk_and_final_goal_is_retained(self):
  obj=RiskManagedPlanner(StaticMap((-1000,2000,-1000,1000)),RiskConfig(threshold=80))
  v=PlannerInput((986,0),0,(1000,0),((0,0),(1000,0)),100,None)
  self.assertEqual(obj.plan(v).target_xy,(1000,0));self.assertFalse(obj.log[-1]['attempt'])
