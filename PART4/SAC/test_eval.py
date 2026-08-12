"""
SAC 模型测试评估脚本
加载已训练模型，运行单次测试，保存观测/动作/风场数据到txt文件，并绘制路径图和帆角舵角变化。
所有输出文件保存到新建的 test_results/ 文件夹中。
"""

import os
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import sys
import copy
import argparse
import numpy as np
import torch
import gymnasium as gym
import globals
import matplotlib
matplotlib.use('Agg')  # 非交互式后端，确保保存图片不弹窗
import matplotlib.pyplot as plt
from datetime import datetime

from utils_fc import str2bool, Action_adapter, Action_adapter_reverse
from noise_utils_wind import NoiseManager
from SAC_fc import SAC_fc_continuous


def parse_args():
    parser = argparse.ArgumentParser(description='SAC Model Test & Evaluation')
    parser.add_argument('--dvc', type=str, default='cpu', help='Device: cuda or cpu')
    parser.add_argument('--model_prefix', type=str, default='sac_s14wind_final',
                        help='Model file prefix (e.g. sac_s14wind_final)')
    parser.add_argument('--model_step', type=int, default=9000,
                        help='Model checkpoint step (e.g. 9000)')
    parser.add_argument('--env_name', type=str, default='sailboat-s14-wind',
                        help='Gymnasium environment name')
    parser.add_argument('--max_steps', type=int, default=1000,
                        help='Max steps per episode')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    parser.add_argument('--render', type=str2bool, default=False, help='Render environment')
    parser.add_argument('--net_width', type=int, default=256, help='Hidden net width')

    # 噪声相关
    parser.add_argument('--enable_sensor_noise', type=str2bool, default=True,
                        help='Enable sensor noise during test')
    parser.add_argument('--enable_actuator_noise', type=str2bool, default=True,
                        help='Enable actuator noise during test')
    parser.add_argument('--sensor_noise_ratio', type=float, default=0.03)
    parser.add_argument('--actuator_noise_ratio', type=float, default=0.03)

    return parser.parse_args()


