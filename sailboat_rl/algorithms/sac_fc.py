from pathlib import Path

from .utils_fc import Actor, Double_Q_Critic, ZScoreNormalizer
from .per_sampling import optimized_sample, validate_per_backend
import torch.nn.functional as F
import numpy as np
import torch
import copy


class SAC_fc_continuous():
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.tau = 0.002
        
        # 添加预热参数
        self.critic_warmup_steps = 0
        self.training_step = 0
        
        # 添加延迟更新参数
        self.policy_update_freq = 4
        self.critic_update_count = 0
        self.actor_update_count = 0
        self.alpha_update_count = 0
        
        # 添加梯度裁剪参数
        self.max_grad_norm = 1.0
        
        # 添加loss监控
        self.q_loss_history = []
        self.a_loss_history = []
        self.alpha_loss_history = []

        # 初始化Z-score标准化器
        self.state_normalizer = ZScoreNormalizer(self.state_dim, self.dvc)

        self.actor = Actor(self.state_dim, self.action_dim, (self.net_width,512,256)).to(self.dvc)
        self.actor_optimizer = torch.optim.Adam(self.actor.parameters(), lr=self.a_lr, weight_decay=1e-5)

        self.q_critic = Double_Q_Critic(self.state_dim, self.action_dim, (self.net_width,512,256),(self.net_width,512,128)).to(self.dvc)
        self.q_critic_optimizer = torch.optim.Adam(self.q_critic.parameters(), lr=self.c_lr, weight_decay=1e-5)
        self.q_critic_target = copy.deepcopy(self.q_critic)
        for p in self.q_critic_target.parameters():
            p.requires_grad = False

        self.replay_buffer = ReplayBuffer(
            self.state_dim,
            self.action_dim,
            max_size=int(getattr(self, 'replay_capacity', 1e6)),
            dvc=self.dvc,
            per_backend=getattr(self, 'per_backend', 'optimized'),
        )

        if self.adaptive_alpha:
            self.target_entropy = torch.tensor(-0.5 * float(self.action_dim), dtype=torch.float32, device=self.dvc)
            self.log_alpha = torch.tensor(np.log(self.alpha), dtype=torch.float32, requires_grad=True, device=self.dvc)
            self.alpha_lr = self.c_lr * 0.2
            self.alpha_optim = torch.optim.Adam([self.log_alpha], lr=self.alpha_lr)

    def select_action(self, state, deterministic):
        with torch.no_grad():
            state = np.asarray(state, dtype=np.float32)
            if not np.all(np.isfinite(state)):
                return np.zeros(self.action_dim, dtype=np.float32)
            state = torch.FloatTensor(state[np.newaxis, ...]).to(self.dvc, non_blocking=True)  # (1, state_dim)
            state = self.state_normalizer.normalize(state)
            if not torch.isfinite(state).all():
                return np.zeros(self.action_dim, dtype=np.float32)
            a, _ = self.actor(current_state=state, deterministic=deterministic, with_logprob=False)
        action = a.cpu().numpy()[0]
        if not np.all(np.isfinite(action)):
            return np.zeros(self.action_dim, dtype=np.float32)
        return action

    def select_actions(self, states, deterministic, backend=None):
        backend = backend or getattr(self, 'actor_inference_backend', 'batched')
        if backend == 'serial':
            return np.asarray([self.select_action(state, deterministic) for state in states])
        if backend != 'batched':
            raise ValueError("actor_inference_backend must be 'serial' or 'batched'")

        states = np.asarray(states, dtype=np.float32)
        actions = np.zeros((len(states), self.action_dim), dtype=np.float32)
        valid_rows = np.all(np.isfinite(states), axis=1)
        if not np.any(valid_rows):
            return actions

        with torch.no_grad():
            state_batch = torch.as_tensor(states[valid_rows], dtype=torch.float32, device=self.dvc)
            state_batch = self.state_normalizer.normalize(state_batch)
            normalized_rows = torch.isfinite(state_batch).all(dim=1)
            if normalized_rows.any():
                valid_indices = np.flatnonzero(valid_rows)[normalized_rows.cpu().numpy()]
                action_batch, _ = self.actor(
                    current_state=state_batch[normalized_rows],
                    deterministic=deterministic,
                    with_logprob=False,
                )
                action_batch = action_batch.cpu().numpy()
                finite_actions = np.all(np.isfinite(action_batch), axis=1)
                actions[valid_indices[finite_actions]] = action_batch[finite_actions]
        return actions

    def train(self):
        s, a, r, s_next, dw, indices, weights = self.replay_buffer.sample(self.batch_size)
        
        self.training_step += 1
        
        # 更新标准化器统计量
        self.state_normalizer.update(s)
        self.state_normalizer.update(s_next)
        
        # 对状态进行标准化
        s = self.state_normalizer.normalize(s)
        s_next = self.state_normalizer.normalize(s_next)

        #----------------------------- Update Q Net ------------------------------#
        with torch.no_grad():
            a_next, log_pi_a_next = self.actor(current_state=s_next, deterministic=False, with_logprob=True)
            target_Q1, target_Q2 = self.q_critic_target(current_state=s_next, current_action=a_next)
            target_Q = torch.min(target_Q1, target_Q2)
            target_Q = r + (~dw) * self.gamma * (target_Q - self.alpha * log_pi_a_next)

        current_Q1, current_Q2 = self.q_critic(current_state=s, current_action=a)
        td_error = (current_Q1 - target_Q).detach().abs() + (current_Q2 - target_Q).detach().abs()

        loss_Q1 = F.mse_loss(current_Q1, target_Q, reduction='none')
        loss_Q2 = F.mse_loss(current_Q2, target_Q, reduction='none')
        q_loss = (loss_Q1 + loss_Q2) * weights
        q_loss = q_loss.mean()

        self.q_critic_optimizer.zero_grad()
        q_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.q_critic.parameters(), self.max_grad_norm)
        self.q_critic_optimizer.step()
        
        self.q_loss_history.append(q_loss.item())

        # 更新采样优先级
        new_priorities = td_error.mean(dim=1)
        self.replay_buffer.update_priorities(indices, new_priorities)

        # 预热阶段：只更新critic，不更新actor和alpha
        if self.training_step <= self.critic_warmup_steps:
            for param, target_param in zip(self.q_critic.parameters(), self.q_critic_target.parameters()):
                target_param.data.copy_(self.tau * param.data + (1 - self.tau) * target_param.data)
            
            return {
                'q_loss': q_loss.item(),
                'a_loss': 0.0,
                'alpha_loss': 0.0,
                'alpha': self.alpha.item() if (self.adaptive_alpha and hasattr(self.alpha, 'item')) else self.alpha,
                'warmup': True,
                'warmup_progress': self.training_step / self.critic_warmup_steps
            }

        self.critic_update_count += 1
        should_update_policy = (self.critic_update_count % self.policy_update_freq == 0)
        
        a_loss = torch.tensor(0.0)
        alpha_loss = torch.tensor(0.0)
        
        if should_update_policy:
            #----------------------------- Update Actor Net ------------------------------#
            for params in self.q_critic.parameters(): 
                params.requires_grad = False

            a_policy, log_pi_a = self.actor(current_state=s, deterministic=False, with_logprob=True)
            current_Q1, current_Q2 = self.q_critic(current_state=s, current_action=a_policy)
            Q = torch.min(current_Q1, current_Q2)
            a_loss = (self.alpha * log_pi_a - Q).mean()

            self.actor_optimizer.zero_grad()
            a_loss.backward()
            torch.nn.utils.clip_grad_norm_(self.actor.parameters(), self.max_grad_norm)
            self.actor_optimizer.step()
            self.actor_update_count += 1
            
            self.a_loss_history.append(a_loss.item())

            for params in self.q_critic.parameters(): 
                params.requires_grad = True

            #----------------------------- Update alpha ------------------------------#
            if self.adaptive_alpha:
                _, log_pi_a_for_alpha = self.actor(current_state=s, deterministic=False, with_logprob=True)
                alpha_loss = -(self.log_alpha * (log_pi_a_for_alpha + self.target_entropy).detach()).mean()

                self.alpha_optim.zero_grad()
                alpha_loss.backward()  
                torch.nn.utils.clip_grad_norm_([self.log_alpha], self.max_grad_norm)
                self.alpha_optim.step()
                self.alpha_update_count += 1
                
                self.alpha = self.log_alpha.exp()
                self.alpha_loss_history.append(alpha_loss.item())
            else:
                alpha_loss = torch.tensor(0.0)
                self.alpha_loss_history.append(0.0)
        else:
            self.a_loss_history.append(0.0)
            self.alpha_loss_history.append(0.0)

        #----------------------------- Update Target Net ------------------------------#
        for param, target_param in zip(self.q_critic.parameters(), self.q_critic_target.parameters()):
            target_param.data.copy_(self.tau * param.data + (1 - self.tau) * target_param.data)
        
        return {
            'q_loss': q_loss.item(),
            'a_loss': a_loss.item(),
            'alpha_loss': alpha_loss.item() if self.adaptive_alpha else 0.0,
            'alpha': self.alpha.item() if (self.adaptive_alpha and hasattr(self.alpha, 'item')) else self.alpha,
            'warmup': False,
            'policy_updated': should_update_policy,
            'critic_update_count': self.critic_update_count,
        }

    def save(self, EnvName, timestep):
        model_dir = Path(self.model_dir)
        model_dir.mkdir(parents=True, exist_ok=True)
        torch.save(self.actor.state_dict(), model_dir / "{}_actor{}.pth".format(EnvName,timestep))
        torch.save(self.q_critic.state_dict(), model_dir / "{}_q_critic{}.pth".format(EnvName,timestep))
        torch.save(self.state_normalizer.state_dict(), model_dir / "{}_normalizer{}.pth".format(EnvName,timestep))

    def load(self, EnvName, timestep):
        model_dir = Path(self.model_dir)
        self.actor.load_state_dict(torch.load(model_dir / "{}_actor{}.pth".format(EnvName, timestep), map_location=self.dvc))
        self.q_critic.load_state_dict(torch.load(model_dir / "{}_q_critic{}.pth".format(EnvName, timestep), map_location=self.dvc))
        try:
            normalizer_state = torch.load(model_dir / "{}_normalizer{}.pth".format(EnvName, timestep), map_location=self.dvc)
            self.state_normalizer.load_state_dict(normalizer_state)
        except FileNotFoundError:
            print("Warning: Normalizer parameters not found, using default initialization.")


