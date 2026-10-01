"""
基于状态分布的输入特征敏感性分析

方法说明：
  1. 加载训练好的SAC-LSTM模型，在环境中采集大量状态样本
  2. 计算每个状态维度的梯度敏感度 |∂a/∂s_i|
  3. 计算各维度在真实运行中的标准差 σ_i
  4. 方差加权敏感度 = |∂a/∂s_i| × σ_i
     - 若某变量梯度大但实际变化极小，其加权敏感度自然被压低
     - 反映各变量在真实控制过程中的实际贡献

输出：
  - 梯度敏感度、标准差、加权敏感度的柱状图对比
  - 数值结果表格（打印到控制台）
"""

import os, sys
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import argparse
import numpy as np
import torch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import rcParams
from collections import deque

# 设置中文字体
rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
rcParams['axes.unicode_minus'] = False

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils_lstm import Actor, ZScoreNormalizer
from SAC_lstm import SAC_lstm_countinuous
import gymnasium as gym
import globals
from stable_baselines3.common.vec_env import SubprocVecEnv


def make_env(env_id, seed):
    def _init():
        env = gym.make(env_id)
        env.reset(seed=seed)
        return env
    return _init


# 14维状态变量名称及物理含义
STATE_NAMES = [
    r'$x$',           # 0: 位置x (m)
    r'$y$',           # 1: 位置y (m)
    r'$\phi$',        # 2: 横摇角 (rad)
    r'$\psi$',        # 3: 艏向角 (rad)
    r'$u$',           # 4: 纵荡速度 (m/s)
    r'$v$',           # 5: 横荡速度 (m/s)
    r'$p$',           # 6: 横摇角速度 (rad/s)
    r'$r$',           # 7: 艏摇角速度 (rad/s)
    r'$\delta_s$',    # 8: 帆角 (rad)
    r'$\delta_r$',    # 9: 舵角 (rad)
    r'$\Delta d$',    # 10: 到目标距离变化 (m)
    r'$\Delta x_d$',  # 11: x方向距离变化 (m)
    r'$x_t$',         # 12: 目标x (m)
    r'$y_t$',         # 13: 目标y (m)
]

STATE_DESCRIPTIONS = [
    '位置 x (m)',
    '位置 y (m)',
    '横摇角 φ (rad)',
    '艏向角 ψ (rad)',
    '纵荡速度 u (m/s)',
    '横荡速度 v (m/s)',
    '横摇角速度 p (rad/s)',
    '艏摇角速度 r (rad/s)',
    '帆角 δ_s (rad)',
    '舵角 δ_r (rad)',
    '距离变化 Δd (m)',
    'x距离变化 Δx_d (m)',
    '目标 x_t (m)',
    '目标 y_t (m)',
]


def collect_states(env, agent, max_action, num_envs, num_episodes=30, max_steps=1000):
    """使用并行环境采集真实状态样本"""
    all_states = []
    episodes_done = 0
    
    # 每个环境维护独立的 prev_state / prev_action
    s_raw = env.reset()  # (num_envs, state_dim)
    prev_states = s_raw.copy()
    prev_actions = np.zeros((num_envs, agent.action_dim))
    ep_steps = np.zeros(num_envs, dtype=int)
    
    for i in range(num_envs):
        agent.actor.reset_hidden_state(env_id=i)
    
    while episodes_done < num_episodes:
        actions = np.zeros((num_envs, agent.action_dim))
        for i in range(num_envs):
            actions[i] = agent.select_action(
                prev_states[i], prev_actions[i], s_raw[i],
                deterministic=True, total_steps=0, env_id=i
            )
        
        acts = actions * max_action
        s_next, rewards, dones, infos = env.step(acts)
        
        # 收集所有环境的当前状态
        all_states.append(s_raw.copy())  # (num_envs, state_dim)
        ep_steps += 1
        
        for i in range(num_envs):
            truncated = ep_steps[i] >= max_steps
            if dones[i] or truncated:
                episodes_done += 1
                agent.actor.reset_hidden_state(env_id=i)
                prev_states[i] = s_next[i].copy()
                prev_actions[i] = np.zeros(agent.action_dim)
                ep_steps[i] = 0
                if episodes_done >= num_episodes:
                    break
            else:
                prev_states[i] = s_raw[i].copy()
                prev_actions[i] = actions[i].copy()
        
        s_raw = s_next
    
    # (T, num_envs, state_dim) -> (T*num_envs, state_dim)
    return np.concatenate(all_states, axis=0)


