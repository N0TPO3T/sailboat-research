"""
训练SAC模型脚本
"""

import os, shutil
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # 只显示错误信息
os.environ["KMP_DUPLICATE_LIB_OK"]="TRUE"

from utils_fc import str2bool, evaluate_policy, Action_adapter, Action_adapter_reverse, Reward_adapter
from noise_utils_nowind import NoiseManager  # 新增噪声模块导入
from datetime import datetime
from SAC_fc import SAC_fc_continuous
import gymnasium as gym
import argparse
import torch
import globals
import time
import numpy as np
from tqdm import tqdm
from stable_baselines3.common.vec_env import SubprocVecEnv
import multiprocessing

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

def make_env(env_id, seed):
    def _init():
        env = gym.make(env_id)
        env.reset(seed=seed)
        return env
    return _init

def _reset_result_obs(reset_result):
    return reset_result[0] if isinstance(reset_result, tuple) else reset_result

def reset_bad_envs(vec_env, bad_indices, noise_manager):
    reset_results = vec_env.env_method("reset", indices=bad_indices.tolist())
    reset_obs = []
    for result in reset_results:
        obs = _reset_result_obs(result)
        reset_obs.append(noise_manager.add_observation_noise(obs))
    return reset_obs

def main():
    '''Hyperparameter Setting'''
    parser = argparse.ArgumentParser()
    parser.add_argument('--dvc', type=str, default='cuda', help='running device: cuda or cpu')
    parser.add_argument('--EnvIdex', type=int, default=0, help='PV1, Lch_Cv2, Humanv4, HCv4, BWv3, BWHv3')
    parser.add_argument('--write', type=str2bool, default=True, help='Use SummaryWriter to record the training')
    parser.add_argument('--render', type=str2bool, default=False, help='Render or Not')
    parser.add_argument('--Loadmodel', type=str2bool, default=False, help='Load pretrained model or Not')
    parser.add_argument('--ModelIdex', type=int, default=9000, help='which model to load')

    parser.add_argument('--seed', type=int, default=0, help='random seed')
    parser.add_argument('--Max_train_steps', type=int, default=int(9e6), help='Max training steps')
    parser.add_argument('--save_interval', type=int, default=int(6e5), help='Model saving interval, in steps.')
    parser.add_argument('--eval_interval', type=int, default=int(6e4), help='Model evaluating interval, in steps.')
    parser.add_argument('--update_every', type=int, default=8, help='Training Frequency, in steps')

    parser.add_argument('--gamma', type=float, default=0.98, help='Discounted Factor')
    parser.add_argument('--net_width', type=int, default=1024, help='Hidden net width, s_dim-400-300-a_dim')
    parser.add_argument('--a_lr', type=float, default=5e-5, help='Learning rate of actor')
    parser.add_argument('--c_lr', type=float, default=5e-5, help='Learning rate of critic')
    parser.add_argument('--batch_size', type=int, default=256, help='batch_size of training')
    parser.add_argument('--alpha', type=float, default=0.2, help='Entropy coefficient')
    parser.add_argument('--adaptive_alpha', type=str2bool, default=True, help='Use adaptive_alpha or Not')
    parser.add_argument('--num_envs', type=int, default=15, help='Number of parallel environments')
    
    # ========== 新增噪声相关参数 ==========
    parser.add_argument('--enable_sensor_noise', type=str2bool, default=True, help='Enable sensor noise')
    parser.add_argument('--enable_actuator_noise', type=str2bool, default=True, help='Enable actuator noise')
    parser.add_argument('--sensor_noise_ratio', type=float, default=0.03, help='Sensor noise ratio (default 3%)')
    parser.add_argument('--actuator_noise_ratio', type=float, default=0.03, help='Actuator noise ratio (default 3%)')
    # =====================================
    
    opt = parser.parse_args()
    opt.dvc = torch.device(opt.dvc) # from str to torch.device
    print(opt)
    
    EnvName = ['sailboat-s14-nowind']
    BrifEnvName = [f'sac_s14nowind_buf1e6_seed{opt.seed}']

    # Build Env
    env_fns = [make_env(EnvName[opt.EnvIdex], opt.seed + i) for i in range(opt.num_envs)]
    env = SubprocVecEnv(env_fns)
    eval_env = gym.make(EnvName[opt.EnvIdex])
    opt.state_dim = env.observation_space.shape[0]
    opt.action_dim = env.action_space.shape[0]
    opt.max_action = env.action_space.high.astype(float)

    opt.max_e_steps = 1000
    print(f'Env:{EnvName[opt.EnvIdex]}  state_dim:{opt.state_dim}  action_dim:{opt.action_dim}  '
          f'max_a_s:{opt.max_action[0]}  max_a_r:{opt.max_action[1]} min_a_s:{env.action_space.low[0],env.action_space.low[1]}  max_e_steps:{opt.max_e_steps}')

    # ========== 初始化噪声管理器 ==========
    noise_manager = NoiseManager(
        sensor_noise_ratio=opt.sensor_noise_ratio,
        actuator_noise_ratio=opt.actuator_noise_ratio,
        enable_sensor_noise=opt.enable_sensor_noise,
        enable_actuator_noise=opt.enable_actuator_noise,
        seed=opt.seed
    )
    print(f'Noise Config: sensor_noise={opt.enable_sensor_noise}({opt.sensor_noise_ratio*100}%), '
          f'actuator_noise={opt.enable_actuator_noise}({opt.actuator_noise_ratio*100}%)')
    # =====================================

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
    agent = SAC_fc_continuous(**vars(opt)) # 传入所有参数

    if opt.Loadmodel: agent.load(BrifEnvName[opt.EnvIdex], opt.ModelIdex)

    # 初始化环境状态
    s_raw = env.reset()  # s_raw: (num_envs, state_dim)
    
    # ========== 对初始状态添加传感器噪声 ==========
    s_noisy = np.array([noise_manager.add_observation_noise(s) for s in s_raw])
    s_noisy = np.nan_to_num(s_noisy, nan=0.0, posinf=1e3, neginf=-1e3)
    # =============================================
    
    current_states = s_noisy  # 当前状态 (带噪声)

    if opt.render:
        while True:
            # 带噪声评估 - 获得最真实的反馈
            score = evaluate_policy(eval_env, agent, opt.max_action, turns=3,
                                   noise_manager=noise_manager, eval_with_noise=True)
            print('EnvName:', BrifEnvName[opt.EnvIdex], 'score:', score)
    else:
        total_steps = 0
        start_time = time.time()
        
        # 添加loss和alpha数据记录的变量
        training_log_interval = 20  # 每20步记录一次训练loss
        
        with tqdm(total=opt.Max_train_steps, desc='Training') as pbar:
            while total_steps < opt.Max_train_steps:
                '''Interact & train'''
                while total_steps < opt.Max_train_steps:
                    actions = []
                    
                    # 为每个环境选择动作
                    for i in range(opt.num_envs):
                        # 在训练初期可选随机动作，否则使用 agent.select_action
                        if total_steps < (20 * opt.max_e_steps):
                            # 针对帆船控制的特殊随机策略
                            random_strategy = np.random.random()
                            
                            if random_strategy < 0.3:  # 30%概率：保持稳定状态（0动作）
                                a = np.zeros(opt.action_dim)
                            elif random_strategy < 0.5:  # 20%概率：小幅调整（模拟微调）
                                # 小幅度调整，适合帆船的渐进式控制
                                a = np.random.uniform(-0.2, 0.2, opt.action_dim)
                            elif random_strategy < 0.65:  # 15%概率：单维度调整
                                # 只调整帆或只调整舵，避免同时大幅调整
                                a = np.zeros(opt.action_dim)
                                if opt.action_dim >= 2:
                                    # 假设第一个维度是帆，第二个是舵
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
                        elif not np.all(np.isfinite(current_states[i])):
                            a = np.zeros(opt.action_dim, dtype=np.float32)
                        else:
                            a = agent.select_action(current_states[i], deterministic=False)
                        actions.append(a)
                    
                    # ========== 添加执行器噪声并转换动作 ==========
                    act_list = []
                    for a in actions:
                        # 先添加执行器噪声，再转换到环境动作范围
                        a_noisy = noise_manager.add_action_noise(a, opt.max_action)
                        if not np.all(np.isfinite(a_noisy)):
                            a_noisy = np.zeros(opt.action_dim, dtype=np.float32)
                        act = Action_adapter(a_noisy, opt.max_action)
                        act_list.append(act)
                    # =============================================
                    
                    s_next_raw, r, done_flags, info = env.step(act_list)  # s_next_raw: (num_envs, state_dim)
                    
                    # ========== 对下一状态添加传感器噪声 ==========
                    s_next_noisy = np.array([noise_manager.add_observation_noise(s) for s in s_next_raw])
                    bad_mask = (
                        ~np.all(np.isfinite(current_states), axis=1) |
                        ~np.all(np.isfinite(s_next_raw), axis=1) |
                        ~np.all(np.isfinite(s_next_noisy), axis=1) |
                        ~np.isfinite(r)
                    )
                    if np.any(bad_mask):
                        bad_indices = np.flatnonzero(bad_mask)
                        reset_obs = reset_bad_envs(env, bad_indices, noise_manager)
                        for env_idx, obs in zip(bad_indices, reset_obs):
                            s_next_noisy[env_idx] = np.nan_to_num(obs, nan=0.0, posinf=1e3, neginf=-1e3)
                            done_flags[env_idx] = True
                            r[env_idx] = -100.0
                    # =============================================
                    
                    # 对每个环境存入ReplayBuffer
                    for i in range(opt.num_envs):
                        if bad_mask[i]:
                            continue
                        # 存储到经验池（使用带噪声的状态）
                        agent.replay_buffer.add(current_states[i], actions[i], r[i], 
                                              s_next_noisy[i], done_flags[i])

                    # 更新当前状态 (使用带噪声的状态)
                    current_states = np.nan_to_num(s_next_noisy, nan=0.0, posinf=1e3, neginf=-1e3)

                    total_steps += opt.num_envs
                    pbar.update(opt.num_envs)

                    '''train after collecting samples from all environments'''
                    if (total_steps >= 20 * opt.max_e_steps) and (agent.replay_buffer.size >= opt.batch_size):
                        # 每20步进行一次训练序列：4次critic更新 + 1次actor和alpha更新
                        if total_steps % 20 == 0:  # 每20步环境采样进行一次训练序列
                            # 计算训练进度，用于更新beta值
                            progress = min(total_steps / 2000000, 1.0)
                            # 更新 beta 值
                            agent.replay_buffer.update_beta(progress)
                            
                            # 执行4次critic更新
                            for update_idx in range(opt.update_every):
                                train_info = agent.train()
                                
                                # 只在最后一次更新时记录日志（避免过多的记录）
                                if opt.write and update_idx == 3:  # 只在第4次更新时记录
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
                            
                            # 强制清理GPU缓存
                            if torch.cuda.is_available():
                                torch.cuda.empty_cache()

                    '''record & log'''
                    if (total_steps >= 20 * opt.max_e_steps) and (total_steps % opt.eval_interval) == 0:
                        # 带噪声评估 - 获得最真实的反馈
                        ep_r = evaluate_policy(eval_env, agent, opt.max_action, turns=5,
                                              noise_manager=noise_manager, eval_with_noise=True)
                        if opt.write: 
                            writer.add_scalar('Eval/Episode_Reward', ep_r, global_step=total_steps)
                        
                        elapsed_time = time.time() - start_time
                        
                        # 添加详细的训练状态打印，包括预热信息
                        current_alpha = agent.alpha.item() if hasattr(agent.alpha, 'item') else agent.alpha
                        recent_q_loss = agent.q_loss_history[-1] if len(agent.q_loss_history) > 0 else 0.0
                        recent_a_loss = agent.a_loss_history[-1] if len(agent.a_loss_history) > 0 else 0.0
                        recent_alpha_loss = agent.alpha_loss_history[-1] if len(agent.alpha_loss_history) > 0 else 0.0
                        
                        # 检查是否处于预热阶段
                        warmup_status = ""
                        if hasattr(agent, 'training_step') and agent.training_step <= agent.critic_warmup_steps:
                            warmup_progress = agent.training_step / agent.critic_warmup_steps * 100
                            warmup_status = f", Warmup: {warmup_progress:.1f}%"
                        
                        print(f'EnvName:{BrifEnvName[opt.EnvIdex]}, Steps: {int(total_steps/1000)}k, '
                              f'Episode Reward:{ep_r}, Alpha:{current_alpha:.4f}, '
                              f'Q_Loss:{recent_q_loss:.4f}, A_Loss:{recent_a_loss:.4f}, '
                              f'Alpha_Loss:{recent_alpha_loss:.4f}, Elapsed Time:{elapsed_time:.2f}s{warmup_status}')

                    '''save model'''
                    if total_steps % opt.save_interval == 0:
                        agent.save(BrifEnvName[opt.EnvIdex], int(total_steps/1000))
                        
                        # 保存训练统计信息
                        if opt.write:
                            training_stats = {
                                'q_loss_history': agent.q_loss_history[-1000:],  # 保存最近1000个loss
                                'a_loss_history': agent.a_loss_history[-1000:],
                                'alpha_loss_history': agent.alpha_loss_history[-1000:],
                                'total_steps': total_steps,
                                'current_alpha': agent.alpha.item() if hasattr(agent.alpha, 'item') else agent.alpha
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
                'final_alpha': agent.alpha.item() if hasattr(agent.alpha, 'item') else agent.alpha
            }
            torch.save(final_stats, f"./model/{BrifEnvName[opt.EnvIdex]}_final_training_stats.pth")
            writer.close()
            
        env.close()
        eval_env.close()

if __name__ == '__main__':    
    try:
        multiprocessing.set_start_method('spawn', force=True)
    except RuntimeError:
        pass

    main()
