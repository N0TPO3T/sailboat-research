import os
import sys
import torch
import numpy as np
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Normal

curr_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(curr_dir)
sys.path.append(project_root)

class ZScoreNormalizer:
    def __init__(self, state_dim, device):
        self.device = device
        self.count = 0
        self.mean = torch.zeros(state_dim, device=device)
        self.var = torch.ones(state_dim, device=device)
        self.epsilon = 1e-6
        
    def update(self, data):
        if len(data.shape) == 3: data = data.view(-1, data.shape[-1])
        elif len(data.shape) == 2: pass
        else: data = data.unsqueeze(0)
            
        batch_count = data.shape[0]
        batch_mean = torch.mean(data, dim=0)
        batch_var = torch.var(data, dim=0, unbiased=False)
        
        if self.count == 0:
            self.mean, self.var = batch_mean, batch_var
        else:
            total_count = self.count + batch_count
            delta = batch_mean - self.mean
            self.mean += delta * batch_count / total_count
            self.var = (self.count * self.var + batch_count * batch_var + delta**2 * self.count * batch_count / total_count) / total_count
        self.count += batch_count
        
    def normalize(self, data): return (data - self.mean) / (torch.sqrt(self.var) + self.epsilon)
    def denormalize(self, data): return data * (torch.sqrt(self.var) + self.epsilon) + self.mean
    def state_dict(self): return {'mean': self.mean, 'var': self.var, 'count': self.count}
    def load_state_dict(self, state_dict): self.mean, self.var, self.count = state_dict['mean'].to(self.device), state_dict['var'].to(self.device), state_dict['count']


class Actor(nn.Module):
    def __init__(self, state_dim, action_dim, hid_shape, dropout_prob=0.05):
        super(Actor, self).__init__()
        self.hidden_size = hid_shape[0]
        
        # 可行性验证版：Actor 仅依赖状态序列（含当前时刻），不再读取动作序列或当前状态旁路
        self.fc_input = nn.Sequential(nn.Linear(state_dim, hid_shape[0]), nn.ReLU(), nn.Dropout(p=dropout_prob))
        self.lstm = nn.LSTM(input_size=hid_shape[0], hidden_size=hid_shape[0], num_layers=1, batch_first=True)
        self.lstm_ln = nn.LayerNorm(hid_shape[0])
        
        # 去掉当前状态融合分支（FC2）后，仅用 LSTM 隐状态生成策略
        self.final_fc = nn.Sequential(nn.Linear(hid_shape[0], hid_shape[-1]), nn.ReLU(), nn.Dropout(p=dropout_prob))
            
        self.mu_layer = nn.Linear(hid_shape[-1], action_dim)
        self.log_std_layer = nn.Linear(hid_shape[-1], action_dim)
        self.LOG_STD_MAX, self.LOG_STD_MIN = 2, -10
        self.hidden_states = {}

    def forward(
        self,
        state_sequence=None,
        current_state=None,
        deterministic=False,
        with_logprob=False,
        env_ids=None,
        single_step_mode=False
    ):
        self.lstm.flatten_parameters()
        
        if single_step_mode:
            if current_state is None:
                raise ValueError("single_step_mode=True 时必须提供 current_state")
            x = self.fc_input(current_state.unsqueeze(1))
            device = current_state.device
            if env_ids is not None:
                h_list, c_list = [], []
                for env_id in env_ids:
                    if env_id not in self.hidden_states:
                        self.hidden_states[env_id] = (torch.zeros(1, self.hidden_size, device=device), torch.zeros(1, self.hidden_size, device=device))
                    h, c = self.hidden_states[env_id]
                    h_list.append(h)
                    c_list.append(c)
                lstm_out, (h_n, c_n) = self.lstm(x, (torch.cat(h_list, dim=0).unsqueeze(0), torch.cat(c_list, dim=0).unsqueeze(0)))
                
                for i, env_id in enumerate(env_ids):
                    self.hidden_states[env_id] = (h_n[0, i:i+1, :].detach(), c_n[0, i:i+1, :].detach())
            else:
                lstm_out, _ = self.lstm(x)
            lstm_final = self.lstm_ln(lstm_out)[:, 0, :]
        else:
            if state_sequence is None:
                raise ValueError("single_step_mode=False 时必须提供 state_sequence")
            x = self.fc_input(state_sequence)
            lstm_out, _ = self.lstm(x)
            lstm_final = self.lstm_ln(lstm_out)[:, -1, :] 
        
        final_out = self.final_fc(lstm_final)
        mu = self.mu_layer(final_out)
        log_std = torch.clamp(self.log_std_layer(final_out), self.LOG_STD_MIN, self.LOG_STD_MAX)
        dist = Normal(mu, torch.exp(log_std))
        
        u = mu if deterministic else dist.rsample()
        a = torch.tanh(u)
        
        if with_logprob:
            logp_pi_a = dist.log_prob(u).sum(axis=1, keepdim=True) - (2 * (np.log(2) - u - F.softplus(-2 * u))).sum(axis=1, keepdim=True)
        else:
            logp_pi_a = None
        return a, logp_pi_a

    def reset_hidden_state(self, env_id=None):
        if env_id is None: self.hidden_states = {}
        elif env_id in self.hidden_states: del self.hidden_states[env_id]


