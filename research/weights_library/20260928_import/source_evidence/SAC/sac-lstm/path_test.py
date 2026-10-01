from utils_lstm_normal_deep import str2bool, Action_adapter
from SAC_lstm_normal_deep import SAC_lstm_countinuous
import gymnasium as gym
import os
import argparse
import torch
import numpy as np
import matplotlib.pyplot as plt
from multiprocessing import Pool
import time

# 定义命令行参数
parser = argparse.ArgumentParser()
parser.add_argument('--dvc', type=str, default='cpu', help='running device: cuda or cpu')
parser.add_argument('--EnvIdex', type=int, default=0, help='Environment index')
parser.add_argument('--ModelIdex', type=int, default=10800, help='which model to load')
parser.add_argument('--wind_angle', type=int, default=1, help='Wind direction angle in degrees (0-360)')
parser.add_argument('--num_experiments', type=int, default=100, help='Number of test experiments to run')
parser.add_argument('--seed', type=int, default=0, help='random seed')
parser.add_argument('--max_e_steps', type=int, default=1000, help='Max steps per episode')
parser.add_argument('--num_parallel', type=int, default=10, help='Number of parallel workers (1=sequential)')

# 模型参数
parser.add_argument('--gamma', type=float, default=0.98, help='Discounted Factor')
parser.add_argument('--net_width', type=int, default=256, help='Hidden net width')
parser.add_argument('--a_lr', type=float, default=1e-4, help='Learning rate of actor')
parser.add_argument('--c_lr', type=float, default=1e-4, help='Learning rate of critic')
parser.add_argument('--batch_size', type=int, default=256, help='batch_size of training')
parser.add_argument('--alpha', type=float, default=0.2, help='Entropy coefficient')
parser.add_argument('--adaptive_alpha', type=str2bool, default=True, help='Use adaptive_alpha or Not')
parser.add_argument('--num_envs', type=int, default=1, help='Number of parallel environments')

opt = parser.parse_args()
opt.dvc = torch.device(opt.dvc)

# 定义环境名称
EnvName = ['sailboat-s14-obst-v2']
BrifEnvName = ['saclstm_s14_obst_1230']

print("=" * 80)
print("路径测试程序启动")
if opt.num_parallel > 1:
    print(f"并行模式: {opt.num_parallel} 个工作进程")
else:
    print("串行模式")
print("=" * 80)


def run_single_experiment(args):
    """运行单个实验的函数（用于并行处理）"""
    exp_idx, seed, env_name, model_params, max_steps = args
    
    try:
        # 创建环境
        env = gym.make(env_name)
        env.reset(seed=seed + exp_idx)
        
        # 重新创建agent（每个进程需要独立的模型实例）
        agent = SAC_lstm_countinuous(**model_params)
        
        # 加载模型
        model_name = model_params['model_name']
        model_idx = model_params['model_idx']
        agent.load(model_name, model_idx)
        
        # 重置环境
        s, info = env.reset(seed=seed + exp_idx)
        
        # 初始化LSTM隐藏状态
        prev_state = s.copy()
        prev_action = np.zeros(model_params['action_dim'])
        test_env_id = f"test_env_exp_{exp_idx}"
        agent.actor.reset_hidden_state(test_env_id)
        
        # 存储轨迹
        trajectory = [[s[0], s[1]]]
        
        step = 0
        total_reward = 0
        done = False
        
        # 运行episode
        while not done and step < max_steps:
            # 选择动作
            a = agent.select_action(prev_state, prev_action, s, deterministic=True, 
                                   total_steps=None, env_id=test_env_id)
            
            # 转换动作
            act = Action_adapter(a, model_params['max_action'])
            
            # 执行动作
            s_next, r, dw, tr, info = env.step(act)
            
            # 保存坐标
            trajectory.append([s_next[0], s_next[1]])
            
            # 累计奖励
            total_reward += r
            
            # 更新状态
            done = (dw or tr)
            prev_state = s.copy()
            prev_action = a.copy()
            s = s_next
            step += 1
        
        env.close()
        
        # 返回结果
        return {
            'experiment': exp_idx + 1,
            'trajectory': np.array(trajectory),
            'steps': step,
            'total_reward': total_reward,
            'avg_reward': total_reward / step if step > 0 else 0,
            'end_x': trajectory[-1][0],
            'end_y': trajectory[-1][1],
            'success': True
        }
        
    except Exception as e:
        print(f"实验 {exp_idx + 1} 失败: {e}")
        return {
            'experiment': exp_idx + 1,
            'success': False,
            'error': str(e)
        }


