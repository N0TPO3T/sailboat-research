import json
import random
import signal
import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch

from sailboat_rl.algorithms.sac_fc import SAC_fc_continuous
from sailboat_rl.algorithms.sac_lstm import SAC_lstm_countinuous
from sailboat_rl.noise_utils_nowind import NoiseManager
from sailboat_rl.training.runtime import (
    GracefulStop,
    load_training_checkpoint,
    prepare_run_manifest,
    save_training_checkpoint,
    seed_everything,
    trainer_state_dict,
)


def assert_nested_equal(testcase, actual, expected):
    testcase.assertEqual(type(actual), type(expected))
    if torch.is_tensor(actual):
        torch.testing.assert_close(actual, expected, rtol=0, atol=0)
    elif isinstance(actual, dict):
        testcase.assertEqual(actual.keys(), expected.keys())
        for key in actual:
            assert_nested_equal(testcase, actual[key], expected[key])
    elif isinstance(actual, (list, tuple)):
        testcase.assertEqual(len(actual), len(expected))
        for actual_item, expected_item in zip(actual, expected):
            assert_nested_equal(testcase, actual_item, expected_item)
    else:
        testcase.assertEqual(actual, expected)


def make_agent(agent_type, model_dir, per_backend="legacy"):
    common = dict(
        state_dim=14,
        action_dim=2,
        net_width=16,
        a_lr=5e-5,
        c_lr=5e-5,
        batch_size=8,
        alpha=0.2,
        adaptive_alpha=True,
        gamma=0.98,
        dvc=torch.device("cpu"),
        model_dir=str(model_dir),
        replay_capacity=32,
        per_backend=per_backend,
    )
    if agent_type == "fc":
        return SAC_fc_continuous(**common)
    return SAC_lstm_countinuous(**common)


def fill_replay(agent, agent_type):
    for index in range(16):
        state = np.full(14, index / 10.0, dtype=np.float32)
        next_state = state + 0.1
        action = np.array([0.1, -0.1], dtype=np.float32)
        reward = np.float32(index / 100.0)
        if agent_type == "fc":
            agent.replay_buffer.add(state, action, reward, next_state, False)
        else:
            state_sequence = np.repeat(state[None, :], 10, axis=0)
            action_sequence = np.repeat(action[None, :], 10, axis=0)
            next_state_sequence = np.repeat(next_state[None, :], 10, axis=0)
            agent.replay_buffer.add(
                state_sequence,
                action_sequence,
                state,
                action,
                reward,
                next_state_sequence,
                action_sequence,
                next_state,
                False,
            )
    for _ in range(4):
        info = agent.train()
        assert np.isfinite(info["q_loss"])