class ReplayBuffer():
    def __init__(self, state_dim, action_dim, max_size, dvc, alpha=0.6, beta=0.4, per_backend='optimized'):
        self.max_size = max_size
        self.dvc = dvc
        self.ptr = 0
        self.size = 0
        
        self.s = torch.zeros((max_size, state_dim), dtype=torch.float, device=self.dvc)
        self.a = torch.zeros((max_size, action_dim), dtype=torch.float, device=self.dvc)
        self.r = torch.zeros((max_size, 1), dtype=torch.float, device=self.dvc)
        self.s_next = torch.zeros((max_size, state_dim), dtype=torch.float, device=self.dvc)
        self.dw = torch.zeros((max_size, 1), dtype=torch.bool, device=self.dvc)
        
        self.priorities = torch.ones((max_size, 1), dtype=torch.float, device=self.dvc)
        self.alpha = alpha
        self.beta = beta
        self.epsilon = 1e-6
        self.per_backend = validate_per_backend(per_backend)

    def add(self, state, action, reward, next_state, dw):
        if not (
            np.all(np.isfinite(state)) and
            np.all(np.isfinite(action)) and
            np.isfinite(reward) and
            np.all(np.isfinite(next_state))
        ):
            return False
        self.s[self.ptr] = torch.from_numpy(state).to(self.dvc, non_blocking=True)
        self.a[self.ptr] = torch.from_numpy(action).to(self.dvc, non_blocking=True)
        self.r[self.ptr] = float(reward)
        self.s_next[self.ptr] = torch.from_numpy(next_state).to(self.dvc, non_blocking=True)
        self.dw[self.ptr] = bool(dw)
        
        if self.size > 0:
            max_prio = self.priorities[:self.size].max().item()
        else:
            max_prio = 1.0
        self.priorities[self.ptr] = max_prio

        self.ptr = (self.ptr + 1) % self.max_size
        self.size = min(self.size + 1, self.max_size)
        return True

    def sample(self, batch_size):
        if self.per_backend == 'optimized':
            indices, weights = optimized_sample(
                self.priorities,
                self.size,
                batch_size,
                self.epsilon,
                self.alpha,
                self.beta,
            )
            return (self.s[indices], self.a[indices], self.r[indices], self.s_next[indices],
                    self.dw[indices], indices, weights)

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

        return (self.s[indices], self.a[indices], self.r[indices], self.s_next[indices], 
                self.dw[indices], indices, weights)

    def update_priorities(self, indices, new_priorities):
        new_priorities = new_priorities.view(-1, 1)
        self.priorities[indices] = new_priorities + self.epsilon
        
    def update_beta(self, progress):
        self.beta = 0.4 + progress * (1.0 - 0.4)

    def state_dict(self):
        size = int(self.size)
        return {
            'schema_version': 1,
            'max_size': int(self.max_size),
            'size': size,
            'ptr': int(self.ptr),
            'alpha': float(self.alpha),
            'beta': float(self.beta),
            'epsilon': float(self.epsilon),
            'per_backend': self.per_backend,
            'max_priority': float(self.priorities[:size].max().item()) if size else 1.0,
            's': self.s[:size].detach().cpu().clone(),
            'a': self.a[:size].detach().cpu().clone(),
            'r': self.r[:size].detach().cpu().clone(),
            's_next': self.s_next[:size].detach().cpu().clone(),
            'dw': self.dw[:size].detach().cpu().clone(),
            'priorities': self.priorities[:size].detach().cpu().clone(),
        }

    def load_state_dict(self, state_dict):
        if int(state_dict['max_size']) != int(self.max_size):
            raise ValueError(
                f"Replay capacity mismatch: checkpoint={state_dict['max_size']}, runtime={self.max_size}"
            )
        saved_backend = state_dict.get('per_backend')
        if saved_backend is not None and validate_per_backend(saved_backend) != self.per_backend:
            raise ValueError(
                f"PER backend mismatch: checkpoint={saved_backend}, runtime={self.per_backend}"
            )
        size = int(state_dict['size'])
        ptr = int(state_dict['ptr'])
        if not 0 <= size <= self.max_size or not 0 <= ptr < self.max_size:
            raise ValueError(f"Invalid replay cursor: size={size}, ptr={ptr}, capacity={self.max_size}")
        for name in ('s', 'a', 'r', 's_next', 'dw', 'priorities'):
            source = state_dict[name]
            target = getattr(self, name)
            if source.shape != target[:size].shape:
                raise ValueError(f"Replay tensor shape mismatch for {name}: {source.shape} != {target[:size].shape}")
            target[:size].copy_(source.to(self.dvc))
        self.size = size
        self.ptr = ptr
        self.alpha = float(state_dict['alpha'])
        self.beta = float(state_dict['beta'])
        self.epsilon = float(state_dict['epsilon'])
