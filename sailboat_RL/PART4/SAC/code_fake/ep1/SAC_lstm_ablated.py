import os
import torch.nn.functional as F
import numpy as np
import torch
import copy

from utils_lstm_ablated import Actor, Double_Q_Critic, ZScoreNormalizer

class SAC_lstm_countinuous():
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.tau, self.seq_len = 0.002, 10
        self.critic_warmup_steps, self.training_step = 0, 0
        self.policy_update_freq, self.critic_update_count = 4, 0
        self.max_grad_norm = 1.0
        self.q_loss_history, self.a_loss_history, self.alpha_loss_history = [], [], []

        self.state_normalizer = ZScoreNormalizer(self.state_dim, self.dvc)

        self.actor = Actor(self.state_dim, self.action_dim, (self.net_width, 256)).to(self.dvc)
        self.actor_optimizer = torch.optim.Adam(self.actor.parameters(), lr=self.a_lr, weight_decay=1e-5)

        self.q_critic = Double_Q_Critic(self.state_dim, self.action_dim, (self.net_width, 256), (self.net_width, 128)).to(self.dvc)
        self.q_critic_optimizer = torch.optim.Adam(self.q_critic.parameters(), lr=self.c_lr, weight_decay=1e-5)
        self.q_critic_target = copy.deepcopy(self.q_critic)
        for p in self.q_critic_target.parameters(): p.requires_grad = False

        self.replay_buffer = ReplayBuffer(self.state_dim, self.action_dim, self.seq_len, max_size=int(1e6), dvc=self.dvc)

        if self.adaptive_alpha:
            self.target_entropy = torch.tensor(-float(self.action_dim), dtype=torch.float32, device=self.dvc)
            self.log_alpha = torch.tensor(np.log(self.alpha), dtype=torch.float32, requires_grad=True, device=self.dvc)
            self.alpha_optim = torch.optim.Adam([self.log_alpha], lr=self.c_lr * 0.1)

    def select_action(self, prev_state, prev_action, current_state, deterministic, total_steps, env_id=None):
        with torch.no_grad():
            current_state = self.state_normalizer.normalize(
                torch.FloatTensor(current_state[np.newaxis, ...]).to(self.dvc, non_blocking=True)
            )
            a, _ = self.actor(
                current_state=current_state,
                deterministic=deterministic,
                with_logprob=False,
                env_ids=[env_id] if env_id is not None else None,
                single_step_mode=True
            )
        return a.cpu().numpy()[0]

    def train(self):
        s_seq, a_seq, s_curr, a_curr, r, s_next_seq, a_next_seq, s_next_curr, dw, indices, weights = self.replay_buffer.sample(self.batch_size)
        
        self.training_step += 1
        self.state_normalizer.update(s_seq)
        self.state_normalizer.update(s_curr)
        self.state_normalizer.update(s_next_seq)
        self.state_normalizer.update(s_next_curr)
        s_seq = self.state_normalizer.normalize(s_seq)
        s_curr = self.state_normalizer.normalize(s_curr)
        s_next_seq = self.state_normalizer.normalize(s_next_seq)
        s_next_curr = self.state_normalizer.normalize(s_next_curr)

        # ------------------- Q Net 更新 ------------------- #
        with torch.no_grad():
            # Actor 仅依赖状态序列，使用 s_{t+1} 序列（末位为 s_{t+1}）
            a_next, log_pi_a_next = self.actor(
                state_sequence=s_next_seq,
                deterministic=False,
                with_logprob=True,
                single_step_mode=False
            )
            target_Q1, target_Q2 = self.q_critic_target(
                state_sequence=s_next_seq,
                action_sequence=a_next_seq,
                current_state=s_next_curr,
                current_action=a_next,
                single_step_mode=False
            )
            target_Q = r + (~dw) * self.gamma * (torch.min(target_Q1, target_Q2) - self.alpha * log_pi_a_next)

        current_Q1, current_Q2 = self.q_critic(
            state_sequence=s_seq,
            action_sequence=a_seq,
            current_state=s_curr,
            current_action=a_curr,
            single_step_mode=False
        )
        td_error = (current_Q1 - target_Q).detach().abs() + (current_Q2 - target_Q).detach().abs()
        q_loss = ((F.mse_loss(current_Q1, target_Q, reduction='none') + F.mse_loss(current_Q2, target_Q, reduction='none')) * weights).mean()

        self.q_critic_optimizer.zero_grad()
        q_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.q_critic.parameters(), self.max_grad_norm)
        self.q_critic_optimizer.step()
        self.q_loss_history.append(q_loss.item())
        self.replay_buffer.update_priorities(indices, td_error.mean(dim=1))

        if self.training_step <= self.critic_warmup_steps:
            for param, target_param in zip(self.q_critic.parameters(), self.q_critic_target.parameters()): target_param.data.copy_(self.tau * param.data + (1 - self.tau) * target_param.data)
            return {'q_loss': q_loss.item(), 'a_loss': 0.0, 'alpha_loss': 0.0, 'warmup': True}

        # ------------------- 策略网络延迟更新 ------------------- #
        self.critic_update_count += 1
        should_update_policy = (self.critic_update_count % self.policy_update_freq == 0)
        a_loss, alpha_loss = torch.tensor(0.0), torch.tensor(0.0)
        
        if should_update_policy:
            for params in self.q_critic.parameters(): params.requires_grad = False
            with torch.set_grad_enabled(True):
                # Actor 使用 s_t 序列（末位为 s_t）
                a_policy, log_pi_a = self.actor(
                    state_sequence=s_seq,
                    deterministic=False,
                    with_logprob=True,
                    single_step_mode=False
                )
                current_Q1, current_Q2 = self.q_critic(
                    state_sequence=s_seq,
                    action_sequence=a_seq,
                    current_state=s_curr,
                    current_action=a_policy,
                    single_step_mode=False
                )
                a_loss = (self.alpha * log_pi_a - torch.min(current_Q1, current_Q2)).mean()

            self.actor_optimizer.zero_grad()
            a_loss.backward()
            torch.nn.utils.clip_grad_norm_(self.actor.parameters(), self.max_grad_norm)
            self.actor_optimizer.step()
            self.a_loss_history.append(a_loss.item())
            for params in self.q_critic.parameters(): params.requires_grad = True

            if self.adaptive_alpha:
                with torch.set_grad_enabled(True):
                    _, log_pi_a_for_alpha = self.actor(
                        state_sequence=s_seq,
                        deterministic=False,
                        with_logprob=True,
                        single_step_mode=False
                    )
                    alpha_loss = -(self.log_alpha * (log_pi_a_for_alpha + self.target_entropy.detach()).detach()).mean()

                self.alpha_optim.zero_grad()
                if self.log_alpha.device != self.dvc: self.log_alpha = self.log_alpha.to(self.dvc)
                alpha_loss.backward()  
                torch.nn.utils.clip_grad_norm_([self.log_alpha], self.max_grad_norm)
                self.alpha_optim.step()
                self.alpha = self.log_alpha.exp()
                self.alpha_loss_history.append(alpha_loss.item())
            else: self.alpha_loss_history.append(0.0)
        else:
            self.a_loss_history.append(0.0); self.alpha_loss_history.append(0.0)

        for param, target_param in zip(self.q_critic.parameters(), self.q_critic_target.parameters()):
            target_param.data.copy_(self.tau * param.data + (1 - self.tau) * target_param.data)
        
        return {
            'q_loss': q_loss.item(), 'a_loss': a_loss.item(),
            'alpha_loss': alpha_loss.item() if self.adaptive_alpha else 0.0,
            'alpha': self.alpha.item() if (self.adaptive_alpha and hasattr(self.alpha, 'item')) else self.alpha,
            'warmup': False, 'policy_updated': should_update_policy, 'critic_update_count': self.critic_update_count
        }

    def _get_model_dir(self):
        model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model_ablated")
        os.makedirs(model_dir, exist_ok=True) 
        return model_dir

    def save(self, EnvName, timestep):
        model_dir = self._get_model_dir()
        torch.save(self.actor.state_dict(), os.path.join(model_dir, f"{EnvName}_ablated_actor{timestep}.pth"))
        torch.save(self.q_critic.state_dict(), os.path.join(model_dir, f"{EnvName}_ablated_q_critic{timestep}.pth"))
        torch.save(self.state_normalizer.state_dict(), os.path.join(model_dir, f"{EnvName}_ablated_normalizer{timestep}.pth"))

    def load(self, EnvName, timestep):
        model_dir = self._get_model_dir()
        self.actor.load_state_dict(torch.load(os.path.join(model_dir, f"{EnvName}_ablated_actor{timestep}.pth"), map_location=self.dvc))
        self.q_critic.load_state_dict(torch.load(os.path.join(model_dir, f"{EnvName}_ablated_q_critic{timestep}.pth"), map_location=self.dvc))
        try:
            self.state_normalizer.load_state_dict(torch.load(os.path.join(model_dir, f"{EnvName}_ablated_normalizer{timestep}.pth"), map_location=self.dvc))
        except FileNotFoundError:
            pass

