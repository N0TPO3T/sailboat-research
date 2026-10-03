import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from analyze_r1 import validate_coverage,pairs,outcome
class AnalysisTests(unittest.TestCase):
 def test_missing_or_duplicate_episode_cannot_shrink_denominator(self):
  manifest={'jobs':[{'scene':{'id':'a'},'variant':'x'},{'scene':{'id':'b'},'variant':'x'}]}
  with self.assertRaises(ValueError):validate_coverage([{'scene_id':'a','variant':'x'}],manifest)
  with self.assertRaises(ValueError):validate_coverage([{'scene_id':'a','variant':'x'}]*2,manifest)
 def test_failed_short_time_is_not_efficiency_benefit(self):
  def row(n,v,ok,t):return dict(scene_id=n,variant=v,success=ok,time_s=t,path_length_m=t,tack_count=0,target_changes=0,planning_seconds=0)
  a=pairs([row('a','x',True,100),row('a','y',True,110),row('b','x',True,100),row('b','y',False,1)],'x','y')
  self.assertEqual(a['common_success_n'],1);self.assertEqual(a['time_s']['paired_mean_difference'],10);self.assertEqual(a['losses'],1)
 def test_buffer_invasion_precedes_software_exception(self):
  self.assertEqual(outcome(dict(min_entity_clearance_m=60,min_safety_clearance_m=-1,reason='NoRouteError',success=False)),'buffer_violation')
