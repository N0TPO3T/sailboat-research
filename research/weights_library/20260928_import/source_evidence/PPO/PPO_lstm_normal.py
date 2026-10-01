from utils_lstm_normal import Actor, Double_Q_Critic, ZScoreNormalizer
import torch.nn.functional as F
import torch.nn as nn
import numpy as np
import torch
import copy
from collections import deque

class Value_Net(nn.Module):
    """PPO的Value网络，结构与Critic类似但只输出单个价值"""
    def __init__(self, state_dim, hid_shape, dropout_prob=0.1, bptt_len=10):
        super(Value_Net, self).__init__()
        
        self.bptt_len = bptt_len
        self.state_dim = state_dim
        self.hidden_size = hid_shape[0]
        
        # FC层处理历史状态
        self.fc_input = nn.Sequential(
            nn.Linear(state_dim, hid_shape[0]),
            nn.ReLU(),
            nn.Dropout(p=dropout_prob)
        )
        
        # LSTM层
        self.lstm = nn.LSTM(input_size=hid_shape[0], hidden_size=hid_shape[0], num_layers=1, batch_first=True)
        self.lstm.flatten_parameters()
        self.lstm_ln = nn.LayerNorm(hid_shape[0])
        
        # 当前状态预处理层
        self.current_state_fc = nn.Sequential(
            nn.Linear(state_dim, hid_shape[0]),
            nn.ReLU(),
            nn.Dropout(p=dropout_prob)
        )
        
        # 最终FC层：拼接LSTM最新隐藏状态和预处理后的当前状态
        self.final_fc = nn.Sequential(
            nn.Linear(hid_shape[0] + hid_shape[0], hid_shape[-1]),
            nn.ReLU(),
            nn.Dropout(p=dropout_prob)
        )
        
        # 输出价值
        self.value_head = nn.Linear(hid_shape[-1], 1)
        
        # 为多环境维护LSTM隐藏状态
        self.hidden_states = {}

    def forward(self, state_sequence=None, current_state=None, env_ids=None, 
                single_step_mode=False, prev_state=None):
        device = current_state.device
        batch_size = current_state.shape[0]
        
        self.lstm.flatten_parameters()
        
        if single_step_mode:
            # 单步模式：用于环境采样
            if prev_state is None:
                raise ValueError("In single_step_mode, prev_state must be provided")
            
            x = self.fc_input(prev_state.unsqueeze(1))  # (batch, 1, hidden_size)
            
            # 管理LSTM隐藏状态
            if env_ids is not None:
                h_list = []
                c_list = []
                for env_id in env_ids:
                    if env_id not in self.hidden_states:
                        self.hidden_states[env_id] = (
                            torch.zeros(1, 1, self.hidden_size, device=device),
                            torch.zeros(1, 1, self.hidden_size, device=device)
                        )
                    h, c = self.hidden_states[env_id]
                    h_list.append(h)
                    c_list.append(c)
                h_0 = torch.cat(h_list, dim=1)
                c_0 = torch.cat(c_list, dim=1)
                lstm_out, (h_n, c_n) = self.lstm(x, (h_0, c_0))
                
                for idx, env_id in enumerate(env_ids):
                    self.hidden_states[env_id] = (h_n[:, idx:idx+1, :].detach(), 
                                                 c_n[:, idx:idx+1, :].detach())
            else:
                lstm_out, _ = self.lstm(x)
            
            lstm_out = self.lstm_ln(lstm_out)
            # 使用LSTM输出的最新隐藏状态
            latest_lstm_out = lstm_out[:, -1, :]  # (batch, hidden_size)
                
        else:
            # 序列模式：用于训练
            if state_sequence is None:
                raise ValueError("In sequence mode, state_sequence must be provided")
            
            x = self.fc_input(state_sequence)  # (batch, seq_len, hidden_size)
            lstm_out, _ = self.lstm(x)
            lstm_out = self.lstm_ln(lstm_out)
            # 使用LSTM输出的最新隐藏状态（序列的最后一个时间步）
            latest_lstm_out = lstm_out[:, -1, :]  # (batch, hidden_size)
        
        # 预处理当前状态
        current_state_processed = self.current_state_fc(current_state)
        
        # 拼接LSTM最新隐藏状态和预处理后的当前状态
        combined = torch.cat([latest_lstm_out, current_state_processed], dim=1)
        final_out = self.final_fc(combined)
        value = self.value_head(final_out)
        
        return value

    def reset_hidden_state(self, env_id=None):
        """重置LSTM隐藏状态"""
        if env_id is None:
            self.hidden_states = {}
        else:
            if env_id in self.hidden_states:
                del self.hidden_states[env_id]


