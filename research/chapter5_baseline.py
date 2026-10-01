"""Bounded Stage-1 witness for the unmodified chapter-5 Attention-SAC-LSTM.

Static-only training is explicitly selected and bounded to 50k steps. No dynamic
obstacles or chapter-4 imports. Without a matching checkpoint, probe rollouts are
random-initialization interface diagnostics, not a baseline.
Outputs are exclusive-created so an earlier receipt cannot be overwritten.
"""
import argparse
import ast
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import sys
import time

os.environ.setdefault('CUDA_VISIBLE_DEVICES', '')
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
sys.dont_write_bytecode = True

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / 'sailboat_RL/PART5/SAC-LSTM-att'
ENV_FILE = ROOT / 'sailboat_RL/gymnasium/envs/sailboat/sailboat_s14_obst_V3.py'
sys.path.insert(0, str(REFERENCE))
import globals as ref_globals
from utils_lstm_att_normal import Actor, Double_Q_Critic, ZScoreNormalizer

torch.set_num_threads(1)


def load_environment():
    spec = importlib.util.spec_from_file_location('chapter5_static_reference', ENV_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Sailboat_obst_v3(render_mode=None)


def reset(env, seed, obstacles=None):
    # The reference reset does not seed Python random or global NumPy.
    random.seed(seed)
    np.random.seed(seed)
    obs, _ = env.reset(seed=seed)
    if obstacles is not None:
        ref_globals.obstacles = list(obstacles)
        ref_globals.observed_obstacles = []
        env.state[14:] = 0
        ref_globals.state[14:] = 0
    return obs.copy()


def interface_checks(env):
    result = {}
    obs = reset(env, 101)
    assert obs.shape == (18,) and env.action_space.shape == (2,)
    np.testing.assert_allclose(env.action_space.high, np.pi / 18)
    result['observation_action_shape'] = 'PASS: 18D, 2D, +/-pi/18'
    ref_globals.obstacles = [(100., 0.), (100., 100.), (-80., 0.), (151., 0.)]
    detected = env._detect_obstacles_in_fov(0., 0., 0.)
    assert [(x, y) for x, y, _ in detected] == [(100., 0.), (100., 100.)]
    result['fov_range'] = 'PASS: front 120 degrees and 150m'
    ref_globals.observed_obstacles = [(100., 0.), (30., 0.), (-20., 0.), (151., 0.)]
    nearest = env._get_two_nearest_obstacles(0., 0., 0.)
    np.testing.assert_allclose([nearest[0][0], nearest[1][0]], [20., 30.])
    result['nearest_two_and_out_of_fov_memory'] = {
        'status': 'PASS', 'distances': [20., 30.],
        'meaning': 'cached target behind vessel is still returned; no FOV refilter',
    }
    # Execute original step's termination block, with distances chosen exactly.
    tree = ast.parse(ENV_FILE.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
    step = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'step')
    nodes = [n for n in step.body if 648 <= n.lineno <= 662]
    assert len(nodes) == 3, 'Reference changed: inspect termination block before reusing witness'
    import math
    flags = []
    for distance in (39.99, 40., 40.01):
        ref_globals.current_state = np.zeros(12)
        ref_globals.current_time = 1
        ref_globals.obstacles = [(distance, 0.)]
        scope = dict(globals=ref_globals, math=math, dis_to_yuandian=0.)
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(ENV_FILE), 'exec'), scope)
        flags.append(bool(scope['truncated']))
    assert flags == [True, False, False]
    result['original_termination_block'] = {'distances': [39.99, 40., 40.01], 'truncated': flags}
    # Reward comparison resets milestone flags; only obstacle distance changes.
    def reward_at(distance):
        reset(env, 101, [])
        ref_globals.current_state = np.zeros(12)
        ref_globals.current_action = np.zeros(2)
        ref_globals.state = env.state.copy()
        env.state[14] = distance
        return float(env.calculate_reward(np.zeros(12), False))
    base = reward_at(0.)
    penalties = {str(d): reward_at(d) - base for d in (40., 60., 100., 149., 150.)}
    np.testing.assert_allclose(penalties['40.0'], -1.)
    np.testing.assert_allclose(penalties['60.0'], -np.exp(-1))
    np.testing.assert_allclose(penalties['150.0'], 0.)
    result['obstacle_reward_delta'] = penalties
    first = reset(env, 123).copy()
    first_next = env.step(np.zeros(2))[0].copy()
    second = reset(env, 123).copy()
    second_next = env.step(np.zeros(2))[0].copy()
    np.testing.assert_array_equal(first, second)
    np.testing.assert_array_equal(first_next, second_next)
    result['seeded_reset_step'] = 'PASS with explicit Python/NumPy seeds'
    return result


