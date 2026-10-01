import unittest

import numpy as np
import torch

from sailboat_rl.algorithms.per_sampling import optimized_priority_distribution
from sailboat_rl.algorithms.sac_fc import ReplayBuffer as FCReplayBuffer
from sailboat_rl.algorithms.sac_lstm import ReplayBuffer as LSTMReplayBuffer


def add_fc_entries(replay, count):
    for index in range(count):
        state = np.full(14, index, dtype=np.float32)
        action = np.array([0.1, -0.1], dtype=np.float32)
        replay.add(state, action, float(index), state + 1, False)


def add_lstm_entries(replay, count):
    for index in range(count):
        state = np.full(14, index, dtype=np.float32)
        action = np.array([0.1, -0.1], dtype=np.float32)
        state_sequence = np.repeat(state[None, :], 10, axis=0)
        action_sequence = np.repeat(action[None, :], 10, axis=0)
        replay.add(
            state_sequence,
            action_sequence,
            state,
            action,
            float(index),
            state_sequence + 1,
            action_sequence,
            state + 1,
            False,
        )


class OptimizedPERSamplingTests(unittest.TestCase):
    def test_default_backend_is_optimized(self):
        fc = FCReplayBuffer(14, 2, max_size=1, dvc=torch.device("cpu"))
        lstm = LSTMReplayBuffer(14, 2, 10, max_size=1, dvc=torch.device("cpu"))
        self.assertEqual(fc.per_backend, "optimized")
        self.assertEqual(lstm.per_backend, "optimized")

    def test_probability_and_finite_fallback_match_legacy_definition(self):
        cases = (
            torch.ones(32),
            torch.logspace(-8, 3, 100),
            torch.tensor([0.1, 0.1, 0.1, 2.0, 100.0]),
        )
        for priorities in cases:
            with self.subTest(size=priorities.numel()):
                scaled, total = optimized_priority_distribution(priorities, 1e-6, 0.6)
                actual = scaled / total
                expected = (priorities + 1e-6).pow(0.6)
                expected = expected / expected.sum()
                torch.testing.assert_close(actual, expected, rtol=1e-6, atol=1e-8)

        invalid = torch.tensor([1.0, float("nan"), 2.0])
        scaled, total = optimized_priority_distribution(invalid, 1e-6, 0.6)
        torch.testing.assert_close(scaled / total, torch.full((3,), 1 / 3), rtol=0, atol=0)

    def test_replacement_importance_weights_and_priority_updates(self):
        torch.manual_seed(17)
        optimized = FCReplayBuffer(14, 2, max_size=8, dvc=torch.device("cpu"), per_backend="optimized")
        legacy = FCReplayBuffer(14, 2, max_size=8, dvc=torch.device("cpu"), per_backend="legacy")
        add_fc_entries(optimized, 8)
        add_fc_entries(legacy, 8)
        priorities = torch.tensor([0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 10.0]).view(-1, 1)
        optimized.priorities.copy_(priorities)
        legacy.priorities.copy_(priorities)

        saw_duplicate = False
        for _ in range(50):
            sample = optimized.sample(8)
            indices, weights = sample[-2:]
            if torch.unique(indices).numel() < indices.numel():
                saw_duplicate = True
            probabilities = (priorities.flatten() + optimized.epsilon).pow(optimized.alpha)
            probabilities = probabilities / probabilities.sum()
            expected = (optimized.size * probabilities[indices]).pow(-optimized.beta).view(-1, 1)
            expected = expected / expected.max()
            torch.testing.assert_close(weights, expected, rtol=1e-6, atol=1e-7)
        self.assertTrue(saw_duplicate)

        duplicate_indices = torch.tensor([1, 1, 3])
        new_priorities = torch.tensor([2.0, 5.0, 7.0])
        optimized.update_priorities(duplicate_indices, new_priorities)
        legacy.update_priorities(duplicate_indices, new_priorities)
        torch.testing.assert_close(optimized.priorities, legacy.priorities, rtol=0, atol=0)
        self.assertTrue(torch.isfinite(optimized.priorities).all())

    def test_fc_lstm_shapes_and_v1_state_rebuild(self):
        fc = FCReplayBuffer(14, 2, max_size=16, dvc=torch.device("cpu"), per_backend="optimized")
        add_fc_entries(fc, 12)
        fc_batch = fc.sample(8)
        expected_fc_shapes = ((8, 14), (8, 2), (8, 1), (8, 14), (8, 1), (8,), (8, 1))
        self.assertEqual(tuple(tuple(item.shape) for item in fc_batch), expected_fc_shapes)
        self.assertTrue(all(item.device.type == "cpu" for item in fc_batch))
        self.assertEqual(fc_batch[4].dtype, torch.bool)
        self.assertEqual(fc_batch[5].dtype, torch.int64)

        lstm = LSTMReplayBuffer(
            14, 2, 10, max_size=16, dvc=torch.device("cpu"), per_backend="optimized"
        )
        add_lstm_entries(lstm, 12)
        lstm_batch = lstm.sample(8)
        expected_lstm_shapes = (
            (8, 10, 14), (8, 10, 2), (8, 14), (8, 2), (8, 1),
            (8, 10, 14), (8, 10, 2), (8, 14), (8, 1), (8,), (8, 1),
        )
        self.assertEqual(tuple(tuple(item.shape) for item in lstm_batch), expected_lstm_shapes)
        self.assertTrue(all(item.device.type == "cpu" for item in lstm_batch))
        self.assertEqual(lstm_batch[8].dtype, torch.bool)
        self.assertEqual(lstm_batch[9].dtype, torch.int64)

        v1_state = fc.state_dict()
        del v1_state["per_backend"]
        restored = FCReplayBuffer(
            14, 2, max_size=16, dvc=torch.device("cpu"), per_backend="optimized"
        )
        restored.load_state_dict(v1_state)
        self.assertEqual(restored.size, fc.size)
        self.assertEqual(restored.ptr, fc.ptr)
        torch.testing.assert_close(restored.priorities, fc.priorities, rtol=0, atol=0)
        self.assertTrue(torch.isfinite(restored.sample(8)[-1]).all())


if __name__ == "__main__":
    unittest.main()