def compute_gradient_sensitivity(agent, states, num_samples=2000):
    """
    计算梯度敏感度: 对采集的状态样本计算 |∂a/∂s_i| 的均值
    使用序列模式，构造虚拟历史序列以匹配训练时的输入格式
    """
    device = agent.dvc
    state_dim = agent.state_dim
    action_dim = agent.action_dim
    seq_len = agent.seq_len
    
    # 随机采样一部分状态
    indices = np.random.choice(len(states), size=min(num_samples, len(states)), replace=False)
    sampled_states = states[indices]
    
    grad_accum = np.zeros(state_dim)
    count = 0
    
    agent.actor.eval()
    
    batch_size = 64
    for start in range(0, len(sampled_states), batch_size):
        batch_states = sampled_states[start:start + batch_size]
        bs = len(batch_states)
        
        # 构造当前状态 (需要梯度)
        s_curr = torch.FloatTensor(batch_states).to(device)
        s_curr.requires_grad_(True)
        
        # 标准化
        s_curr_norm = agent.state_normalizer.normalize(s_curr)
        
        # 构造虚拟历史序列（使用同一状态填充 + 零动作）
        s_seq = s_curr_norm.unsqueeze(1).expand(-1, seq_len, -1).detach()  # (bs, seq_len, state_dim)
        a_seq = torch.zeros(bs, seq_len, action_dim, device=device)
        
        # 前向传播 - 序列模式
        a, _ = agent.actor(state_sequence=s_seq, action_sequence=a_seq,
                           current_state=s_curr_norm,
                           deterministic=True, with_logprob=False,
                           single_step_mode=False)
        
        # 对每个动作维度分别求梯度，然后取绝对值均值
        for a_idx in range(action_dim):
            agent.actor.zero_grad()
            if s_curr.grad is not None:
                s_curr.grad.zero_()
            
            a[:, a_idx].sum().backward(retain_graph=(a_idx < action_dim - 1))
            
            if s_curr.grad is not None:
                grad_accum += s_curr.grad.abs().mean(dim=0).cpu().numpy()
        
        count += 1
    
    grad_sensitivity = grad_accum / (count * action_dim)
    
    agent.actor.train()
    return grad_sensitivity