def run_experiments_sequential(opt):
    """串行运行实验"""
    # 创建环境获取参数
    env = gym.make(EnvName[opt.EnvIdex])
    env.reset(seed=opt.seed)
    state_dim = env.observation_space.shape[0]
    action_dim = env.observation_space.shape[0]
    max_action = env.action_space.high.astype(float)
    env.close()
    
    # 准备模型参数
    opt.state_dim = state_dim
    opt.action_dim = action_dim
    opt.max_action = max_action
    
    # 加载模型
    agent = SAC_lstm_countinuous(**vars(opt))
    
    # 检查模型文件
    model_files = [
        f'./model/{BrifEnvName[opt.EnvIdex]}_actor{opt.ModelIdex}.pth',
        f'./model/{BrifEnvName[opt.EnvIdex]}_q_critic{opt.ModelIdex}.pth',
        f'./model/{BrifEnvName[opt.EnvIdex]}_normalizer{opt.ModelIdex}.pth'
    ]
    
    for model_file in model_files:
        if not os.path.exists(model_file):
            print(f"模型文件不存在: {model_file}")
            exit()
    
    try:
        agent.load(BrifEnvName[opt.EnvIdex], opt.ModelIdex)
        print(f"✓ 成功加载模型: {BrifEnvName[opt.EnvIdex]}_{opt.ModelIdex}")
    except Exception as e:
        print(f"✗ 加载模型失败: {e}")
        exit()
    
    all_trajectories = []
    experiment_stats = []
    
    print(f"\n开始进行 {opt.num_experiments} 次路径测试...")
    print("=" * 80)
    
    start_time = time.time()
    
    # 串行执行
    for exp_idx in range(opt.num_experiments):
        env = gym.make(EnvName[opt.EnvIdex])
        s, info = env.reset(seed=opt.seed + exp_idx)
        
        # 初始化LSTM
        prev_state = s.copy()
        prev_action = np.zeros(opt.action_dim)
        test_env_id = f"test_env_exp_{exp_idx}"
        agent.actor.reset_hidden_state(test_env_id)
        
        # 存储轨迹
        trajectory = [[s[0], s[1]]]
        
        step = 0
        total_reward = 0
        done = False
        
        while not done and step < opt.max_e_steps:
            a = agent.select_action(prev_state, prev_action, s, deterministic=True, 
                                   total_steps=None, env_id=test_env_id)
            act = Action_adapter(a, opt.max_action)
            s_next, r, dw, tr, info = env.step(act)
            
            trajectory.append([s_next[0], s_next[1]])
            total_reward += r
            
            done = (dw or tr)
            prev_state = s.copy()
            prev_action = a.copy()
            s = s_next
            step += 1
        
        env.close()
        
        # 保存结果
        all_trajectories.append(np.array(trajectory))
        experiment_stats.append({
            'experiment': exp_idx + 1,
            'steps': step,
            'total_reward': total_reward,
            'avg_reward': total_reward / step if step > 0 else 0,
            'end_x': trajectory[-1][0],
            'end_y': trajectory[-1][1]
        })
        
        print(f"实验 {exp_idx + 1:3d}/{opt.num_experiments}: "
              f"步数={step:4d}, 总奖励={total_reward:8.2f}, "
              f"平均奖励={total_reward/step:6.2f}")
    
    elapsed_time = time.time() - start_time
    print(f"\n耗时: {elapsed_time:.2f} 秒")
    
    return all_trajectories, experiment_stats