class PPO_lstm_continuous():
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.seq_len = 5  # 序列长度
        
        # PPO超参数
        self.clip_epsilon = 0.2  # PPO裁剪参数
        self.K_epochs = 10  # 每次更新的epoch数
        self.entropy_coef = 0.05  # 熵正则化系数
        self.value_coef = 0.5  # 价值损失系数
        self.max_grad_norm = 1  # 梯度裁剪
        self.gae_lambda = 0.95  # GAE lambda
        
        # 添加loss监控
        self.policy_loss_history = []
        self.value_loss_history = []
        self.entropy_history = []

        # 初始化Z-score标准化器
        self.state_normalizer = ZScoreNormalizer(self.state_dim, self.dvc)

        # Actor网络
        self.actor = Actor(self.state_dim, self.action_dim, (self.net_width, 256)).to(self.dvc)
        
        # Value网络
        self.value_net = Value_Net(self.state_dim, (self.net_width, 256)).to(self.dvc)
        
        # 优化器
        self.actor_optimizer = torch.optim.Adam(self.actor.parameters(), lr=self.a_lr, weight_decay=1e-5)
        self.value_optimizer = torch.optim.Adam(self.value_net.parameters(), lr=self.c_lr, weight_decay=1e-5)

        # 经验缓存（PPO使用on-policy数据）
        self.replay_buffer = PPOReplayBuffer(self.state_dim, self.action_dim, self.seq_len, 
                                            max_size=int(2e4), dvc=self.dvc)

    def select_action(self, prev_state, prev_action, current_state, deterministic, total_steps, env_id=None):
        with torch.no_grad():
            prev_state = torch.FloatTensor(prev_state[np.newaxis, ...]).to(self.dvc, non_blocking=True)
            prev_action = torch.FloatTensor(prev_action[np.newaxis, ...]).to(self.dvc, non_blocking=True)
            current_state = torch.FloatTensor(current_state[np.newaxis, ...]).to(self.dvc, non_blocking=True)
            
            # 应用Z-score标准化
            prev_state = self.state_normalizer.normalize(prev_state)
            current_state = self.state_normalizer.normalize(current_state)
            
            env_ids = [env_id] if env_id is not None else None
            
            # 获取动作和log_prob
            a, log_prob = self.actor(current_state=current_state, deterministic=deterministic, 
                                    with_logprob=True, env_ids=env_ids, single_step_mode=True, 
                                    prev_state=prev_state, prev_action=prev_action)
            
            # 获取价值估计
            value = self.value_net(current_state=current_state, env_ids=env_ids, 
                                  single_step_mode=True, prev_state=prev_state)
            
        return a.cpu().numpy()[0], log_prob.cpu().numpy()[0], value.cpu().numpy()[0]

    def train(self):
        if self.replay_buffer.size < self.batch_size:
            return None
            
        # 获取所有数据
        data = self.replay_buffer.get_all_data()
        s_seq, a_seq, s_curr, a_curr, r, s_next_seq, s_next_curr, dw, old_log_probs, values = data
        
        # 更新标准化器
        self.state_normalizer.update(s_seq)
        self.state_normalizer.update(s_curr)
        self.state_normalizer.update(s_next_seq)
        self.state_normalizer.update(s_next_curr)
        
        # 标准化状态
        s_seq = self.state_normalizer.normalize(s_seq)
        s_curr = self.state_normalizer.normalize(s_curr)
        s_next_seq = self.state_normalizer.normalize(s_next_seq)
        s_next_curr = self.state_normalizer.normalize(s_next_curr)
        
        # 计算优势函数（使用GAE）
        with torch.no_grad():
            next_values = self.value_net(state_sequence=s_next_seq, current_state=s_next_curr, 
                                        single_step_mode=False)
            
            advantages = torch.zeros_like(r)
            last_gae = 0
            
            for t in reversed(range(len(r))):
                if t == len(r) - 1:
                    next_value = next_values[t] * (~dw[t])
                else:
                    next_value = values[t + 1]
                
                delta = r[t] + self.gamma * next_value - values[t]
                advantages[t] = last_gae = delta + self.gamma * self.gae_lambda * (~dw[t]) * last_gae
            
            returns = advantages + values
            advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        
        # PPO更新
        dataset_size = s_seq.shape[0]
        total_policy_loss = 0
        total_value_loss = 0
        total_entropy = 0
        update_count = 0
        
        for _ in range(self.K_epochs):
            # 随机打乱数据
            indices = torch.randperm(dataset_size, device=self.dvc)
            
            for start in range(0, dataset_size, self.batch_size):
                end = min(start + self.batch_size, dataset_size)
                batch_indices = indices[start:end]
                
                # 获取当前批次的新log_probs和values
                _, new_log_probs = self.actor(state_sequence=s_seq[batch_indices], 
                                             action_sequence=a_seq[batch_indices],
                                             current_state=s_curr[batch_indices], 
                                             deterministic=False, with_logprob=True,
                                             single_step_mode=False)
                
                new_values = self.value_net(state_sequence=s_seq[batch_indices], 
                                           current_state=s_curr[batch_indices],
                                           single_step_mode=False)
                
                # 计算ratio
                ratio = torch.exp(new_log_probs - old_log_probs[batch_indices])
                
                # PPO裁剪目标
                surr1 = ratio * advantages[batch_indices]
                surr2 = torch.clamp(ratio, 1 - self.clip_epsilon, 1 + self.clip_epsilon) * advantages[batch_indices]
                policy_loss = -torch.min(surr1, surr2).mean()
                
                # Value损失
                value_loss = F.mse_loss(new_values, returns[batch_indices])
                
                # 熵正则化
                dist = torch.distributions.Normal(0, 1)  # 简化的熵计算
                entropy = -new_log_probs.mean()
                
                # 总损失
                loss = policy_loss + self.value_coef * value_loss - self.entropy_coef * entropy
                
                # 更新网络
                self.actor_optimizer.zero_grad()
                self.value_optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.actor.parameters(), self.max_grad_norm)
                torch.nn.utils.clip_grad_norm_(self.value_net.parameters(), self.max_grad_norm)
                self.actor_optimizer.step()
                self.value_optimizer.step()
                
                total_policy_loss += policy_loss.item()
                total_value_loss += value_loss.item()
                total_entropy += entropy.item()
                update_count += 1
        
        # 清空经验缓存
        self.replay_buffer.clear()
        
        avg_policy_loss = total_policy_loss / update_count
        avg_value_loss = total_value_loss / update_count
        avg_entropy = total_entropy / update_count
        
        self.policy_loss_history.append(avg_policy_loss)
        self.value_loss_history.append(avg_value_loss)
        self.entropy_history.append(avg_entropy)
        
        return {
            'policy_loss': avg_policy_loss,
            'value_loss': avg_value_loss,
            'entropy': avg_entropy
        }

    def save(self, EnvName, timestep):
        torch.save(self.actor.state_dict(), "./model/{}_actor{}.pth".format(EnvName, timestep))
        torch.save(self.value_net.state_dict(), "./model/{}_value{}.pth".format(EnvName, timestep))
        torch.save(self.state_normalizer.state_dict(), "./model/{}_normalizer{}.pth".format(EnvName, timestep))

    def load(self, EnvName, timestep):
        self.actor.load_state_dict(torch.load("./model/{}_actor{}.pth".format(EnvName, timestep), 
                                              map_location=self.dvc))
        self.value_net.load_state_dict(torch.load("./model/{}_value{}.pth".format(EnvName, timestep), 
                                                  map_location=self.dvc))
        try:
            normalizer_state = torch.load("./model/{}_normalizer{}.pth".format(EnvName, timestep), 
                                         map_location=self.dvc)
            self.state_normalizer.load_state_dict(normalizer_state)
        except FileNotFoundError:
            print("Warning: Normalizer parameters not found, using default initialization.")


