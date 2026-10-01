from utils_lstm import Actor, Double_Q_Critic
import torch.nn.functional as F
import numpy as np
import torch
import copy
import globals


class SAC_lstm_countinuous():
    def __init__(self, **kwargs):
        # Init hyperparameters for agent, just like "self.gamma = opt.gamma, self.lambd = opt.lambd, ..."
        self.__dict__.update(kwargs)
        self.tau = 0.005
        
        # 添加梯度裁剪参数
        self.max_grad_norm = 1.0
        
        # 添加loss监控
        self.q_loss_history = []
        self.a_loss_history = []
        self.alpha_loss_history = []

        self.actor = Actor(self.state_dim, self.action_dim, (self.net_width,128)).to(self.dvc)
        self.actor_optimizer = torch.optim.Adam(self.actor.parameters(), lr=self.a_lr, weight_decay=1e-5)

        self.q_critic = Double_Q_Critic(self.state_dim, self.action_dim, (self.net_width,128),(self.net_width,64)).to(self.dvc)
        self.q_critic_optimizer = torch.optim.Adam(self.q_critic.parameters(), lr=self.c_lr, weight_decay=1e-5)
        self.q_critic_target = copy.deepcopy(self.q_critic)
        # Freeze target networks with respect to optimizers (only update via polyak averaging)
        for p in self.q_critic_target.parameters():
            p.requires_grad = False

        self.replay_buffer = ReplayBuffer(self.state_dim, self.action_dim, max_size=int(1e6), dvc=self.dvc)

        if self.adaptive_alpha:
            # Target Entropy = −dim(A) (e.g. , -6 for HalfCheetah-v2) as given in the paper
            self.target_entropy = torch.tensor(-self.action_dim, dtype=float, requires_grad=True, device=self.dvc)
            # We learn log_alpha instead of alpha to ensure alpha>0
            self.log_alpha = torch.tensor(np.log(self.alpha), dtype=float, requires_grad=True, device=self.dvc)
            self.alpha_optim = torch.optim.Adam([self.log_alpha], lr=self.c_lr)

    def select_action(self, state_seq, deterministic, total_steps):
        # state_seq 应为 (5, state_dim)
        with torch.no_grad():
            state_seq = torch.FloatTensor(state_seq[np.newaxis, ...]).to(self.dvc)  # shape: (1,5,state_dim)
            a, _ = self.actor(state_seq, deterministic, with_logprob=False)
                
        return a.cpu().numpy()[0]

    def train(self,):
        s, a, r, s_next, dw, indices, weights = self.replay_buffer.sample(self.batch_size)

        #----------------------------- Update Q Net ------------------------------#
        with torch.no_grad():
            a_next, log_pi_a_next = self.actor(s_next, deterministic=False, with_logprob=True)
            a_next = a_next.unsqueeze(1).repeat(1, s_next.shape[1], 1)
            target_Q1, target_Q2 = self.q_critic_target(s_next, a_next)
            target_Q = torch.min(target_Q1, target_Q2)
            target_Q = r + (~dw) * self.gamma * (target_Q - self.alpha * log_pi_a_next)

        current_Q1, current_Q2 = self.q_critic(s, a)
        # 计算每个样本的TD误差（用于后续更新优先级）
        td_error = (current_Q1 - target_Q).detach().abs() + (current_Q2 - target_Q).detach().abs()

        # 使用 weights 调整 loss
        loss_Q1 = F.mse_loss(current_Q1, target_Q, reduction='none')
        loss_Q2 = F.mse_loss(current_Q2, target_Q, reduction='none')
        q_loss = (loss_Q1 + loss_Q2) * weights.unsqueeze(1)
        q_loss = q_loss.mean()

        self.q_critic_optimizer.zero_grad()
        q_loss.backward()
        # 添加梯度裁剪
        torch.nn.utils.clip_grad_norm_(self.q_critic.parameters(), self.max_grad_norm)
        self.q_critic_optimizer.step()
        
        # 记录 critic loss
        self.q_loss_history.append(q_loss.item())

        # 更新采样优先级
        new_priorities = td_error.mean(dim=1)
        self.replay_buffer.update_priorities(indices, new_priorities)

        #----------------------------- ↓↓↓↓↓ Update Actor Net ↓↓↓↓↓ ------------------------------#
        # Freeze critic so you don't waste computational effort computing gradients for them when update actor
        for params in self.q_critic.parameters(): params.requires_grad = False

        a, log_pi_a = self.actor(s, deterministic=False, with_logprob=True)
        if a.dim() == 2: a = a.unsqueeze(1).repeat(1, s.shape[1], 1)
        current_Q1, current_Q2 = self.q_critic(s, a)
        Q = torch.min(current_Q1, current_Q2)

        a_loss = (self.alpha * log_pi_a - Q).mean()
        self.actor_optimizer.zero_grad()
        a_loss.backward()
        # 添加梯度裁剪 
        torch.nn.utils.clip_grad_norm_(self.actor.parameters(), self.max_grad_norm)
        self.actor_optimizer.step()
        
        # 记录 actor loss
        self.a_loss_history.append(a_loss.item())

        for params in self.q_critic.parameters(): params.requires_grad = True

        #----------------------------- ↓↓↓↓↓ Update alpha ↓↓↓↓↓ ------------------------------#
        if self.adaptive_alpha:
            # We learn log_alpha instead of alpha to ensure alpha>0
            alpha_loss = -(self.log_alpha * (log_pi_a + self.target_entropy).detach()).mean()
            self.alpha_optim.zero_grad()
            alpha_loss.backward()
            # 添加梯度裁剪
            torch.nn.utils.clip_grad_norm_([self.log_alpha], self.max_grad_norm)
            self.alpha_optim.step()
            self.alpha = self.log_alpha.exp()
            
            # 记录 alpha loss
            self.alpha_loss_history.append(alpha_loss.item())
        else:
            alpha_loss = torch.tensor(0.0)
            self.alpha_loss_history.append(0.0)

        #----------------------------- ↓↓↓↓↓ Update Target Net ↓↓↓↓↓ ------------------------------#
        for param, target_param in zip(self.q_critic.parameters(), self.q_critic_target.parameters()):
            target_param.data.copy_(self.tau * param.data + (1 - self.tau) * target_param.data)
        
        return {
            'q_loss': q_loss.item(),
            'a_loss': a_loss.item(),
            'alpha_loss': alpha_loss.item() if self.adaptive_alpha else 0.0,
            'alpha': self.alpha.item() if self.adaptive_alpha else self.alpha
        }

    def save(self,EnvName, timestep):
        torch.save(self.actor.state_dict(), "./model/{}_actor{}.pth".format(EnvName,timestep))
        torch.save(self.q_critic.state_dict(), "./model/{}_q_critic{}.pth".format(EnvName,timestep))

    def load(self,EnvName, timestep):
        self.actor.load_state_dict(torch.load("./model/{}_actor{}.pth".format(EnvName, timestep), map_location=self.dvc))
        self.q_critic.load_state_dict(torch.load("./model/{}_q_critic{}.pth".format(EnvName, timestep), map_location=self.dvc))