def run_sensitivity_analysis(env_name, model_name, model_step, device='cuda',
                             num_episodes=30, num_grad_samples=2000, num_envs=8):
    """运行完整的敏感性分析流程"""
    
    # ---- 1. 构建并行环境和agent ----
    env_fns = [make_env(env_name, seed=i) for i in range(num_envs)]
    env = SubprocVecEnv(env_fns)
    state_dim = env.observation_space.shape[0]
    action_dim = env.action_space.shape[0]
    max_action = env.action_space.high.astype(float)
    
    dvc = torch.device(device if torch.cuda.is_available() else 'cpu')
    
    # 创建agent所需的参数
    agent_kwargs = {
        'dvc': dvc,
        'state_dim': state_dim,
        'action_dim': action_dim,
        'max_action': max_action,
        'net_width': 256,
        'a_lr': 5e-5,
        'c_lr': 5e-5,
        'gamma': 0.98,
        'batch_size': 256,
        'alpha': 0.2,
        'adaptive_alpha': True,
    }
    agent = SAC_lstm_countinuous(**agent_kwargs)
    agent.load(model_name, model_step)
    agent.actor.eval()
    
    print(f"模型加载完成: {model_name}, step={model_step}")
    print(f"状态维度: {state_dim}, 动作维度: {action_dim}")
    print(f"设备: {dvc}")
    
    # ---- 2. 采集状态样本 (并行) ----
    print(f"\n[1/3] 使用 {num_envs} 个并行环境采集状态样本 ({num_episodes} episodes)...")
    states = collect_states(env, agent, max_action, num_envs=num_envs, num_episodes=num_episodes)
    print(f"  采集到 {len(states)} 个状态样本")
    
    # ---- 3. 计算各维度的统计量 ----
    print("\n[2/3] 计算状态分布统计量...")
    state_means = states.mean(axis=0)
    state_stds = states.std(axis=0)
    state_mins = states.min(axis=0)
    state_maxs = states.max(axis=0)
    
    print(f"{'维度':<6} {'名称':<25} {'均值':>10} {'标准差':>10} {'最小值':>10} {'最大值':>10}")
    print("-" * 75)
    for i in range(state_dim):
        print(f"  s[{i:2d}] {STATE_DESCRIPTIONS[i]:<25} {state_means[i]:>10.4f} {state_stds[i]:>10.4f} "
              f"{state_mins[i]:>10.4f} {state_maxs[i]:>10.4f}")
    
    # ---- 4. 计算梯度敏感度 ----
    print(f"\n[3/3] 计算梯度敏感度 ({num_grad_samples} samples)...")
    grad_sensitivity = compute_gradient_sensitivity(agent, states, num_samples=num_grad_samples)
    
    # ---- 5. 方差加权敏感度 ----
    weighted_sensitivity = grad_sensitivity * state_stds
    
    # 归一化 (方便比较)
    grad_norm = grad_sensitivity / (grad_sensitivity.max() + 1e-10)
    weighted_norm = weighted_sensitivity / (weighted_sensitivity.max() + 1e-10)
    std_norm = state_stds / (state_stds.max() + 1e-10)
    
    # ---- 6. 打印结果表 ----
    print("\n" + "=" * 95)
    print("敏感性分析结果")
    print("=" * 95)
    print(f"{'维度':<6} {'名称':<25} {'梯度敏感度':>12} {'标准差σ':>12} {'加权敏感度':>12} {'归一化加权':>12}")
    print("-" * 95)
    
    # 按加权敏感度排序
    sorted_indices = np.argsort(weighted_sensitivity)[::-1]
    for idx in sorted_indices:
        print(f"  s[{idx:2d}] {STATE_DESCRIPTIONS[idx]:<25} {grad_sensitivity[idx]:>12.6f} "
              f"{state_stds[idx]:>12.6f} {weighted_sensitivity[idx]:>12.6f} {weighted_norm[idx]:>12.4f}")
    
    # ---- 7. 绘图 ----
    fig, axes = plt.subplots(3, 1, figsize=(14, 12), dpi=150)
    x = np.arange(state_dim)
    bar_width = 0.6
    colors = plt.cm.viridis(np.linspace(0.2, 0.8, state_dim))
    
    # 子图1: 梯度敏感度 (归一化)
    ax1 = axes[0]
    bars1 = ax1.bar(x, grad_norm, width=bar_width, color=colors, edgecolor='black', linewidth=0.5)
    ax1.set_ylabel('归一化梯度敏感度', fontsize=12)
    ax1.set_title('(a) 梯度敏感度 $\\overline{|\\partial a / \\partial s_i|}$', fontsize=13)
    ax1.set_xticks(x)
    ax1.set_xticklabels(STATE_NAMES, fontsize=10)
    ax1.grid(axis='y', alpha=0.3)
    # 标注数值
    for i, v in enumerate(grad_norm):
        ax1.text(i, v + 0.02, f'{v:.2f}', ha='center', va='bottom', fontsize=7)
    
    # 子图2: 状态标准差 (归一化)
    ax2 = axes[1]
    bars2 = ax2.bar(x, std_norm, width=bar_width, color=colors, edgecolor='black', linewidth=0.5)
    ax2.set_ylabel('归一化标准差', fontsize=12)
    ax2.set_title('(b) 状态变量标准差 $\\sigma_i$', fontsize=13)
    ax2.set_xticks(x)
    ax2.set_xticklabels(STATE_NAMES, fontsize=10)
    ax2.grid(axis='y', alpha=0.3)
    for i, v in enumerate(std_norm):
        ax2.text(i, v + 0.02, f'{v:.2f}', ha='center', va='bottom', fontsize=7)
    
    # 子图3: 方差加权敏感度 (归一化)
    ax3 = axes[2]
    bars3 = ax3.bar(x, weighted_norm, width=bar_width, color=colors, edgecolor='black', linewidth=0.5)
    ax3.set_ylabel('归一化加权敏感度', fontsize=12)
    ax3.set_title('(c) 方差加权敏感度 $\\overline{|\\partial a / \\partial s_i|} \\times \\sigma_i$', fontsize=13)
    ax3.set_xticks(x)
    ax3.set_xticklabels(STATE_NAMES, fontsize=10)
    ax3.set_xlabel('状态变量', fontsize=12)
    ax3.grid(axis='y', alpha=0.3)
    for i, v in enumerate(weighted_norm):
        ax3.text(i, v + 0.02, f'{v:.2f}', ha='center', va='bottom', fontsize=7)
    
    plt.tight_layout()
    save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             f'sensitivity_{model_name}_{model_step}.png')
    plt.savefig(save_path, bbox_inches='tight')
    print(f"\n图表已保存至: {save_path}")
    plt.close()
    
    # ---- 8. 保存数值结果 ----
    results = {
        'state_names': STATE_DESCRIPTIONS,
        'state_means': state_means,
        'state_stds': state_stds,
        'state_mins': state_mins,
        'state_maxs': state_maxs,
        'grad_sensitivity': grad_sensitivity,
        'weighted_sensitivity': weighted_sensitivity,
        'grad_norm': grad_norm,
        'weighted_norm': weighted_norm,
        'num_samples': len(states),
        'num_episodes': num_episodes,
    }
    result_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               f'sensitivity_{model_name}_{model_step}.npy')
    np.save(result_path, results)
    print(f"数值结果已保存至: {result_path}")
    
    env.close()
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='基于状态分布的输入特征敏感性分析')
    parser.add_argument('--env', type=str, default='sailboat-s14-nowind',
                        help='环境名称')
    parser.add_argument('--model_name', type=str, default='saclstm_s14nowind_final',
                        help='模型前缀名 (与训练时 BrifEnvName 一致)')
    parser.add_argument('--model_step', type=int, default=9000,
                        help='模型保存时的步数标识 (k)')
    parser.add_argument('--device', type=str, default='cpu',
                        help='运行设备: cuda 或 cpu')
    parser.add_argument('--num_episodes', type=int, default=200,
                        help='采集状态样本的episode数')
    parser.add_argument('--num_grad_samples', type=int, default=2000,
                        help='用于计算梯度的采样数')
    parser.add_argument('--num_envs', type=int, default=5,
                        help='并行环境数量')
    
    args = parser.parse_args()
    
    run_sensitivity_analysis(
        env_name=args.env,
        model_name=args.model_name,
        model_step=args.model_step,
        device=args.device,
        num_episodes=args.num_episodes,
        num_grad_samples=args.num_grad_samples,
        num_envs=args.num_envs,
    )