class PPOReplayBuffer():
    def __init__(self, state_dim, action_dim, seq_len, max_size, dvc):
        self.max_size = max_size
        self.dvc = dvc
        self.ptr = 0
        self.size = 0
        self.seq_len = seq_len
        
        # 存储序列数据
        self.s_seq = torch.zeros((max_size, seq_len, state_dim), dtype=torch.float, device=self.dvc)
        self.a_seq = torch.zeros((max_size, seq_len, action_dim), dtype=torch.float, device=self.dvc)
        self.s_curr = torch.zeros((max_size, state_dim), dtype=torch.float, device=self.dvc)
        self.a_curr = torch.zeros((max_size, action_dim), dtype=torch.float, device=self.dvc)
        self.r = torch.zeros((max_size, 1), dtype=torch.float, device=self.dvc)
        self.s_next_seq = torch.zeros((max_size, seq_len, state_dim), dtype=torch.float, device=self.dvc)
        self.s_next_curr = torch.zeros((max_size, state_dim), dtype=torch.float, device=self.dvc)
        self.dw = torch.zeros((max_size, 1), dtype=torch.bool, device=self.dvc)
        self.log_probs = torch.zeros((max_size, 1), dtype=torch.float, device=self.dvc)
        self.values = torch.zeros((max_size, 1), dtype=torch.float, device=self.dvc)

    def add(self, s_seq, a_seq, s_curr, action, r, s_next_seq, s_next_curr, dw, log_prob, value):
        self.s_seq[self.ptr] = torch.from_numpy(s_seq).to(self.dvc, non_blocking=True)
        self.a_seq[self.ptr] = torch.from_numpy(a_seq).to(self.dvc, non_blocking=True)
        self.s_curr[self.ptr] = torch.from_numpy(s_curr).to(self.dvc, non_blocking=True)
        self.a_curr[self.ptr] = torch.from_numpy(action).to(self.dvc, non_blocking=True)
        self.r[self.ptr] = r
        self.s_next_seq[self.ptr] = torch.from_numpy(s_next_seq).to(self.dvc, non_blocking=True)
        self.s_next_curr[self.ptr] = torch.from_numpy(s_next_curr).to(self.dvc, non_blocking=True)
        self.dw[self.ptr] = bool(dw)
        # 转换 log_prob 和 value 为 tensor
        if isinstance(log_prob, np.ndarray):
            self.log_probs[self.ptr] = torch.from_numpy(log_prob).to(self.dvc, non_blocking=True)
        else:
            self.log_probs[self.ptr] = log_prob

        if isinstance(value, np.ndarray):
            self.values[self.ptr] = torch.from_numpy(value).to(self.dvc, non_blocking=True)
        else:
            self.values[self.ptr] = value

        self.ptr = (self.ptr + 1) % self.max_size
        self.size = min(self.size + 1, self.max_size)

    def get_all_data(self):
        """获取所有数据用于PPO更新"""
        return (self.s_seq[:self.size], self.a_seq[:self.size], self.s_curr[:self.size], 
                self.a_curr[:self.size], self.r[:self.size], self.s_next_seq[:self.size], 
                self.s_next_curr[:self.size], self.dw[:self.size], 
                self.log_probs[:self.size], self.values[:self.size])
    
    def clear(self):
        """清空缓存"""
        self.ptr = 0
        self.size = 0