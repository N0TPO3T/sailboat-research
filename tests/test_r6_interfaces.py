import unittest,sys
from pathlib import Path
from collections import deque
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from sailboat_routing.runtime import SeniorModules,FrozenController
from sailboat_routing.r6_controller import WindowController,FeedforwardController,ObstacleFrame,change_reference
from sailboat_routing.frames import LocalFrame
from sailboat_routing.planner import CircleObstacle
import numpy as np
import torch

class R6Interfaces(unittest.TestCase):
    def test_training_window_matches_original_buffer_alignment(self):
        m=SeniorModules();p=WindowController(m,ROOT/"checkpoints/actor.pth",ROOT/"checkpoints/normalizer.pth")
        initial=np.zeros(14,dtype=np.float32);initial[12]=500;p.reset(initial)
        states=deque([initial.copy() for _ in range(10)],maxlen=10);actions=deque([np.zeros(2,dtype=np.float32) for _ in range(10)],maxlen=10)
        current=initial.copy()
        for t in range(15):
            with torch.inference_mode():
                expected,_=p.actor(state_sequence=p.normalizer.normalize(torch.tensor(np.array(states)[None])),action_sequence=torch.tensor(np.array(actions)[None]),current_state=p.normalizer.normalize(torch.tensor(current[None])),deterministic=True)
            got=p.act(current).action;np.testing.assert_allclose(got,expected[0].numpy(),atol=1e-7,rtol=0)
            actions.append(got.copy());current=current.copy();current[0]+=2;current[3]+=.01;states.append(current.copy())
        p.close()
    def test_change_frame_preserves_actual_commands_and_raw_history(self):
        m=SeniorModules();p=WindowController(m,ROOT/"checkpoints/actor.pth",ROOT/"checkpoints/normalizer.pth")
        raw=np.zeros((14,14),dtype=np.float32);raw[:,0]=np.arange(14)*2;raw[:,12]=500
        commands=[np.array([.1*i,-.1],dtype=np.float32) for i in range(13)];saved=raw.copy()
        p.reset(raw[0]);frame=LocalFrame.for_leg(raw[-1,:2],(450,180));obs,_=change_reference(p,frame,raw,commands)
        np.testing.assert_array_equal(raw,saved);np.testing.assert_array_equal(p.previous_action,commands[-1]);np.testing.assert_array_equal(p.actions[-1],commands[-1]);np.testing.assert_array_equal(obs[12:14],[500,0]);self.assertEqual(len(p.observations),10);p.close()
    def test_obstacle_inputs_distance_heading_and_no_future(self):
        f=ObstacleFrame(LocalFrame.for_leg((0,0),(500,0)),(CircleObstacle((100,0),30,60),CircleObstacle((0,140),30,60),CircleObstacle((0,160),30,60)))
        raw=np.zeros(14);raw[3]=np.pi/2;got=f.encode(raw)
        np.testing.assert_allclose(got[14:],[100,-np.pi/2,140,0],atol=1e-6)
    def test_boundary_mapping_retains_real_safety_radius(self):
        circle=CircleObstacle((200,0),70,60);frame=LocalFrame.for_leg((0,0),(500,0));raw=np.zeros(14)
        original=ObstacleFrame(frame,(circle,),"center").encode(raw)
        adapted=ObstacleFrame(frame,(circle,),"boundary40").encode(raw)
        absent=ObstacleFrame(frame,(circle,),"none").encode(raw)
        np.testing.assert_array_equal(original[14:],[0,0,0,0]);np.testing.assert_array_equal(adapted[14:],[110,0,0,0]);np.testing.assert_array_equal(absent[14:],[0,0,0,0]);self.assertEqual(circle.exclusion_radius,130)
    def test_feedforward_matching_assets_load_and_finite(self):
        p=FeedforwardController(SeniorModules());s=np.zeros(14,dtype=np.float32);s[12]=500;p.reset(s);a=p.act(s).action;self.assertEqual(a.shape,(2,));self.assertTrue(np.isfinite(a).all());self.assertTrue((abs(a)<=1).all())
if __name__=="__main__":unittest.main()
