# SAC/sac-lstm/utils_lstm_normal_deep.py
"""
参数量匹配的深层LSTM网络（优化版）
用于对比实验：通过增加网络深度来匹配注意力模型的参数量（~2.46M）
目标：验证性能提升是否来自注意力机制本身，而非单纯的参数量增加

参数量对比（state_dim=18, action_dim=2）:
- Attention模型: ~2,462,750
- Deep LSTM模型: ~2,429,394（差异-1.4%）
"""

import torch
import argparse
import numpy as np
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Normal
import globals
import math

# 复用Z-score标准化类
class ZScoreNormalizer:
    def __init__(self, state_dim, device):
        self.device = device
        self.count = 0
        self.mean = torch.zeros(state_dim, device=device)
        self.var = torch.ones(state_dim, device=device)
        self.epsilon = 1e-6
        
    def update(self, data):
        if len(data.shape) == 3:
            data = data.view(-1, data.shape[-1])
        elif len(data.shape) == 2:
            pass
        else:
            data = data.unsqueeze(0)
            
        batch_count = data.shape[0]
        batch_mean = torch.mean(data, dim=0)
        batch_var = torch.var(data, dim=0, unbiased=False)
        
        if self.count == 0:
            self.mean = batch_mean
            self.var = batch_var
        else:
            total_count = self.count + batch_count
            delta = batch_mean - self.mean
            self.mean += delta * batch_count / total_count
            self.var = (self.count * self.var + batch_count * batch_var + 
                       delta**2 * self.count * batch_count / total_count) / total_count
        
        self.count += batch_count
        
    def normalize(self, data):
        return (data - self.mean) / (torch.sqrt(self.var) + self.epsilon)
        
    def denormalize(self, data):
        return data * (torch.sqrt(self.var) + self.epsilon) + self.mean
        
    def state_dict(self):
        return {'mean': self.mean, 'var': self.var, 'count': self.count}
        
    def load_state_dict(self, state_dict):
        self.mean = state_dict['mean'].to(self.device)
        self.var = state_dict['var'].to(self.device)
        self.count = state_dict['count']