class ReplayBuffer():
    def __init__(self, state_dim, action_dim, max_size, dvc, alpha=0.6, beta=0.4):
        self.max_size = max_size
        self.dvc = dvc
        self.ptr = 0
        self.size = 0
        # 存储5个连续时刻的状态
        self.s = torch.zeros((max_size, 5, state_dim), dtype=torch.float, device=self.dvc)
        self.a = torch.zeros((max_size, 5, action_dim), dtype=torch.float, device=self.dvc)
        self.r = torch.zeros((max_size, 1), dtype=torch.float, device=self.dvc)
        self.s_next = torch.zeros((max_size, 5, state_dim), dtype=torch.float, device=self.dvc)
        self.dw = torch.zeros((max_size, 1), dtype=torch.bool, device=self.dvc)
        
        # 初始化所有样本的优先级（初始值设为1）
        self.priorities = torch.ones((max_size, 1), dtype=torch.float, device=self.dvc)
        # PER参数
        self.alpha = alpha   # 控制优先级的重要性
        self.beta = beta     # importance-sampling权重
        self.epsilon = 1e-6  # 防止优先级为0

    def add(self, s_seq, a_seq, r, s_next_seq, dw):
        # s_seq 和 s_next_seq 的形状应为 (5, state_dim)， a_seq 的形状为 (5, action_dim)
        self.s[self.ptr] = torch.from_numpy(s_seq).to(self.dvc)
        self.a[self.ptr] = torch.from_numpy(a_seq).to(self.dvc)
        self.r[self.ptr] = r
        # self.r[self.ptr] = torch.tensor(r, dtype=torch.float, device=self.dvc)
        self.s_next[self.ptr] = torch.from_numpy(s_next_seq).to(self.dvc)
        self.dw[self.ptr] = bool(dw)
        # 对新加入的样本赋予最大的优先级
        if self.size > 0:
            max_prio = self.priorities[:self.size].max().item()
        else:
            max_prio = 1.0
        self.priorities[self.ptr] = max_prio

        self.ptr = (self.ptr + 1) % self.max_size
        self.size = min(self.size + 1, self.max_size)

    def sample(self, batch_size):
        # 从当前样本中根据优先级采样
        prios = self.priorities[:self.size]  # (size,1)
        probs = (prios + self.epsilon) ** self.alpha
        probs = probs / probs.sum()

        # 使用numpy按照概率采样索引
        indices = np.random.choice(self.size, batch_size, p=probs.cpu().numpy().flatten())
        indices = torch.tensor(indices, device=self.dvc)

        # importance-sampling权重
        total = self.size
        weights = (total * probs[indices]) ** (-self.beta)
        weights = weights / weights.max()

        return self.s[indices], self.a[indices], self.r[indices], self.s_next[indices], self.dw[indices], indices, weights

    def update_priorities(self, indices, new_priorities):
        # 更新采样的优先级值，new_priorities可以是TD error的绝对值
        new_priorities = new_priorities.view(-1, 1)
        self.priorities[indices] = new_priorities + self.epsilon
    def update_beta(self, progress):
		# 更新beta值
        self.beta = self.beta + progress * (1.0 - self.beta)  # 逐渐增加beta值