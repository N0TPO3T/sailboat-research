import importlib.util
import random
import sys
import tempfile
import types
import unittest
from pathlib import Path

import gymnasium as gym
import numpy as np
import torch

import sailboat_rl
from sailboat_rl.algorithms.sac_lstm import ReplayBuffer
from sailboat_rl.algorithms.utils_fc import Actor as FCActor
from sailboat_rl.algorithms.utils_fc import Double_Q_Critic as FCCritic
from sailboat_rl.algorithms.utils_lstm import Actor as LSTMActor
from sailboat_rl.algorithms.utils_lstm import Double_Q_Critic as LSTMCritic
from sailboat_rl.evaluation import batch_eval


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_legacy_environment(filename: str, class_name: str):
    globals_path = REPO_ROOT / "gymnasium" / "envs" / "sailboat" / "globals.py"
    env_path = REPO_ROOT / "gymnasium" / "envs" / "sailboat" / filename

    globals_spec = importlib.util.spec_from_file_location(f"legacy_globals_{filename}", globals_path)
    globals_module = importlib.util.module_from_spec(globals_spec)
    globals_spec.loader.exec_module(globals_module)

    previous_globals = sys.modules.get("globals")
    previous_pygame = sys.modules.get("pygame")
    sys.modules["globals"] = globals_module
    if previous_pygame is None or not hasattr(previous_pygame, "time"):
        pygame_stub = types.ModuleType("pygame")
        pygame_stub.time = types.SimpleNamespace(Clock=lambda: None)
        sys.modules["pygame"] = pygame_stub
    try:
        env_spec = importlib.util.spec_from_file_location(f"legacy_env_{filename}", env_path)
        env_module = importlib.util.module_from_spec(env_spec)
        env_spec.loader.exec_module(env_module)
    finally:
        if previous_globals is None:
            del sys.modules["globals"]
        else:
            sys.modules["globals"] = previous_globals
        if previous_pygame is None:
            del sys.modules["pygame"]
        else:
            sys.modules["pygame"] = previous_pygame
    return getattr(env_module, class_name)


def one_step(env_class):
    random.seed(123)
    np.random.seed(123)
    env = env_class()
    observation, info = env.reset(seed=123)
    result = env.step(np.array([0.01, -0.01], dtype=np.float32))
    env.close()
    return np.asarray(observation).copy(), info, result


class EnvironmentTests(unittest.TestCase):
    def test_registered_environments_reset_and_step(self):
        for env_id, obs_dim in (("sailboat-s14-nowind", 14), ("sailboat-s14-wind", 16)):
            with self.subTest(env_id=env_id):
                env = gym.make(env_id)
                observation, info = env.reset(seed=7)
                self.assertEqual(observation.shape, (obs_dim,))
                self.assertEqual(env.action_space.shape, (2,))
                result = env.step(np.zeros(2, dtype=np.float32))
                self.assertEqual(len(result), 5)
                self.assertEqual(result[0].shape, (obs_dim,))
                self.assertIsInstance(result[4], dict)
                env.close()

    def test_extraction_matches_legacy_one_step(self):
        cases = (
            ("sailboat_s14.py", "Sailboat_nowind_last", "sailboat_rl.envs.sailboat_s14"),
            ("sailboat_s14_wind.py", "Sailboat_wind_last", "sailboat_rl.envs.sailboat_s14_wind"),
        )
        for filename, class_name, canonical_module_name in cases:
            with self.subTest(filename=filename):
                legacy_class = load_legacy_environment(filename, class_name)
                canonical_module = __import__(canonical_module_name, fromlist=[class_name])
                canonical_class = getattr(canonical_module, class_name)

                legacy_reset, legacy_info, legacy_step = one_step(legacy_class)
                canonical_reset, canonical_info, canonical_step = one_step(canonical_class)

                np.testing.assert_allclose(canonical_reset, legacy_reset, rtol=1e-6, atol=1e-6)
                np.testing.assert_allclose(canonical_step[0], legacy_step[0], rtol=1e-6, atol=1e-6)
                self.assertAlmostEqual(float(canonical_step[1]), float(legacy_step[1]), places=6)
                self.assertEqual(bool(canonical_step[2]), bool(legacy_step[2]))
                self.assertEqual(bool(canonical_step[3]), bool(legacy_step[3]))
                self.assertEqual(canonical_info, legacy_info)
                self.assertEqual(canonical_step[4], legacy_step[4])


