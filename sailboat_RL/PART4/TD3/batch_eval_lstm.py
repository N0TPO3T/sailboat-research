"""
SAC-LSTM 模型批量测试评估脚本
使用 SubprocVecEnv 并行运行多个环境，统计成功样例的路径距离、步数、帆角/舵角变化总量的均值与标准差。
LSTM版本需要维护每个环境的隐藏状态和前一步状态/动作。
"""

import os
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import argparse
import numpy as np
import torch
from stable_baselines3.common.vec_env import SubprocVecEnv
import gymnasium as gym

from utils_lstm_normal import str2bool, Action_adapter
from noise_utils_nowind import NoiseManager
from TD3_lstm_normal import TD3_lstm_continuous


def make_env(env_id, seed):
    def _init():
        env = gym.make(env_id)
        env.reset(seed=seed)
        return env
    return _init


def parse_args():
    parser = argparse.ArgumentParser(description='TD3-LSTM Batch Evaluation')
    parser.add_argument('--dvc', type=str, default='cpu')
    parser.add_argument('--model_prefix', type=str, default='td3lstm_s14nowind_final')
    parser.add_argument('--model_step', type=int, default=6600)
    parser.add_argument('--env_name', type=str, default='sailboat-s14-nowind')
    parser.add_argument('--max_steps', type=int, default=1000)
    parser.add_argument('--num_envs', type=int, default=5, help='Number of parallel environments')
    parser.add_argument('--total_episodes', type=int, default=1000, help='Total episodes to run')
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--net_width', type=int, default=256)

    parser.add_argument('--enable_sensor_noise', type=str2bool, default=True)
    parser.add_argument('--enable_actuator_noise', type=str2bool, default=True)
    parser.add_argument('--sensor_noise_ratio', type=float, default=0.03)
    parser.add_argument('--actuator_noise_ratio', type=float, default=0.03)

    return parser.parse_args()