class Double_Q_Critic(nn.Module):
    def __init__(self, state_dim, action_dim, hid_shape_q1, hid_shape_q2, dropout_prob=0.05):
        super(Double_Q_Critic, self).__init__()
        self.hidden_size_q1, self.hidden_size_q2 = hid_shape_q1[0], hid_shape_q2[0]
        
        self.fc_input_q1 = nn.Sequential(nn.Linear(state_dim + action_dim, hid_shape_q1[0]), nn.ReLU(), nn.Dropout(p=dropout_prob))
        self.lstm_q1 = nn.LSTM(input_size=hid_shape_q1[0], hidden_size=hid_shape_q1[0], num_layers=1, batch_first=True)
        self.lstm_ln_q1 = nn.LayerNorm(hid_shape_q1[0])
        self.current_sa_fc_q1 = nn.Sequential(
            nn.Linear(state_dim + action_dim, hid_shape_q1[0]),
            nn.ReLU(),
            nn.Dropout(p=dropout_prob)
        )
        self.final_fc_q1 = nn.Sequential(nn.Linear(hid_shape_q1[0] + hid_shape_q1[0], hid_shape_q1[-1]), nn.ReLU(), nn.Dropout(p=dropout_prob))
        self.Q_1 = nn.Linear(hid_shape_q1[-1], 1)

        self.fc_input_q2 = nn.Sequential(nn.Linear(state_dim + action_dim, hid_shape_q2[0]), nn.ReLU(), nn.Dropout(p=dropout_prob))
        self.lstm_q2 = nn.LSTM(input_size=hid_shape_q2[0], hidden_size=hid_shape_q2[0], num_layers=1, batch_first=True)
        self.lstm_ln_q2 = nn.LayerNorm(hid_shape_q2[0])
        self.current_sa_fc_q2 = nn.Sequential(
            nn.Linear(state_dim + action_dim, hid_shape_q2[0]),
            nn.ReLU(),
            nn.Dropout(p=dropout_prob)
        )
        self.final_fc_q2 = nn.Sequential(nn.Linear(hid_shape_q2[0] + hid_shape_q2[0], hid_shape_q2[-1]), nn.ReLU(), nn.Dropout(p=dropout_prob))
        self.Q_2 = nn.Linear(hid_shape_q2[-1], 1)
        
        self.hidden_states_q1, self.hidden_states_q2 = {}, {}

    def forward(
        self,
        state_sequence=None,
        action_sequence=None,
        current_state=None,
        current_action=None,
        env_ids=None,
        single_step_mode=False,
        prev_state=None,
        prev_action=None
    ):
        self.lstm_q1.flatten_parameters(); self.lstm_q2.flatten_parameters()
        device = current_state.device if current_state is not None else state_sequence.device
        
        if single_step_mode:
            if prev_state is None or prev_action is None:
                raise ValueError("single_step_mode=True 时必须提供 prev_state 和 prev_action")
            if current_state is None or current_action is None:
                raise ValueError("single_step_mode=True 时必须提供 current_state 和 current_action")

            prev_sa = torch.cat([prev_state, prev_action], dim=-1)
            current_sa = torch.cat([current_state, current_action], dim=-1)
            sa_input = prev_sa.unsqueeze(1)
            x1, x2 = self.fc_input_q1(sa_input), self.fc_input_q2(sa_input)
            if env_ids is not None:
                h_list_q1, c_list_q1, h_list_q2, c_list_q2 = [], [], [], []
                for env_id in env_ids:
                    if env_id not in self.hidden_states_q1: 
                        self.hidden_states_q1[env_id] = (torch.zeros(1, self.hidden_size_q1, device=device), torch.zeros(1, self.hidden_size_q1, device=device))
                        self.hidden_states_q2[env_id] = (torch.zeros(1, self.hidden_size_q2, device=device), torch.zeros(1, self.hidden_size_q2, device=device))
                    h_list_q1.append(self.hidden_states_q1[env_id][0]); c_list_q1.append(self.hidden_states_q1[env_id][1])
                    h_list_q2.append(self.hidden_states_q2[env_id][0]); c_list_q2.append(self.hidden_states_q2[env_id][1])
                
                lstm_out1, (h_n_q1, c_n_q1) = self.lstm_q1(x1, (torch.cat(h_list_q1, dim=0).unsqueeze(0), torch.cat(c_list_q1, dim=0).unsqueeze(0)))
                lstm_out2, (h_n_q2, c_n_q2) = self.lstm_q2(x2, (torch.cat(h_list_q2, dim=0).unsqueeze(0), torch.cat(c_list_q2, dim=0).unsqueeze(0)))
                
                for i, env_id in enumerate(env_ids):
                    self.hidden_states_q1[env_id] = (h_n_q1[0, i:i+1, :].detach(), c_n_q1[0, i:i+1, :].detach())
                    self.hidden_states_q2[env_id] = (h_n_q2[0, i:i+1, :].detach(), c_n_q2[0, i:i+1, :].detach())
            else:
                lstm_out1, _ = self.lstm_q1(x1); lstm_out2, _ = self.lstm_q2(x2)
            lstm_final1, lstm_final2 = self.lstm_ln_q1(lstm_out1)[:, 0, :], self.lstm_ln_q2(lstm_out2)[:, 0, :]
        else:
            if state_sequence is None or action_sequence is None:
                raise ValueError("single_step_mode=False 时必须提供 state_sequence 和 action_sequence")
            if current_state is None or current_action is None:
                raise ValueError("single_step_mode=False 时必须提供 current_state 和 current_action")

            sa_seq = torch.cat([state_sequence, action_sequence], dim=-1)
            x1, x2 = self.fc_input_q1(sa_seq), self.fc_input_q2(sa_seq)
            lstm_out1, _ = self.lstm_q1(x1); lstm_out2, _ = self.lstm_q2(x2)
            lstm_final1, lstm_final2 = self.lstm_ln_q1(lstm_out1)[:, -1, :], self.lstm_ln_q2(lstm_out2)[:, -1, :]
            current_sa = torch.cat([current_state, current_action], dim=-1)
        
        current_sa_processed1 = self.current_sa_fc_q1(current_sa)
        current_sa_processed2 = self.current_sa_fc_q2(current_sa)

        q1 = self.Q_1(self.final_fc_q1(torch.cat([lstm_final1, current_sa_processed1], dim=1)))
        q2 = self.Q_2(self.final_fc_q2(torch.cat([lstm_final2, current_sa_processed2], dim=1)))
        return q1, q2

    def reset_hidden_state(self, env_id=None):
        if env_id is None: self.hidden_states_q1, self.hidden_states_q2 = {}, {}
        else:
            if env_id in self.hidden_states_q1: del self.hidden_states_q1[env_id]
            if env_id in self.hidden_states_q2: del self.hidden_states_q2[env_id]

