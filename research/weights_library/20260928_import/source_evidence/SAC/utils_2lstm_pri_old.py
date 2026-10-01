import torch
import argparse
import numpy as np
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Normal
import globals


class SelfAttention(nn.Module):
    """自注意力机制模块"""
    def __init__(self, hidden_dim, num_heads=4):
        super(SelfAttention, self).__init__()
        self.attention = nn.MultiheadAttention(embed_dim=hidden_dim, num_heads=num_heads)
        self.norm = nn.LayerNorm(hidden_dim)
        
    def forward(self, x):
        # x 形状: (batch, seq_len, hidden_dim)
        # MultiheadAttention 需要 seq_len 在第一维
        x_t = x.transpose(0, 1)  # (seq_len, batch, hidden_dim)
        attn_out, _ = self.attention(x_t, x_t, x_t)
        attn_out = attn_out.transpose(0, 1)  # 转回 (batch, seq_len, hidden_dim)
        
        # 残差连接和层归一化
        output = self.norm(x + attn_out)  # (batch, seq_len, hidden_dim)
        return output


def build_net(layer_shape, hidden_activation, output_activation, dropout_prob=0.1):
    '''构建包含Dropout正则化的网络'''
    layers = []
    for j in range(len(layer_shape)-1):
        layers.append(nn.Linear(layer_shape[j], layer_shape[j+1]))
        # 对于隐藏层添加激活函数和Dropout（最后一层不加）
        if j < len(layer_shape)-2:
            layers.append(hidden_activation())
            if dropout_prob > 0:
                layers.append(nn.Dropout(p=dropout_prob))
        else:
            layers.append(output_activation())
    return nn.Sequential(*layers)


class Actor(nn.Module):
    def __init__(self, state_dim, action_dim, hid_shape, hidden_activation=nn.ReLU, output_activation=nn.ReLU):
        super(Actor, self).__init__()
        # LSTM层
        self.lstm = nn.LSTM(input_size=state_dim, hidden_size=hid_shape[0], num_layers=1, batch_first=True)
        
        # 注意力机制层
        self.attention = SelfAttention(hidden_dim=hid_shape[0])
        
        # MLP层
        if len(hid_shape) > 1:
            mlp_layers = [hid_shape[0]] + list(hid_shape[1:])
        else:
            mlp_layers = [hid_shape[0]]
        self.mlp = build_net(mlp_layers, hidden_activation, output_activation)
        self.mu_layer = nn.Linear(mlp_layers[-1], action_dim)
        self.log_std_layer = nn.Linear(mlp_layers[-1], action_dim)

        self.LOG_STD_MAX = 2
        self.LOG_STD_MIN = -10

    def forward(self, state, deterministic, with_logprob):
        '''输入形状：(batch, seq_len, state_dim)'''
        self.lstm.flatten_parameters()
        # LSTM处理
        lstm_out, _ = self.lstm(state)  # lstm_out: (batch, seq_len, hidden_size)
        
        # 注意力处理
        attn_out = self.attention(lstm_out)  # attn_out: (batch, seq_len, hidden_size)
        
        # 取最后一个时间步，或者也可以考虑对所有时间步加权
        x = attn_out[:, -1, :]  # (batch, hidden_size)
        
        # MLP处理
        mlp_out = self.mlp(x)
        mu = self.mu_layer(mlp_out)
        log_std = self.log_std_layer(mlp_out)
        log_std = self.LOG_STD_MIN + 0.5 * (self.LOG_STD_MAX - self.LOG_STD_MIN) * (torch.tanh(log_std) + 1)
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

    def summary_forward(self, state):
        mu, _ = self.forward(state, deterministic=False, with_logprob=False)
        return mu


class Double_Q_Critic(nn.Module):
    def __init__(self, state_dim, action_dim, hid_shape_q1, hid_shape_q2):
        super(Double_Q_Critic, self).__init__()
        # Q_1 网络
        self.lstm_q1 = nn.LSTM(input_size=state_dim+action_dim, hidden_size=hid_shape_q1[0], num_layers=1, batch_first=True)
        self.attention_q1 = SelfAttention(hidden_dim=hid_shape_q1[0])
        mlp_layers_q1 = [hid_shape_q1[0]] + list(hid_shape_q1[1:]) + [1]
        self.Q_1 = build_net(mlp_layers_q1, nn.ReLU, nn.Identity)

        # Q_2 网络
        self.lstm_q2 = nn.LSTM(input_size=state_dim+action_dim, hidden_size=hid_shape_q2[0], num_layers=1, batch_first=True)
        self.attention_q2 = SelfAttention(hidden_dim=hid_shape_q2[0])
        mlp_layers_q2 = [hid_shape_q2[0]] + list(hid_shape_q2[1:]) + [1]
        self.Q_2 = build_net(mlp_layers_q2, nn.ReLU, nn.Identity)

    def forward(self, state, action):
        '''输入形状：state: (batch, seq_len, state_dim), action: (batch, seq_len, action_dim)'''
        sa = torch.cat([state, action], dim=2)  # (batch, seq_len, state_dim+action_dim)
        
        # Q1 处理
        self.lstm_q1.flatten_parameters()
        out1, _ = self.lstm_q1(sa)  # (batch, seq_len, hidden_dim)
        attn_out1 = self.attention_q1(out1)  # (batch, seq_len, hidden_dim)
        x1 = attn_out1[:, -1, :]  # 取最后一个时间步
        q1 = self.Q_1(x1)

        # Q2 处理
        self.lstm_q2.flatten_parameters()
        out2, _ = self.lstm_q2(sa)
        attn_out2 = self.attention_q2(out2)
        x2 = attn_out2[:, -1, :]
        q2 = self.Q_2(x2)

        return q1, q2


def Reward_adapter(r, EnvIdex):
    # For Pendulum-v0
    if EnvIdex == 0:
        r = (r + 8) / 8
    # For LunarLander
    elif EnvIdex == 1:
        if r <= -100: r = -10
    # For BipedalWalker
    elif EnvIdex == 4 or EnvIdex == 5:
        if r <= -100: r = -1
    return r


def Action_adapter(a, max_action):
    # from [-1,1] to [-max,max]
    return a * max_action

def Action_adapter_reverse(act, max_action):
    # from [-max,max] to [-1,1]
    return act / max_action


def evaluate_policy(env, agent, max_action, turns=3, total_steps=None):
    total_scores = 0
    for j in range(turns):
        s, info = env.reset()  # 旧版API直接返回观测值
        episode_reward = 0
        step_count = 0
        done = False
        
        # 为LSTM模型准备历史状态序列
        state_seq = np.repeat(s[None, :], 10, axis=0)  # 创建初始状态序列
        
        while not done:
            a = agent.select_action(state_seq, deterministic=True, total_steps=total_steps)
            act = Action_adapter(a, max_action)
            s_next, r, dw, dr, _ = env.step(act)  # 旧版API返回4个值

            if dw or dr:
                done = True

            # 更新状态序列
            state_seq = np.concatenate((state_seq[1:], s_next[None, :]), axis=0)
            
            episode_reward += r
            step_count += 1
        
        total_scores += episode_reward
    
    return int(total_scores / turns)


def str2bool(v):
    '''transfer str to bool for argparse'''
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'True','true','TRUE', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'False','false','FALSE', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')