"""Real, short frozen-controller checks for the navigation integration."""
import json
from pathlib import Path
import tempfile
import unittest
from sailboat_routing.runtime import ROOT
from sailboat_routing.navigation import run_episode

class NoBudget:
    def check(self): pass

class NavigationTests(unittest.TestCase):
    def setUp(self):
        self.suite=json.loads((ROOT/'configs/development_suite.json').read_text())
        self.scene=self.suite['capture_scenarios'][0]
        self.admission={'protocol':json.loads((ROOT/'configs/navigation_contract.json').read_text()),'source_identity':{}}
    def test_partial_capture_rejected_before_output(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as d:
            with self.assertRaisesRegex(ValueError,'Partial interface'):
                run_episode(self.scene,self.suite,self.admission,d,NoBudget(),capture=True,max_steps=2)
            self.assertEqual(list(Path(d).iterdir()),[])
    def test_bounded_run_is_incomplete_and_sidepath_does_not_change_dynamics(self):
        records=[]
        for capture in [False,True]:
            with tempfile.TemporaryDirectory(dir=ROOT/'runs') as d:
                row=run_episode(self.scene,self.suite,self.admission,d,NoBudget(),record_features=capture,max_steps=3)
                self.assertFalse(row['complete'])
                self.assertEqual(row['reason'],'bounded_interface_smoke')
                self.assertFalse(list(Path(d).glob('*.npz')))
                records.append(json.loads((ROOT/row['evidence']).read_text())['trajectory'])
        self.assertEqual(records[0],records[1])

    def test_unreachable_map_returns_failed_episode_without_losing_denominator(self):
        self.suite['maps']['open']=[{'center_xy':[0,0],'entity_radius':20,'safety_buffer':10}]
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as d:
            row=run_episode(self.scene,self.suite,self.admission,d,NoBudget())
            self.assertFalse(row['success'])
            self.assertEqual(row['reason'],'NoRouteError')
            self.assertTrue((ROOT/row['evidence']).is_file())
