import os
import sys
import torch
import numpy as np
import gymnasium as gym
import argparse
from collections import deque
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # 3D绘图

# 添加路径以正确导入模块
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from utils_lstm_att_normal import str2bool, Action_adapter
from SAC_lstm_att_normal import SAC_lstm_countinuous

def collect_data(agent, env, max_steps, seq_len, action_dim, state_dim, max_action, device):
    """收集状态和奖励数据"""
    states = []
    rewards = []
    
    s_raw, _ = env.reset()
    
    # 初始化序列缓存 (与训练时一致)
    state_buffer = deque(maxlen=seq_len)
    action_buffer = deque(maxlen=seq_len)
    
    # 填充初始缓存
    for _ in range(seq_len):
        state_buffer.append(s_raw)
        action_buffer.append(np.zeros(action_dim))
        
    prev_state = s_raw.copy()
    prev_action = np.zeros(action_dim)
    current_state = s_raw.copy()
    
    print(f"正在采集 {max_steps} 步数据...")
    
    step = 0
    episode_count = 0
    
    while step < max_steps:
        try:
            # 选择动作 (使用确定性策略进行评估)
            a = agent.select_action(prev_state, prev_action, current_state, 
                                  deterministic=True, total_steps=0, env_id=0)
            
            # 执行动作
            act = Action_adapter(a, max_action)
            s_next, r, terminated, truncated, _ = env.step(act)
            done = terminated or truncated
            
            # 记录数据 (当前状态, 获得的奖励)
            states.append(current_state.copy())
            rewards.append(r)
            
            # 更新缓存
            state_buffer.append(s_next)
            action_buffer.append(a)
            
            # 更新指针
            prev_state = current_state.copy()
            prev_action = a.copy()
            current_state = s_next.copy()
            
            step += 1
            
            if step % 500 == 0:
                print(f"已采集 {step}/{max_steps} 步数据")
            
            if done:
                episode_count += 1
                s_raw, _ = env.reset()
                
                # 重置缓存
                state_buffer.clear()
                action_buffer.clear()
                for _ in range(seq_len):
                    state_buffer.append(s_raw)
                    action_buffer.append(np.zeros(action_dim))
                prev_state = s_raw.copy()
                prev_action = np.zeros(action_dim)
                current_state = s_raw.copy()
                
                # 重置隐藏状态
                if hasattr(agent.actor, 'reset_hidden_state'):
                    agent.actor.reset_hidden_state(env_id=0)
                    
        except Exception as e:
            print(f"采集数据时出错: {e}")
            break
            
    print(f"数据采集完成！共采集 {len(states)} 个样本，{episode_count} 个回合")
    return np.array(states), np.array(rewards)

