import copy
import unittest
from types import MethodType

import torch

from sailboat_rl.algorithms.utils_lstm import Actor, Double_Q_Critic


STATE_DIM = 14
ACTION_DIM = 2
HIDDEN = 16
SEQ_LEN = 10


def add_repeated_flatten_hooks(module):
    handles = []
    for child in module.modules():
        if isinstance(child, torch.nn.LSTM):
            handles.append(child.register_forward_pre_hook(lambda lstm, _inputs: lstm.flatten_parameters()))
    return handles


def make_actor():
    return Actor(STATE_DIM, ACTION_DIM, (HIDDEN, HIDDEN), dropout_prob=0.05).eval()


def make_critic():
    return Double_Q_Critic(
        STATE_DIM,
        ACTION_DIM,
        (HIDDEN, HIDDEN),
        (HIDDEN, HIDDEN),
        dropout_prob=0.05,
    ).eval()


def actor_inputs(batch=4):
    generator = torch.Generator().manual_seed(101)
    return (
        torch.randn(batch, SEQ_LEN, STATE_DIM, generator=generator),
        torch.randn(batch, SEQ_LEN, ACTION_DIM, generator=generator),
        torch.randn(batch, STATE_DIM, generator=generator),
    )


def critic_inputs(batch=4):
    state_sequence, action_sequence, current_state = actor_inputs(batch)
    generator = torch.Generator().manual_seed(202)
    current_action = torch.randn(batch, ACTION_DIM, generator=generator)
    return state_sequence, action_sequence, current_state, current_action


def capture_actor_outputs(actor, *inputs):
    captured = {}
    mu_handle = actor.mu_layer.register_forward_hook(
        lambda _module, _args, output: captured.__setitem__("mu", output.detach().clone())
    )
    log_std_handle = actor.log_std_layer.register_forward_hook(
        lambda _module, _args, output: captured.__setitem__(
            "log_std", output.detach().clamp(actor.LOG_STD_MIN, actor.LOG_STD_MAX).clone()
        )
    )
    try:
        action, _ = actor(
            state_sequence=inputs[0],
            action_sequence=inputs[1],
            current_state=inputs[2],
            deterministic=True,
            with_logprob=False,
        )
    finally:
        mu_handle.remove()
        log_std_handle.remove()
    return captured["mu"], captured["log_std"], action


class LSTMFlattenRegressionTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(7)

    def test_actor_outputs_and_persistent_hidden_match_repeated_flatten(self):
        optimized = make_actor()
        baseline = copy.deepcopy(optimized)
        handles = add_repeated_flatten_hooks(baseline)
        inputs = actor_inputs()

        baseline_outputs = capture_actor_outputs(baseline, *inputs)
        optimized_outputs = capture_actor_outputs(optimized, *inputs)
        for actual, expected in zip(optimized_outputs, baseline_outputs):
            torch.testing.assert_close(actual, expected, rtol=0, atol=0)

        env_ids = list(range(inputs[2].shape[0]))
        initial_hidden = {
            env_id: (
                torch.full((1, HIDDEN), (env_id + 1) / 100.0),
                torch.full((1, HIDDEN), -(env_id + 1) / 100.0),
            )
            for env_id in env_ids
        }
        baseline.hidden_states = copy.deepcopy(initial_hidden)
        optimized.hidden_states = copy.deepcopy(initial_hidden)
        kwargs = dict(
            current_state=inputs[2],
            deterministic=True,
            env_ids=env_ids,
            single_step_mode=True,
            prev_state=inputs[0][:, -1],
            prev_action=inputs[1][:, -1],
        )
        baseline_action, _ = baseline(**kwargs)
        optimized_action, _ = optimized(**kwargs)
        torch.testing.assert_close(optimized_action, baseline_action, rtol=0, atol=0)
        for env_id in env_ids:
            for actual, expected in zip(optimized.hidden_states[env_id], baseline.hidden_states[env_id]):
                torch.testing.assert_close(actual, expected, rtol=0, atol=0)

        for handle in handles:
            handle.remove()

    def test_online_and_target_critic_outputs_match_repeated_flatten(self):
        optimized = make_critic()
        baseline = copy.deepcopy(optimized)
        target_optimized = copy.deepcopy(optimized)
        target_baseline = copy.deepcopy(optimized)
        handles = add_repeated_flatten_hooks(baseline) + add_repeated_flatten_hooks(target_baseline)
        inputs = critic_inputs()

        for repeated, lifecycle in ((baseline, optimized), (target_baseline, target_optimized)):
            repeated_q = repeated(
                state_sequence=inputs[0],
                action_sequence=inputs[1],
                current_state=inputs[2],
                current_action=inputs[3],
            )
            lifecycle_q = lifecycle(
                state_sequence=inputs[0],
                action_sequence=inputs[1],
                current_state=inputs[2],
                current_action=inputs[3],
            )
            for actual, expected in zip(lifecycle_q, repeated_q):
                torch.testing.assert_close(actual, expected, rtol=0, atol=0)

        for handle in handles:
            handle.remove()

    def test_actor_and_critic_gradients_match_repeated_flatten(self):
        actor_optimized = make_actor()
        actor_baseline = copy.deepcopy(actor_optimized)
        critic_optimized = make_critic()
        critic_baseline = copy.deepcopy(critic_optimized)
        handles = add_repeated_flatten_hooks(actor_baseline) + add_repeated_flatten_hooks(critic_baseline)

        actor_batch = actor_inputs()
        for actor in (actor_baseline, actor_optimized):
            action, log_prob = actor(
                state_sequence=actor_batch[0],
                action_sequence=actor_batch[1],
                current_state=actor_batch[2],
                deterministic=True,
                with_logprob=True,
            )
            (action.square().mean() + 0.1 * log_prob.mean()).backward()
        for baseline_param, optimized_param in zip(actor_baseline.parameters(), actor_optimized.parameters()):
            torch.testing.assert_close(optimized_param.grad, baseline_param.grad, rtol=0, atol=0)

        critic_batch = critic_inputs()
        for critic in (critic_baseline, critic_optimized):
            q1, q2 = critic(
                state_sequence=critic_batch[0],
                action_sequence=critic_batch[1],
                current_state=critic_batch[2],
                current_action=critic_batch[3],
            )
            (q1.square().mean() + q2.square().mean()).backward()
        for baseline_param, optimized_param in zip(critic_baseline.parameters(), critic_optimized.parameters()):
            torch.testing.assert_close(optimized_param.grad, baseline_param.grad, rtol=0, atol=0)

        for handle in handles:
            handle.remove()

    def test_optimizer_steps_match_repeated_flatten(self):
        actor_optimized = make_actor()
        actor_baseline = copy.deepcopy(actor_optimized)
        critic_optimized = make_critic()
        critic_baseline = copy.deepcopy(critic_optimized)
        handles = add_repeated_flatten_hooks(actor_baseline) + add_repeated_flatten_hooks(critic_baseline)
        optimizers = {
            "actor_baseline": torch.optim.Adam(actor_baseline.parameters(), lr=1e-4),
            "actor_optimized": torch.optim.Adam(actor_optimized.parameters(), lr=1e-4),
            "critic_baseline": torch.optim.Adam(critic_baseline.parameters(), lr=1e-4),
            "critic_optimized": torch.optim.Adam(critic_optimized.parameters(), lr=1e-4),
        }
        actor_batch = actor_inputs()
        critic_batch = critic_inputs()

        for _ in range(20):
            for name, actor in (("actor_baseline", actor_baseline), ("actor_optimized", actor_optimized)):
                optimizer = optimizers[name]
                optimizer.zero_grad()
                action, log_prob = actor(
                    state_sequence=actor_batch[0],
                    action_sequence=actor_batch[1],
                    current_state=actor_batch[2],
                    deterministic=True,
                    with_logprob=True,
                )
                (action.square().mean() + 0.1 * log_prob.mean()).backward()
                optimizer.step()
            for name, critic in (("critic_baseline", critic_baseline), ("critic_optimized", critic_optimized)):
                optimizer = optimizers[name]
                optimizer.zero_grad()
                q1, q2 = critic(
                    state_sequence=critic_batch[0],
                    action_sequence=critic_batch[1],
                    current_state=critic_batch[2],
                    current_action=critic_batch[3],
                )
                (q1.square().mean() + q2.square().mean()).backward()
                optimizer.step()

        for baseline_param, optimized_param in zip(actor_baseline.parameters(), actor_optimized.parameters()):
            torch.testing.assert_close(optimized_param, baseline_param, rtol=0, atol=0)
        for baseline_param, optimized_param in zip(critic_baseline.parameters(), critic_optimized.parameters()):
            torch.testing.assert_close(optimized_param, baseline_param, rtol=0, atol=0)

        for handle in handles:
            handle.remove()

    def test_standard_lifecycle_reflattens_only_on_tensor_identity_changes(self):
        actor = make_actor()
        calls = 0
        original = actor.lstm.flatten_parameters

        def counted(self):
            nonlocal calls
            calls += 1
            return original()

        actor.lstm.flatten_parameters = MethodType(counted, actor.lstm)
        inputs = actor_inputs()

        capture_actor_outputs(actor, *inputs)
        self.assertEqual(calls, 0)

        optimizer = torch.optim.SGD(actor.parameters(), lr=1e-4)
        optimizer.zero_grad()
        action, _ = actor(
            state_sequence=inputs[0],
            action_sequence=inputs[1],
            current_state=inputs[2],
            deterministic=True,
        )
        action.square().mean().backward()
        optimizer.step()
        capture_actor_outputs(actor, *inputs)
        self.assertEqual(calls, 0)

        state = copy.deepcopy(actor.state_dict())
        actor.load_state_dict(state)
        capture_actor_outputs(actor, *inputs)
        self.assertEqual(calls, 0)

        actor.to(dtype=torch.float64)
        self.assertGreaterEqual(calls, 1)
        actor.to(dtype=torch.float32)
        self.assertGreaterEqual(calls, 2)


if __name__ == "__main__":
    unittest.main()
