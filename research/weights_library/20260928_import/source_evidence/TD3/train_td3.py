# train_td3_lstm_att_normal.py
import os, shutil
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from utils_lstm_normal import str2bool, evaluate_policy, Action_adapter, Action_adapter_reverse
from datetime import datetime
from TD3_lstm_att_normal import TD3_lstm_continuous
import gymnasium as gym
import argparse
import torch
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


def evaluate_policy_td3(env, agent, max_action, turns=3):
    """TD3专用的评估函数"""
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
            # TD3使用确定性策略，不添加噪声
            a = agent.select_action(prev_state, prev_action, s, add_noise=False, env_id=eval_env_id)
            act = Action_adapter(a, max_action)
            
            s_next, r, dw, tr, info = env.step(act)
            done = (dw or tr)
            
            episode_score += r
            
            prev_state = s.copy()
            prev_action = a.copy()
            s = s_next
        
        total_scores += episode_score
    
    return int(total_scores / turns)


def main():
    '''Hyperparameter Setting'''
    parser = argparse.ArgumentParser()
    parser.add_argument('--dvc', type=str, default='cuda:1', help='running device: cuda or cpu')
    parser.add_argument('--EnvIdex', type=int, default=0, help='Environment index')
    parser.add_argument('--write', type=str2bool, default=True, help='Use SummaryWriter to record the training')
    parser.add_argument('--render', type=str2bool, default=False, help='Render or Not')
    parser.add_argument('--Loadmodel', type=str2bool, default=False, help='Load pretrained model or Not')
    parser.add_argument('--ModelIdex', type=int, default=0, help='which model to load')

    parser.add_argument('--seed', type=int, default=0, help='random seed')
    parser.add_argument('--Max_train_steps', type=int, default=int(15e6), help='Max training steps')
    parser.add_argument('--save_interval', type=int, default=int(9e5), help='Model saving interval, in steps.')
    parser.add_argument('--eval_interval', type=int, default=int(6e4), help='Model evaluating interval, in steps.')
    parser.add_argument('--update_every', type=int, default=8, help='Training Frequency, in steps')

    parser.add_argument('--gamma', type=float, default=0.98, help='Discounted Factor')
    parser.add_argument('--net_width', type=int, default=256, help='Hidden net width')
    parser.add_argument('--a_lr', type=float, default=5e-5, help='Learning rate of actor')
    parser.add_argument('--c_lr', type=float, default=5e-5, help='Learning rate of critic')
    parser.add_argument('--batch_size', type=int, default=256, help='batch_size of training')
    parser.add_argument('--num_envs', type=int, default=10, help='Number of parallel environments')
    
    opt = parser.parse_args()
    opt.dvc = torch.device(opt.dvc)
    print(opt)
    
    EnvName = ['sailboat-s14-v1']
    BrifEnvName = ['td3lstm_s14_0126']

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
          f'max_action:{opt.max_action}  max_e_steps:{opt.max_e_steps}')

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

    # Build TD3 model
    if not os.path.exists('model'): os.mkdir('model')
    agent = TD3_lstm_continuous(**vars(opt))

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
            score = evaluate_policy_td3(eval_env, agent, opt.max_action, turns=3)
            print('EnvName:', BrifEnvName[opt.EnvIdex], 'score:', score)
    else:
        total_steps = 0
        start_time = time.time()
        
        with tqdm(total=opt.Max_train_steps, desc='Training TD3') as pbar:
            while total_steps < opt.Max_train_steps:
                done_flags = [False] * opt.num_envs

                '''Interact & train'''
                while not all(done_flags):
                    actions = []
                    
                    for i in range(opt.num_envs):
                        # 训练初期使用随机动作探索
                        if total_steps < (20 * opt.max_e_steps):
                            random_strategy = np.random.random()
                            
                            if random_strategy < 0.3:
                                a = np.zeros(opt.action_dim)
                            elif random_strategy < 0.5:
                                a = np.random.uniform(-0.2, 0.2, opt.action_dim)
                            elif random_strategy < 0.65:
                                a = np.zeros(opt.action_dim)
                                if opt.action_dim >= 2:
                                    if np.random.random() < 0.5:
                                        a[0] = np.random.uniform(-0.5, 0.5)
                                    else:
                                        a[1] = np.random.uniform(-0.5, 0.5)
                                else:
                                    random_dim = np.random.randint(0, opt.action_dim)
                                    a[random_dim] = np.random.uniform(-0.5, 0.5)
                            else:
                                act = env.action_space.sample()
                                a = Action_adapter_reverse(act, opt.max_action)
                        else:
                            # TD3在训练时添加探索噪声
                            a = agent.select_action(prev_states[i], prev_actions[i], current_states[i],
                                                   add_noise=True, total_steps=total_steps, env_id=i)
                        actions.append(a)
                    
                    act_list = [Action_adapter(a, opt.max_action) for a in actions]
                    s_next_raw, r, done_flags, info = env.step(act_list)
                    
                    for i in range(opt.num_envs):
                        curr_state_seq = np.array(list(state_buffers[i]))
                        curr_action_seq = np.array(list(action_buffers[i]))
                        
                        action_buffers[i].append(actions[i].copy())
                        state_buffers[i].append(s_next_raw[i].copy())
                        
                        next_state_seq = np.array(list(state_buffers[i]))
                        next_action_seq = np.array(list(action_buffers[i]))

                        agent.replay_buffer.add(curr_state_seq, curr_action_seq, current_states[i],
                                              actions[i], r[i], next_state_seq, next_action_seq, 
                                              s_next_raw[i], done_flags[i])
                        
                        prev_states[i] = current_states[i].copy()
                        prev_actions[i] = actions[i].copy()
                        
                        if done_flags[i]:
                            agent.actor.reset_hidden_state(env_id=i)
                            agent.q_critic.reset_hidden_state(env_id=i)
                            agent.q_critic_target.reset_hidden_state(env_id=i)
                            agent.actor_target.reset_hidden_state(env_id=i)
                            
                            state_buffers[i].clear()
                            action_buffers[i].clear()
                            for _ in range(seq_len):
                                state_buffers[i].append(s_next_raw[i].copy())
                                action_buffers[i].append(np.zeros(opt.action_dim))
                            
                            prev_states[i] = s_next_raw[i].copy()
                            prev_actions[i] = np.zeros(opt.action_dim)

                    current_states = s_next_raw
                    total_steps += opt.num_envs
                    pbar.update(opt.num_envs)

                    '''train after warmup'''
                    if (total_steps >= 20 * opt.max_e_steps) and (agent.replay_buffer.size >= opt.batch_size):
                        if total_steps % 20 == 0:
                            progress = min(total_steps / 2000000, 1.0)
                            agent.replay_buffer.update_beta(progress)
                            
                            for _ in range(opt.update_every):
                                train_info = agent.train()
                            
                            if opt.write:
                                writer.add_scalar('Train/Q_Loss', train_info['q_loss'], global_step=total_steps)
                                writer.add_scalar('Train/Actor_Loss', train_info['a_loss'], global_step=total_steps)
                                writer.add_scalar('Train/Policy_Updated', 
                                                float(train_info['policy_updated']), global_step=total_steps)
                                writer.add_scalar('Train/Buffer_Beta', agent.replay_buffer.beta, 
                                                global_step=total_steps)
                                writer.add_scalar('Train/Buffer_Size', agent.replay_buffer.size, 
                                                global_step=total_steps)
                            
                            if torch.cuda.is_available():
                                torch.cuda.empty_cache()

                    '''record & log'''
                    if (total_steps >= 20 * opt.max_e_steps) and (total_steps % opt.eval_interval) == 0:
                        ep_r = evaluate_policy_td3(eval_env, agent, opt.max_action, turns=4)
                        if opt.write: 
                            writer.add_scalar('Eval/Episode_Reward', ep_r, global_step=total_steps)
                        
                        elapsed_time = time.time() - start_time
                        recent_q_loss = agent.q_loss_history[-1] if len(agent.q_loss_history) > 0 else 0.0
                        recent_a_loss = agent.a_loss_history[-1] if len(agent.a_loss_history) > 0 else 0.0
                        
                        print(f'EnvName:{BrifEnvName[opt.EnvIdex]}, Steps: {int(total_steps/1000)}k, '
                              f'Episode Reward:{ep_r}, Q_Loss:{recent_q_loss:.4f}, '
                              f'A_Loss:{recent_a_loss:.4f}, Elapsed Time:{elapsed_time:.2f}s')

                    '''save model'''
                    if total_steps % opt.save_interval == 0:
                        agent.save(BrifEnvName[opt.EnvIdex], int(total_steps/1000))
                        
                        if opt.write:
                            training_stats = {
                                'q_loss_history': agent.q_loss_history[-1000:],
                                'a_loss_history': agent.a_loss_history[-1000:],
                                'total_steps': total_steps,
                            }
                            torch.save(training_stats, 
                                     f"./model/{BrifEnvName[opt.EnvIdex]}_td3_training_stats_{int(total_steps/1000)}.pth")
                
                if total_steps >= opt.Max_train_steps:
                    break
        
        if opt.write:
            final_stats = {
                'q_loss_history': agent.q_loss_history,
                'a_loss_history': agent.a_loss_history,
                'total_steps': total_steps,
            }
            torch.save(final_stats, f"./model/{BrifEnvName[opt.EnvIdex]}_td3_final_training_stats.pth")
            writer.close()
        
        env.close()
        eval_env.close()


if __name__ == '__main__':
    try:
        multiprocessing.set_start_method('spawn', force=True)
    except RuntimeError:
        pass

    main()
