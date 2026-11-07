# feature_importance_analysis.py - 改进版本 (完整可运行代码)
import torch
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
from tqdm import tqdm

class FeatureImportanceAnalyzer:
    """分析SAC LSTM模型的特征重要性 - 支持适度噪声扰动"""
    
    def __init__(self, agent, state_normalizer, device):
        self.agent = agent
        self.state_normalizer = state_normalizer
        self.device = device
        self.feature_stats = None  # 存储特征统计信息
        
    def collect_feature_statistics(self, env, n_episodes=50, n_steps_per_episode=500):
        """
        收集特征的统计信息（均值、标准差）
        这用于确定适度噪声的幅度
        
        Args:
            env: 环境
            n_episodes: episode数量
            n_steps_per_episode: 每个episode的最大步数
        
        Returns:
            dict: 包含mean, std, min, max的统计信息
        """
        print("=" * 70)
        print("收集特征统计信息中...")
        print("=" * 70)
        
        state_dim = self.agent.state_dim
        all_states = []
        
        for ep in tqdm(range(n_episodes), desc="采集样本"):
            s, _ = env.reset(seed=ep)
            eval_env_id = f"stats_{ep}"
            self.agent.actor.reset_hidden_state(eval_env_id)
            
            prev_state = s.copy()
            prev_action = np.zeros(self.agent.action_dim)
            
            for step in range(n_steps_per_episode):
                all_states.append(s.copy())
                
                action = self.agent.select_action(
                    prev_state, prev_action, s,
                    deterministic=True, total_steps=None, env_id=eval_env_id
                )
                
                from utils_lstm_att_normal import Action_adapter
                act = Action_adapter(action, self.agent.max_action)
                
                s_next, r, dw, tr, _ = env.step(act)
                
                if dw or tr:
                    break
                    
                prev_state = s.copy()
                prev_action = action.copy()
                s = s_next
        
        # 计算统计信息
        all_states = np.array(all_states)
        self.feature_stats = {
            'mean': np.mean(all_states, axis=0),
            'std': np.std(all_states, axis=0),
            'min': np.min(all_states, axis=0),
            'max': np.max(all_states, axis=0),
        }
        
        print("\n特征统计信息摘要：")
        print("-" * 70)
        for i in range(state_dim):
            mean_val = self.feature_stats['mean'][i]
            std_val = self.feature_stats['std'][i]
            min_val = self.feature_stats['min'][i]
            max_val = self.feature_stats['max'][i]
            print(f"特征{i:2d}: μ={mean_val:9.4f}, σ={std_val:9.4f}, "
                  f"范围=[{min_val:9.4f}, {max_val:9.4f}]")
        print("=" * 70)
        
        return self.feature_stats
    
    def permutation_importance(self, env, n_episodes=50, n_permutations=30, 
                               perturbation_method='modest', noise_ratio=0.2):
        """
        改进的排列重要性方法 - 使用适度噪声而不是完全随机
        
        Args:
            env: 环境
            n_episodes: episode数量
            n_permutations: 每个特征的排列次数
            perturbation_method: 扰动方法选择
                - 'random': 完全随机替换（原始方法，用于对比）
                - 'modest': 适度高斯噪声（推荐，特别是对u,v,p,r）
                - 'shuffle': 时间排列（用历史值替换）
            noise_ratio: 噪声标准差相对于特征标准差的倍数（仅当perturbation_method='modest'时有效）
        
        Returns:
            dict: {feature_idx: importance_score}
        """
        # 如果使用modest方法但还未收集统计信息，先收集
        if self.feature_stats is None and perturbation_method == 'modest':
            print("\n提示：使用modest方法需要特征统计信息，自动收集中...")
            self.collect_feature_statistics(env, n_episodes=min(20, n_episodes))
        
        state_dim = self.agent.state_dim
        baseline_rewards = []
        
        # 1. 获取基准性能
        print("\n" + "=" * 70)
        print("第1阶段：计算基准性能...")
        print("=" * 70)
        for ep in tqdm(range(n_episodes), desc="基准评估"):
            total_reward = self._run_episode(env, ep)
            baseline_rewards.append(total_reward)
        baseline_mean = np.mean(baseline_rewards)
        baseline_std = np.std(baseline_rewards)
        
        print(f"\n基准性能统计：")
        print(f"  平均奖励: {baseline_mean:.4f}")
        print(f"  标准差: {baseline_std:.4f}")
        print(f"  最小值: {min(baseline_rewards):.4f}")
        print(f"  最大值: {max(baseline_rewards):.4f}")
        
        # 2. 对每个特征进行扰动测试
        print("\n" + "=" * 70)
        print(f"第2阶段：特征重要性分析")
        print(f"扰动方法: {perturbation_method}")
        if perturbation_method == 'modest':
            print(f"噪声幅度: {noise_ratio:.1%} × 特征标准差")
        print("=" * 70)
        
        feature_importance = {}
        
        for feature_idx in tqdm(range(state_dim), desc="特征扫描"):
            permuted_rewards = []
            
            for perm in range(n_permutations):
                for ep in range(n_episodes // n_permutations):
                    total_reward = self._run_episode(
                        env, ep + perm * 10000,
                        perturb_feature=feature_idx,
                        perturbation_method=perturbation_method,
                        noise_ratio=noise_ratio
                    )
                    permuted_rewards.append(total_reward)
            
            # 性能下降 = 基准 - 扰动后
            importance = baseline_mean - np.mean(permuted_rewards)
            feature_importance[feature_idx] = importance
        
        return feature_importance
    
    def _run_episode(self, env, seed, perturb_feature=None, 
                     perturbation_method='modest', noise_ratio=0.2):
        """
        运行一个episode并返回总奖励
        
        Args:
            env: 环境
            seed: 随机种子
            perturb_feature: 要扰动的特征索引（None表示不扰动）
            perturbation_method: 扰动方法
            noise_ratio: 噪声幅度参数
        
        Returns:
            float: 总奖励
        """
        s, _ = env.reset(seed=seed)
        eval_env_id = f"importance_{seed}"
        self.agent.actor.reset_hidden_state(eval_env_id)
        
        prev_state = s.copy()
        prev_action = np.zeros(self.agent.action_dim)
        total_reward = 0
        done = False
        
        # 用于shuffle方法的历史值缓冲区
        perturb_sequence = []
        
        step = 0
        while not done:
            # 如果需要扰动某个特征
            if perturb_feature is not None:
                s_perturbed = s.copy()
                
                if perturbation_method == 'random':
                    # ===== 方法1：完全随机替换（原始方法） =====
                    s_perturbed[perturb_feature] = np.random.randn()
                    
                elif perturbation_method == 'modest':
                    # ===== 方法2：适度高斯噪声（推荐） =====
                    if self.feature_stats is not None:
                        # 基于特征统计信息的适度噪声
                        noise_std = noise_ratio * self.feature_stats['std'][perturb_feature]
                        noise = np.random.normal(0, noise_std)
                        s_perturbed[perturb_feature] += noise
                        
                        # 可选：限制在观测范围内（防止物理不合理的状态）
                        # s_perturbed[perturb_feature] = np.clip(
                        #     s_perturbed[perturb_feature],
                        #     self.feature_stats['min'][perturb_feature],
                        #     self.feature_stats['max'][perturb_feature]
                        # )
                    else:
                        # 如果没有统计信息，使用小噪声
                        s_perturbed[perturb_feature] += np.random.normal(0, 0.1)
                
                elif perturbation_method == 'shuffle':
                    # ===== 方法3：时间排列（用历史值） =====
                    if len(perturb_sequence) > 0:
                        # 从已有的值中随机选择
                        s_perturbed[perturb_feature] = np.random.choice(perturb_sequence)
                    perturb_sequence.append(s[perturb_feature])
                
                action = self.agent.select_action(
                    prev_state, prev_action, s_perturbed,
                    deterministic=True, total_steps=None, env_id=eval_env_id
                )
            else:
                action = self.agent.select_action(
                    prev_state, prev_action, s,
                    deterministic=True, total_steps=None, env_id=eval_env_id
                )
            
            # 动作适配
            from utils_lstm_att_normal import Action_adapter
            act = Action_adapter(action, self.agent.max_action)
            
            s_next, r, dw, tr, _ = env.step(act)
            done = dw or tr
            total_reward += r
            
            prev_state = s.copy()
            prev_action = action.copy()
            s = s_next
            step += 1
        
        return total_reward
    
    def integrated_gradients(self, state_seq, action_seq, current_state, 
                           baseline=None, n_steps=50):
        """
        Integrated Gradients方法
        返回: 每个特征的归因分数
        """
        if baseline is None:
            baseline = torch.zeros_like(current_state)
        
        # 创建插值路径
        alphas = torch.linspace(0, 1, n_steps, device=self.device)
        grads = []
        
        for alpha in alphas:
            # 插值状态
            interpolated_state = baseline + alpha * (current_state - baseline)
            interpolated_state.requires_grad = True
            
            # 前向传播
            action, _ = self.agent.actor(
                state_sequence=state_seq,
                action_sequence=action_seq,
                current_state=interpolated_state,
                deterministic=True,
                with_logprob=False,
                single_step_mode=False
            )
            
            # 计算梯度
            action.sum().backward()
            grads.append(interpolated_state.grad.clone())
            interpolated_state.grad.zero_()
        
        # 积分近似
        grads = torch.stack(grads)
        avg_grads = grads.mean(dim=0)
        integrated_grads = (current_state - baseline) * avg_grads
        
        return integrated_grads.abs().mean(dim=0).cpu().numpy()
    
    def attention_weights_analysis(self, env, n_episodes=20):
        """
        分析注意力权重,了解模型关注历史的哪些时刻
        """
        attention_weights_history = []
        
        for ep in tqdm(range(n_episodes)):
            s, _ = env.reset(seed=ep)
            eval_env_id = f"attention_{ep}"
            self.agent.actor.reset_hidden_state(eval_env_id)
            
            # 构建初始序列
            seq_len = self.agent.seq_len
            state_buffer = [s.copy() for _ in range(seq_len)]
            action_buffer = [np.zeros(self.agent.action_dim) for _ in range(seq_len)]
            
            prev_state = s.copy()
            prev_action = np.zeros(self.agent.action_dim)
            
            done = False
            step = 0
            while not done and step < 200:
                # 准备序列数据
                s_seq = torch.FloatTensor(np.array(state_buffer)).unsqueeze(0).to(self.device)
                a_seq = torch.FloatTensor(np.array(action_buffer)).unsqueeze(0).to(self.device)
                s_curr = torch.FloatTensor(s).unsqueeze(0).to(self.device)
                
                # 标准化
                s_seq = self.state_normalizer.normalize(s_seq)
                s_curr = self.state_normalizer.normalize(s_curr)
                
                # 前向传播并获取注意力权重
                with torch.no_grad():
                    # 预处理当前状态
                    current_state_processed = self.agent.actor.current_state_fc(s_curr)
                    
                    # 获取LSTM输出(使用序列模式)
                    sa_seq = torch.cat([s_seq, a_seq], dim=2)
                    x = self.agent.actor.fc_input(sa_seq)
                    lstm_out, _ = self.agent.actor.lstm(x)
                    lstm_out = self.agent.actor.lstm_ln(lstm_out)
                    
                    # 获取注意力权重
                    _, attn_weights = self.agent.actor.attention(
                        current_state_processed, lstm_out
                    )
                    attention_weights_history.append(attn_weights.cpu().numpy()[0])
                
                # 选择动作
                action = self.agent.select_action(
                    prev_state, prev_action, s,
                    deterministic=True, total_steps=None, env_id=eval_env_id
                )
                
                from utils_lstm_att_normal import Action_adapter
                act = Action_adapter(action, self.agent.max_action)
                
                s_next, r, dw, tr, _ = env.step(act)
                done = dw or tr
                
                # 更新缓存
                state_buffer.append(s_next.copy())
                action_buffer.append(action.copy())
                state_buffer.pop(0)
                action_buffer.pop(0)
                
                prev_state = s.copy()
                prev_action = action.copy()
                s = s_next
                step += 1
        
        return np.array(attention_weights_history)
    
    def gradient_based_importance(self, replay_buffer, n_samples=1000):
        """
        基于梯度的特征重要性
        """
        # 从replay buffer采样
        s_seq, a_seq, s_curr, a_curr, r, s_next_seq, a_next_seq, s_next_curr, dw, indices, weights = \
            replay_buffer.sample(min(n_samples, replay_buffer.size))
        
        # 标准化
        s_seq = self.state_normalizer.normalize(s_seq)
        s_curr = self.state_normalizer.normalize(s_curr)
        
        s_curr.requires_grad = True
        
        # 前向传播
        action, _ = self.agent.actor(
            state_sequence=s_seq,
            action_sequence=a_seq,
            current_state=s_curr,
            deterministic=True,
            with_logprob=False,
            single_step_mode=False
        )
        
        # 计算梯度
        action.sum().backward()
        
        # 特征重要性 = 梯度的绝对值
        importance = s_curr.grad.abs().mean(dim=0).cpu().numpy()
        
        return importance
    
    def visualize_importance(self, importance_dict, feature_names=None, 
                           save_path='feature_importance.png'):
        """
        可视化特征重要性
        
        Args:
            importance_dict: dict {feature_idx: importance_score}
            feature_names: 特征名称列表
            save_path: 保存路径
        """
        n_features = len(importance_dict)
        
        if feature_names is None:
            feature_names = [f'Feature {i}' for i in range(n_features)]
        
        # 排序
        sorted_idx = np.argsort(list(importance_dict.values()))[::-1]
        sorted_importance = [list(importance_dict.values())[i] for i in sorted_idx]
        sorted_names = [feature_names[i] for i in sorted_idx]
        
        # 绘图
        plt.figure(figsize=(12, 8))
        colors = plt.cm.RdYlGn_r(np.linspace(0.3, 0.7, n_features))
        plt.barh(range(n_features), sorted_importance, color=colors)
        plt.yticks(range(n_features), sorted_names, fontsize=11)
        plt.xlabel('Importance Score', fontsize=12)
        plt.ylabel('Features', fontsize=12)
        plt.title('Feature Importance Analysis (Modest Perturbation)', fontsize=14, fontweight='bold')
        plt.grid(axis='x', alpha=0.3)
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"\n特征重要性图已保存至: {save_path}")
        
        # 打印排序后的重要性
        print("\n特征重要性排序（从高到低）：")
        print("-" * 60)
        for i, (name, score) in enumerate(zip(sorted_names, sorted_importance)):
            print(f"  {i+1:2d}. {name:20s}: {score:10.6f}")
        print("-" * 60)
    
    def visualize_attention_weights(self, attention_weights, 
                                   save_path='attention_weights.png'):
        """可视化注意力权重的时间分布"""
        plt.figure(figsize=(12, 6))
        
        # 计算平均注意力权重
        mean_weights = attention_weights.mean(axis=0)
        std_weights = attention_weights.std(axis=0)
        
        time_steps = range(len(mean_weights))
        plt.plot(time_steps, mean_weights, 'b-', linewidth=2, marker='o')
        plt.fill_between(time_steps, 
                        mean_weights - std_weights,
                        mean_weights + std_weights,
                        alpha=0.3)
        
        plt.xlabel('Historical Time Step (t-10 to t-1)', fontsize=12)
        plt.ylabel('Attention Weight', fontsize=12)
        plt.title('Attention Weights over Historical Sequence', fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"注意力权重图已保存至: {save_path}")
        
        # 打印统计信息
        print("\n注意力权重统计:")
        for i, (mean, std) in enumerate(zip(mean_weights, std_weights)):
            print(f"  时刻 t-{len(mean_weights)-i}: {mean:.4f} ± {std:.4f}")


