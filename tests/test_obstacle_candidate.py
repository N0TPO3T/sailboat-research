"""Consumer-visible 18D protocol boundaries, using the copied real checkpoint."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import numpy as np
from sailboat_routing.obstacle_candidate import ROOT, ObstacleController, CandidateModules, ObstacleSegment, observation, torch


class ObstacleCandidateTests(unittest.TestCase):
    def test_rejects_incompatible_or_nonfinite_observation(self):
        for bad in (np.zeros(14), np.zeros((1,18)), np.full(18,np.nan)):
            with self.assertRaises(ValueError):
                observation(bad)

    def test_requires_reset_and_explicit_mode(self):
        with self.assertRaises(ValueError):
            ObstacleController(mode="automatic")
        controller = ObstacleController(mode="eval")
        self.addCleanup(controller.close)
        with self.assertRaises(RuntimeError):
            controller.act(np.zeros(18))

    def test_original_select_action_persistent_history_and_same_forward_features(self):
        reference = ObstacleController(mode="legacy_training")
        candidate = ObstacleController(mode="legacy_training")
        self.addCleanup(reference.close); self.addCleanup(candidate.close)
        initial = np.zeros(18, dtype=np.float32); initial[12] = 500
        reference.reset(initial); candidate.reset(initial)
        agent = reference.reference()
        for step in range(12):
            obs = initial.copy(); obs[0] = step; obs[14:18] = [90,.2,130,-.3]
            state = torch.get_rng_state()
            expected = reference.modules.original.SAC_lstm_countinuous.select_action(
                agent, reference.previous, reference.previous_action, obs, True, None, env_id="v0")
            reference.previous = obs.copy(); reference.previous_action = expected.copy()
            torch.set_rng_state(state)
            decision = candidate.act(obs, record_features=True)
            np.testing.assert_allclose(decision.action, expected, atol=1e-6, rtol=0)
            self.assertEqual(decision.history_steps, step+1)
            for key, value in reference.history().items():
                np.testing.assert_allclose(candidate.history()[key], value, atol=1e-6, rtol=0)
            expected_feature = np.concatenate((candidate.normalizer.normalize(torch.from_numpy(obs)).numpy(),
                                               candidate.history()["attention_history"][-1]))
            np.testing.assert_array_equal(decision.features, expected_feature)
        candidate.reset(initial)
        self.assertEqual(candidate.steps, 0)
        self.assertNotIn("v0", candidate.actor.hidden_states)
        self.assertNotIn("v0", candidate.actor.lstm_output_history)

    def test_obstacle_slots_are_two_distance_relative_bearing_pairs(self):
        modules = CandidateModules()
        segment = ObstacleSegment(modules, noise_enabled=False)
        self.addCleanup(segment.close)
        segment.reset(0, 0, [])
        modules.globals.observed_obstacles = [(100.,0.),(0.,120.),(200.,0.)]
        first, second = segment.env._get_two_nearest_obstacles(0, 0, np.pi/2)
        np.testing.assert_allclose(first, [100.,-np.pi/2], atol=1e-7)
        np.testing.assert_allclose(second, [120.,0.], atol=1e-7)
        modules.globals.observed_obstacles = [(151.,0.)]
        self.assertEqual(segment.env._get_two_nearest_obstacles(0,0,0), ((0.,0.),(0.,0.)))
        for action in (np.array([2.,0.]),np.array([np.nan,0.]),np.zeros(18)):
            with self.assertRaises(ValueError):
                segment.step(action)

    def test_normalizer_rejects_wrong_dimension_or_negative_variance(self):
        with TemporaryDirectory(dir=ROOT/".tmp") as directory:
            for state in ({"mean":torch.zeros(14),"var":torch.ones(14),"count":1},
                          {"mean":torch.zeros(18),"var":-torch.ones(18),"count":1}):
                path = Path(directory)/"normalizer.pth"
                torch.save(state, path)
                with self.assertRaises(ValueError):
                    ObstacleController(normalizer_path=path)


if __name__ == "__main__":
    unittest.main()
