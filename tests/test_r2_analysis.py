import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from analyze_r2 import paired_detail,quantile
class R2AnalysisTests(unittest.TestCase):
 def test_conditional_efficiency_excludes_early_failures_and_exposes_tail(self):
  rows=[]
  for i,(a,b,sa,sb) in enumerate([(10,20,True,True),(20,15,True,True),(100,90,True,True),(1,600,False,True)]):
   for v,t,s in [('a',a,sa),('b',b,sb)]:
    rows.append(dict(scene_id=str(i),variant=v,success=s,time_s=t,path_length_m=t*2,tack_count=1,target_changes=2,planning_seconds=1,reencoding_seconds=2,cpu_seconds=3,wall_seconds=3))
  d=paired_detail(rows,'a','b')
  self.assertEqual(d['n'],4);self.assertEqual(d['wins'],1);self.assertEqual(d['common_success_n'],3)
  self.assertEqual(d['common_success_scene_ids'],['0','1','2'])
  self.assertEqual(d['time_s']['paired_median_difference'],-5)
  self.assertAlmostEqual(d['time_s']['control_p90'],84)
  self.assertAlmostEqual(d['time_s']['treatment_p90'],76)
 def test_single_episode_tail_not_fabricated_repeats(self):
  self.assertEqual(quantile([7],.9),7)
