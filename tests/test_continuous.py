"""Behavioral checks over the actual inherited ODE; no mock dynamics."""
import copy
import json
import pickle
import random
import unittest
from unittest.mock import patch

import numpy as np

from sailboat_routing.continuous import ContinuousPhysics
from sailboat_routing.runtime import OriginalSegment, SeniorModules


def rng_bytes(physics):
    return pickle.dumps((physics.random_state, physics.numpy_state))


def continuity_snapshot(physics):
    env, g = physics.env, physics.modules.globals
    return {
        "physical_state": env.state[:12].copy(),
        "global_physical_state": g.state[:12].copy(),
        "time": g.current_time,
        "dryden": (env.dryden_state_u, env.dryden_state_v),
        "dryden_parameters": copy.deepcopy(env.dryden_params),
        "wind": copy.deepcopy({name: getattr(g, name) for name in (
            "w0", "w_ini_v", "w_ini_d", "w_last_v", "w_last_d", "w_change_v", "w_change_d")}),
        "targets": (env.target_sail_angle, env.target_rudder_angle),
        "rng": rng_bytes(physics),
        "gym_rng": copy.deepcopy(env.np_random.bit_generator.state),
        "path": copy.deepcopy(g.path),
    }


class ContinuousPhysicsTests(unittest.TestCase):
    def make_physics(self, **kwargs):
        physics = ContinuousPhysics(SeniorModules(), **kwargs)
        self.addCleanup(physics.close)
        return physics

    def assert_snapshot_equal(self, before, after):
        np.testing.assert_array_equal(before.pop("physical_state"), after.pop("physical_state"))
        np.testing.assert_array_equal(before.pop("global_physical_state"), after.pop("global_physical_state"))
        self.assertEqual(before, after)

    def test_one_step_matches_original_without_noise(self):
        continuous = self.make_physics()
        original = OriginalSegment(SeniorModules(), noise_enabled=False)
        self.addCleanup(original.close)
        np.testing.assert_array_equal(continuous.reset(100, 90), original.reset(100, 90))
        command = np.array([0.413, -0.227], dtype=np.float32)
        actual = continuous.step(command)
        expected = original.step(command)
        np.testing.assert_array_equal(actual[0], expected[0])
        self.assertEqual(actual[1:4], expected[1:4])
        np.testing.assert_array_equal(actual[4]["physical_action"], expected[4]["physical_action"])
        self.assertEqual(actual[4]["physical_action"].dtype, np.float64)
        self.assertEqual(actual[4]["time"], expected[4]["time"])
        self.assertFalse(actual[4]["integration_failed"])
        self.assertEqual(rng_bytes(continuous), rng_bytes(original))
        self.assertEqual(continuous.env.target_sail_angle, original.env.target_sail_angle)
        self.assertEqual(continuous.env.target_rudder_angle, original.env.target_rudder_angle)
        self.assertEqual(continuous.env.dryden_state_u, original.env.dryden_state_u)
        self.assertEqual(continuous.env.dryden_state_v, original.env.dryden_state_v)

    def test_goal_change_preserves_all_physics_and_rng(self):
        physics = self.make_physics()
        physics.reset(123, -45)
        physics.step(np.array([0.35, -0.25], dtype=np.float32))
        before = continuity_snapshot(physics)
        public_before = json.dumps(physics.continuity_snapshot(), sort_keys=True)
        external = pickle.dumps((random.getstate(), np.random.get_state()))
        with patch.object(physics.env, "reset", side_effect=AssertionError("physical reset forbidden")):
            physics.set_goal([850.0, 210.0])
            after = continuity_snapshot(physics)
            self.assert_snapshot_equal(before, after)
            self.assertEqual(public_before, json.dumps(physics.continuity_snapshot(), sort_keys=True))
            self.assertEqual(external, pickle.dumps((random.getstate(), np.random.get_state())))
            np.testing.assert_array_equal(physics.env.state[12:14], [850.0, 210.0])
            np.testing.assert_array_equal(physics.modules.globals.state[12:14], [850.0, 210.0])
            np.testing.assert_array_equal(physics.raw[12:14], [850.0, 210.0])
            state, _, _, _, info = physics.step(np.zeros(2, dtype=np.float32))
        np.testing.assert_array_equal(state[12:14], [850.0, 210.0])
        self.assertEqual(info["time"], 2.0)

    def test_legacy_radius_and_time_no_longer_truncate_or_reset(self):
        physics = self.make_physics()
        physics.reset(100, 90)
        physics.env.state[0] = 800.0
        physics.modules.globals.state[0] = 800.0
        physics.modules.globals.current_time = 1001.0
        physics.set_goal([1300.0, 0.0])
        physics.env.target_sail_angle = 0.3
        physics.env.target_rudder_angle = -0.1
        before_position = physics.env.state[:2].copy()
        with patch.object(physics.env, "reset", side_effect=AssertionError("physical reset forbidden")):
            state, _, terminated, truncated, info = physics.step(np.zeros(2, dtype=np.float32))
        self.assertFalse(terminated)
        self.assertFalse(truncated)
        self.assertFalse(info["integration_failed"])
        self.assertTrue(info["legacy_radius_limit_reached"])
        self.assertTrue(info["legacy_time_limit_reached"])
        self.assertFalse(info["legacy_limits_enforced"])
        self.assertEqual(info["time"], 1002.0)
        self.assertGreater(state[0], 750.0)
        self.assertLess(np.linalg.norm(state[:2] - before_position), 10.0)
        self.assertEqual(physics.env.target_sail_angle, 0.3)
        self.assertEqual(physics.env.target_rudder_angle, -0.1)
        np.testing.assert_array_equal(state[12:14], [1300.0, 0.0])

    def test_wrapper_enforces_total_time_and_world_radius(self):
        for kwargs, flag in (
            ({"total_time_limit": 1}, "total_time_limit_reached"),
            ({"world_radius_limit": 750}, "world_radius_limit_reached"),
        ):
            with self.subTest(limit=flag):
                physics = self.make_physics(**kwargs)
                physics.reset(100, 90)
                if flag == "world_radius_limit_reached":
                    physics.env.state[0] = 800.0
                    physics.modules.globals.state[0] = 800.0
                    physics.set_goal([1300.0, 0.0])
                _, _, _, truncated, info = physics.step(np.zeros(2, dtype=np.float32))
                self.assertTrue(truncated)
                self.assertTrue(info[flag])
                self.assertFalse(info["integration_failed"])
                self.assertEqual(info["time"], 1.0)

    def test_goal_notification_can_continue_to_next_goal(self):
        physics = self.make_physics()
        state = physics.reset(100, 90)
        physics.set_goal(state[:2])
        with patch.object(physics.env, "reset", side_effect=AssertionError("physical reset forbidden")):
            _, _, reached, truncated, info = physics.step(np.zeros(2, dtype=np.float32))
            self.assertTrue(reached)
            self.assertTrue(info["goal_reached"])
            self.assertFalse(truncated)
            physics.set_goal([500.0, 100.0])
            _, _, reached, truncated, info = physics.step(np.zeros(2, dtype=np.float32))
        self.assertFalse(reached)
        self.assertFalse(truncated)
        self.assertEqual(info["time"], 2.0)

    def test_instances_isolate_python_and_numpy_random_streams(self):
        first = self.make_physics()
        second = self.make_physics()
        unrelated = self.make_physics()
        external = pickle.dumps((random.getstate(), np.random.get_state()))
        first.reset(234, 90)
        second.reset(234, 90)
        unrelated.reset(987, -120)
        self.assertEqual(external, pickle.dumps((random.getstate(), np.random.get_state())))
        for command in (np.array([0.2, -0.1]), np.array([-0.4, 0.3]), np.zeros(2)):
            a = first.step(command)
            unrelated.step(np.array([0.7, -0.6]))
            b = second.step(command)
            np.testing.assert_array_equal(a[0], b[0])
            self.assertEqual(a[1:4], b[1:4])
            self.assertEqual(rng_bytes(first), rng_bytes(second))
            self.assertEqual(external, pickle.dumps((random.getstate(), np.random.get_state())))


if __name__ == "__main__":
    unittest.main()
