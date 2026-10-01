import os
import torch
import numpy as np
import gymnasium as gym
import argparse
import matplotlib.pyplot as plt
import seaborn as sns
from SAC_lstm_att_normal import SAC_lstm_countinuous
from utils_lstm_att_normal import Action_adapter, str2bool

def make_env(env_id, seed):
    def _init():
        env = gym.make(env_id)
        env.reset(seed=seed)
        return env
    return _init

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_save_dir = os.path.join(script_dir, "outputs")
    parser = argparse.ArgumentParser(description="Load model and extract attention weights")
    parser.add_argument('--dvc', type=str, default='cpu', help='running device: cuda or cpu')
    parser.add_argument('--EnvIdex', type=int, default=0, help='Index of the environment')
    parser.add_argument('--ModelIdex', type=int, default=14400, help='Model timestep to load (e.g. 4500)')
    parser.add_argument('--seed', type=int, default=0, help='random seed')
    parser.add_argument('--net_width', type=int, default=256, help='Hidden net width')
    parser.add_argument('--a_lr', type=float, default=5e-5, help='Learning rate of actor')
    parser.add_argument('--c_lr', type=float, default=5e-5, help='Learning rate of critic')
    parser.add_argument('--gamma', type=float, default=0.98, help='Discounted Factor')
    parser.add_argument('--alpha', type=float, default=0.2, help='Entropy coefficient')
    parser.add_argument('--adaptive_alpha', type=str2bool, default=True, help='Use adaptive_alpha')
    parser.add_argument('--batch_size', type=int, default=256, help='batch_size')
    parser.add_argument('--render', type=str2bool, default=False, help='Render or Not')
    parser.add_argument('--steps', type=int, default=1000, help='Number of steps to run')
    parser.add_argument('--model_name', type=str, default='saclstm_s14obst_v3_0126_20',
                        help='Model name prefix used by agent.load(model_name, ModelIdex)')
    parser.add_argument('--save_dir', type=str, default=default_save_dir, help='Directory to save outputs')
    parser.add_argument('--run_tag', type=str, default='K10', help='Optional tag appended in output filename')
    


    opt = parser.parse_args()
    opt.dvc = torch.device(opt.dvc)
    
    # 环境配置 (请确保这里与训练时的配置一致)
    EnvName = ['sailboat-s14-obst-v3']
    BrifEnvName = [opt.model_name]
    
    
    # 检查索引是否越界
    if opt.EnvIdex >= len(EnvName):
        print(f"Error: EnvIdex {opt.EnvIdex} is out of range. Available: {len(EnvName)}")
        return

    print(f"Environment: {EnvName[opt.EnvIdex]}")
    
    # 构建环境
    try:
        env = gym.make(EnvName[opt.EnvIdex], render_mode='human' if opt.render else None)
    except Exception as e:
        print(f"Error creating environment: {e}")
        return

    opt.state_dim = env.observation_space.shape[0]
    opt.action_dim = env.action_space.shape[0]
    opt.max_action = env.action_space.high.astype(float)
    
    print(f"Loading model: {BrifEnvName[opt.EnvIdex]} at step {opt.ModelIdex}")
    
    # 初始化 Agent
    agent = SAC_lstm_countinuous(**vars(opt))
    
    # 加载模型
    try:
        agent.load(BrifEnvName[opt.EnvIdex], opt.ModelIdex)
        print("Model loaded successfully.")
    except FileNotFoundError:
        print(f"Error: Model file not found for {BrifEnvName[opt.EnvIdex]} at step {opt.ModelIdex}")
        print(f"Please check the 'model' directory and ensure 'ModelIdex' is correct.")
        return

    # 注册 Hook 来捕获注意力权重
    attention_weights_history = []
    
    def attention_hook(module, input, output):
        # output 是 (context, attn_weights)
        # attn_weights shape: (batch, seq_len)
        # 我们只取第一个样本（因为评估时通常 batch=1）
        weights = output[1].detach().cpu().numpy()
        if len(weights) > 0:
            attention_weights_history.append(weights[0]) # 保存 (seq_len,)
        
    # 注册到 Actor 的 attention 层
    # 注意：这里假设 Actor 类中有一个名为 attention 的层
    hook_handle = agent.actor.attention.register_forward_hook(attention_hook)
    
    # 运行评估
    s, _ = env.reset(seed=opt.seed)
    done = False
    
    # 重置 Agent 的隐藏状态
    eval_env_id = "eval_0"
    agent.actor.reset_hidden_state(eval_env_id)
    
    prev_state = s.copy()
    prev_action = np.zeros(opt.action_dim)
    
    steps = 0
    rewards = 0
    trajectory_xy = []
    
    print(f"Running simulation for {opt.steps} steps...")
    
    while not done and steps < opt.steps:
        # 选择动作
        a = agent.select_action(prev_state, prev_action, s, deterministic=True, 
                              total_steps=0, env_id=eval_env_id)
        
        act = Action_adapter(a, opt.max_action)
        
        s_next, r, dw, tr, info = env.step(act)
        done = (dw or tr)
        trajectory_xy.append(np.asarray(s_next[:2], dtype=np.float64).copy())
        
        prev_state = s.copy()
        prev_action = a.copy()
        s = s_next
        
        rewards += r
        steps += 1
        
        if opt.render:
            env.render()

    hook_handle.remove()
    env.close()
    
    print(f"Simulation finished. Total Reward: {rewards:.2f}")
    
    if len(attention_weights_history) == 0:
        print("No attention weights collected. Check if the model uses attention.")
        return

    # 输出目录
    os.makedirs(opt.save_dir, exist_ok=True)

    # 文件名后缀
    tag = f"_{opt.run_tag}" if opt.run_tag.strip() else ""
    base_name = f"{BrifEnvName[opt.EnvIdex]}_{opt.ModelIdex}{tag}"

    # 保存注意力权重
    # 填充数据以处理可能的长度不一致（虽然在评估模式下长度应该是固定的）
    max_len = max(len(w) for w in attention_weights_history)
    padded_weights = np.zeros((len(attention_weights_history), max_len))
    for i, w in enumerate(attention_weights_history):
        padded_weights[i, :len(w)] = w

    att_weights = padded_weights # (steps, seq_len)
    att_path = os.path.join(opt.save_dir, f"attention_weights_{base_name}.npy")
    np.save(att_path, att_weights)
    print(f"Attention weights saved to {att_path}")
    print(f"Shape of weights: {att_weights.shape}")

    # 保存轨迹 (N,2)
    if len(trajectory_xy) > 0:
        traj = np.asarray(trajectory_xy, dtype=np.float64)
        traj_path = os.path.join(opt.save_dir, f"trajectory_xy_{base_name}.npy")
        np.save(traj_path, traj)
        print(f"Trajectory saved to {traj_path}, shape={traj.shape}")
    else:
        traj = None
        print("Warning: trajectory is empty.")
    
    # 绘制热力图
    plt.figure(figsize=(12, 8))
    # 转置以便 x 轴是时间步，y 轴是序列位置（历史）
    # y轴 0 表示最旧的历史，最大值表示最近的历史
    sns.heatmap(att_weights.T, cmap="viridis", cbar_kws={'label': 'Attention Weight'})
    plt.xlabel("Time Step (Simulation)")
    plt.ylabel("History Position (0=Oldest)")
    plt.title(f"Attention Weights Over Time\nModel: {BrifEnvName[opt.EnvIdex]}, Step: {opt.ModelIdex}")
    plt.tight_layout()
    
    heatmap_path = os.path.join(opt.save_dir, f"attention_weights_{base_name}.png")
    plt.savefig(heatmap_path)
    print(f"Attention heatmap saved to {heatmap_path}")

    # 额外保存一个简洁运行摘要，方便后续填配置
    summary_path = os.path.join(opt.save_dir, f"attention_run_summary_{base_name}.json")
    summary = {
        "model_name": BrifEnvName[opt.EnvIdex],
        "model_id": int(opt.ModelIdex),
        "env_name": EnvName[opt.EnvIdex],
        "attention_path": os.path.abspath(att_path),
        "trajectory_path": os.path.abspath(os.path.join(opt.save_dir, f"trajectory_xy_{base_name}.npy")) if traj is not None else "",
        "attention_shape": list(att_weights.shape),
        "trajectory_shape": list(traj.shape) if traj is not None else [],
        "total_reward": float(rewards),
        "steps": int(steps),
    }
    import json
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"Run summary saved to {summary_path}")
    # plt.show() 

if __name__ == '__main__':
    main()