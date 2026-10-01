import os, shutil
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # 只显示错误信息
os.environ["KMP_DUPLICATE_LIB_OK"]="TRUE"

from utils_lstm_att_normal import str2bool, evaluate_policy, Action_adapter, Action_adapter_reverse, Reward_adapter
from datetime import datetime
from SAC_lstm_att_normal import SAC_lstm_countinuous
import gymnasium as gym
import argparse
import torch
import globals
import time
import numpy as np
from tqdm import tqdm
from stable_baselines3.common.vec_env import SubprocVecEnv
from collections import deque
import multiprocessing


def make_env(env_id, seed):
    def _init():
        env = gym.make(env_id)
        env.reset(seed=seed)
        return env
    return _init


def get_random_snr(opt):
    """
    从指定范围内随机选择SNR值（优先选择step的倍数）
    
    Returns:
        float: 选择的SNR值（dB）
    """
    if not opt.random_snr:
        return opt.snr_db
    
    # 生成SNR候选值（优先选择step的倍数）
    snr_candidates = []
    current_snr = opt.snr_min
    while current_snr <= opt.snr_max:
        snr_candidates.append(current_snr)
        current_snr += opt.snr_step
    
    # 如果候选列表为空，使用范围的中间值
    if len(snr_candidates) == 0:
        return (opt.snr_min + opt.snr_max) / 2.0
    
    # 随机选择一个SNR值
    selected_snr = np.random.choice(snr_candidates)
    return selected_snr


def add_awgn_noise(observation, snr_db, opt):
    """
    使用AWGN（加性高斯白噪声）为观测值添加噪声
    
    观测空间 (18维):
    [0-1]: x, y (位置) - 添加噪声
    [2]: psi (航向角) - 添加噪声
    [3]: phi (横滚角) - 添加噪声
    [4-7]: u, v, p, r (速度) - 添加噪声
    [8-9]: sail_angle, rudder_angle (帆角、舵角) - 不添加噪声
    [10-11]: 距离相关 - 添加噪声
    [12-13]: 目标位置 - 不添加噪声
    [14-17]: 障碍物位置 - 添加噪声
    
    AWGN模型: y = x + n, 其中 n ~ N(0, σ²)
    σ² = P_signal / (10^(SNR/10))
    
    Args:
        observation: 原始观测值，可以是单个观测 (state_dim,) 或批量观测 (num_envs, state_dim)
        snr_db: 信噪比（dB）
        opt: 参数对象
    """
    if not opt.add_sensor_noise:
        return observation.copy()
    
    # 判断输入是单个观测还是批量观测
    is_batch = len(observation.shape) == 2
    
    if is_batch:
        noisy_obs = observation.copy()
    else:
        noisy_obs = observation.copy()
        noisy_obs = noisy_obs.reshape(1, -1)  # 转换为批量格式以统一处理
    
    snr_linear = 10 ** (snr_db / 10.0)  # 将dB转换为线性值
    
    def add_awgn_to_signal(signal, snr_linear, scale_factor=1.0):
        """
        为单个信号或信号数组添加AWGN
        
        Args:
            signal: 信号值（可以是1D或2D数组）
            snr_linear: 线性信噪比
            scale_factor: 噪声缩放因子（用于调整不同类型信号的噪声强度）
        """
        # 计算信号功率
        signal_power = np.mean(signal ** 2)
        
        # 避免零信号功率（使用小的默认值）
        if signal_power < 1e-10:
            signal_power = 1e-10
        
        # 根据SNR计算噪声功率
        noise_power = signal_power / snr_linear
        
        # 应用缩放因子
        noise_std = np.sqrt(noise_power) * scale_factor
        
        # 生成高斯白噪声
        noise = np.random.normal(0, noise_std, signal.shape)
        
        return signal + noise
    
    # 位置噪声 (x, y)
    noisy_obs[:, 0:2] = add_awgn_to_signal(noisy_obs[:, 0:2], snr_linear, opt.noise_scale_pos)
    
    # 角度噪声 (psi, phi)
    noisy_obs[:, 2] = add_awgn_to_signal(noisy_obs[:, 2], snr_linear, opt.noise_scale_angle)
    noisy_obs[:, 3] = add_awgn_to_signal(noisy_obs[:, 3], snr_linear, opt.noise_scale_angle)
    
    # 速度噪声 (u, v, p, r)
    noisy_obs[:, 4:8] = add_awgn_to_signal(noisy_obs[:, 4:8], snr_linear, opt.noise_scale_vel)
    
    # 帆角和舵角 [8-9] - 不添加噪声
    # noisy_obs[:, 8] = add_awgn_to_signal(noisy_obs[:, 8], snr_linear, opt.noise_scale_angle)
    # noisy_obs[:, 9] = add_awgn_to_signal(noisy_obs[:, 9], snr_linear, opt.noise_scale_angle)
    
    # 距离测量噪声
    noisy_obs[:, 10] = add_awgn_to_signal(noisy_obs[:, 10], snr_linear, opt.noise_scale_dist)
    noisy_obs[:, 11] = add_awgn_to_signal(noisy_obs[:, 11], snr_linear, opt.noise_scale_dist)
    
    # 目标位置 [12-13] - 不添加噪声
    # noisy_obs[:, 12:14] = add_awgn_to_signal(noisy_obs[:, 12:14], snr_linear, opt.noise_scale_pos)
    
    # 障碍物位置噪声
    for i in range(14, 18):
        mask = noisy_obs[:, i] != 0.0  # 只对非零值（已观测的障碍物）添加噪声
        if np.any(mask):
            noisy_obs[mask, i] = add_awgn_to_signal(noisy_obs[mask, i], snr_linear, opt.noise_scale_pos)
    
    # 如果输入是单个观测，返回单个观测
    if not is_batch:
        noisy_obs = noisy_obs.reshape(-1)
    
    return noisy_obs