def run_experiments_parallel(opt):
    """并行运行实验"""
    # 创建环境获取参数
    env = gym.make(EnvName[opt.EnvIdex])
    env.reset(seed=opt.seed)
    state_dim = env.observation_space.shape[0]
    action_dim = env.action_space.shape[0]
    max_action = env.action_space.high.astype(float)
    env.close()
    
    # 检查模型文件
    model_files = [
        f'./model/{BrifEnvName[opt.EnvIdex]}_actor{opt.ModelIdex}.pth',
        f'./model/{BrifEnvName[opt.EnvIdex]}_q_critic{opt.ModelIdex}.pth',
        f'./model/{BrifEnvName[opt.EnvIdex]}_normalizer{opt.ModelIdex}.pth'
    ]
    
    for model_file in model_files:
        if not os.path.exists(model_file):
            print(f"模型文件不存在: {model_file}")
            exit()
    
    print(f"✓ 模型文件检查完成")
    
    # 准备模型参数（用于传递给子进程）
    model_params = {
        'state_dim': state_dim,
        'action_dim': action_dim,
        'max_action': max_action,
        'gamma': opt.gamma,
        'net_width': opt.net_width,
        'a_lr': opt.a_lr,
        'c_lr': opt.c_lr,
        'batch_size': opt.batch_size,
        'alpha': opt.alpha,
        'adaptive_alpha': opt.adaptive_alpha,
        'num_envs': opt.num_envs,
        'dvc': opt.dvc,
        'model_name': BrifEnvName[opt.EnvIdex],
        'model_idx': opt.ModelIdex,
        'Max_train_steps': opt.Max_train_steps if hasattr(opt, 'Max_train_steps') else int(9e6),
        'save_interval': opt.save_interval if hasattr(opt, 'save_interval') else int(9e5),
        'eval_interval': opt.eval_interval if hasattr(opt, 'eval_interval') else int(1e5),
        'update_every': opt.update_every if hasattr(opt, 'update_every') else 0
    }
    
    # 准备任务参数
    tasks = [
        (exp_idx, opt.seed, EnvName[opt.EnvIdex], model_params, opt.max_e_steps)
        for exp_idx in range(opt.num_experiments)
    ]
    
    print(f"\n开始进行 {opt.num_experiments} 次路径测试（使用 {opt.num_parallel} 个并行工作进程）...")
    print("=" * 80)
    
    start_time = time.time()
    
    # 使用进程池并行执行
    with Pool(processes=opt.num_parallel) as pool:
        results = pool.map(run_single_experiment, tasks)
    
    elapsed_time = time.time() - start_time
    
    # 处理结果
    all_trajectories = []
    experiment_stats = []
    
    for result in results:
        if result['success']:
            all_trajectories.append(result['trajectory'])
            experiment_stats.append({
                'experiment': result['experiment'],
                'steps': result['steps'],
                'total_reward': result['total_reward'],
                'avg_reward': result['avg_reward'],
                'end_x': result['end_x'],
                'end_y': result['end_y']
            })
            print(f"实验 {result['experiment']:3d}/{opt.num_experiments}: "
                  f"步数={result['steps']:4d}, 总奖励={result['total_reward']:8.2f}, "
                  f"平均奖励={result['avg_reward']:6.2f}")
        else:
            print(f"实验 {result['experiment']} 失败: {result.get('error', 'Unknown error')}")
    
    print(f"\n耗时: {elapsed_time:.2f} 秒")
    print(f"加速比: {elapsed_time / (elapsed_time / opt.num_parallel if opt.num_parallel > 1 else 1):.2f}x")
    
    return all_trajectories, experiment_stats