# ============================================================================
# 使用示例
# ============================================================================

def analyze_trained_model(env_name, model_path, timestep, use_perturbation_method='modest'):
    """
    分析已训练模型的完整示例函数
    
    Args:
        env_name: 环境名称
        model_path: 模型路径
        timestep: 时间步
        use_perturbation_method: 扰动方法('random'|'modest'|'shuffle')
    """
    import gymnasium as gym
    from SAC_lstm_att_normal import SAC_lstm_countinuous
    import argparse
    
    # 设置参数
    parser = argparse.ArgumentParser()
    parser.add_argument('--dvc', type=str, default='cpu', help='running device')
    parser.add_argument('--state_dim', type=int, default=18)  # 根据您的环境调整
    parser.add_argument('--action_dim', type=int, default=2)
    parser.add_argument('--net_width', type=int, default=256)
    parser.add_argument('--gamma', type=float, default=0.98)
    parser.add_argument('--a_lr', type=float, default=5e-5)
    parser.add_argument('--c_lr', type=float, default=5e-5)
    parser.add_argument('--batch_size', type=int, default=256)
    parser.add_argument('--alpha', type=float, default=0.2)
    parser.add_argument('--adaptive_alpha', type=bool, default=True)
    opt = parser.parse_args([])
    opt.dvc = torch.device(opt.dvc)
    
    # 创建环境和agent
    env = gym.make(env_name)
    opt.state_dim = env.observation_space.shape[0]
    opt.action_dim = env.action_space.shape[0]
    opt.max_action = env.action_space.high
    
    agent = SAC_lstm_countinuous(**vars(opt))
    agent.load(model_path, timestep)
    agent.actor.eval()
    agent.q_critic.eval()
    
    # 定义特征名称（根据你的环境调整）
    feature_names = [
        'x', 'y', 'phi', 'psi', 'u', 'v', 'p', 'r', 
        'sail', 'rudder', 'l', 'lx', 'xf', 'yf', 
        'ox1', 'oy1', 'ox2', 'oy2'
    ]
    
    # 创建分析器
    analyzer = FeatureImportanceAnalyzer(
        agent, agent.state_normalizer, opt.dvc
    )
    
    print("\n" + "=" * 70)
    print("SAC LSTM 特征重要性分析")
    print("=" * 70)
    
    # ======== 步骤1：收集特征统计信息 ========
    print("\n[步骤1/3] 收集特征统计信息...")
    analyzer.collect_feature_statistics(env, n_episodes=30)
    
    # ======== 步骤2：计算特征重要性 ========
    print("\n[步骤2/3] 计算特征重要性...")
    perm_importance = analyzer.permutation_importance(
        env,
        n_episodes=50,
        n_permutations=10,
        perturbation_method=use_perturbation_method,  # 使用指定的扰动方法
        noise_ratio=0.2  # 20%的噪声标准差
    )
    
    # ======== 步骤3：可视化结果 ========
    print("\n[步骤3/3] 可视化结果...")
    analyzer.visualize_importance(
        perm_importance,
        feature_names=feature_names[:len(perm_importance)],
        save_path=f'importance_{use_perturbation_method}.png'
    )
    
    env.close()
    print("\n分析完成！")
    print("=" * 70 + "\n")
    
    return analyzer, perm_importance


if __name__ == '__main__':
    # 示例调用：使用适度噪声方法分析特征重要性
    
    # 配置
    env_name = 'sailboat-s14-obst-v2'
    model_path = 'saclstm_s14obst_1216'
    timestep = 12600
    perturbation_method = 'modest'  # 改为 'random' 对比, 'shuffle' 也可试
    
    analyzer, importance = analyze_trained_model(
        env_name=env_name,
        model_path=model_path,
        timestep=timestep,
        use_perturbation_method=perturbation_method
    )