class ReplayBuffer():
    # 保持与原始 Baseline 的 Buffer 代码完全一致，直接沿用原来的那段即可，不要做任何精简。
    def __init__(self, state_dim, action_dim, seq_len, max_size, dvc, alpha=0.6, beta=0.4):
        self.max_size, self.dvc, self.ptr, self.size, self.seq_len = max_size, dvc, 0, 0, seq_len
        self.s_seq = torch.zeros((max_size, seq_len, state_dim), dtype=torch.float, device=self.dvc)
        self.a_seq = torch.zeros((max_size, seq_len, action_dim), dtype=torch.float, device=self.dvc)
        self.s_curr, self.a_curr, self.r = torch.zeros((max_size, state_dim), dtype=torch.float, device=self.dvc), torch.zeros((max_size, action_dim), dtype=torch.float, device=self.dvc), torch.zeros((max_size, 1), dtype=torch.float, device=self.dvc)
        self.s_next_seq = torch.zeros((max_size, seq_len, state_dim), dtype=torch.float, device=self.dvc)
        self.a_next_seq = torch.zeros((max_size, seq_len, action_dim), dtype=torch.float, device=self.dvc)
        self.s_next_curr, self.dw = torch.zeros((max_size, state_dim), dtype=torch.float, device=self.dvc), torch.zeros((max_size, 1), dtype=torch.bool, device=self.dvc)
        self.priorities, self.alpha, self.beta, self.epsilon = torch.ones((max_size, 1), dtype=torch.float, device=self.dvc), alpha, beta, 1e-6

    def add(self, s_seq, a_seq, s_curr, action, r, s_next_seq, a_next_seq, s_next_curr, dw):
        self.s_seq[self.ptr], self.a_seq[self.ptr] = torch.from_numpy(s_seq).to(self.dvc, non_blocking=True), torch.from_numpy(a_seq).to(self.dvc, non_blocking=True)
        self.s_curr[self.ptr], self.a_curr[self.ptr], self.r[self.ptr] = torch.from_numpy(s_curr).to(self.dvc, non_blocking=True), torch.from_numpy(action).to(self.dvc, non_blocking=True), r
        self.s_next_seq[self.ptr], self.a_next_seq[self.ptr] = torch.from_numpy(s_next_seq).to(self.dvc, non_blocking=True), torch.from_numpy(a_next_seq).to(self.dvc, non_blocking=True)
        self.s_next_curr[self.ptr], self.dw[self.ptr] = torch.from_numpy(s_next_curr).to(self.dvc, non_blocking=True), bool(dw)
        self.priorities[self.ptr] = self.priorities[:self.size].max().item() if self.size > 0 else 1.0
        self.ptr = (self.ptr + 1) % self.max_size
        self.size = min(self.size + 1, self.max_size)

    def sample(self, batch_size):
        probs = ((self.priorities[:self.size].cpu().flatten() + self.epsilon) ** self.alpha).numpy()
        probs = (probs / probs.sum()) if not (np.any(np.isnan(probs)) or np.any(np.isinf(probs))) else np.ones(self.size) / self.size
        indices = torch.tensor(np.random.choice(self.size, min(batch_size, self.size), p=probs), device=self.dvc)
        weights = ((self.size * torch.tensor(probs[indices.cpu()], device=self.dvc).view(-1, 1)) ** (-self.beta))
        weights = weights / weights.max()
        return (self.s_seq[indices], self.a_seq[indices], self.s_curr[indices], self.a_curr[indices], self.r[indices], self.s_next_seq[indices], self.a_next_seq[indices], self.s_next_curr[indices], self.dw[indices], indices, weights)

    def update_priorities(self, indices, new_priorities): self.priorities[indices] = new_priorities.view(-1, 1) + self.epsilon
    def update_beta(self, progress): self.beta = 0.4 + progress * (1.0 - 0.4)