# 主程序
if __name__ == '__main__':
    # 根据并行设置选择执行方式
    if opt.num_parallel > 1:
        all_trajectories, experiment_stats = run_experiments_parallel(opt)
    else:
        all_trajectories, experiment_stats = run_experiments_sequential(opt)
    
    print("\n" + "=" * 80)
    print(f"✓ 所有 {len(all_trajectories)} 次实验完成!")
    
    # 文件保存路径
    desktop_path = 'C:\\Users\\24809\\Desktop\\'
    file_suffix = f"_model{opt.ModelIdex}_wind{opt.wind_angle}deg_{opt.num_experiments}exps"
    
    # 保存数据
    print("\n保存数据...")
    try:
        # 保存为numpy格式
        np.save(desktop_path + f'trajectories{file_suffix}.npy', 
                all_trajectories, allow_pickle=True)
        print(f"✓ 轨迹数据已保存: trajectories{file_suffix}.npy")
        
        # 保存为文本格式
        with open(desktop_path + f'trajectories{file_suffix}.txt', 'w') as f:
            f.write(f"# 路径测试数据\n")
            f.write(f"# 模型: {BrifEnvName[opt.EnvIdex]}_{opt.ModelIdex}\n")
            f.write(f"# 实验次数: {opt.num_experiments}\n")
            f.write(f"# 风向角度: {opt.wind_angle}度\n")
            f.write(f"# 并行工作进程: {opt.num_parallel}\n")
            f.write(f"# 格式: 每个实验以 'Experiment N:' 开头，后跟 x,y 坐标\n\n")
            
            for exp_idx, traj in enumerate(all_trajectories):
                f.write(f"Experiment {exp_idx + 1}:\n")
                np.savetxt(f, traj, delimiter=',', fmt='%.6f')
                f.write("\n")
        
        print(f"✓ 轨迹数据已保存: trajectories{file_suffix}.txt")
        
        # 保存统计信息
        with open(desktop_path + f'trajectory_stats{file_suffix}.txt', 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("实验统计信息\n")
            f.write("=" * 80 + "\n\n")
            
            for stat in experiment_stats:
                f.write(f"实验 {stat['experiment']:3d}: "
                       f"步数={stat['steps']:4d}, "
                       f"总奖励={stat['total_reward']:8.2f}, "
                       f"平均奖励={stat['avg_reward']:6.2f}, "
                       f"终点=({stat['end_x']:8.2f}, {stat['end_y']:8.2f})\n")
            
            # 计算总体统计
            steps_list = [s['steps'] for s in experiment_stats]
            rewards_list = [s['total_reward'] for s in experiment_stats]
            avg_rewards_list = [s['avg_reward'] for s in experiment_stats]
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("总体统计:\n")
            f.write("=" * 80 + "\n")
            f.write(f"平均步数:     {np.mean(steps_list):8.2f} ± {np.std(steps_list):.2f}\n")
            f.write(f"平均总奖励:   {np.mean(rewards_list):8.2f} ± {np.std(rewards_list):.2f}\n")
            f.write(f"平均单步奖励: {np.mean(avg_rewards_list):8.2f} ± {np.std(avg_rewards_list):.2f}\n")
            f.write(f"最大总奖励:   {np.max(rewards_list):8.2f}\n")
            f.write(f"最小总奖励:   {np.min(rewards_list):8.2f}\n")
        
        print(f"✓ 统计信息已保存: trajectory_stats{file_suffix}.txt")
        
    except Exception as e:
        print(f"✗ 保存数据时出错: {e}")
        import traceback
        traceback.print_exc()
    
    # 绘制所有轨迹
    print("\n绘制轨迹图...")
    try:
        fig, ax = plt.subplots(figsize=(14, 12))
        
        # 使用不同颜色绘制轨迹
        if opt.num_experiments <= 20:
            colors = plt.cm.tab20(np.linspace(0, 1, opt.num_experiments))
            show_legend = True
        else:
            colors = plt.cm.viridis(np.linspace(0, 1, opt.num_experiments))
            show_legend = False
        
        # 绘制每条轨迹
        for exp_idx, (traj, color) in enumerate(zip(all_trajectories, colors)):
            x = traj[:, 0]
            y = traj[:, 1]
            
            if show_legend:
                label = f'Exp {exp_idx + 1}'
            else:
                label = 'Trajectory' if exp_idx == 0 else None
            
            ax.plot(x, y, color=color, linewidth=1.5, alpha=0.7, label=label)
            ax.plot(x[0], y[0], 'o', color='green', markersize=6, alpha=0.8, 
                    markeredgecolor='darkgreen', markeredgewidth=1)
            ax.plot(x[-1], y[-1], 's', color='red', markersize=6, alpha=0.8,
                    markeredgecolor='darkred', markeredgewidth=1)
        
        # 图例标记
        ax.plot([], [], 'o', color='green', markersize=8, 
                markeredgecolor='darkgreen', markeredgewidth=1, label='Start Point')
        ax.plot([], [], 's', color='red', markersize=8, 
                markeredgecolor='darkred', markeredgewidth=1, label='End Point')
        
        # 设置图表
        ax.set_title(f'All Trajectories ({opt.num_experiments} Experiments)\n'
                     f'Model: {BrifEnvName[opt.EnvIdex]}_{opt.ModelIdex}', 
                     fontsize=16, fontweight='bold')
        ax.set_xlabel('X Coordinate (m)', fontsize=14)
        ax.set_ylabel('Y Coordinate (m)', fontsize=14)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_aspect('equal', adjustable='box')
        
        # 设置图例
        if show_legend:
            if opt.num_experiments <= 10:
                ax.legend(loc='best', fontsize=9, ncol=2, framealpha=0.9)
            else:
                ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), 
                         fontsize=8, ncol=1, framealpha=0.9)
        else:
            ax.legend(loc='best', fontsize=10, framealpha=0.9)
        
        plt.tight_layout()
        plt.savefig(desktop_path + f'trajectories{file_suffix}.png', 
                    dpi=300, bbox_inches='tight')
        print(f"✓ 轨迹图已保存: trajectories{file_suffix}.png")
        plt.show()
        
    except Exception as e:
        print(f"✗ 绘图时出错: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("✓ 所有测试完成")
    print("=" * 80)
    
    # 使用说明
    print("\n" + "=" * 80)
    print("数据加载示例:")
    print("=" * 80)
    print(f"""
# 加载轨迹数据:
import numpy as np
import matplotlib.pyplot as plt

trajectories = np.load('trajectories{file_suffix}.npy', allow_pickle=True)

# 访问轨迹
for i, traj in enumerate(trajectories):
    plt.plot(traj[:, 0], traj[:, 1], alpha=0.7)
plt.xlabel('X (m)')
plt.ylabel('Y (m)')
plt.axis('equal')
plt.show()
""")
    print("=" * 80)