def main():
    parser = argparse.ArgumentParser()
    # 基础参数 (保持与训练脚本一致)
    parser.add_argument('--dvc', type=str, default='cpu', help='running device: cuda or cpu')
    parser.add_argument('--EnvIdex', type=int, default=0, help='PV1, Lch_Cv2, Humanv4, HCv4, BWv3, BWHv3')
    parser.add_argument('--Loadmodel', type=str2bool, default=True, help='Load pretrained model or Not')
    parser.add_argument('--ModelIdex', type=int, default=12600, help='which model to load (timestep)')
    
    # 模型参数 (需要与训练时一致)
    parser.add_argument('--seed', type=int, default=0, help='random seed')
    parser.add_argument('--gamma', type=float, default=0.98, help='Discounted Factor')
    parser.add_argument('--net_width', type=int, default=256, help='Hidden net width')
    parser.add_argument('--a_lr', type=float, default=5e-5, help='Learning rate of actor')
    parser.add_argument('--c_lr', type=float, default=5e-5, help='Learning rate of critic')
    parser.add_argument('--batch_size', type=int, default=256, help='batch_size')
    parser.add_argument('--alpha', type=float, default=0.2, help='Entropy coefficient')
    parser.add_argument('--adaptive_alpha', type=str2bool, default=True, help='Use adaptive_alpha')
    
    # 可视化特定参数
    parser.add_argument('--collect_steps', type=int, default=10000, help='采集多少步数据用于可视化')
    parser.add_argument('--pca_components', type=int, default=3, help='PCA降维目标维度: 2 或 3')

    opt = parser.parse_args()
    
    # 设置设备
    if opt.dvc == 'cuda' and torch.cuda.is_available():
        opt.dvc = torch.device('cuda')
        print("使用 CUDA 设备")
    else:
        opt.dvc = torch.device('cpu')
        print("使用 CPU 设备")
    
    # 设置随机种子
    np.random.seed(opt.seed)
    torch.manual_seed(opt.seed)
    
    # 环境名称配置
    EnvName = ['sailboat-s14-obst-v2']
    BrifEnvName = ['saclstm_s14obst_1216'] 
    
    print(f"创建环境: {EnvName[opt.EnvIdex]}")
    
    try:
        # 构建环境
        env = gym.make(EnvName[opt.EnvIdex])
        opt.state_dim = env.observation_space.shape[0]
        opt.action_dim = env.action_space.shape[0]
        opt.max_action = env.action_space.high.astype(float)
        
        print(f'环境: {EnvName[opt.EnvIdex]}')
        print(f'状态维度: {opt.state_dim}')
        print(f'动作维度: {opt.action_dim}')
        print(f'最大动作: {opt.max_action}')
        
    except Exception as e:
        print(f"创建环境失败: {e}")
        print("请确保环境已正确注册")
        return
    
    # 构建模型
    print("初始化 SAC 模型...")
    agent = SAC_lstm_countinuous(**vars(opt))
    
    # 加载模型
    if opt.Loadmodel:
        model_path = os.path.join(current_dir, "..", "..", "model")
        model_name = f"{BrifEnvName[opt.EnvIdex]}_actor{opt.ModelIdex}.pth"
        full_path = os.path.join(model_path, model_name)
        
        if not os.path.exists(full_path):
            print(f"警告: 模型文件不存在: {full_path}")
            print("将使用未训练的模型进行可视化")
        else:
            print(f"加载模型: {BrifEnvName[opt.EnvIdex]} at step {opt.ModelIdex}")
            try:
                agent.load(BrifEnvName[opt.EnvIdex], opt.ModelIdex)
                print("模型加载成功!")
            except Exception as e:
                print(f"模型加载失败: {e}")
                print("将使用未训练的模型进行可视化")
    
    # 1. 采集数据
    print("\n" + "="*50)
    states, rewards = collect_data(agent, env, opt.collect_steps, 5, 
                                   opt.action_dim, opt.state_dim, 
                                   opt.max_action, opt.dvc)
    
    if len(states) == 0:
        print("错误: 未能采集到数据")
        return
    
    print(f"\n采集的数据统计:")
    print(f"  状态数量: {states.shape[0]}")
    print(f"  状态维度: {states.shape[1]}")
    print(f"  奖励范围: [{rewards.min():.4f}, {rewards.max():.4f}]")
    print(f"  平均奖励: {rewards.mean():.4f}")
    print(f"  奖励标准差: {rewards.std():.4f}")
    
    # 新增：使用训练时的 normalizer 归一化状态
    print(f"\n对状态进行归一化...")
    with torch.no_grad():
        states_tensor = torch.FloatTensor(states).to(opt.dvc)
        states_normalized = agent.state_normalizer.normalize(states_tensor)
        states_normalized = states_normalized.cpu().numpy()

    print(f"归一化前状态范围示例 (前3维):")
    for i in range(min(3, states.shape[1])):
        print(f"  维度{i}: [{states[:, i].min():.4f}, {states[:, i].max():.4f}]")

    print(f"归一化后状态范围示例 (前3维):")
    for i in range(min(3, states_normalized.shape[1])):
        print(f"  维度{i}: [{states_normalized[:, i].min():.4f}, {states_normalized[:, i].max():.4f}]")

    # 2. 执行 PCA（使用归一化后的状态）
    print("\n" + "="*50)

    # # 先用所有维度做 PCA 看整体情况
    # print(f"完整 PCA 分析 (所有 {states_normalized.shape[1]} 个主成分)...")
    # pca_full = PCA()
    # pca_full.fit(states_normalized)

    # print(f"\n各主成分解释方差比:")
    # for i, var_ratio in enumerate(pca_full.explained_variance_ratio_[:10]):  # 显示前10个
    #     cumsum = pca_full.explained_variance_ratio_[:i+1].sum()
    #     print(f"  PC{i+1}: {var_ratio:.4f} (累计: {cumsum:.4f})")

    # # 绘制累计方差曲线
    # plt.figure(figsize=(10, 6))
    # cumsum_variance = np.cumsum(pca_full.explained_variance_ratio_)
    # plt.plot(range(1, len(cumsum_variance)+1), cumsum_variance, 'bo-', linewidth=2, markersize=8)
    # plt.axhline(y=0.8, color='r', linestyle='--', label='80% 解释方差')
    # plt.axhline(y=0.9, color='g', linestyle='--', label='90% 解释方差')
    # plt.xlabel('主成分数量')
    # plt.ylabel('累计解释方差比')
    # plt.title('PCA 累计解释方差曲线')
    # plt.grid(True, alpha=0.3)
    # plt.legend()
    # plt.savefig(os.path.join(current_dir, f'pca_variance_{BrifEnvName[opt.EnvIdex]}_{opt.ModelIdex}.png'), dpi=300)
    # plt.show()

    # # 找出达到 80% 和 90% 需要的主成分数
    # n_components_80 = np.argmax(cumsum_variance >= 0.8) + 1
    # n_components_90 = np.argmax(cumsum_variance >= 0.9) + 1
    # print(f"\n达到 80% 解释方差需要: {n_components_80} 个主成分")
    # print(f"达到 90% 解释方差需要: {n_components_90} 个主成分")

    # # 然后再用指定维度进行可视化
    # print(f"\n对 {states_normalized.shape[0]} 个归一化状态进行 PCA 降维 (目标维度: {opt.pca_components})...")
    pca = PCA(n_components=opt.pca_components)
    states_pca = pca.fit_transform(states_normalized)

    print(f"PCA 降维完成!")
    print(f"解释方差比: {pca.explained_variance_ratio_}")
    print(f"累计解释方差: {pca.explained_variance_ratio_.sum():.4f}")
    
    # 3. 绘图
    print("\n" + "="*50)
    print("生成可视化图表...")
    
    if opt.pca_components == 2:
        plt.figure(figsize=(10, 8))
        # c=rewards 设置颜色根据奖励值变化
        sc = plt.scatter(states_pca[:, 0], states_pca[:, 1], c=rewards, 
                        cmap='viridis', alpha=0.6, s=15, edgecolors='none')
        plt.colorbar(sc, label='Reward')
        plt.xlabel('Principal Component 1')
        plt.ylabel('Principal Component 2')
        plt.title(f'Reward Distribution in State Space (PCA 2D)\n'
                 f'Env: {EnvName[opt.EnvIdex]}, Model: {opt.ModelIdex}')
        plt.grid(True, alpha=0.3)
        
        # 保存图像
        save_path = os.path.join(current_dir, 
                                f'reward_pca2d_{BrifEnvName[opt.EnvIdex]}_{opt.ModelIdex}.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"图像已保存至: {save_path}")
        
        plt.show()
        
    elif opt.pca_components == 3:
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')
        sc = ax.scatter(states_pca[:, 0], states_pca[:, 1], states_pca[:, 2], 
                       c=rewards, cmap='viridis', alpha=0.6, s=15, edgecolors='none')
        cbar = fig.colorbar(sc, label='Reward', pad=0.1)
        ax.set_xlabel('Principal Component 1')
        ax.set_ylabel('Principal Component 2')
        ax.set_zlabel('Principal Component 3')
        ax.set_title(f'Reward Distribution in State Space (PCA 3D)\n'
                    f'Env: {EnvName[opt.EnvIdex]}, Model: {opt.ModelIdex}')
        
        # 保存图像
        save_path = os.path.join(current_dir, 
                                f'reward_pca3d_{BrifEnvName[opt.EnvIdex]}_{opt.ModelIdex}.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"图像已保存至: {save_path}")
        
        plt.show()
    else:
        print(f"错误: pca_components 必须是 2 或 3，当前值为 {opt.pca_components}")
    
    env.close()
    print("\n可视化完成!")

if __name__ == '__main__':
    main()