# TD3_lstm_normal.py
from utils_lstm_normal import Actor, Double_Q_Critic, ZScoreNormalizer
import torch.nn.functional as F
import numpy as np
import torch
import copy


class TD3_Actor(torch.nn.Module):
    """TD3专用的确定性Actor，移除SAC中的随机性部分"""
    def __init__(self, state_dim, action_dim, hid_shape, hidden_activation=torch.nn.ReLU, 
                 output_activation=torch.nn.ReLU, dropout_prob=0.1, bptt_len=10):
        super(TD3_Actor, self).__init__()
        
        self.bptt_len = bptt_len
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.hidden_size = hid_shape[0]
        
        # 第一层：FC层 - 处理历史序列（状态+动作）
        self.fc_input = torch.nn.Sequential(
            torch.nn.Linear(state_dim + action_dim, hid_shape[0]),
            torch.nn.ReLU(),
            torch.nn.Dropout(p=dropout_prob)
        )
        
        # 第二层：LSTM层 - 用于处理时序信息
        self.lstm = torch.nn.LSTM(input_size=hid_shape[0], hidden_size=hid_shape[0], 
                                   num_layers=1, batch_first=True)
        self.lstm.flatten_parameters()
        
        # 添加Layer Normalization
        self.lstm_ln = torch.nn.LayerNorm(hid_shape[0])
        
        # 当前状态预处理层
        self.current_state_fc = torch.nn.Sequential(
            torch.nn.Linear(state_dim, hid_shape[0]),
            torch.nn.ReLU(),
            torch.nn.Dropout(p=dropout_prob)
        )
        
        # 第三层：拼接LSTM最新隐藏状态和预处理后的当前状态的FC层
        self.final_fc = torch.nn.Sequential(
            torch.nn.Linear(hid_shape[0] + hid_shape[0], hid_shape[-1]),
            torch.nn.ReLU(),
            torch.nn.Dropout(p=dropout_prob)
        )
        
        # TD3使用确定性输出，直接输出动作
        self.action_layer = torch.nn.Linear(hid_shape[-1], action_dim)
        
        # 为多环境维护LSTM隐藏状态
        self.hidden_states = {}

    def forward(self, state_sequence=None, action_sequence=None, current_state=None, 
                env_ids=None, single_step_mode=False, prev_state=None, prev_action=None):
        '''
        两种模式：
        1. 序列模式 (single_step_mode=False): 用于训练，输入完整序列
           - state_sequence: (batch, seq_len, state_dim) - 历史状态序列
           - action_sequence: (batch, seq_len, action_dim) - 历史动作序列
           - current_state: (batch, state_dim) - 当前状态
           
        2. 单步模式 (single_step_mode=True): 用于环境采样，逐步更新
           - prev_state: (batch, state_dim) - 上一时刻状态
           - prev_action: (batch, action_dim) - 上一时刻动作
           - current_state: (batch, state_dim) - 当前状态
        '''
        device = current_state.device
        batch_size = current_state.shape[0]
        
        # 确保LSTM权重连续性
        self.lstm.flatten_parameters()
        
        if single_step_mode:
            # 单步模式：用于环境采样
            if prev_state is None or prev_action is None:
                raise ValueError("在单步模式下，必须提供prev_state和prev_action")
            
            # 拼接上一时刻的状态和动作
            prev_sa = torch.cat([prev_state, prev_action], dim=1)
            
            # FC层处理
            x = self.fc_input(prev_sa.unsqueeze(1))  # (batch, 1, hidden_size)
            
            # 管理LSTM隐藏状态
            if env_ids is not None:
                h_list, c_list = [], []
                for env_id in env_ids:
                    if env_id not in self.hidden_states:
                        # 初始化新环境的隐藏状态
                        h = torch.zeros(1, self.hidden_size, device=device)
                        c = torch.zeros(1, self.hidden_size, device=device)
                        self.hidden_states[env_id] = (h, c)
                    
                    h, c = self.hidden_states[env_id]
                    h_list.append(h)
                    c_list.append(c)
                
                h_0 = torch.cat(h_list, dim=0).unsqueeze(0)
                c_0 = torch.cat(c_list, dim=0).unsqueeze(0)
                
                # LSTM前向传播（单步）
                lstm_out, (h_n, c_n) = self.lstm(x, (h_0, c_0))
                
                # 更新各环境的隐藏状态
                for i, env_id in enumerate(env_ids):
                    self.hidden_states[env_id] = (h_n[0, i:i+1, :], c_n[0, i:i+1, :])
            else:
                lstm_out, _ = self.lstm(x)
            
            lstm_out = self.lstm_ln(lstm_out)
            # 使用LSTM输出的最新隐藏状态
            latest_lstm_out = lstm_out[:, -1, :]  # (batch, hidden_size)
            
        else:
            # 序列模式：用于训练
            if state_sequence is None or action_sequence is None:
                raise ValueError("在序列模式下，必须提供state_sequence和action_sequence")
            
            # 拼接历史状态和动作序列
            sa_sequence = torch.cat([state_sequence, action_sequence], dim=2)
            
            # 第一层：FC层处理历史序列
            x = self.fc_input(sa_sequence)  # (batch, seq_len, hidden_size)
            
            # LSTM前向传播（序列模式不使用持久隐藏状态）
            lstm_out, _ = self.lstm(x)
            lstm_out = self.lstm_ln(lstm_out)
            
            # 使用LSTM输出的最新隐藏状态（序列的最后一个时间步）
            latest_lstm_out = lstm_out[:, -1, :]  # (batch, hidden_size)
        
        # 预处理当前状态
        current_state_processed = self.current_state_fc(current_state)  # (batch, hidden_size)
        
        # 拼接LSTM最新隐藏状态和预处理后的当前状态
        combined = torch.cat([latest_lstm_out, current_state_processed], dim=1)
        
        # 最终FC层
        final_out = self.final_fc(combined)
        
        # TD3使用tanh激活函数将动作限制在[-1, 1]
        action = torch.tanh(self.action_layer(final_out))
        
        return action

    def reset_hidden_state(self, env_id=None):
        """重置LSTM隐藏状态"""
        if env_id is None:
            # 重置所有环境的隐藏状态
            self.hidden_states = {}
        else:
            # 重置特定环境的隐藏状态
            if env_id in self.hidden_states:
                del self.hidden_states[env_id]