def main():
    '''Hyperparameter Setting'''
    parser = argparse.ArgumentParser()
    parser.add_argument('--dvc', type=str, default='cuda', help='running device: cuda or cpu')
    parser.add_argument('--EnvIdex', type=int, default=0, help='PV1, Lch_Cv2, Humanv4, HCv4, BWv3, BWHv3')
    parser.add_argument('--write', type=str2bool, default=True, help='Use SummaryWriter to record the training')
    parser.add_argument('--render', type=str2bool, default=False, help='Render or Not')
    parser.add_argument('--Loadmodel', type=str2bool, default=False, help='Load pretrained model or Not')
    parser.add_argument('--ModelIdex', type=int, default=0, help='which model to load')

    parser.add_argument('--seed', type=int, default=0, help='random seed')
    parser.add_argument('--Max_train_steps', type=int, default=int(9e6), help='Max training steps')
    parser.add_argument('--save_interval', type=int, default=int(6e5), help='Model saving interval, in steps.')
    parser.add_argument('--eval_interval', type=int, default=int(6e4), help='Model evaluating interval, in steps.')
    parser.add_argument('--update_every', type=int, default=8, help='Training Frequency, in steps')

    parser.add_argument('--gamma', type=float, default=0.98, help='Discounted Factor')
    parser.add_argument('--net_width', type=int, default=256, help='Hidden net width, s_dim-400-300-a_dim')
    parser.add_argument('--a_lr', type=float, default=5e-5, help='Learning rate of actor')
    parser.add_argument('--c_lr', type=float, default=5e-5, help='Learning rate of critic')
    parser.add_argument('--batch_size', type=int, default=256, help='batch_size of training')
    parser.add_argument('--alpha', type=float, default=0.2, help='Entropy coefficient')
    parser.add_argument('--adaptive_alpha', type=str2bool, default=True, help='Use adaptive_alpha or Not')
    parser.add_argument('--num_envs', type=int, default=15, help='Number of parallel environments')
    
    # AWGN噪声参数
    parser.add_argument('--add_sensor_noise', type=str2bool, default=True, help='Add sensor noise to observations')
    parser.add_argument('--use_awgn', type=str2bool, default=True, help='Use AWGN noise model')
    parser.add_argument('--random_snr', type=str2bool, default=True, help='Randomly select SNR for each episode')
    parser.add_argument('--snr_db', type=float, default=30.0, help='Fixed Signal-to-Noise Ratio in dB (if random_snr=False)')
    parser.add_argument('--snr_min', type=float, default=25.0, help='Minimum SNR in dB for random selection')
    parser.add_argument('--snr_max', type=float, default=40.0, help='Maximum SNR in dB for random selection')
    parser.add_argument('--snr_step', type=float, default=5.0, help='Step size for SNR values (e.g., 5 for 25,30,35,40)')
    parser.add_argument('--noise_scale_pos', type=float, default=1.0, help='Noise scale factor for position')
    parser.add_argument('--noise_scale_angle', type=float, default=1.0, help='Noise scale factor for angles')
    parser.add_argument('--noise_scale_vel', type=float, default=1.0, help='Noise scale factor for velocities')
    parser.add_argument('--noise_scale_dist', type=float, default=1.0, help='Noise scale factor for distances')
    
    opt = parser.parse_args()
    opt.dvc = torch.device(opt.dvc) # from str to torch.device
    print(opt)
    EnvName = ['sailboat-s14-obst-v2']
    BrifEnvName = ['saclstm_s14obst_awgn_1227']

    # Build Env
    env_fns = [make_env(EnvName[opt.EnvIdex], opt.seed + i) for i in range(opt.num_envs)]
    env = SubprocVecEnv(env_fns)
    eval_env = gym.make(EnvName[opt.EnvIdex])
    opt.state_dim = env.observation_space.shape[0]
    opt.action_dim = env.action_space.shape[0]
    opt.max_action = env.action_space.high.astype(float)

    opt.max_e_steps = 1000
    seq_len = 5  # 序列长度
    
    # 打印噪声配置
    print(f'Env:{EnvName[opt.EnvIdex]}  state_dim:{opt.state_dim}  action_dim:{opt.action_dim}  '
          f'max_a_s:{opt.max_action[0]}  max_a_r:{opt.max_action[1]} min_a_s:{env.action_space.low[0],env.action_space.low[1]}  max_e_steps:{opt.max_e_steps}')
    
    if opt.add_sensor_noise and opt.use_awgn:
        if opt.random_snr:
            print(f'AWGN Noise: Random SNR mode, Range: {opt.snr_min}-{opt.snr_max} dB, Step: {opt.snr_step} dB')
        else:
            print(f'AWGN Noise: Fixed SNR = {opt.snr_db} dB')
        print(f'Noise scales - Pos:{opt.noise_scale_pos}, Angle:{opt.noise_scale_angle}, Vel:{opt.noise_scale_vel}, Dist:{opt.noise_scale_dist}')
    elif opt.add_sensor_noise:
        print('Using fixed standard deviation noise (legacy mode)')
    else:
        print('Sensor noise disabled')

    # Seed Everything
    env_seed = opt.seed
    torch.manual_seed(opt.seed)
    torch.cuda.manual_seed(opt.seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    print("Random Seed: {}".format(opt.seed))

    # Build SummaryWriter to record training curves
    if opt.write:
        from torch.utils.tensorboard import SummaryWriter
        timenow = str(datetime.now())[0:-10]
        timenow = ' ' + timenow[0:13] + '_' + timenow[-2::]
        writepath = 'runs/{}'.format(BrifEnvName[opt.EnvIdex]) + timenow
        if os.path.exists(writepath): shutil.rmtree(writepath)
        writer = SummaryWriter(log_dir=writepath)

    # Build DRL model
    if not os.path.exists('model'): os.mkdir('model')
    agent = SAC_lstm_countinuous(**vars(opt)) # 传入所有参数

    if opt.Loadmodel: agent.load(BrifEnvName[opt.EnvIdex], opt.ModelIdex)

    # ==================== 修改1: 初始化部分 ====================
    # 初始化状态序列缓存 - 为每个环境维护独立的状态和动作序列
    s_raw = env.reset()  # s_raw: (num_envs, state_dim)
    
    # 为每个episode随机选择SNR（如果启用了随机SNR）
    episode_snr_list = []
    if opt.add_sensor_noise and opt.use_awgn:
        for i in range(opt.num_envs):
            episode_snr_list.append(get_random_snr(opt))
        print(f"Initial SNR values for each environment: {episode_snr_list}")
    
    # 关键修改：为初始状态添加传感器噪声，得到智能体实际观测到的状态
    if opt.add_sensor_noise and opt.use_awgn:
        current_states = np.array([
            add_awgn_noise(s_raw[i], episode_snr_list[i], opt) 
            for i in range(opt.num_envs)
        ])
        print("Initial states with AWGN noise applied")
    else:
        current_states = s_raw.copy()
        print("Initial states without noise")
    
    # 为每个环境初始化状态和动作序列缓存（用于训练时的序列输入）
    state_buffers = [deque(maxlen=seq_len) for _ in range(opt.num_envs)]
    action_buffers = [deque(maxlen=seq_len) for _ in range(opt.num_envs)]
    
    # 为每个环境维护前一步的状态和动作（用于采样时的单步输入）
    prev_states = [None for _ in range(opt.num_envs)]
    prev_actions = [np.zeros(opt.action_dim) for _ in range(opt.num_envs)]
    
    # 用初始观测填充缓存（已带噪声）
    for i in range(opt.num_envs):
        for _ in range(seq_len):
            state_buffers[i].append(current_states[i].copy())  # 存储带噪声的观测
            action_buffers[i].append(np.zeros(opt.action_dim))
        prev_states[i] = current_states[i].copy()  # 初始化前一状态（带噪声）

    if opt.render:
        # 评估时也需要创建状态序列
        eval_state_buffer = deque(maxlen=seq_len)
        while True:
            score = evaluate_policy(eval_env, agent, opt.max_action, turns=3)
            print('EnvName:', BrifEnvName[opt.EnvIdex], 'score:', score)
    else:
        total_steps = 0
        start_time = time.time()
        
        # 添加loss和alpha数据记录的变量
        training_log_interval = 20  # 每20步记录一次训练loss
        
        # 记录SNR统计
        snr_usage_count = {}
        
        with tqdm(total=opt.Max_train_steps, desc='Training') as pbar:
            while total_steps < opt.Max_train_steps:
                done_flags = [False] * opt.num_envs

                '''Interact & train'''
                while not all(done_flags):
                    actions = []
                    
                    # ==================== 修改2: 动作选择部分 ====================
                    # 为每个环境选择动作
                    for i in range(opt.num_envs):
                        # 关键修改：current_states已经是带噪声的观测，直接使用
                        # 不需要再次添加噪声
                        
                        # 在训练初期可选随机动作，否则使用 agent.select_action
                        if total_steps < (20 * opt.max_e_steps):
                            # 针对帆船控制的特殊随机策略
                            random_strategy = np.random.random()
                            
                            if random_strategy < 0.3:  # 30%概率：保持稳定状态（0动作）
                                a = np.zeros(opt.action_dim)
                            elif random_strategy < 0.5:  # 20%概率：小幅调整（模拟微调）
                                a = np.random.uniform(-0.2, 0.2, opt.action_dim)
                            elif random_strategy < 0.65:  # 15%概率：单维度调整
                                a = np.zeros(opt.action_dim)
                                if opt.action_dim >= 2:
                                    if np.random.random() < 0.5:
                                        a[0] = np.random.uniform(-0.5, 0.5)  # 调整帆
                                    else:
                                        a[1] = np.random.uniform(-0.5, 0.5)  # 调整舵
                                else:
                                    random_dim = np.random.randint(0, opt.action_dim)
                                    a[random_dim] = np.random.uniform(-0.5, 0.5)
                            else:  # 35%概率：正常随机动作
                                act = env.action_space.sample()
                                a = Action_adapter_reverse(act, opt.max_action)
                        else:
                            # 使用单步模式，直接使用带噪声的观测（prev_states和current_states已带噪声）
                            a = agent.select_action(prev_states[i], prev_actions[i], current_states[i], 
                                                  deterministic=False, total_steps=total_steps, env_id=i)
                        actions.append(a)
                    
                    # 将连续动作转换至环境所需范围
                    act_list = [Action_adapter(a, opt.max_action) for a in actions]
                    s_next_raw, r, done_flags, info = env.step(act_list)  # s_next_raw: (num_envs, state_dim)
                    
                    # ==================== 修改3: 状态转换和存储部分 ====================
                    # 关键修改：立即为s_next_raw添加传感器噪声，得到智能体观测到的下一状态
                    if opt.add_sensor_noise and opt.use_awgn:
                        s_next_observed = np.array([
                            add_awgn_noise(s_next_raw[i], episode_snr_list[i], opt) 
                            for i in range(opt.num_envs)
                        ])
                    else:
                        s_next_observed = s_next_raw.copy()
                    
                    # 对每个环境存入ReplayBuffer并更新缓存
                    for i in range(opt.num_envs):
                        # 获取当前环境的序列数据（已带噪声）
                        curr_state_seq = np.array(list(state_buffers[i]))  # (seq_len, state_dim)
                        curr_action_seq = np.array(list(action_buffers[i]))  # (seq_len, action_dim)
                        
                        # 更新动作缓存（添加当前选择的动作）
                        action_buffers[i].append(actions[i].copy())
                        # 关键修改：更新状态缓存，添加观测到的下一状态（带噪声）
                        state_buffers[i].append(s_next_observed[i].copy())
                        
                        # 构建下一个状态的序列（包含带噪声的观测）
                        next_state_seq = np.array(list(state_buffers[i]))  # (seq_len, state_dim)
                        next_action_seq = np.array(list(action_buffers[i]))

                        # 关键修改：存储到经验池，使用观测值（带噪声）
                        agent.replay_buffer.add(
                            curr_state_seq,        # 历史观测序列（带噪声）
                            curr_action_seq,       # 历史动作
                            current_states[i],     # 当前观测（带噪声）
                            actions[i],            # 当前动作
                            r[i],                  # 奖励
                            next_state_seq,        # 下一观测序列（带噪声）
                            next_action_seq,       # 下一动作序列
                            s_next_observed[i],    # 下一观测（带噪声）
                            done_flags[i]
                        )
                        
                        # 更新前一步状态和动作（用于下次采样）
                        prev_states[i] = current_states[i].copy()
                        prev_actions[i] = actions[i].copy()
                        
                        # ==================== 修改4: Episode重置部分 ====================
                        # 如果episode结束，重置该环境的相关状态
                        if done_flags[i]:
                            agent.actor.reset_hidden_state(env_id=i)
                            agent.q_critic.reset_hidden_state(env_id=i)
                            agent.q_critic_target.reset_hidden_state(env_id=i)
                            
                            # 为新的episode随机选择SNR
                            if opt.add_sensor_noise and opt.use_awgn:
                                old_snr = episode_snr_list[i]
                                episode_snr_list[i] = get_random_snr(opt)
                                
                                # 统计SNR使用次数
                                snr_usage_count[old_snr] = snr_usage_count.get(old_snr, 0) + 1
                                
                                # 关键修改：为新episode的初始状态添加噪声
                                s_init_observed = add_awgn_noise(s_next_raw[i], episode_snr_list[i], opt)
                            else:
                                s_init_observed = s_next_raw[i].copy()
                            
                            # 重置状态和动作缓存
                            state_buffers[i].clear()
                            action_buffers[i].clear()
                            # 用新的初始观测（带噪声）填充缓存
                            for _ in range(seq_len):
                                state_buffers[i].append(s_init_observed.copy())
                                action_buffers[i].append(np.zeros(opt.action_dim))
                        
                            # 重置前一步状态和动作
                            prev_states[i] = s_init_observed.copy()
                            prev_actions[i] = np.zeros(opt.action_dim)

                    # ==================== 修改5: 状态更新部分 ====================
                    # 关键修改：更新当前状态为观测到的下一状态（带噪声）
                    current_states = s_next_observed

                    total_steps += opt.num_envs
                    pbar.update(opt.num_envs)

                    '''train after collecting samples from all environments'''
                    if (total_steps >= 20 * opt.max_e_steps) and (agent.replay_buffer.size >= opt.batch_size):
                        # 每20步进行一次训练序列：8次critic更新
                        if total_steps % 20 == 0:
                            # 计算训练进度，用于更新beta值
                            progress = min(total_steps / 2000000, 1.0)
                            # 更新 beta 值
                            agent.replay_buffer.update_beta(progress)
                            
                            # 执行多次更新
                            for update_idx in range(opt.update_every):
                                train_info = agent.train()
                                
                                # 只在最后一次更新时记录日志
                                if opt.write and update_idx == (opt.update_every - 1):
                                    writer.add_scalar('Train/Q_Loss', train_info['q_loss'], global_step=total_steps)
                                    
                                    # 预热阶段特殊处理
                                    if train_info.get('warmup', False):
                                        writer.add_scalar('Train/Warmup_Progress', train_info['warmup_progress'], global_step=total_steps)
                                        writer.add_scalar('Train/Actor_Loss', 0.0, global_step=total_steps)
                                        writer.add_scalar('Train/Alpha_Loss', 0.0, global_step=total_steps)
                                    else:
                                        # 预热后：记录实际的loss值
                                        writer.add_scalar('Train/Actor_Loss', train_info['a_loss'], global_step=total_steps)
                                        writer.add_scalar('Train/Alpha_Loss', train_info['alpha_loss'], global_step=total_steps)
                                        
                                        # 记录策略更新状态
                                        writer.add_scalar('Train/Policy_Updated', float(train_info.get('policy_updated', False)), global_step=total_steps)
                                        writer.add_scalar('Train/Critic_Update_Count', train_info.get('critic_update_count', 0), global_step=total_steps)
                                    
                                    # 记录当前alpha值
                                    writer.add_scalar('Train/Alpha_Value', train_info['alpha'], global_step=total_steps)
                                    
                                    # 记录replay buffer beta值
                                    writer.add_scalar('Train/Buffer_Beta', agent.replay_buffer.beta, global_step=total_steps)
                                    
                                    # 记录buffer大小
                                    writer.add_scalar('Train/Buffer_Size', agent.replay_buffer.size, global_step=total_steps)
                                    
                                    # 记录当前使用的平均SNR
                                    if opt.add_sensor_noise and opt.use_awgn:
                                        avg_snr = np.mean(episode_snr_list)
                                        writer.add_scalar('Train/Average_SNR', avg_snr, global_step=total_steps)
                            
                            # 强制清理GPU缓存
                            if torch.cuda.is_available():
                                torch.cuda.empty_cache()

                    '''record & log'''
                    if (total_steps >= 20 * opt.max_e_steps) and (total_steps % opt.eval_interval) == 0:
                        ep_r = evaluate_policy(eval_env, agent, opt.max_action, turns=4)
                        if opt.write: writer.add_scalar('Eval/Episode_Reward', ep_r, global_step=total_steps)
                        
                        elapsed_time = time.time() - start_time
                        
                        # 添加详细的训练状态打印
                        current_alpha = agent.alpha.item() if hasattr(agent.alpha, 'item') else agent.alpha
                        recent_q_loss = agent.q_loss_history[-1] if len(agent.q_loss_history) > 0 else 0.0
                        recent_a_loss = agent.a_loss_history[-1] if len(agent.a_loss_history) > 0 else 0.0
                        recent_alpha_loss = agent.alpha_loss_history[-1] if len(agent.alpha_loss_history) > 0 else 0.0
                        
                        # 检查是否处于预热阶段
                        warmup_status = ""
                        if hasattr(agent, 'training_step') and agent.training_step <= agent.critic_warmup_steps:
                            warmup_progress = agent.training_step / agent.critic_warmup_steps * 100
                            warmup_status = f", Warmup: {warmup_progress:.1f}%"
                        
                        # SNR统计信息
                        snr_info = ""
                        if opt.add_sensor_noise and opt.use_awgn:
                            avg_snr = np.mean(episode_snr_list)
                            snr_info = f", Avg_SNR: {avg_snr:.1f}dB"
                        
                        print(f'EnvName:{BrifEnvName[opt.EnvIdex]}, Steps: {int(total_steps/1000)}k, '
                              f'Episode Reward:{ep_r}, Alpha:{current_alpha:.4f}, '
                              f'Q_Loss:{recent_q_loss:.4f}, A_Loss:{recent_a_loss:.4f}, '
                              f'Alpha_Loss:{recent_alpha_loss:.4f}, Elapsed Time:{elapsed_time:.2f}s{warmup_status}{snr_info}')
                        
                        # 每隔一定间隔打印SNR使用统计
                        if opt.add_sensor_noise and opt.use_awgn and len(snr_usage_count) > 0:
                            print(f"SNR usage statistics: {dict(sorted(snr_usage_count.items()))}")

                    '''save model'''
                    if total_steps % opt.save_interval == 0:
                        agent.save(BrifEnvName[opt.EnvIdex], int(total_steps/1000))
                        
                        # 保存训练统计信息
                        if opt.write:
                            training_stats = {
                                'q_loss_history': agent.q_loss_history[-1000:],
                                'a_loss_history': agent.a_loss_history[-1000:],
                                'alpha_loss_history': agent.alpha_loss_history[-1000:],
                                'total_steps': total_steps,
                                'current_alpha': agent.alpha.item() if hasattr(agent.alpha, 'item') else agent.alpha,
                                'snr_usage_count': snr_usage_count.copy() if opt.add_sensor_noise and opt.use_awgn else {}
                            }
                            torch.save(training_stats, f"./model/{BrifEnvName[opt.EnvIdex]}_training_stats_{int(total_steps/1000)}.pth")
                        
                if total_steps >= opt.Max_train_steps:
                    break
        
        # 训练完成后保存最终的训练统计信息
        if opt.write:
            final_stats = {
                'q_loss_history': agent.q_loss_history,
                'a_loss_history': agent.a_loss_history,  
                'alpha_loss_history': agent.alpha_loss_history,
                'total_steps': total_steps,
                'final_alpha': agent.alpha.item() if hasattr(agent.alpha, 'item') else agent.alpha,
                'final_snr_usage_count': snr_usage_count if opt.add_sensor_noise and opt.use_awgn else {}
            }
            torch.save(final_stats, f"./model/{BrifEnvName[opt.EnvIdex]}_final_training_stats.pth")
            writer.close()
            
            # 打印最终的SNR使用统计
            if opt.add_sensor_noise and opt.use_awgn and len(snr_usage_count) > 0:
                print("\n=== Final SNR Usage Statistics ===")
                total_episodes = sum(snr_usage_count.values())
                for snr, count in sorted(snr_usage_count.items()):
                    percentage = (count / total_episodes) * 100
                    print(f"SNR {snr:.1f} dB: {count} episodes ({percentage:.1f}%)")
                print(f"Total episodes: {total_episodes}")
            
        env.close()
        eval_env.close()

if __name__ == '__main__':    
    try:
        multiprocessing.set_start_method('spawn', force=True)
    except RuntimeError:
        pass

    main()