def network_checks(actor, critic):
    actor.eval(); critic.eval()
    generator = torch.Generator().manual_seed(991)
    states = torch.randn(1, 12, 18, generator=generator)
    actions = torch.randn(1, 12, 2, generator=generator).tanh()
    current = torch.randn(1, 18, generator=generator)
    seen = []
    hook = actor.attention.register_forward_hook(lambda m, i, o: seen.append(o[1].detach().clone()))
    with torch.no_grad():
        seq, _ = actor(state_sequence=states[:, :10], action_sequence=actions[:, :10],
                       current_state=current, deterministic=True)
        q1, q2 = critic(state_sequence=states[:, :10], action_sequence=actions[:, :10],
                        current_state=current, current_action=actions[:, 0])
        assert seq.shape == (1, 2) and q1.shape == q2.shape == (1, 1)
        assert all(torch.isfinite(x).all() for x in (seq, q1, q2))
        assert seen[-1].shape == (1, 10)
        torch.testing.assert_close(seen[-1].sum(1), torch.ones(1))
        actor.reset_hidden_state()
        for t in range(10):
            stream, _ = actor(current_state=current, prev_state=states[:, t],
                              prev_action=actions[:, t], single_step_mode=True,
                              deterministic=True, env_ids=['witness'])
        torch.testing.assert_close(stream, seq, atol=2e-6, rtol=2e-5)
        prefix_error = float((stream - seq).abs().max())
        for t in range(10, 12):
            stream, _ = actor(current_state=current, prev_state=states[:, t],
                              prev_action=actions[:, t], single_step_mode=True,
                              deterministic=True, env_ids=['witness'])
        window, _ = actor(state_sequence=states[:, 2:], action_sequence=actions[:, 2:],
                         current_state=current, deterministic=True)
        long_error = float((stream - window).abs().max())
        # Selective reset removes both h/c and attention-output history, preserves peers.
        actor(current_state=current, prev_state=states[:, 0], prev_action=actions[:, 0],
              single_step_mode=True, deterministic=True, env_ids=['peer'])
        actor.reset_hidden_state('witness')
        assert 'witness' not in actor.hidden_states and 'witness' not in actor.lstm_output_history
        assert 'peer' in actor.hidden_states
        def first_action():
            actor.reset_hidden_state('witness')
            return actor(current_state=current, prev_state=states[:, 0], prev_action=actions[:, 0],
                         single_step_mode=True, deterministic=True, env_ids=['witness'])[0]
        torch.testing.assert_close(first_action(), first_action(), atol=0, rtol=0)
        critic(current_state=current, current_action=actions[:, 0], prev_state=states[:, 0],
               prev_action=actions[:, 0], single_step_mode=True, env_ids=['witness'])
        critic.reset_hidden_state('witness')
        assert all('witness' not in getattr(critic, name) for name in
                   ('hidden_states_q1', 'hidden_states_q2', 'lstm_output_history_q1', 'lstm_output_history_q2'))
    hook.remove()
    actor.reset_hidden_state(); critic.reset_hidden_state()
    return {'actor_double_critic_finite': True, 'attention_shape': [1, 10],
            'attention_sum_eval': 1., 'reset_isolation_and_repeatability': True,
            'same_prefix_stream_sequence_max_error': prefix_error,
            'persistent_stream_vs_last10_zero_hidden_max_error': long_error,
            'scope': 'Synthetic-input API checks, not checkpoint quality or navigation evidence'}


