import copy
import tempfile
import unittest
from collections import deque
from pathlib import Path

import numpy as np
import torch

from sailboat_rl.algorithms.sac_fc import SAC_fc_continuous
from sailboat_rl.algorithms.sac_lstm import SAC_lstm_countinuous
from sailboat_rl.noise_utils_nowind import NoiseManager
from sailboat_rl.training.runtime import (
    load_training_checkpoint,
    prepare_run_manifest,
    save_training_checkpoint,
    seed_everything,
)
from sailboat_rl.training.train_sac_lstm import reset_recurrent_environment


def make_agent(agent_type, model_dir):
    options = dict(
        state_dim=14,
        action_dim=2,
        net_width=16,
        a_lr=5e-5,
        c_lr=5e-5,
        batch_size=8,
        alpha=0.2,
        adaptive_alpha=True,
        gamma=0.98,
        dvc=torch.device('cpu'),
        model_dir=str(model_dir),
        replay_capacity=32,
        per_backend='optimized',
        actor_inference_backend='batched',
    )
    if agent_type == 'fc':
        return SAC_fc_continuous(**options)
    return SAC_lstm_countinuous(**options)


def set_distinct_hidden(actor, env_ids):
    actor.hidden_states = {
        env_id: (
            torch.full((1, actor.hidden_size), (index + 1) / 100.0),
            torch.full((1, actor.hidden_size), -(index + 1) / 100.0),
        )
        for index, env_id in enumerate(env_ids)
    }


def fill_replay(agent, agent_type):
    for index in range(16):
        state = np.full(14, index / 10.0, dtype=np.float32)
        next_state = state + 0.1
        action = np.array([0.1, -0.1], dtype=np.float32)
        if agent_type == 'fc':
            agent.replay_buffer.add(state, action, 0.1, next_state, False)
        else:
            state_sequence = np.repeat(state[None], 10, axis=0)
            action_sequence = np.repeat(action[None], 10, axis=0)
            next_state_sequence = np.repeat(next_state[None], 10, axis=0)
            agent.replay_buffer.add(
                state_sequence, action_sequence, state, action, 0.1,
                next_state_sequence, action_sequence, next_state, False,
            )
    for _ in range(4):
        info = agent.train()
        assert np.isfinite(info['q_loss'])