def Action_adapter(a, max_action): return a * max_action
def Action_adapter_reverse(act, max_action): return act / max_action
def str2bool(v): return v.lower() in ('yes', 'true', 't', 'y', '1') if isinstance(v, str) else bool(v)

def Reward_adapter(r, EnvIdex):
    if EnvIdex == 0: r = (r + 8) / 8
    elif EnvIdex == 1: 
        if r <= -100: r = -10
    elif EnvIdex == 4 or EnvIdex == 5:
        if r <= -100: r = -1
    return r

def evaluate_policy(env, agent, max_action, turns=3, total_steps=None, noise_manager=None, eval_with_noise=False):
    total_scores = 0
    for j in range(turns):
        s_raw, info = env.reset()
        s = noise_manager.add_observation_noise(s_raw) if eval_with_noise and noise_manager else s_raw.copy()
        eval_env_id = f"eval_{j}"
        agent.actor.reset_hidden_state(eval_env_id)
        episode_score = 0
        done = False
        prev_s, prev_a = s.copy(), np.zeros(env.action_space.shape[0])
        while not done:
            # 兼容外部的原版调用逻辑
            a = agent.select_action(prev_s, prev_a, s, deterministic=True, total_steps=total_steps, env_id=eval_env_id)
            a_noisy = noise_manager.add_action_noise(a, max_action) if eval_with_noise and noise_manager else a
            act = Action_adapter(a_noisy, max_action)
            s_next_raw, r, dw, tr, _ = env.step(act)
            done = dw or tr
            s_next = noise_manager.add_observation_noise(s_next_raw) if eval_with_noise and noise_manager else s_next_raw.copy()
            prev_s, prev_a = s.copy(), a.copy()
            s = s_next
            episode_score += r
        total_scores += episode_score
    return int(total_scores / turns)