class ResumeCheckpointTests(unittest.TestCase):
    def check_agent_round_trip(self, agent_type, per_backend="legacy"):
        seed_everything(123)
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory) / "run"
            agent = make_agent(agent_type, Path(directory) / "models", per_backend)
            noise = NoiseManager(seed=123)
            fill_replay(agent, agent_type)
            self.assertEqual(agent.critic_update_count, 4)
            self.assertEqual(agent.actor_update_count, 1)
            self.assertEqual(agent.alpha_update_count, 1)
            expected_trainer = trainer_state_dict(agent)
            expected_replay = agent.replay_buffer.state_dict()

            checkpoint = save_training_checkpoint(
                agent,
                run_dir,
                total_steps=64,
                completed_episodes=3,
                noise_manager=noise,
                extra_counters={"nonfinite_transition_count": 0},
            )
            self.assertTrue((checkpoint / "trainer_state.pt").is_file())
            self.assertTrue((checkpoint / "replay_state.pt").is_file())
            self.assertTrue((checkpoint / "manifest.json").is_file())
            with (run_dir / "checkpoints" / "latest.json").open(encoding="utf-8") as handle:
                self.assertEqual(json.load(handle)["total_steps"], 64)

            expected_python = random.random()
            expected_numpy = np.random.random()
            expected_torch = torch.rand(3)
            expected_sensor = noise.sensor_noise.rng.rand()
            expected_actuator = noise.actuator_noise.rng.rand()
            expected_indices = agent.replay_buffer.sample(4)[-2].cpu()

            restored = make_agent(agent_type, Path(directory) / "models-restored", per_backend)
            restored_noise = NoiseManager(seed=999)
            counters = load_training_checkpoint(restored, run_dir, restored_noise)

            self.assertEqual(counters["total_steps"], 64)
            self.assertEqual(counters["completed_episodes"], 3)
            self.assertEqual(counters["extra_counters"]["nonfinite_transition_count"], 0)
            assert_nested_equal(self, trainer_state_dict(restored), expected_trainer)
            restored_replay = restored.replay_buffer.state_dict()
            assert_nested_equal(self, restored_replay, expected_replay)

            self.assertEqual(random.random(), expected_python)
            self.assertEqual(np.random.random(), expected_numpy)
            torch.testing.assert_close(torch.rand(3), expected_torch, rtol=0, atol=0)
            self.assertEqual(restored_noise.sensor_noise.rng.rand(), expected_sensor)
            self.assertEqual(restored_noise.actuator_noise.rng.rand(), expected_actuator)
            torch.testing.assert_close(restored.replay_buffer.sample(4)[-2].cpu(), expected_indices, rtol=0, atol=0)

            continued = restored.train()
            self.assertTrue(np.isfinite(continued["q_loss"]))
            self.assertEqual(restored.training_step, 5)
            self.assertEqual(restored.critic_update_count, 5)
            self.assertEqual(restored.actor_update_count, 1)
            self.assertEqual(restored.alpha_update_count, 1)

    def test_fc_training_resume_round_trip(self):
        self.check_agent_round_trip("fc")

    def test_lstm_training_resume_round_trip(self):
        self.check_agent_round_trip("lstm")

    def test_fc_optimized_per_resume_round_trip(self):
        self.check_agent_round_trip("fc", per_backend="optimized")

    def test_lstm_optimized_per_resume_round_trip(self):
        self.check_agent_round_trip("lstm", per_backend="optimized")

    def test_graceful_stop_handler_only_sets_flag(self):
        stop = GracefulStop()
        stop._handle(signal.SIGTERM, None)
        self.assertTrue(stop.requested)
        self.assertEqual(stop.signal_number, signal.SIGTERM)

    def test_run_manifest_rejects_resume_configuration_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            run_dir = repo_root / "run"
            source = repo_root / "source.py"
            source.write_text("pass\n", encoding="utf-8")
            config = {
                "replay_capacity": 32,
                "batch_size": 8,
                "num_envs": 2,
                "strict_deterministic": False,
            }
            manifest_path = prepare_run_manifest(
                run_dir=run_dir,
                repo_root=repo_root,
                model_family="SAC-nowind",
                environment_id="test-env",
                model_prefix="test-run",
                master_seed=123,
                config=config,
                device=torch.device("cpu"),
                source_paths=[source],
                resume_source=None,
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(list(manifest["source_sha256"]), ["source.py"])

            checkpoint = run_dir / "checkpoints" / "step_000000000064"
            checkpoint.mkdir(parents=True)
            (checkpoint / "trainer_state.pt").touch()
            drifted_config = dict(config, batch_size=16)
            with self.assertRaisesRegex(ValueError, "batch_size"):
                prepare_run_manifest(
                    run_dir=run_dir,
                    repo_root=repo_root,
                    model_family="SAC-nowind",
                    environment_id="test-env",
                    model_prefix="test-run",
                    master_seed=123,
                    config=drifted_config,
                    device=torch.device("cpu"),
                    source_paths=[source],
                    resume_source=checkpoint,
                )


if __name__ == "__main__":
    unittest.main()