def run_batch_eval(opt):
    # ==================== 环境初始化 ====================
    env_fns = [make_env(opt.env_name, opt.seed + i) for i in range(opt.num_envs)]
    vec_env = SubprocVecEnv(env_fns)

    state_dim = vec_env.observation_space.shape[0]
    action_dim = vec_env.action_space.shape[0]
    max_action = vec_env.action_space.high.astype(float)

    print(f'Env: {opt.env_name}  state_dim: {state_dim}  action_dim: {action_dim}')
    print(f'Parallel envs: {opt.num_envs}  Total episodes: {opt.total_episodes}')

    # ==================== 模型加载 ====================
    device = torch.device(opt.dvc if torch.cuda.is_available() else 'cpu')
    agent = TD3_lstm_continuous(
        state_dim=state_dim,
        action_dim=action_dim,
        net_width=opt.net_width,
        a_lr=5e-5, c_lr=5e-5,
        gamma=0.98, batch_size=256,
        dvc=device,
    )
    agent.load(opt.model_prefix, opt.model_step)
    agent.actor.eval()
    print(f'Model loaded: {opt.model_prefix} @ step {opt.model_step}')

    # ==================== 噪声管理器 (每个并行环境一个) ====================
    noise_managers = [
        NoiseManager(
            sensor_noise_ratio=opt.sensor_noise_ratio,
            actuator_noise_ratio=opt.actuator_noise_ratio,
            enable_sensor_noise=opt.enable_sensor_noise,
            enable_actuator_noise=opt.enable_actuator_noise,
            seed=opt.seed + i,
        )
        for i in range(opt.num_envs)
    ]

    # ==================== 随机种子 ====================
    torch.manual_seed(opt.seed)
    np.random.seed(opt.seed)

    # ==================== 并行收集 ====================
    obs_all = vec_env.reset()  # (num_envs, state_dim)

    # 初始化每个环境的带噪声状态
    states = []
    for i in range(opt.num_envs):
        if opt.enable_sensor_noise:
            states.append(noise_managers[i].add_observation_noise(obs_all[i]))
        else:
            states.append(obs_all[i].copy())
    states = np.array(states)

    # LSTM需要维护前一步的状态和动作
    prev_states = states.copy()  # 初始时前一状态 = 当前状态
    prev_actions = np.zeros((opt.num_envs, action_dim))  # 初始前一动作为0

    # 重置所有环境的LSTM隐藏状态
    agent.actor.reset_hidden_state()

    # 每个环境的当前 episode 累计量
    env_steps = np.zeros(opt.num_envs, dtype=int)
    env_path_dist = np.zeros(opt.num_envs, dtype=float)
    env_sail_change = np.zeros(opt.num_envs, dtype=float)
    env_rudder_change = np.zeros(opt.num_envs, dtype=float)
    env_prev_obs = obs_all.copy()  # 上一步原始观测, 用于计算帆角舵角变化

    # 成功样例统计
    success_path_dists = []
    success_steps = []
    success_sail_changes = []
    success_rudder_changes = []
    total_finished = 0

    print('Running episodes...')

    while total_finished < opt.total_episodes:
        # 逐个环境选择动作（LSTM需要维护per-env隐藏状态）
        raw_actions = []  # 存储agent原始输出 [-1,1]
        for i in range(opt.num_envs):
            a = agent.select_action(
                prev_states[i], prev_actions[i], states[i],
                add_noise=False, env_id=i
            )
            raw_actions.append(a)

        # 添加执行器噪声并转换动作（与训练代码一致）
        act_list = []
        for i, a in enumerate(raw_actions):
            if opt.enable_actuator_noise:
                a_noisy = noise_managers[i].add_action_noise(a, max_action)
            else:
                a_noisy = a.copy()
            act_list.append(Action_adapter(a_noisy, max_action))
        actions_arr = np.array(act_list)

        # 环境步进
        obs_next_all, rewards, dones, infos = vec_env.step(actions_arr)

        for i in range(opt.num_envs):
            if total_finished >= opt.total_episodes:
                break

            env_steps[i] += 1

            # 如果 episode 结束，用 terminal_observation 而非自动重置后的观测
            if dones[i]:
                step_obs = infos[i].get('terminal_observation', obs_next_all[i])
            else:
                step_obs = obs_next_all[i]

            # 累计路径距离
            dx = step_obs[0] - env_prev_obs[i, 0]
            dy = step_obs[1] - env_prev_obs[i, 1]
            env_path_dist[i] += np.sqrt(dx ** 2 + dy ** 2)

            # 累计帆角/舵角变化总量
            env_sail_change[i] += abs(step_obs[8] - env_prev_obs[i, 8])
            env_rudder_change[i] += abs(step_obs[9] - env_prev_obs[i, 9])

            if dones[i]:
                total_finished += 1

                # 判断是否成功: terminated 通过 info 获取
                # SubprocVecEnv 在 done 时自动 reset，原始 info 在 infos[i]
                # 成功条件: 到达目标点 (距离 <= 10m)
                terminal_obs = infos[i].get('terminal_observation', obs_next_all[i])
                target_x = terminal_obs[12] if state_dim >= 14 else 0
                target_y = terminal_obs[13] if state_dim >= 14 else 0
                final_dist = np.sqrt(
                    (terminal_obs[0] - target_x) ** 2 +
                    (terminal_obs[1] - target_y) ** 2
                )
                is_success = final_dist <= 10.0

                if is_success:
                    success_path_dists.append(env_path_dist[i])
                    success_steps.append(env_steps[i])
                    success_sail_changes.append(env_sail_change[i])
                    success_rudder_changes.append(env_rudder_change[i])

                status = 'SUCCESS' if is_success else 'FAIL'
                print(f'  Episode {total_finished}/{opt.total_episodes}: {status} | '
                      f'steps={env_steps[i]}, path_dist={env_path_dist[i]:.1f}m, '
                      f'final_dist={final_dist:.1f}m')

                # 重置该环境的累计量
                env_steps[i] = 0
                env_path_dist[i] = 0.0
                env_sail_change[i] = 0.0
                env_rudder_change[i] = 0.0

                # 重置该环境的LSTM隐藏状态
                agent.actor.reset_hidden_state(env_id=i)

                # 重置前一步状态和动作
                if opt.enable_sensor_noise:
                    prev_states[i] = noise_managers[i].add_observation_noise(obs_next_all[i])
                else:
                    prev_states[i] = obs_next_all[i].copy()
                prev_actions[i] = np.zeros(action_dim)

            env_prev_obs[i] = obs_next_all[i].copy()

        # 更新 states 和 prev_states / prev_actions
        for i in range(opt.num_envs):
            if not dones[i]:
                # 非结束环境: 更新前一步为当前步
                prev_states[i] = states[i].copy()
                prev_actions[i] = raw_actions[i].copy()  # 使用agent原始动作，与训练代码一致

            if opt.enable_sensor_noise:
                states[i] = noise_managers[i].add_observation_noise(obs_next_all[i])
            else:
                states[i] = obs_next_all[i].copy()

    vec_env.close()

    # ==================== 统计输出 ====================
    n_success = len(success_steps)
    n_total = opt.total_episodes
    print('\n' + '=' * 60)
    print(f'Model: {opt.model_prefix} @ step {opt.model_step}')
    print(f'Noise: sensor={opt.enable_sensor_noise}({opt.sensor_noise_ratio*100:.0f}%), '
          f'actuator={opt.enable_actuator_noise}({opt.actuator_noise_ratio*100:.0f}%)')
    print(f'Total episodes: {n_total}')
    print(f'Success count:  {n_success}  ({n_success/n_total*100:.1f}%)')
    print('-' * 60)

    if n_success > 0:
        path_arr = np.array(success_path_dists)
        steps_arr = np.array(success_steps)
        sail_arr = np.rad2deg(np.array(success_sail_changes))   # 转为度
        rudder_arr = np.rad2deg(np.array(success_rudder_changes))

        print(f'{"Metric":<25s} {"Mean":>10s} {"Std":>10s}')
        print('-' * 60)
        print(f'{"Path Distance (m)":<25s} {path_arr.mean():>10.2f} {path_arr.std():>10.2f}')
        print(f'{"Steps":<25s} {steps_arr.mean():>10.2f} {steps_arr.std():>10.2f}')
        print(f'{"Sail Angle Change (deg)":<25s} {sail_arr.mean():>10.2f} {sail_arr.std():>10.2f}')
        print(f'{"Rudder Angle Change (deg)":<25s} {rudder_arr.mean():>10.2f} {rudder_arr.std():>10.2f}')
    else:
        print('No successful episodes — no statistics to report.')

    print('=' * 60)


if __name__ == '__main__':
    opt = parse_args()
    run_batch_eval(opt)