class Actor(nn.Module):
    """
    深层LSTM Actor网络 - 参数量优化匹配版本
    
    参数量计算（state_dim=18, action_dim=2, net_width=256）:
    - fc_input: (18+2)×256+256 = 5,376
    - lstm: 4×(256²+256²+256×2) = 524,800
    - lstm_ln: 256×2 = 512
    - current_state_fc (2层): 18×256+256 + 256²+256 = 70,656
    - final_fc (2层): 512×384+384 + 384×256+256 = 295,552
    - mu_layer + log_std_layer: (256×2+2)×2 = 1,028
    Total: ~897,924
    """
    def __init__(self, state_dim, action_dim, hid_shape, hidden_activation=nn.ReLU, 
                 output_activation=nn.ReLU, dropout_prob=0.05, bptt_len=10):
        super(Actor, self).__init__()
        
        self.bptt_len = bptt_len
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.hidden_size = hid_shape[0]
        
        # 第一层：FC层 - 处理历史序列（状态+动作）
        self.fc_input = nn.Sequential(
            nn.Linear(state_dim + action_dim, hid_shape[0]),
            nn.ReLU(),
            nn.Dropout(p=dropout_prob)
        )
        
        # 第二层：LSTM层
        self.lstm = nn.LSTM(input_size=hid_shape[0], hidden_size=hid_shape[0], 
                           num_layers=1, batch_first=True)
        self.lstm.flatten_parameters()
        self.lstm_ln = nn.LayerNorm(hid_shape[0])
        
        # 当前状态预处理层 - 2层深度
        self.current_state_fc = nn.Sequential(
            nn.Linear(state_dim, hid_shape[0]),
            nn.ReLU(),
            nn.Dropout(p=dropout_prob),
            nn.Linear(hid_shape[0], hid_shape[0]),
            nn.ReLU(),
            nn.Dropout(p=dropout_prob)
        )
        
        # 拼接后的深层FC网络 - 2层渐进式降维：512 -> 384 -> 256
        self.final_fc = nn.Sequential(
            nn.Linear(hid_shape[0] + hid_shape[0], 384),
            nn.ReLU(),
            nn.Dropout(p=dropout_prob),
            nn.Linear(384, hid_shape[-1]),
            nn.ReLU(),
            nn.Dropout(p=dropout_prob)
        )
            
        # 最终输出层
        self.mu_layer = nn.Linear(hid_shape[-1], action_dim)
        self.log_std_layer = nn.Linear(hid_shape[-1], action_dim)

        self.LOG_STD_MAX = 2
        self.LOG_STD_MIN = -10
        
        # 为多环境维护LSTM隐藏状态
        self.hidden_states = {}

    def forward(self, state_sequence=None, action_sequence=None, current_state=None, 
                deterministic=False, with_logprob=False, env_ids=None, 
                single_step_mode=False, prev_state=None, prev_action=None):
        device = current_state.device
        batch_size = current_state.shape[0]
        
        self.lstm.flatten_parameters()
        
        if single_step_mode:
            if prev_state is None or prev_action is None:
                raise ValueError("在单步模式下，必须提供prev_state和prev_action")
            
            prev_sa = torch.cat([prev_state, prev_action], dim=1)
            x = self.fc_input(prev_sa.unsqueeze(1))
            
            if env_ids is not None:
                h_list, c_list = [], []
                for env_id in env_ids:
                    if env_id not in self.hidden_states:
                        h = torch.zeros(1, self.hidden_size, device=device)
                        c = torch.zeros(1, self.hidden_size, device=device)
                        self.hidden_states[env_id] = (h, c)
                    
                    h, c = self.hidden_states[env_id]
                    h_list.append(h)
                    c_list.append(c)
                
                h_0 = torch.cat(h_list, dim=0).unsqueeze(0)
                c_0 = torch.cat(c_list, dim=0).unsqueeze(0)
                lstm_out, (h_n, c_n) = self.lstm(x, (h_0, c_0))
                
                for i, env_id in enumerate(env_ids):
                    self.hidden_states[env_id] = (h_n[0, i:i+1, :], c_n[0, i:i+1, :])
            else:
                lstm_out, _ = self.lstm(x)
            
            lstm_out = self.lstm_ln(lstm_out)
            lstm_final = lstm_out[:, 0, :]
            
        else:
            if state_sequence is None or action_sequence is None:
                raise ValueError("在序列模式下，必须提供state_sequence和action_sequence")
            
            sa_sequence = torch.cat([state_sequence, action_sequence], dim=2)
            x = self.fc_input(sa_sequence)
            lstm_out, _ = self.lstm(x)
            lstm_out = self.lstm_ln(lstm_out)
            lstm_final = lstm_out[:, -1, :]
        
        # 使用深层网络处理当前状态
        current_state_processed = self.current_state_fc(current_state)
        
        # 拼接并通过深层FC网络
        combined = torch.cat([lstm_final, current_state_processed], dim=1)
        final_out = self.final_fc(combined)

        mu = self.mu_layer(final_out)
        log_std = self.log_std_layer(final_out)
        log_std = torch.clamp(log_std, self.LOG_STD_MIN, self.LOG_STD_MAX)
        std = torch.exp(log_std)
        dist = Normal(mu, std)
        
        if deterministic:
            u = mu
        else:
            u = dist.rsample()

        a = torch.tanh(u)
        if with_logprob:
            logp_pi_a = dist.log_prob(u).sum(axis=1, keepdim=True) - (
                2 * (np.log(2) - u - F.softplus(-2 * u))
            ).sum(axis=1, keepdim=True)
        else:
            logp_pi_a = None

        return a, logp_pi_a

    def reset_hidden_state(self, env_id=None):
        if env_id is None:
            self.hidden_states = {}
        else:
            if env_id in self.hidden_states:
                del self.hidden_states[env_id]