class TD3_lstm_continuous():
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.tau = 0.002
        self.seq_len = 10
        
        # TD3特有参数
        self.policy_noise = 0.2  # 目标策略平滑噪声
        self.noise_clip = 0.5    # 噪声裁剪范围
        self.policy_freq = 4     # 策略延迟更新频率
        self.total_it = 0        # 总迭代次数
        
        # 梯度裁剪
        self.max_grad_norm = 1.0
        
        # Loss监控
        self.q_loss_history = []
        self.a_loss_history = []
        
        # 初始化Z-score标准化器
        self.state_normalizer = ZScoreNormalizer(self.state_dim, self.dvc)
        
        # 使用TD3专用的Actor
        self.actor = TD3_Actor(self.state_dim, self.action_dim, (self.net_width, 256)).to(self.dvc)
        self.actor_optimizer = torch.optim.Adam(self.actor.parameters(), lr=self.a_lr, weight_decay=1e-5)
        self.actor_target = copy.deepcopy(self.actor)
        
        # 使用Double Q Critic
        self.q_critic = Double_Q_Critic(self.state_dim, self.action_dim, 
                                        (self.net_width, 256), (self.net_width, 128)).to(self.dvc)
        self.q_critic_optimizer = torch.optim.Adam(self.q_critic.parameters(), lr=self.c_lr, weight_decay=1e-5)
        self.q_critic_target = copy.deepcopy(self.q_critic)
        
        # 冻结目标网络
        for p in self.actor_target.parameters():
            p.requires_grad = False
        for p in self.q_critic_target.parameters():
            p.requires_grad = False
        
        self.replay_buffer = ReplayBuffer(self.state_dim, self.action_dim, self.seq_len, 
                                         max_size=int(1e3), dvc=self.dvc)

    def select_action(self, prev_state, prev_action, current_state, add_noise=False, total_steps=None, env_id=None):
        with torch.no_grad():
            prev_state = torch.FloatTensor(prev_state[np.newaxis, ...]).to(self.dvc, non_blocking=True)
            prev_action = torch.FloatTensor(prev_action[np.newaxis, ...]).to(self.dvc, non_blocking=True)
            current_state = torch.FloatTensor(current_state[np.newaxis, ...]).to(self.dvc, non_blocking=True)
            
            # 应用Z-score标准化
            prev_state = self.state_normalizer.normalize(prev_state)
            current_state = self.state_normalizer.normalize(current_state)
            
            env_ids = [env_id] if env_id is not None else None
            action = self.actor(current_state=current_state, env_ids=env_ids, single_step_mode=True,
                               prev_state=prev_state, prev_action=prev_action)
            
            if add_noise:
                # 添加探索噪声
                noise = torch.randn_like(action) * 0.1
                action = (action + noise).clamp(-1, 1)
            
        return action.cpu().numpy()[0]

    def train(self):
        self.total_it += 1
        
        s_seq, a_seq, s_curr, a_curr, r, s_next_seq, a_next_seq, s_next_curr, dw, indices, weights = \
            self.replay_buffer.sample(self.batch_size)
        
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
        
        # =================== Update Critic ===================
        with torch.no_grad():
            # 目标策略平滑：为目标动作添加噪声
            noise = (torch.randn_like(a_curr) * self.policy_noise).clamp(-self.noise_clip, self.noise_clip)
            
            next_action = self.actor_target(state_sequence=s_next_seq, action_sequence=a_next_seq,
                                           current_state=s_next_curr, single_step_mode=False)
            next_action = (next_action + noise).clamp(-1, 1)
            
            # 计算目标Q值（取两个Q网络的最小值）
            target_Q1, target_Q2 = self.q_critic_target(state_sequence=s_next_seq, action_sequence=a_next_seq,
                                                        current_state=s_next_curr, current_action=next_action,
                                                        single_step_mode=False)
            target_Q = torch.min(target_Q1, target_Q2)
            target_Q = r + (~dw) * self.gamma * target_Q
        
        # 当前Q值
        current_Q1, current_Q2 = self.q_critic(state_sequence=s_seq, action_sequence=a_seq,
                                               current_state=s_curr, current_action=a_curr,
                                               single_step_mode=False)
        
        # TD误差用于更新优先级
        td_error = (current_Q1 - target_Q).detach().abs() + (current_Q2 - target_Q).detach().abs()
        
        # Critic损失（带PER权重）
        loss_Q1 = F.mse_loss(current_Q1, target_Q, reduction='none')
        loss_Q2 = F.mse_loss(current_Q2, target_Q, reduction='none')
        q_loss = ((loss_Q1 + loss_Q2) * weights).mean()
        
        # 优化Critic
        self.q_critic_optimizer.zero_grad()
        q_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.q_critic.parameters(), self.max_grad_norm)
        self.q_critic_optimizer.step()
        
        self.q_loss_history.append(q_loss.item())
        
        # 更新优先级
        new_priorities = td_error.mean(dim=1)
        self.replay_buffer.update_priorities(indices, new_priorities)
        
        # =================== Delayed Policy Updates ===================
        a_loss_value = 0.0
        if self.total_it % self.policy_freq == 0:
            # 冻结Critic
            for params in self.q_critic.parameters():
                params.requires_grad = False
            
            # Actor损失：最大化Q值
            action = self.actor(state_sequence=s_seq, action_sequence=a_seq,
                               current_state=s_curr, single_step_mode=False)
            Q1, Q2 = self.q_critic(state_sequence=s_seq, action_sequence=a_seq,
                                  current_state=s_curr, current_action=action,
                                  single_step_mode=False)
            a_loss = -Q1.mean()  # TD3只使用Q1
            
            # 优化Actor
            self.actor_optimizer.zero_grad()
            a_loss.backward()
            torch.nn.utils.clip_grad_norm_(self.actor.parameters(), self.max_grad_norm)
            self.actor_optimizer.step()
            
            a_loss_value = a_loss.item()
            self.a_loss_history.append(a_loss_value)
            
            # 解冻Critic
            for params in self.q_critic.parameters():
                params.requires_grad = True
            
            # 软更新目标网络
            for param, target_param in zip(self.actor.parameters(), self.actor_target.parameters()):
                target_param.data.copy_(self.tau * param.data + (1 - self.tau) * target_param.data)
            
            for param, target_param in zip(self.q_critic.parameters(), self.q_critic_target.parameters()):
                target_param.data.copy_(self.tau * param.data + (1 - self.tau) * target_param.data)
        else:
            self.a_loss_history.append(0.0)
        
        return {
            'q_loss': q_loss.item(),
            'a_loss': a_loss_value,
            'policy_updated': (self.total_it % self.policy_freq == 0)
        }

    def save(self, EnvName, timestep):
        torch.save(self.actor.state_dict(), "./model/{}_td3_actor{}.pth".format(EnvName, timestep))
        torch.save(self.q_critic.state_dict(), "./model/{}_td3_q_critic{}.pth".format(EnvName, timestep))
        torch.save(self.state_normalizer.state_dict(), "./model/{}_td3_normalizer{}.pth".format(EnvName, timestep))

    def load(self, EnvName, timestep):
        self.actor.load_state_dict(torch.load("./model/{}_td3_actor{}.pth".format(EnvName, timestep), 
                                              map_location=self.dvc))
        self.q_critic.load_state_dict(torch.load("./model/{}_td3_q_critic{}.pth".format(EnvName, timestep), 
                                                 map_location=self.dvc))
        try:
            normalizer_state = torch.load("./model/{}_td3_normalizer{}.pth".format(EnvName, timestep), 
                                         map_location=self.dvc)
            self.state_normalizer.load_state_dict(normalizer_state)
        except FileNotFoundError:
            print("Warning: Normalizer parameters not found, using default initialization.")