class AlgorithmTests(unittest.TestCase):
    def test_fc_actor_and_critic_shapes(self):
        torch.manual_seed(3)
        actor = FCActor(14, 2, (32, 16, 8)).eval()
        critic = FCCritic(14, 2, (32, 16, 8), (32, 16, 8)).eval()
        state = torch.randn(4, 14)
        action, log_prob = actor(state, deterministic=False, with_logprob=True)
        q1, q2 = critic(state, action)
        self.assertEqual(action.shape, (4, 2))
        self.assertEqual(log_prob.shape, (4, 1))
        self.assertEqual(q1.shape, (4, 1))
        self.assertEqual(q2.shape, (4, 1))

    def test_lstm_forward_replay_and_hidden_reset(self):
        torch.manual_seed(5)
        actor = LSTMActor(14, 2, (32, 16)).eval()
        critic = LSTMCritic(14, 2, (32, 16), (32, 16)).eval()
        state_sequence = torch.randn(4, 10, 14)
        action_sequence = torch.randn(4, 10, 2)
        current_state = torch.randn(4, 14)

        action, log_prob = actor(
            state_sequence=state_sequence,
            action_sequence=action_sequence,
            current_state=current_state,
            deterministic=False,
            with_logprob=True,
        )
        q1, q2 = critic(
            state_sequence=state_sequence,
            action_sequence=action_sequence,
            current_state=current_state,
            current_action=action,
        )
        self.assertEqual(action.shape, (4, 2))
        self.assertEqual(log_prob.shape, (4, 1))
        self.assertEqual(q1.shape, (4, 1))
        self.assertEqual(q2.shape, (4, 1))

        actor(
            current_state=current_state[:1],
            deterministic=True,
            with_logprob=False,
            env_ids=["smoke"],
            single_step_mode=True,
            prev_state=current_state[:1],
            prev_action=torch.zeros(1, 2),
        )
        self.assertIn("smoke", actor.hidden_states)
        actor.reset_hidden_state("smoke")
        self.assertNotIn("smoke", actor.hidden_states)

        replay = ReplayBuffer(14, 2, 10, max_size=32, dvc=torch.device("cpu"))
        s_seq = np.zeros((10, 14), dtype=np.float32)
        a_seq = np.zeros((10, 2), dtype=np.float32)
        state = np.zeros(14, dtype=np.float32)
        act = np.zeros(2, dtype=np.float32)
        replay.add(s_seq, a_seq, state, act, 1.0, s_seq, a_seq, state, False)
        sample = replay.sample(1)
        self.assertEqual(sample[0].shape, (1, 10, 14))
        self.assertEqual(sample[1].shape, (1, 10, 2))
        self.assertEqual(sample[2].shape, (1, 14))
        self.assertEqual(sample[3].shape, (1, 2))


class EvaluationTests(unittest.TestCase):
    def test_protocol_and_missing_checkpoint_error(self):
        specs = batch_eval.load_model_specs(Path(batch_eval.__file__).with_name("seed_eval_models.csv"))
        args = batch_eval.parse_args([])
        scenarios = batch_eval.build_scenarios(args)
        self.assertEqual(len(specs), 6)
        self.assertEqual(sum(item.num_episodes for item in scenarios) * len(specs), 10800)

        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(FileNotFoundError, "missing actor checkpoint"):
                batch_eval.validate_checkpoints(Path(directory), specs[:1])


if __name__ == "__main__":
    unittest.main()