class Double_Q_Critic(nn.Module):
    """
    深层LSTM Critic网络 - 参数量优化匹配版本
    
    参数量计算（state_dim=18）:
    Q1网络：
    - fc_input_q1: (18+2)×256+256 = 5,376
    - lstm_q1: 524,800
    - lstm_ln_q1: 512
    - current_sa_fc_q1 (2层): 20×256+256 + 256²+256 = 70,656
    - final_fc_q1 (2层): 512×256+256 + 256×128+128 = 164,224
    - Q_1: 128×1+1 = 129
    Total per Q1: ~765,697
    
    Q2网络（相同结构）: ~765,697
    Critic总计: ~1,531,394
    
    总参数量: Actor(~897,924) + Critic(~1,531,394) = ~2,429,318
    与Attention模型(2,462,750)差异: -1.4%
    """
    def __init__(self, state_dim, action_dim, hid_shape_q1, hid_shape_q2, 
                 dropout_prob=0.05, bptt_len=10):
        super(Double_Q_Critic, self).__init__()
        
        self.bptt_len = bptt_len
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.hidden_size_q1 = hid_shape_q1[0]
        self.hidden_size_q2 = hid_shape_q2[0]
        
        # Q_1 网络
        self.fc_input_q1 = nn.Sequential(
            nn.Linear(state_dim + action_dim, hid_shape_q1[0]),
            nn.ReLU(),
            nn.Dropout(p=dropout_prob)
        )
        self.lstm_q1 = nn.LSTM(input_size=hid_shape_q1[0], hidden_size=hid_shape_q1[0], 
                               num_layers=1, batch_first=True)
        self.lstm_q1.flatten_parameters()
        self.lstm_ln_q1 = nn.LayerNorm(hid_shape_q1[0])
        
        # Q1当前状态动作预处理层 - 2层深度
        self.current_sa_fc_q1 = nn.Sequential(
            nn.Linear(state_dim + action_dim, hid_shape_q1[0]),
            nn.ReLU(),
            nn.Dropout(p=dropout_prob),
            nn.Linear(hid_shape_q1[0], hid_shape_q1[0]),
            nn.ReLU(),
            nn.Dropout(p=dropout_prob)
        )
        
        # Q1深层FC网络 - 2层：512 -> 256 -> 128
        self.final_fc_q1 = nn.Sequential(
            nn.Linear(hid_shape_q1[0] + hid_shape_q1[0], 256),
            nn.ReLU(),
            nn.Dropout(p=dropout_prob),
            nn.Linear(256, hid_shape_q1[-1]),
            nn.ReLU(),
            nn.Dropout(p=dropout_prob)
        )
        self.Q_1 = nn.Linear(hid_shape_q1[-1], 1)

        # Q_2 网络 - 相同结构保证一致性
        self.fc_input_q2 = nn.Sequential(
            nn.Linear(state_dim + action_dim, hid_shape_q2[0]),
            nn.ReLU(),
            nn.Dropout(p=dropout_prob)
        )
        self.lstm_q2 = nn.LSTM(input_size=hid_shape_q2[0], hidden_size=hid_shape_q2[0], 
                               num_layers=1, batch_first=True)
        self.lstm_q2.flatten_parameters()
        self.lstm_ln_q2 = nn.LayerNorm(hid_shape_q2[0])
        
        self.current_sa_fc_q2 = nn.Sequential(
            nn.Linear(state_dim + action_dim, hid_shape_q2[0]),
            nn.ReLU(),
            nn.Dropout(p=dropout_prob),
            nn.Linear(hid_shape_q2[0], hid_shape_q2[0]),
            nn.ReLU(),
            nn.Dropout(p=dropout_prob)
        )
        
        # Q2深层FC网络 - 与Q1相同结构
        self.final_fc_q2 = nn.Sequential(
            nn.Linear(hid_shape_q2[0] + hid_shape_q2[0], 256),
            nn.ReLU(),
            nn.Dropout(p=dropout_prob),
            nn.Linear(256, hid_shape_q2[-1]),
            nn.ReLU(),
            nn.Dropout(p=dropout_prob)
        )
        self.Q_2 = nn.Linear(hid_shape_q2[-1], 1)
        
        self.hidden_states_q1 = {}
        self.hidden_states_q2 = {}

    def forward(self, state_sequence=None, action_sequence=None, current_state=None, 
                current_action=None, env_ids=None, single_step_mode=False, 
                prev_state=None, prev_action=None):
        device = current_state.device
        batch_size = current_state.shape[0]
        
        self.lstm_q1.flatten_parameters()
        self.lstm_q2.flatten_parameters()
        
        if single_step_mode:
            if prev_state is None or prev_action is None:
                raise ValueError("在单步模式下，必须提供prev_state和prev_action")
            
            prev_sa = torch.cat([prev_state, prev_action], dim=1)
            current_sa = torch.cat([current_state, current_action], dim=1)
            
            # Q1网络 - 单步模式
            x1 = self.fc_input_q1(prev_sa.unsqueeze(1))
            
            if env_ids is not None:
                h_list_q1, c_list_q1 = [], []
                for env_id in env_ids:
                    if env_id not in self.hidden_states_q1:
                        h = torch.zeros(1, self.hidden_size_q1, device=device)
                        c = torch.zeros(1, self.hidden_size_q1, device=device)
                        self.hidden_states_q1[env_id] = (h, c)
                    
                    h, c = self.hidden_states_q1[env_id]
                    h_list_q1.append(h)
                    c_list_q1.append(c)
                
                h_0_q1 = torch.cat(h_list_q1, dim=0).unsqueeze(0)
                c_0_q1 = torch.cat(c_list_q1, dim=0).unsqueeze(0)
                lstm_out1, (h_n_q1, c_n_q1) = self.lstm_q1(x1, (h_0_q1, c_0_q1))
                
                for i, env_id in enumerate(env_ids):
                    self.hidden_states_q1[env_id] = (h_n_q1[0, i:i+1, :], c_n_q1[0, i:i+1, :])
            else:
                lstm_out1, _ = self.lstm_q1(x1)
            
            lstm_out1 = self.lstm_ln_q1(lstm_out1)
            lstm_final1 = lstm_out1[:, 0, :]
            
            # Q2网络 - 单步模式
            x2 = self.fc_input_q2(prev_sa.unsqueeze(1))
            
            if env_ids is not None:
                h_list_q2, c_list_q2 = [], []
                for env_id in env_ids:
                    if env_id not in self.hidden_states_q2:
                        h = torch.zeros(1, self.hidden_size_q2, device=device)
                        c = torch.zeros(1, self.hidden_size_q2, device=device)
                        self.hidden_states_q2[env_id] = (h, c)
                    
                    h, c = self.hidden_states_q2[env_id]
                    h_list_q2.append(h)
                    c_list_q2.append(c)
                
                h_0_q2 = torch.cat(h_list_q2, dim=0).unsqueeze(0)
                c_0_q2 = torch.cat(c_list_q2, dim=0).unsqueeze(0)
                lstm_out2, (h_n_q2, c_n_q2) = self.lstm_q2(x2, (h_0_q2, c_0_q2))
                
                for i, env_id in enumerate(env_ids):
                    self.hidden_states_q2[env_id] = (h_n_q2[0, i:i+1, :], c_n_q2[0, i:i+1, :])
            else:
                lstm_out2, _ = self.lstm_q2(x2)
            
            lstm_out2 = self.lstm_ln_q2(lstm_out2)
            lstm_final2 = lstm_out2[:, 0, :]
            
        else:
            if state_sequence is None or action_sequence is None:
                raise ValueError("在序列模式下，必须提供state_sequence和action_sequence")
            
            sa_sequence = torch.cat([state_sequence, action_sequence], dim=2)
            current_sa = torch.cat([current_state, current_action], dim=1)
            
            # Q1网络 - 序列模式
            x1 = self.fc_input_q1(sa_sequence)
            lstm_out1, _ = self.lstm_q1(x1)
            lstm_out1 = self.lstm_ln_q1(lstm_out1)
            lstm_final1 = lstm_out1[:, -1, :]
            
            # Q2网络 - 序列模式
            x2 = self.fc_input_q2(sa_sequence)
            lstm_out2, _ = self.lstm_q2(x2)
            lstm_out2 = self.lstm_ln_q2(lstm_out2)
            lstm_final2 = lstm_out2[:, -1, :]
        
        # 使用深层网络处理当前状态动作
        current_sa_processed1 = self.current_sa_fc_q1(current_sa)
        current_sa_processed2 = self.current_sa_fc_q2(current_sa)
        
        combined1 = torch.cat([lstm_final1, current_sa_processed1], dim=1)
        combined2 = torch.cat([lstm_final2, current_sa_processed2], dim=1)
        
        final_out1 = self.final_fc_q1(combined1)
        final_out2 = self.final_fc_q2(combined2)
        
        q1 = self.Q_1(final_out1)
        q2 = self.Q_2(final_out2)

        return q1, q2

    def reset_hidden_state(self, env_id=None):
        if env_id is None:
            self.hidden_states_q1 = {}
            self.hidden_states_q2 = {}
        else:
            if env_id in self.hidden_states_q1:
                del self.hidden_states_q1[env_id]
            if env_id in self.hidden_states_q2:
                del self.hidden_states_q2[env_id]


