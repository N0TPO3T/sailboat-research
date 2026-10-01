import os
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ["KMP_DUPLICATE_LIB_OK"]="TRUE"

from utils_lstm_normal import str2bool, evaluate_policy, Action_adapter, Action_adapter_reverse
from datetime import datetime
from PPO_lstm_normal import PPO_lstm_continuous
import gymnasium as gym
import numpy as np
import torch
import argparse
import time
import shutil
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


def main():
    '''Hyperparameter Setting'''
    parser = argparse.ArgumentParser()
    parser.add_argument('--dvc', type=str, default='cuda', help='running device: cuda or cpu')
    parser.add_argument('--EnvIdex', type=int, default=0, help='Environment index')
    parser.add_argument('--write', type=str2bool, default=True, help='Use SummaryWriter to record the training')
    parser.add_argument('--render', type=str2bool, default=False, help='Render or Not')
    parser.add_argument('--Loadmodel', type=str2bool, default=False, help='Load pretrained model or Not')
    parser.add_argument('--ModelIdex', type=int, default=0, help='which model to load')

    parser.add_argument('--seed', type=int, default=0, help='random seed')
    parser.add_argument('--Max_train_steps', type=int, default=int(15e6), help='Max training steps')
    parser.add_argument('--save_interval', type=int, default=int(9e5), help='Model saving interval, in steps.')
    parser.add_argument('--eval_interval', type=int, default=int(6e4), help='Model evaluating interval, in steps.')
    parser.add_argument('--update_every', type=int, default=4096, help='Update frequency (steps to collect before update)')

    parser.add_argument('--gamma', type=float, default=0.98, help='Discounted Factor')
    parser.add_argument('--net_width', type=int, default=256, help='Hidden net width')
    parser.add_argument('--a_lr', type=float, default=5e-5, help='Learning rate of actor')
    parser.add_argument('--c_lr', type=float, default=5e-5, help='Learning rate of critic')
    parser.add_argument('--batch_size', type=int, default=256, help='batch_size of training')
    parser.add_argument('--num_envs', type=int, default=16, help='Number of parallel environments')
    
    opt = parser.parse_args()
    opt.dvc = torch.device(opt.dvc)
    print(opt)
    
    EnvName = ['sailboat-s14-v1']
    BrifEnvName = ['ppolstm_s14_0129']

    # Build Env
    env_fns = [make_env(EnvName[opt.EnvIdex], opt.seed + i) for i in range(opt.num_envs)]
    env = SubprocVecEnv(env_fns)
    eval_env = gym.make(EnvName[opt.EnvIdex])
    opt.state_dim = env.observation_space.shape[0]
    opt.action_dim = env.action_space.shape[0]
    opt.max_action = env.action_space.high.astype(float)
    opt.max_e_steps = 1000
    seq_len = 5

    print(f'Env:{EnvName[opt.EnvIdex]}  state_dim:{opt.state_dim}  action_dim:{opt.action_dim}  '
          f'max_a:{opt.max_action}  max_e_steps:{opt.max_e_steps}')

    # Seed Everything
    torch.manual_seed(opt.seed)
    torch.cuda.manual_seed(opt.seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    print("Random Seed: {}".format(opt.seed))

    # Build SummaryWriter
    if opt.write:
        from torch.utils.tensorboard import SummaryWriter
        timenow = str(datetime.now())[0:-10]
        timenow = ' ' + timenow[0:13] + '_' + timenow[-2::]
        writepath = 'runs/{}'.format(BrifEnvName[opt.EnvIdex]) + timenow
        if os.path.exists(writepath): shutil.rmtree(writepath)
        writer = SummaryWriter(log_dir=writepath)

    # Build DRL model
    if not os.path.exists('model'): os.mkdir('model')
    agent = PPO_lstm_continuous(**vars(opt))

    if opt.Loadmodel: 
        agent.load(BrifEnvName[opt.EnvIdex], opt.ModelIdex)

    # 初始化状态序列缓存
    s_raw = env.reset()
    state_buffers = [deque(maxlen=seq_len) for _ in range(opt.num_envs)]
    action_buffers = [deque(maxlen=seq_len) for _ in range(opt.num_envs)]
    prev_states = [None for _ in range(opt.num_envs)]
    prev_actions = [np.zeros(opt.action_dim) for _ in range(opt.num_envs)]
    
    for i in range(opt.num_envs):
        for _ in range(seq_len):
            state_buffers[i].append(s_raw[i].copy())
            action_buffers[i].append(np.zeros(opt.action_dim))
        prev_states[i] = s_raw[i].copy()
    
    current_states = s_raw

    if opt.render:
        while True:
            score = evaluate_policy(eval_env, agent, opt.max_action, turns=3)
            print('EnvName:', BrifEnvName[opt.EnvIdex], 'score:', score)
    else:
        total_steps = 0
        last_eval_step = 0  # 记录上次评估的步数
        last_save_step = 0  # 记录上次保存的步数
        start_time = time.time()
        
        with tqdm(total=opt.Max_train_steps, desc='Training') as pbar:
            while total_steps < opt.Max_train_steps:
                done_flags = [False] * opt.num_envs
                
                '''Collect experience'''
                steps_in_episode = 0
                while not all(done_flags) and steps_in_episode < opt.update_every:
                    actions = []
                    log_probs_list = []
                    values_list = []
                    
                    # 为每个环境选择动作
                    for i in range(opt.num_envs):
                        if not done_flags[i]:
                            # 使用PPO策略选择动作
                            a, log_prob, value = agent.select_action(
                                prev_states[i], prev_actions[i], current_states[i], 
                                deterministic=False, total_steps=total_steps, env_id=i
                            )
                            actions.append(a)
                            log_probs_list.append(log_prob)
                            values_list.append(value)
                        else:
                            actions.append(np.zeros(opt.action_dim))
                            log_probs_list.append(0.0)
                            values_list.append(0.0)
                    
                    # 执行动作
                    act_list = [Action_adapter(a, opt.max_action) for a in actions]
                    s_next_raw, r, done_flags, info = env.step(act_list)
                    
                    # 存储经验
                    for i in range(opt.num_envs):
                        curr_state_seq = np.array(list(state_buffers[i]))
                        curr_action_seq = np.array(list(action_buffers[i]))
                        
                        action_buffers[i].append(actions[i].copy())
                        state_buffers[i].append(s_next_raw[i].copy())
                        
                        next_state_seq = np.array(list(state_buffers[i]))
                        
                        # 添加到经验池
                        agent.replay_buffer.add(
                            curr_state_seq, curr_action_seq, current_states[i], 
                            actions[i], r[i], next_state_seq, s_next_raw[i], 
                            done_flags[i], log_probs_list[i], values_list[i]
                        )
                        
                        prev_states[i] = current_states[i].copy()
                        prev_actions[i] = actions[i].copy()
                        
                        if done_flags[i]:
                            # 重置环境的隐藏状态
                            agent.actor.reset_hidden_state(env_id=i)
                            agent.value_net.reset_hidden_state(env_id=i)
                            
                            state_buffers[i].clear()
                            action_buffers[i].clear()
                            for _ in range(seq_len):
                                state_buffers[i].append(s_next_raw[i].copy())
                                action_buffers[i].append(np.zeros(opt.action_dim))
                            
                            prev_states[i] = s_next_raw[i].copy()
                            prev_actions[i] = np.zeros(opt.action_dim)
                    
                    current_states = s_next_raw
                    total_steps += opt.num_envs
                    steps_in_episode += opt.num_envs
                    pbar.update(opt.num_envs)
                
                '''Train PPO'''
                if agent.replay_buffer.size >= opt.batch_size:
                    train_info = agent.train()
                    
                    if opt.write and train_info is not None:
                        writer.add_scalar('Loss/Policy_Loss', train_info['policy_loss'], global_step=total_steps)
                        writer.add_scalar('Loss/Value_Loss', train_info['value_loss'], global_step=total_steps)
                        writer.add_scalar('Loss/Entropy', train_info['entropy'], global_step=total_steps)
                    
                    # 清理GPU缓存
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                
                '''Evaluate & Log'''
                # 修改：使用整除判断是否跨越了评估边界
                if total_steps // opt.eval_interval > last_eval_step // opt.eval_interval:
                    ep_r = evaluate_policy(eval_env, agent, opt.max_action, turns=4)
                    if opt.write: 
                        writer.add_scalar('Eval/Episode_Reward', ep_r, global_step=total_steps)
                    
                    elapsed_time = time.time() - start_time
                    recent_policy_loss = agent.policy_loss_history[-1] if len(agent.policy_loss_history) > 0 else 0.0
                    recent_value_loss = agent.value_loss_history[-1] if len(agent.value_loss_history) > 0 else 0.0
                    recent_entropy = agent.entropy_history[-1] if len(agent.entropy_history) > 0 else 0.0
                    
                    print(f'EnvName:{BrifEnvName[opt.EnvIdex]}, Steps: {int(total_steps/1000)}k, '
                          f'Episode Reward:{ep_r}, Policy_Loss:{recent_policy_loss:.4f}, '
                          f'Value_Loss:{recent_value_loss:.4f}, Entropy:{recent_entropy:.4f}, '
                          f'Elapsed Time:{elapsed_time:.2f}s')
                    
                    last_eval_step = total_steps
                
                '''Save model'''
                # 修改：使用整除判断是否跨越了保存边界
                if total_steps // opt.save_interval > last_save_step // opt.save_interval:
                    agent.save(BrifEnvName[opt.EnvIdex], int(total_steps/1000))
                    last_save_step = total_steps
        
        if opt.write:
            writer.close()
        
        env.close()
        eval_env.close()


if __name__ == '__main__':    
    main()