class BatchedActorInferenceTests(unittest.TestCase):
    def setUp(self):
        seed_everything(123)
        rng = np.random.default_rng(123)
        self.states = rng.normal(size=(15, 14)).astype(np.float32)
        self.prev_states = rng.normal(size=(15, 14)).astype(np.float32)
        self.prev_actions = rng.uniform(-1, 1, size=(15, 2)).astype(np.float32)
        self.env_ids = list(range(15))

    def test_fc_serial_and_batched_deterministic_equivalence(self):
        agent = make_agent('fc', '.')
        agent.actor.eval()
        serial = agent.select_actions(self.states, True, backend='serial')
        batched = agent.select_actions(self.states, True, backend='batched')

        self.assertEqual(serial.shape, (15, 2))
        self.assertTrue(np.isfinite(batched).all())
        np.testing.assert_allclose(serial, batched, rtol=1e-5, atol=1e-6)

        with_nonfinite = self.states.copy()
        with_nonfinite[7, 0] = np.nan
        action = agent.select_actions(with_nonfinite, True, backend='batched')
        np.testing.assert_array_equal(action[7], np.zeros(2, dtype=np.float32))

    def test_lstm_serial_and_batched_hidden_equivalence(self):
        base = make_agent('lstm', '.')
        base.actor.eval()
        set_distinct_hidden(base.actor, self.env_ids)
        serial_agent = copy.deepcopy(base)
        batched_agent = copy.deepcopy(base)

        serial = serial_agent.select_actions(
            self.prev_states, self.prev_actions, self.states, True, 100, self.env_ids, 'serial'
        )
        batched = batched_agent.select_actions(
            self.prev_states, self.prev_actions, self.states, True, 100, self.env_ids, 'batched'
        )

        np.testing.assert_allclose(serial, batched, rtol=1e-5, atol=1e-6)
        for env_id in self.env_ids:
            for serial_state, batched_state in zip(
                serial_agent.actor.hidden_states[env_id],
                batched_agent.actor.hidden_states[env_id],
            ):
                torch.testing.assert_close(serial_state, batched_state, rtol=1e-5, atol=1e-6)

    def test_lstm_done_reset_is_isolated(self):
        agent = make_agent('lstm', '.')
        agent.actor.eval()
        set_distinct_hidden(agent.actor, self.env_ids)
        state_buffers = [deque([self.states[i].copy()] * 10, maxlen=10) for i in self.env_ids]
        action_buffers = [deque([self.prev_actions[i].copy()] * 10, maxlen=10) for i in self.env_ids]
        prev_states = [state.copy() for state in self.prev_states]
        prev_actions = [action.copy() for action in self.prev_actions]
        untouched_hidden = {
            env_id: tuple(value.clone() for value in agent.actor.hidden_states[env_id])
            for env_id in self.env_ids
        }

        for env_id in (2, 7, 13):
            reset_recurrent_environment(
                agent,
                state_buffers,
                action_buffers,
                prev_states,
                prev_actions,
                env_id,
                self.states[env_id],
                2,
                10,
            )

        for env_id in (2, 7, 13):
            self.assertNotIn(env_id, agent.actor.hidden_states)
            self.assertTrue(all(np.array_equal(item, self.states[env_id]) for item in state_buffers[env_id]))
            self.assertTrue(all(np.array_equal(item, np.zeros(2)) for item in action_buffers[env_id]))
        for env_id in set(self.env_ids) - {2, 7, 13}:
            for actual, expected in zip(agent.actor.hidden_states[env_id], untouched_hidden[env_id]):
                torch.testing.assert_close(actual, expected, rtol=0, atol=0)

        explicit_zero_agent = copy.deepcopy(agent)
        for env_id in (2, 7, 13):
            explicit_zero_agent.actor.hidden_states[env_id] = (
                torch.zeros(1, agent.actor.hidden_size),
                torch.zeros(1, agent.actor.hidden_size),
            )
        implicit = agent.select_actions(
            prev_states, prev_actions, self.states, True, 101, self.env_ids, 'batched'
        )
        explicit = explicit_zero_agent.select_actions(
            prev_states, prev_actions, self.states, True, 101, self.env_ids, 'batched'
        )
        np.testing.assert_allclose(implicit, explicit, rtol=0, atol=0)

    def test_policy_distribution_parameters_and_train_mode(self):
        agent = make_agent('fc', '.')
        captured = []

        def capture(_module, _inputs, output):
            captured.append(output.detach().clone())

        mu_hook = agent.actor.mu_layer.register_forward_hook(capture)
        log_std_hook = agent.actor.log_std_layer.register_forward_hook(capture)
        try:
            agent.actor.eval()
            agent.select_actions(self.states, True, backend='serial')
            serial_mu = torch.cat(captured[0::2])
            serial_log_std = torch.cat(captured[1::2])
            captured.clear()
            agent.select_actions(self.states, True, backend='batched')
            batched_mu, batched_log_std = captured
        finally:
            mu_hook.remove()
            log_std_hook.remove()

        torch.testing.assert_close(serial_mu, batched_mu, rtol=1e-5, atol=1e-6)
        torch.testing.assert_close(serial_log_std, batched_log_std, rtol=1e-5, atol=1e-6)

        agent.actor.train()
        stochastic = agent.select_actions(self.states, False, backend='batched')
        self.assertEqual(stochastic.shape, (15, 2))
        self.assertTrue(np.isfinite(stochastic).all())
        dropout_probabilities = [module.p for module in agent.actor.modules() if isinstance(module, torch.nn.Dropout)]
        self.assertEqual(dropout_probabilities, [0.05, 0.05])

    def test_batched_checkpoint_rng_resume(self):
        for agent_type in ('fc', 'lstm'):
            with self.subTest(agent_type=agent_type), tempfile.TemporaryDirectory() as directory:
                seed_everything(456)
                run_dir = Path(directory) / 'run'
                agent = make_agent(agent_type, Path(directory) / 'model')
                noise = NoiseManager(seed=456)
                fill_replay(agent, agent_type)
                save_training_checkpoint(agent, run_dir, 64, 0, noise)
                if agent_type == 'fc':
                    expected = agent.select_actions(self.states, False, backend='batched')
                else:
                    expected = agent.select_actions(
                        self.prev_states, self.prev_actions, self.states, False, 0, self.env_ids, 'batched'
                    )

                restored = make_agent(agent_type, Path(directory) / 'restored')
                resumed = load_training_checkpoint(restored, run_dir, NoiseManager(seed=999))
                self.assertEqual(resumed['total_steps'], 64)
                self.assertEqual(restored.training_step, 4)
                self.assertEqual(restored.replay_buffer.size, 16)
                if agent_type == 'fc':
                    actual = restored.select_actions(self.states, False, backend='batched')
                else:
                    actual = restored.select_actions(
                        self.prev_states, self.prev_actions, self.states, False, 0, self.env_ids, 'batched'
                    )
                np.testing.assert_allclose(actual, expected, rtol=0, atol=0)
                continued = restored.train()
                self.assertTrue(np.isfinite(continued['q_loss']))
                self.assertEqual(restored.training_step, 5)

    def test_legacy_manifest_requires_explicit_serial_backend(self):
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            run_dir = repo_root / 'run'
            source = repo_root / 'source.py'
            source.write_text('pass\n', encoding='utf-8')
            legacy_config = {'replay_capacity': 32, 'num_envs': 15, 'batch_size': 8}
            prepare_run_manifest(
                run_dir, repo_root, 'SAC-nowind', 'test-env', 'test-run', 0,
                legacy_config, torch.device('cpu'), [source], None,
            )
            checkpoint = run_dir / 'checkpoints' / 'step_000000000001'
            checkpoint.mkdir(parents=True)
            (checkpoint / 'trainer_state.pt').touch()

            prepare_run_manifest(
                run_dir, repo_root, 'SAC-nowind', 'test-env', 'test-run', 0,
                dict(legacy_config, actor_inference_backend='serial'),
                torch.device('cpu'), [source], checkpoint,
            )
            with self.assertRaisesRegex(ValueError, 'actor_inference_backend'):
                prepare_run_manifest(
                    run_dir, repo_root, 'SAC-nowind', 'test-env', 'test-run', 0,
                    dict(legacy_config, actor_inference_backend='batched'),
                    torch.device('cpu'), [source], checkpoint,
                )


if __name__ == '__main__':
    unittest.main()