def run_test(opt):
    # ==================== 创建输出文件夹 ====================
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'test_results', f'{opt.model_prefix}_{timestamp}')
    os.makedirs(output_dir, exist_ok=True)
    print(f'Output directory: {output_dir}')

    # ==================== 环境初始化 ====================
    render_mode = 'human' if opt.render else None
    env = gym.make(opt.env_name, render_mode=render_mode) if render_mode else gym.make(opt.env_name)
    obs, info = env.reset(seed=opt.seed)

    state_dim = env.observation_space.shape[0]
    action_dim = env.action_space.shape[0]
    max_action = env.action_space.high.astype(float)

    print(f'Env: {opt.env_name}  state_dim: {state_dim}  action_dim: {action_dim}')
    print(f'max_action: {max_action}  min_action: {env.action_space.low}')

    # ==================== 模型加载 ====================
    device = torch.device(opt.dvc if torch.cuda.is_available() else 'cpu')
    agent = SAC_fc_continuous(
        state_dim=state_dim,
        action_dim=action_dim,
        net_width=opt.net_width,
        a_lr=5e-5,
        c_lr=5e-5,
        gamma=0.98,
        batch_size=256,
        alpha=0.2,
        adaptive_alpha=True,
        dvc=device,
    )
    agent.load(opt.model_prefix, opt.model_step)
    agent.actor.eval()
    print(f'Model loaded: {opt.model_prefix} @ step {opt.model_step}')

    # ==================== 噪声管理器 ====================
    noise_manager = NoiseManager(
        sensor_noise_ratio=opt.sensor_noise_ratio,
        actuator_noise_ratio=opt.actuator_noise_ratio,
        enable_sensor_noise=opt.enable_sensor_noise,
        enable_actuator_noise=opt.enable_actuator_noise,
        seed=opt.seed,
    )
    print(f'Noise: sensor={opt.enable_sensor_noise}, actuator={opt.enable_actuator_noise}')

    # ==================== 随机种子 ====================
    torch.manual_seed(opt.seed)
    np.random.seed(opt.seed)

    # ==================== 数据收集 ====================
    observations_raw = []   # 原始观测
    observations_noisy = [] # 带噪声观测
    actions_agent = []      # agent输出的归一化动作 [-1,1]
    actions_env = []        # 实际发送给环境的动作
    rewards = []
    wind_speeds = []
    wind_dirs = []
    steps_list = []

    # 初始观测
    if opt.enable_sensor_noise:
        s = noise_manager.add_observation_noise(obs)
    else:
        s = obs.copy()

    done = False
    step = 0
    total_reward = 0.0

    while not done and step < opt.max_steps:
        # Agent 选择动作
        a = agent.select_action(s, deterministic=True)

        # 动作噪声
        if opt.enable_actuator_noise:
            a_noisy = noise_manager.add_action_noise(a, max_action)
        else:
            a_noisy = a.copy()

        act = Action_adapter(a_noisy, max_action)

        # 环境交互
        obs_next_raw, reward, terminated, truncated, info = env.step(act)
        done = terminated or truncated

        # 下一状态噪声
        if opt.enable_sensor_noise:
            s_next = noise_manager.add_observation_noise(obs_next_raw)
        else:
            s_next = obs_next_raw.copy()

        # 记录数据
        steps_list.append(step)
        observations_raw.append(copy.deepcopy(obs if step == 0 else obs_next_raw))
        observations_noisy.append(copy.deepcopy(s))
        actions_agent.append(a.copy())
        actions_env.append(act.copy())
        rewards.append(reward)
        wind_speeds.append(globals.w_change_v)
        wind_dirs.append(globals.w_change_d)

        # 更新状态
        s = s_next
        obs = obs_next_raw
        total_reward += reward
        step += 1

    # 记录最后一帧观测
    observations_raw.append(copy.deepcopy(obs))
    observations_noisy.append(copy.deepcopy(s))

    env.close()
    print(f'Episode finished: steps={step}, total_reward={total_reward:.2f}, '
          f'terminated={terminated}, truncated={truncated}')

    # ==================== 转换为numpy数组 ====================
    obs_raw_arr = np.array(observations_raw)       # (steps+1, state_dim)
    obs_noisy_arr = np.array(observations_noisy)   # (steps+1, state_dim)
    act_agent_arr = np.array(actions_agent)         # (steps, action_dim)
    act_env_arr = np.array(actions_env)             # (steps, action_dim)
    rewards_arr = np.array(rewards)                 # (steps,)
    wind_speed_arr = np.array(wind_speeds)          # (steps,)
    wind_dir_arr = np.array(wind_dirs)              # (steps,)
    steps_arr = np.array(steps_list)                # (steps,)

    # ==================== 保存txt文件 ====================
    obs_header = 'x,y,phi,psi,u,v,p,r,sail_angle,rudder_angle,proj_dist,target_info,target_x,target_y,wind_speed' if state_dim == 15 else ','.join([f'obs_{i}' for i in range(state_dim)])

    np.savetxt(os.path.join(output_dir, 'observations_raw.txt'),
               obs_raw_arr, delimiter=',', header=obs_header, comments='')

    np.savetxt(os.path.join(output_dir, 'observations_noisy.txt'),
               obs_noisy_arr, delimiter=',', header=obs_header, comments='')

    np.savetxt(os.path.join(output_dir, 'actions_agent.txt'),
               act_agent_arr, delimiter=',', header='sail_cmd_norm,rudder_cmd_norm', comments='')

    np.savetxt(os.path.join(output_dir, 'actions_env.txt'),
               act_env_arr, delimiter=',', header='sail_cmd,rudder_cmd', comments='')

    np.savetxt(os.path.join(output_dir, 'rewards.txt'),
               np.column_stack([steps_arr, rewards_arr]),
               delimiter=',', header='step,reward', comments='')

    np.savetxt(os.path.join(output_dir, 'wind_info.txt'),
               np.column_stack([steps_arr, wind_speed_arr, wind_dir_arr]),
               delimiter=',', header='step,wind_speed,wind_direction', comments='')

    # 汇总信息
    with open(os.path.join(output_dir, 'summary.txt'), 'w', encoding='utf-8') as f:
        f.write(f'Model: {opt.model_prefix} @ step {opt.model_step}\n')
        f.write(f'Environment: {opt.env_name}\n')
        f.write(f'Seed: {opt.seed}\n')
        f.write(f'Total Steps: {step}\n')
        f.write(f'Total Reward: {total_reward:.4f}\n')
        f.write(f'Terminated: {terminated}\n')
        f.write(f'Truncated: {truncated}\n')
        f.write(f'Sensor Noise: {opt.enable_sensor_noise} ({opt.sensor_noise_ratio*100:.1f}%)\n')
        f.write(f'Actuator Noise: {opt.enable_actuator_noise} ({opt.actuator_noise_ratio*100:.1f}%)\n')
        f.write(f'Start Position: ({obs_raw_arr[0, 0]:.2f}, {obs_raw_arr[0, 1]:.2f})\n')
        f.write(f'Final Position: ({obs_raw_arr[-1, 0]:.2f}, {obs_raw_arr[-1, 1]:.2f})\n')
        if state_dim >= 14:
            f.write(f'Target Position: ({obs_raw_arr[0, 12]:.2f}, {obs_raw_arr[0, 13]:.2f})\n')
            final_dist = np.sqrt((obs_raw_arr[-1, 0] - obs_raw_arr[0, 12])**2 +
                                 (obs_raw_arr[-1, 1] - obs_raw_arr[0, 13])**2)
            f.write(f'Final Distance to Target: {final_dist:.2f} m\n')

    print(f'Data saved to {output_dir}')

    # ==================== 绘图 ====================
    plot_results(obs_raw_arr, act_env_arr, rewards_arr, wind_speed_arr, wind_dir_arr,
                 steps_arr, state_dim, output_dir)

    return output_dir