class ReplayBuffer():
    def __init__(self, state_dim, action_dim, seq_len, max_size, dvc, alpha=0.6, beta=0.4):
        self.max_size = max_size
        self.dvc = dvc
        self.ptr = 0
        self.size = 0
        self.seq_len = seq_len
        
        self.s_seq = torch.zeros((max_size, seq_len, state_dim), dtype=torch.float, device=self.dvc)
        self.a_seq = torch.zeros((max_size, seq_len, action_dim), dtype=torch.float, device=self.dvc)
        self.s_curr = torch.zeros((max_size, state_dim), dtype=torch.float, device=self.dvc)
        self.a_curr = torch.zeros((max_size, action_dim), dtype=torch.float, device=self.dvc)
        self.r = torch.zeros((max_size, 1), dtype=torch.float, device=self.dvc)
        self.s_next_seq = torch.zeros((max_size, seq_len, state_dim), dtype=torch.float, device=self.dvc)
        self.a_next_seq = torch.zeros((max_size, seq_len, action_dim), dtype=torch.float, device=self.dvc)
        self.s_next_curr = torch.zeros((max_size, state_dim), dtype=torch.float, device=self.dvc)
        self.dw = torch.zeros((max_size, 1), dtype=torch.bool, device=self.dvc)
        
        self.priorities = torch.ones((max_size, 1), dtype=torch.float, device=self.dvc)
        self.alpha = alpha
        self.beta = beta
        self.epsilon = 1e-6

    def add(self, s_seq, a_seq, s_curr, action, r, s_next_seq, a_next_seq, s_next_curr, dw):
        self.s_seq[self.ptr] = torch.from_numpy(s_seq).to(self.dvc, non_blocking=True)
        self.a_seq[self.ptr] = torch.from_numpy(a_seq).to(self.dvc, non_blocking=True)
        self.s_curr[self.ptr] = torch.from_numpy(s_curr).to(self.dvc, non_blocking=True)
        self.a_curr[self.ptr] = torch.from_numpy(action).to(self.dvc, non_blocking=True)
        self.r[self.ptr] = r
        self.s_next_seq[self.ptr] = torch.from_numpy(s_next_seq).to(self.dvc, non_blocking=True)
        self.a_next_seq[self.ptr] = torch.from_numpy(a_next_seq).to(self.dvc, non_blocking=True)
        self.s_next_curr[self.ptr] = torch.from_numpy(s_next_curr).to(self.dvc, non_blocking=True)
        self.dw[self.ptr] = bool(dw)
        
        if self.size > 0:
            max_prio = self.priorities[:self.size].max().item()
        else:
            max_prio = 1.0
        self.priorities[self.ptr] = max_prio

        self.ptr = (self.ptr + 1) % self.max_size
        self.size = min(self.size + 1, self.max_size)

    def sample(self, batch_size):
        prios = self.priorities[:self.size]
        prios_cpu = prios.cpu().flatten()
        probs_cpu = (prios_cpu + self.epsilon) ** self.alpha
        probs_cpu = probs_cpu / probs_cpu.sum()
        
        probs_numpy = probs_cpu.numpy()
        if np.any(np.isnan(probs_numpy)) or np.any(np.isinf(probs_numpy)):
            probs_numpy = np.ones(self.size) / self.size
        
        actual_batch_size = min(batch_size, self.size)
        indices = np.random.choice(self.size, actual_batch_size, p=probs_numpy)
        indices = torch.tensor(indices, device=self.dvc)

        total = self.size
        selected_probs = torch.tensor(probs_numpy[indices.cpu()], device=self.dvc).view(-1, 1)
        weights = (total * selected_probs) ** (-self.beta)
        weights = weights / weights.max()

        return (self.s_seq[indices], self.a_seq[indices], self.s_curr[indices], self.a_curr[indices],
                self.r[indices], self.s_next_seq[indices], self.a_next_seq[indices], self.s_next_curr[indices],
                self.dw[indices], indices, weights)

    def update_priorities(self, indices, new_priorities):
        new_priorities = new_priorities.view(-1, 1)
        self.priorities[indices] = new_priorities + self.epsilon
    
    def update_beta(self, progress):
        self.beta = 0.4 + progress * (1.0 - 0.4)