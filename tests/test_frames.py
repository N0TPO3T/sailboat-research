"""Frame semantics and real-checkpoint recurrent replay (no mock Actor)."""
import math
import unittest

import numpy as np

from sailboat_routing.runtime import ROOT, FrozenController, SeniorModules, torch
from sailboat_routing.frames import LocalFrame, reencode_controller


def observations(count=25):
    history = []
    for i in range(count):
        raw = np.array([
            2.4 * i, 3.0 * math.sin(i / 7), 0.07 * math.sin(i / 5),
            0.12 + 0.04 * math.sin(i / 6), 2.4, 0.12, -0.01, 0.02,
            0.4, -0.08, 777.0, -888.0, 1900.0, -300.0,
        ], dtype=np.float32)
        history.append(raw)
    return history


class LocalFrameTests(unittest.TestCase):
    def test_rigid_inverse_and_fixed_target_without_length_scaling(self):
        frame = LocalFrame.for_leg((70.0, -25.0), (670.0, 775.0))
        self.assertAlmostEqual(frame.angle, math.atan2(800.0, 600.0))
        np.testing.assert_allclose(frame.origin, (370.0, 375.0))
        np.testing.assert_allclose(frame.world_to_local(frame.goal_world), (500.0, 0.0), atol=1e-12)
        np.testing.assert_allclose(frame.world_to_local((70.0, -25.0)), (-500.0, 0.0), atol=1e-12)
        for point in [(11.0, 27.0), (-34.0, -80.0), frame.goal_world]:
            np.testing.assert_allclose(frame.local_to_world(frame.world_to_local(point)), point, atol=1e-12)
        a, b = (80.0, -3.0), (112.0, 42.0)
        self.assertAlmostEqual(np.linalg.norm(frame.world_to_local(a) - frame.world_to_local(b)),
                               np.linalg.norm(np.array(a) - b))

    def test_heading_and_wind_wrap_but_body_fields_do_not_rotate(self):
        frame = LocalFrame.for_leg((0.0, 0.0), (0.0, 500.0))
        raw = observations(1)[0]
        raw[3] = -math.pi + 0.1
        encoded = frame.encode(raw)
        np.testing.assert_array_equal(encoded[[2, 4, 5, 6, 7, 8, 9]], raw[[2, 4, 5, 6, 7, 8, 9]])
        self.assertAlmostEqual(float(encoded[3]), math.pi / 2 + 0.1, places=6)
        np.testing.assert_array_equal(encoded[10:14], (0.0, 0.0, 500.0, 0.0))
        np.testing.assert_array_equal(raw[10:14], (777.0, -888.0, 1900.0, -300.0))
        for angle in [-math.pi - 0.1, -math.pi, -0.2, 0.0, math.pi, 9.0]:
            local = frame.wind_to_local(angle)
            world = frame.wind_to_world(local)
            self.assertLessEqual(abs(local), math.pi)
            self.assertLessEqual(abs(world), math.pi)
            self.assertAlmostEqual(math.sin(world), math.sin(angle), places=12)
            self.assertAlmostEqual(math.cos(world), math.cos(angle), places=12)

    def test_target_switch_progress_uses_same_new_target_for_both_states(self):
        old = LocalFrame.for_leg((0.0, 0.0), (500.0, 0.0))
        new = LocalFrame.for_leg((490.0, 0.0), (490.0, 500.0))
        previous, current = observations(2)
        previous[:2], current[:2] = (490.0, 0.0), (492.0, 3.0)
        previous[12:14], current[12:14] = old.goal_world, new.goal_world
        encoded = new.encode(current, previous)
        expected = 500.0 - math.hypot(2.0, 497.0)
        self.assertAlmostEqual(float(encoded[10]), expected, places=6)
        self.assertAlmostEqual(float(encoded[11]), 3.0, places=6)
        stationary = new.encode(previous, previous)
        np.testing.assert_array_equal(stationary[10:12], (0.0, 0.0))


class RealControllerReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modules = SeniorModules()

    def controller(self):
        controller = FrozenController(self.modules, ROOT / "checkpoints/actor.pth",
                                      ROOT / "checkpoints/normalizer.pth")
        self.addCleanup(controller.close)
        return controller

    def assert_hidden_equal(self, left, right):
        for actual, expected in zip(left, right):
            np.testing.assert_array_equal(actual, expected)

    def test_zero_variance_target_inputs_and_frozen_statistics(self):
        controller = self.controller()
        frame = LocalFrame.for_leg((80.0, 70.0), (-420.0, 570.0))
        encoded = frame.encode(observations(1)[0])
        stats = controller.normalizer.state_dict()
        before = {key: value.clone() if torch.is_tensor(value) else value for key, value in stats.items()}
        np.testing.assert_array_equal(controller.normalizer.mean[12:14].numpy(), (500.0, 0.0))
        np.testing.assert_array_equal(controller.normalizer.var[12:14].numpy(), (0.0, 0.0))
        normalized = controller.normalizer.normalize(torch.from_numpy(encoded))
        np.testing.assert_array_equal(normalized[12:14].numpy(), (0.0, 0.0))
        controller.reset(encoded)
        controller.act(encoded)
        reencode_controller(controller, frame, observations(1), [])
        for key, value in controller.normalizer.state_dict().items():
            if torch.is_tensor(value):
                self.assertTrue(torch.equal(value, before[key]))
            else:
                self.assertEqual(value, before[key])
        self.assertFalse(controller.actor.training)
        self.assertTrue(all(not parameter.requires_grad for parameter in controller.actor.parameters()))

    def test_same_frame_every_prefix_hidden_and_next_action_match(self):
        frame = LocalFrame.for_leg((0.0, 0.0), (500.0, 0.0))
        raw = observations()
        encoded = [frame.encode(value, None if i == 0 else raw[i - 1]) for i, value in enumerate(raw)]
        original, replay = self.controller(), self.controller()
        original.reset(encoded[0])
        actions, hidden = [], []
        for observation in encoded:
            actions.append(original.act(observation, record_features=True).action)
            hidden.append(original.hidden())
        # Includes >10 steps: bptt_len=10 is not an online history window.
        for t in range(len(raw)):
            current, elapsed = reencode_controller(replay, frame, raw[:t + 1], actions[:t])
            self.assertGreaterEqual(elapsed, 0.0)
            self.assertEqual(replay.steps, t)
            np.testing.assert_array_equal(current, encoded[t])
            np.testing.assert_array_equal(replay.previous, encoded[t - 1] if t else encoded[0])
            np.testing.assert_array_equal(replay.previous_action, actions[t - 1] if t else (0.0, 0.0))
            if t:
                self.assert_hidden_equal(replay.hidden(), hidden[t - 1])
            else:
                self.assertNotIn("v0", replay.actor.hidden_states)
            decision = replay.act(current, record_features=True)
            np.testing.assert_array_equal(decision.action, actions[t])
            self.assert_hidden_equal(replay.hidden(), hidden[t])
            self.assertEqual(replay.steps, t + 1)

    def test_changed_frame_preserves_executed_commands_and_disables_capture(self):
        raw = observations()
        old = LocalFrame.for_leg((0.0, 0.0), (500.0, 0.0))
        new = LocalFrame.for_leg((60.0, 0.0), (310.0, 433.0))
        old_controller, reference, replay = self.controller(), self.controller(), self.controller()
        old_controller.reset(old.encode(raw[0]))
        commands = [old_controller.act(old.encode(value, None if i == 0 else raw[i - 1])).action
                    for i, value in enumerate(raw[:-1])]
        encoded = [new.encode(value, None if i == 0 else raw[i - 1]) for i, value in enumerate(raw)]
        reference.reset(encoded[0])
        recomputed = []
        for i, observation in enumerate(encoded[:-1]):
            recomputed.append(reference.act(observation).action)
            # A counterfactual new-frame prediction was NOT the executed command.
            reference.previous_action = commands[i].copy()
        self.assertTrue(any(not np.array_equal(a, b) for a, b in zip(commands, recomputed)))
        weights = {key: value.clone() for key, value in replay.actor.state_dict().items()}
        sentinel = np.array([123.0], dtype=np.float32)
        replay._feature = sentinel
        replay._capture = True
        current, _ = reencode_controller(replay, new, raw, commands)
        self.assertIs(replay._feature, sentinel)
        self.assertTrue(replay._capture)
        self.assert_hidden_equal(replay.hidden(), reference.hidden())
        for key, value in replay.actor.state_dict().items():
            self.assertTrue(torch.equal(value, weights[key]))
        np.testing.assert_array_equal(replay.act(current).action, reference.act(encoded[-1]).action)
        self.assert_hidden_equal(replay.hidden(), reference.hidden())

    def test_rejects_incomplete_history_without_mutating_live_memory(self):
        controller = self.controller()
        frame = LocalFrame.for_leg((0.0, 0.0), (500.0, 0.0))
        raw = observations(2)
        controller.reset(frame.encode(raw[0]))
        controller.act(frame.encode(raw[0]))
        before = controller.hidden()
        with self.assertRaises(ValueError):
            reencode_controller(controller, frame, raw, [])
        self.assert_hidden_equal(controller.hidden(), before)
        self.assertEqual(controller.steps, 1)


if __name__ == "__main__":
    unittest.main()