def plot_results(obs, actions, rewards, wind_speed, wind_dir, steps, state_dim, output_dir):
    """绘制路径图、帆角/舵角变化、奖励曲线、风场信息等"""

    x = obs[:, 0]
    y = obs[:, 1]
    psi_deg = np.rad2deg(obs[:, 3])         # 航向角
    sail_deg = np.rad2deg(obs[:, 8])        # 帆角
    rudder_deg = np.rad2deg(obs[:, 9])      # 舵角
    speed_u = obs[:, 4]                     # 前向速度
    if state_dim >= 14:
        target_x = obs[0, 12]
        target_y = obs[0, 13]
    else:
        target_x, target_y = None, None

    wind_dir_deg = np.rad2deg(wind_dir)

    plt.rcParams.update({'font.size': 11})

    # ========== 图1: 路径图 ==========
    fig1, ax1 = plt.subplots(figsize=(10, 8))
    sc = ax1.scatter(x[:-1], y[:-1], c=steps, cmap='viridis', s=8, zorder=2)
    ax1.plot(x, y, 'b-', alpha=0.3, linewidth=1, zorder=1)
    ax1.plot(x[0], y[0], 'go', markersize=12, label='Start', zorder=3)
    ax1.plot(x[-1], y[-1], 'rs', markersize=10, label='End', zorder=3)
    if target_x is not None:
        ax1.plot(target_x, target_y, 'r*', markersize=18, label='Target', zorder=3)
        circle = plt.Circle((target_x, target_y), 5, color='red', fill=False,
                             linestyle='--', linewidth=1.5, label='Target radius (5m)')
        ax1.add_patch(circle)

    # 每隔一定步数画航向箭头
    arrow_interval = max(1, len(steps) // 20)
    for i in range(0, len(steps), arrow_interval):
        dx = np.cos(obs[i, 3]) * 3
        dy = np.sin(obs[i, 3]) * 3
        ax1.annotate('', xy=(x[i] + dx, y[i] + dy), xytext=(x[i], y[i]),
                     arrowprops=dict(arrowstyle='->', color='red', lw=1.2))

    plt.colorbar(sc, ax=ax1, label='Step')
    ax1.set_xlabel('X (m)')
    ax1.set_ylabel('Y (m)')
    ax1.set_title('Sailboat Trajectory')
    ax1.legend(loc='best')
    ax1.set_aspect('equal')
    ax1.grid(True, alpha=0.3)
    fig1.tight_layout()
    fig1.savefig(os.path.join(output_dir, 'trajectory.png'), dpi=150)
    plt.close(fig1)

    # ========== 图2: 帆角和舵角变化 ==========
    fig2, (ax2a, ax2b) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    ax2a.plot(steps, sail_deg[:-1], 'b-', linewidth=1.5, label='Sail Angle')
    ax2a.set_ylabel('Sail Angle (deg)')
    ax2a.set_title('Sail & Rudder Angle Over Time')
    ax2a.legend(loc='best')
    ax2a.grid(True, alpha=0.3)

    ax2b.plot(steps, rudder_deg[:-1], 'r-', linewidth=1.5, label='Rudder Angle')
    ax2b.set_xlabel('Step')
    ax2b.set_ylabel('Rudder Angle (deg)')
    ax2b.legend(loc='best')
    ax2b.grid(True, alpha=0.3)

    fig2.tight_layout()
    fig2.savefig(os.path.join(output_dir, 'sail_rudder_angles.png'), dpi=150)
    plt.close(fig2)

    # ========== 图3: 动作指令(agent输出) ==========
    fig3, (ax3a, ax3b) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    act_sail_deg = np.rad2deg(actions[:, 0])
    act_rudder_deg = np.rad2deg(actions[:, 1])

    ax3a.plot(steps, act_sail_deg, 'b-', linewidth=1.2, label='Sail Command')
    ax3a.set_ylabel('Sail Command (deg)')
    ax3a.set_title('Action Commands Sent to Environment')
    ax3a.legend(loc='best')
    ax3a.grid(True, alpha=0.3)

    ax3b.plot(steps, act_rudder_deg, 'r-', linewidth=1.2, label='Rudder Command')
    ax3b.set_xlabel('Step')
    ax3b.set_ylabel('Rudder Command (deg)')
    ax3b.legend(loc='best')
    ax3b.grid(True, alpha=0.3)

    fig3.tight_layout()
    fig3.savefig(os.path.join(output_dir, 'action_commands.png'), dpi=150)
    plt.close(fig3)

    # ========== 图4: 奖励变化 ==========
    fig4, ax4 = plt.subplots(figsize=(12, 4))
    ax4.plot(steps, rewards, 'g-', linewidth=1, alpha=0.6, label='Step Reward')
    # 累计奖励
    cumulative_rewards = np.cumsum(rewards)
    ax4_twin = ax4.twinx()
    ax4_twin.plot(steps, cumulative_rewards, 'b-', linewidth=1.5, label='Cumulative Reward')
    ax4_twin.set_ylabel('Cumulative Reward', color='b')

    ax4.set_xlabel('Step')
    ax4.set_ylabel('Step Reward', color='g')
    ax4.set_title('Reward Over Time')
    ax4.grid(True, alpha=0.3)

    lines1, labels1 = ax4.get_legend_handles_labels()
    lines2, labels2 = ax4_twin.get_legend_handles_labels()
    ax4.legend(lines1 + lines2, labels1 + labels2, loc='best')

    fig4.tight_layout()
    fig4.savefig(os.path.join(output_dir, 'rewards.png'), dpi=150)
    plt.close(fig4)

    # ========== 图5: 风场信息 ==========
    fig5, (ax5a, ax5b) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    ax5a.plot(steps, wind_speed, 'm-', linewidth=1.5, label='Wind Speed')
    ax5a.set_ylabel('Wind Speed (m/s)')
    ax5a.set_title('Wind Conditions Over Time')
    ax5a.legend(loc='best')
    ax5a.grid(True, alpha=0.3)

    ax5b.plot(steps, wind_dir_deg, 'c-', linewidth=1.5, label='Wind Direction')
    ax5b.set_xlabel('Step')
    ax5b.set_ylabel('Wind Direction (deg)')
    ax5b.legend(loc='best')
    ax5b.grid(True, alpha=0.3)

    fig5.tight_layout()
    fig5.savefig(os.path.join(output_dir, 'wind_info.png'), dpi=150)
    plt.close(fig5)

    # ========== 图6: 速度和航向角 ==========
    fig6, (ax6a, ax6b) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    ax6a.plot(steps, speed_u[:-1], 'b-', linewidth=1.5, label='Forward Speed (u)')
    ax6a.set_ylabel('Speed (m/s)')
    ax6a.set_title('Speed & Heading Over Time')
    ax6a.legend(loc='best')
    ax6a.grid(True, alpha=0.3)

    ax6b.plot(steps, psi_deg[:-1], 'r-', linewidth=1.5, label='Heading (psi)')
    ax6b.set_xlabel('Step')
    ax6b.set_ylabel('Heading (deg)')
    ax6b.legend(loc='best')
    ax6b.grid(True, alpha=0.3)

    fig6.tight_layout()
    fig6.savefig(os.path.join(output_dir, 'speed_heading.png'), dpi=150)
    plt.close(fig6)

    print(f'Plots saved to {output_dir}')


if __name__ == '__main__':
    opt = parse_args()
    run_test(opt)