def history_witness():
    from collections import deque
    path = REFERENCE / 'parll_lstm_att_normal.py'
    tree = ast.parse(path.read_text())
    append_nodes = [n for n in ast.walk(tree) if isinstance(n, ast.Expr)
                    and n.lineno in (217, 219)]
    assert len(append_nodes) == 2, 'Reference changed: inspect history update'
    append_nodes.sort(key=lambda n: n.lineno)
    scope = dict(i=0, actions=[np.array([7., 8.])], s_next_noisy=np.full((1, 18), 11.),
                 state_buffers=[deque([np.full(18, 10.)] * 10, maxlen=10)],
                 action_buffers=[deque([np.zeros(2)] * 10, maxlen=10)])
    exec(compile(ast.Module(body=append_nodes, type_ignores=[]), str(path), 'exec'), scope)
    actual_state = float(scope['state_buffers'][0][-1][0])
    assert actual_state == 11.
    return {'status': 'CONFIRMED_MISMATCH', 'original_appended_state_marker': actual_state,
            'single_step_expected_previous_state_marker': 10., 'action_marker': [7., 8.],
            'evidence': 'Executed original AST append statements at lines 217,219'}


def rollout(env, actor, normalizer, seed, obstacles, max_steps, path, trained, sequence=False):
    from collections import deque
    obs = reset(env, seed, obstacles)
    previous, action = obs.copy(), np.zeros(2, dtype=np.float32)
    states = deque([obs.copy() for _ in range(10)], maxlen=10)
    actions = deque([action.copy() for _ in range(10)], maxlen=10)
    device = next(actor.parameters()).device
    actor.reset_hidden_state(); actor.eval()
    start = time.monotonic()
    length = sail_tv = rudder_tv = reward_sum = 0.
    min_distance = float('inf')
    violation = proxy = terminated = truncated = False
    fields = ['time', 'x', 'y', 'heading', 'sail_angle', 'rudder_angle', 'sail_increment',
              'rudder_increment', 'distance', 'goal_distance', 'reward', 'terminated', 'truncated']
    with path.open('x', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fields); writer.writeheader()
        for step in range(max_steps):
            old = obs.copy()
            with torch.no_grad():
                norm = lambda x: normalizer.normalize(torch.as_tensor(np.asarray(x), device=device).float().unsqueeze(0))
                if sequence:
                    a, _ = actor(current_state=norm(obs), state_sequence=norm(states),
                                 action_sequence=torch.as_tensor(np.asarray(actions), device=device).float().unsqueeze(0),
                                 deterministic=True)
                else:
                    a, _ = actor(current_state=norm(obs), prev_state=norm(previous),
                                 prev_action=torch.tensor(action, device=device).unsqueeze(0), single_step_mode=True,
                                 deterministic=True, env_ids=['rollout'])
            action = a[0].cpu().numpy().copy()
            states.append(old.copy()); actions.append(action.copy())
            obs, reward, terminated, truncated, _ = env.step(action * env.action_space.high)
            obs = obs.copy()
            assert np.isfinite(obs).all() and np.isfinite(reward) and np.isfinite(action).all()
            previous = old
            distances = [float(np.linalg.norm(obs[:2] - p)) for p in ref_globals.obstacles]
            distance = min(distances, default=float('inf'))
            min_distance = min(min_distance, distance)
            violation |= distance < 40.; proxy |= distance < 15.
            length += float(np.linalg.norm(obs[:2] - old[:2]))
            sail_tv += abs(float(obs[8] - old[8])); rudder_tv += abs(float(obs[9] - old[9]))
            reward_sum += float(reward)
            writer.writerow(dict(zip(fields, [step+1, float(obs[0]), float(obs[1]), float(obs[3]),
                float(obs[8]), float(obs[9]), float(action[0]*env.action_space.high[0]),
                float(action[1]*env.action_space.high[1]), None if not distances else distance,
                float(np.linalg.norm(obs[:2]-obs[12:14])), float(reward), bool(terminated), bool(truncated)])))
            if terminated or truncated: break
    elapsed = step + 1
    out_of_bounds = bool(np.linalg.norm(obs[:2]) >= 750.)
    timeout = bool(ref_globals.current_time >= ref_globals.total_time)
    censored = bool(not terminated and not truncated and elapsed == max_steps)
    return {'policy': 'strictly_loaded_checkpoint_NOT_PAPER_REPRODUCTION' if trained else 'random_initialization_NOT_BASELINE',
            'seed': seed, 'steps': elapsed, 'task_success': bool(terminated),
            'safe_success_endpoint_only': bool(terminated and not violation),
            'safety_violation_endpoint_only': bool(violation), 'physical_proxy_endpoint_only': bool(proxy),
            'timeout': timeout, 'out_of_bounds': out_of_bounds, 'censored_by_probe_limit': censored,
            'minimum_separation_endpoint_only_m': min_distance if np.isfinite(min_distance) else None,
            'navigation_time_s_if_success': elapsed if terminated else None, 'episode_duration_s': elapsed,
            'trajectory_length_endpoint_polyline_m': length, 'sail_total_variation_rad': sail_tv,
            'rudder_total_variation_rad': rudder_tv, 'sail_variation_rate_rad_s': sail_tv/elapsed,
            'rudder_variation_rate_rad_s': rudder_tv/elapsed, 'episode_reward': reward_sum,
            'wall_seconds': time.monotonic()-start,
            'safety_limit': 'Original endpoint-only reference logic; no continuous-safety claim'}