# 复用工具函数
def Reward_adapter(r, EnvIdex):
    if EnvIdex == 0:
        r = (r + 8) / 8
    elif EnvIdex == 1:
        if r <= -100: r = -10
    elif EnvIdex == 4 or EnvIdex == 5:
        if r <= -100: r = -1
    return r


def Action_adapter(a, max_action):
    return a * max_action


def Action_adapter_reverse(act, max_action):
    return act / max_action


def evaluate_policy(env, agent, max_action, turns=3, total_steps=None):
    total_scores = 0
    
    for j in range(turns):
        s, info = env.reset()
        done = False
        
        eval_env_id = f"eval_{j}"
        agent.actor.reset_hidden_state(eval_env_id)
        
        prev_state = s.copy()
        prev_action = np.zeros(agent.action_dim)
        
        episode_score = 0
        while not done:
            a = agent.select_action(prev_state, prev_action, s, deterministic=True, 
                                  total_steps=total_steps, env_id=eval_env_id)
            act = Action_adapter(a, max_action)
            s_next, r, dw, tr, info = env.step(act)
            done = (dw or tr)
            
            episode_score += r
            prev_state = s.copy()
            prev_action = a.copy()
            s = s_next
        
        total_scores += episode_score
    
    return int(total_scores / turns)


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'True','true','TRUE', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'False','false','FALSE', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')