def train_static(args, out):
    """Short static baseline attempt using the original SAC updates and network.

    Collector-only repairs: history pairs (s_t,a_t), same zero-initialized window
    at collection/evaluation/training, direct terminal obs, hard step budget.
    Original static reward, action quantization, and 1Hz environment are retained.
    """
    from collections import deque
    from SAC_lstm_att_normal import SAC_lstm_countinuous
    device = torch.device(args.device)
    if device.type == 'cuda':
        assert torch.cuda.is_available()
        witness = torch.arange(64, device=device).float().reshape(8, 8)
        assert torch.isfinite(witness @ witness.T).all()
    config = dict(state_dim=18, action_dim=2, net_width=256, batch_size=256,
                  a_lr=5e-5, c_lr=5e-5, gamma=.98, alpha=.2, adaptive_alpha=True,
                  seed=args.seed, train_steps=args.train_steps, warmup_steps=args.warmup_steps,
                  updates_per_20_steps=8, history_length=10, replay_capacity=2000,
                  static_no_obstacle_probability=.3, scene='otherwise original fixed seven obstacles',
                  sensor_noise=False, actuator_noise=False, policy_wind_observation=False,
                  inference='sequence_last10_zero_hidden', history_pairs='s_t,a_t',
                  terminal='original terminated OR truncated; no bootstrap at finite episode end',
                  max_episode_steps=1000, dynamic_enabled=False,
                  source_reference_commit='19422525cb337831ca68f53a45661d34f3683ee1')
    (out/'config.json').write_text(json.dumps(config, indent=2))
    agent = SAC_lstm_countinuous(dvc=device, **config)
    rng = np.random.default_rng(args.seed + 400000)
    env = load_environment()
    total = 0; episode = 0; start = time.monotonic()
    stats = {'budget':args.train_steps, 'optimizer_updates':0, 'policy_updates':0,
             'completed':False, 'stage_gate':'STATIC_TRAINING_IN_PROGRESS',
             'device':str(device), 'versions':{'python':sys.version, 'torch':torch.__version__, 'numpy':np.__version__},
             'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in [Path(__file__), ENV_FILE, REFERENCE/'utils_lstm_att_normal.py',
                                        REFERENCE/'SAC_lstm_att_normal.py', REFERENCE/'globals.py']}}
    def save(step):
        prefix = out/'static'
        for name, obj in [('actor', agent.actor), ('q_critic', agent.q_critic),
                          ('normalizer', agent.state_normalizer)]:
            torch.save(obj.state_dict(), f'{prefix}_{name}{step}.pth')
        stats.update(total_steps=step, wall_seconds=time.monotonic()-start)
        (out/'training_status.json').write_text(json.dumps(stats, indent=2))
    try:
        with (out/'episodes.jsonl').open('x') as logs, (out/'loss.jsonl').open('x') as losses:
            while total < args.train_steps:
                episode_seed = args.seed + episode
                obs = reset(env, episode_seed, [] if rng.random() < .3 else None)
                states = deque([obs.copy() for _ in range(10)], maxlen=10)
                actions = deque([np.zeros(2, dtype=np.float32) for _ in range(10)], maxlen=10)
                episode_reward = length = sail_tv = rudder_tv = 0.
                minimum = float('inf'); violated = proxy = False
                for t in range(1000):
                    s_seq = np.asarray(states).copy(); a_seq = np.asarray(actions).copy()
                    agent.actor.eval()
                    if total < config['warmup_steps']:
                        choice = rng.random()
                        action = np.zeros(2, dtype=np.float32)
                        if .3 <= choice < .5: action = rng.uniform(-.2,.2,2).astype(np.float32)
                        elif .5 <= choice < .65: action[rng.integers(2)] = rng.uniform(-.5,.5)
                        elif choice >= .65: action = rng.uniform(-1.,1.,2).astype(np.float32)
                    else:
                        with torch.no_grad():
                            a, _ = agent.actor(
                                state_sequence=agent.state_normalizer.normalize(torch.as_tensor(s_seq, device=device).unsqueeze(0)),
                                action_sequence=torch.as_tensor(a_seq, device=device).unsqueeze(0),
                                current_state=agent.state_normalizer.normalize(torch.as_tensor(obs, device=device).unsqueeze(0)),
                                deterministic=False)
                        action = a[0].cpu().numpy().copy()
                    next_obs, reward, term, trunc, _ = env.step(action * env.action_space.high)
                    next_obs = next_obs.copy()
                    assert np.isfinite(next_obs).all() and np.isfinite(action).all() and np.isfinite(reward)
                    # Crucial: append CURRENT state paired with current commanded action.
                    states.append(obs.copy()); actions.append(action.copy())
                    agent.replay_buffer.add(s_seq, a_seq, obs, action, float(reward), np.asarray(states).copy(),
                                            np.asarray(actions).copy(), next_obs, bool(term or trunc))
                    distances = [float(np.linalg.norm(next_obs[:2]-p)) for p in ref_globals.obstacles]
                    distance = min(distances, default=float('inf'))
                    minimum = min(minimum, distance); violated |= distance < 40.; proxy |= distance < 15.
                    length += float(np.linalg.norm(next_obs[:2]-obs[:2]))
                    sail_tv += abs(float(next_obs[8]-obs[8])); rudder_tv += abs(float(next_obs[9]-obs[9]))
                    obs = next_obs; episode_reward += float(reward); total += 1
                    if total >= config['warmup_steps'] and total % 20 == 0 and agent.replay_buffer.size >= 256:
                        agent.actor.train(); agent.q_critic.train(); agent.q_critic_target.eval()
                        agent.replay_buffer.update_beta(min(total/2000000,1.))
                        for _ in range(config['updates_per_20_steps']):
                            row = agent.train()
                            assert all(np.isfinite(row[k]) for k in ('q_loss','a_loss','alpha_loss','alpha'))
                            stats['optimizer_updates'] += 1
                            stats['policy_updates'] += int(row.get('policy_updated', False))
                            if row.get('policy_updated', False):
                                loss_row = dict(step=total, **row); losses.write(json.dumps(loss_row)+'\n')
                        losses.flush()
                    if total % 1000 == 0:
                        print(json.dumps(dict(step=total, episodes=episode, updates=stats['optimizer_updates'],
                                              wall_seconds=time.monotonic()-start)), flush=True)
                    if total % 10000 == 0: save(total)
                    if term or trunc or total >= args.train_steps: break
                logs.write(json.dumps(dict(episode=episode, seed=episode_seed, total_steps=total,
                    episode_steps=t+1, episode_reward=episode_reward, task_success=bool(term),
                    safe_success_endpoint_only=bool(term and not violated), safety_violation_endpoint_only=bool(violated),
                    physical_proxy_endpoint_only=bool(proxy), timeout=bool(ref_globals.current_time>=1000),
                    budget_censored=bool(not term and not trunc and total>=args.train_steps),
                    minimum_separation_endpoint_only_m=minimum if np.isfinite(minimum) else None,
                    trajectory_length_endpoint_polyline_m=length, sail_variation_rate_rad_s=sail_tv/(t+1),
                    rudder_variation_rate_rad_s=rudder_tv/(t+1)))+'\n'); logs.flush()
                episode += 1
        stats['completed'] = True
        stats['stage_gate'] = 'STATIC_TRAINING_COMPLETE_PENDING_BEHAVIOR_CHECK'
        # Final weights always saved, even for a bounded gradient smoke.
        if total % 10000 != 0: save(total)
        stats.update(total_steps=total, wall_seconds=time.monotonic()-start)
        (out/'training_status.json').write_text(json.dumps(stats, indent=2))
    except Exception as exc:
        stats.update(stage_gate='STATIC_TRAINING_FAILED', error=f'{type(exc).__name__}: {exc}')
        save(total)
        raise
    finally:
        env.close()
    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--checkpoint-prefix', type=Path, help='Full prefix before _actor/_q_critic/_normalizer')
    parser.add_argument('--checkpoint-step', type=int)
    parser.add_argument('--seed', type=int, default=101)
    parser.add_argument('--max-steps', type=int, default=1000)
    parser.add_argument('--mode', choices=['probe','train-static'], default='probe')
    parser.add_argument('--device', choices=['cpu','cuda'], default='cpu')
    parser.add_argument('--train-steps', type=int, default=50000)
    parser.add_argument('--warmup-steps', type=int, default=20000,
                        help='Default original 20k; reduce only for a labelled integration smoke')
    parser.add_argument('--sequence', action='store_true', help='Use the repaired last10 history protocol')
    parser.add_argument('--history-protocol', choices=['legacy','aligned'],
                        help='Explicit legacy streaming or aligned sequence; prefer chapter5_static.py for recovery')
    args = parser.parse_args()
    if args.history_protocol:
        if args.sequence and args.history_protocol!='aligned':parser.error('--sequence conflicts with legacy protocol')
        args.sequence=args.history_protocol=='aligned'
    if not 1 <= args.max_steps <= 1000: parser.error('max-steps must be 1..1000')
    out = args.output_dir.resolve()
    if sys.platform.startswith('linux'):
        hs = Path('/home/ot/Students/hs').resolve()
        if not ROOT.resolve().is_relative_to(hs) or not out.is_relative_to(hs):
            parser.error('Server root and output must resolve inside hs')
    out.mkdir(parents=True, exist_ok=False)
    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed)
    if args.mode == 'train-static':
        if args.history_protocol=='legacy':parser.error('This old engineering trainer is aligned-only; no legacy retraining')
        if not 1 <= args.train_steps <= 50000: parser.error('Static attempt budget is 1..50000')
        if not 0 <= args.warmup_steps <= 20000: parser.error('warmup-steps must be 0..20000')
        train_static(args, out)
        return
    actor = Actor(18, 2, (256, 256))
    critic = Double_Q_Critic(18, 2, (256, 256), (256, 128))
    normalizer = ZScoreNormalizer(18, torch.device('cpu'))
    used = [ENV_FILE, REFERENCE/'utils_lstm_att_normal.py', REFERENCE/'SAC_lstm_att_normal.py',
            REFERENCE/'parll_lstm_att_normal.py', REFERENCE/'globals.py', Path(__file__)]
    report = {'stage': 1, 'seed': args.seed, 'dynamic_enabled': False,
              'checkpoint_loaded': False, 'noise': 'no external sensor/actuator wrapper',
              'versions': {'python': sys.version, 'numpy': np.__version__, 'torch': torch.__version__},
              'scope': 'Current chapter-5 static implementation only; not paper Table 5.1 reproduction'}
    if args.checkpoint_prefix:
        if args.checkpoint_step is None: parser.error('checkpoint-step is required with prefix')
        paths = [Path(f'{args.checkpoint_prefix}_{kind}{args.checkpoint_step}.pth')
                 for kind in ('actor','q_critic','normalizer')]
        try:
            actor.load_state_dict(torch.load(paths[0], map_location='cpu', weights_only=True), strict=True)
            critic.load_state_dict(torch.load(paths[1], map_location='cpu', weights_only=True), strict=True)
            stats = torch.load(paths[2], map_location='cpu', weights_only=True)
            assert stats['mean'].shape == stats['var'].shape == (18,)
            assert torch.isfinite(stats['mean']).all() and torch.isfinite(stats['var']).all()
            assert (stats['var'] >= 0).all() and stats['count'] > 0
            normalizer.load_state_dict(stats)
            assert all(torch.isfinite(p).all() for model in (actor, critic) for p in model.parameters())
            used.extend(paths); report['checkpoint_loaded'] = True
        except (OSError, RuntimeError, AssertionError, KeyError) as exc:
            report.update(stage_gate='BLOCKED_CHECKPOINT', error=str(exc))
            (out/'receipt.json').write_text(json.dumps(report, indent=2)); raise
    env = load_environment()
    try:
        report['interface_checks'] = interface_checks(env)
        report['network_checks'] = network_checks(actor, critic)
        report['history_witness'] = history_witness()
        report['rollouts'] = {}
        for name, obstacles in [('no_obstacle', []), ('static_reference', None)]:
            report['rollouts'][name] = rollout(env, actor, normalizer, args.seed, obstacles,
                                               args.max_steps, out/f'{name}.csv', report['checkpoint_loaded'], args.sequence)
            print(json.dumps({name:report['rollouts'][name]}, ensure_ascii=False), flush=True)
        report['stage_gate'] = 'PENDING_BASELINE_BEHAVIOR_REVIEW' if args.sequence else 'BLOCKED_HISTORY_PROTOCOL'
        report['inference_protocol'] = 'sequence_last10_zero_hidden' if args.sequence else 'original_streaming'
        if not report['checkpoint_loaded']: report['stage_gate'] = 'BLOCKED_MATCHED_CHECKPOINT_AND_HISTORY_PROTOCOL'
        report['CURRENT_HYPOTHESIS'] = 'INCONCLUSIVE'
    except Exception as exc:
        report.update(stage_gate='PROBE_FAILED', error=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        env.close()
        report['source_sha256'] = {str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p):
                                   hashlib.sha256(p.read_bytes()).hexdigest() for p in used}
        (out/'receipt.json').write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False))
    print(report['stage_gate'], flush=True)


if __name__ == '__main__':
    main()
