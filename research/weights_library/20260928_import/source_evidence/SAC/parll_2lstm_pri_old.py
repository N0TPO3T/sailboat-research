import os, shutil
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # 只显示错误信息

from utils_2lstm_pri import str2bool, evaluate_policy, Action_adapter, Action_adapter_reverse, Reward_adapter
from datetime import datetime
from SAC_2lstm_pri import SAC_lstm_countinuous
import gymnasium as gym
import argparse
import torch
import globals
import time
import numpy as np
from tqdm import tqdm
from stable_baselines3.common.vec_env import SubprocVecEnv
# from torchsummary import summary
# import torch
# from torchviz import make_dot


# from torch.utils.tensorboard import summary
'''Hyperparameter Setting'''
parser = argparse.ArgumentParser()
parser.add_argument('--dvc', type=str, default='cuda:0', help='running device: cuda or cpu')
parser.add_argument('--EnvIdex', type=int, default=0, help='PV1, Lch_Cv2, Humanv4, HCv4, BWv3, BWHv3')
parser.add_argument('--write', type=str2bool, default=True, help='Use SummaryWriter to record the training')
parser.add_argument('--render', type=str2bool, default=False, help='Render or Not')
parser.add_argument('--Loadmodel', type=str2bool, default=False, help='Load pretrained model or Not')
parser.add_argument('--ModelIdex', type=int, default=0, help='which model to load')

parser.add_argument('--seed', type=int, default=0, help='random seed')
parser.add_argument('--Max_train_steps', type=int, default=int(9e6), help='Max training steps')
parser.add_argument('--save_interval', type=int, default=int(9e5), help='Model saving interval, in steps.')
parser.add_argument('--eval_interval', type=int, default=int(3e4), help='Model evaluating interval, in steps.')
parser.add_argument('--update_every', type=int, default=300, help='Training Fraquency, in stpes')

parser.add_argument('--gamma', type=float, default=0.98, help='Discounted Factor')
parser.add_argument('--net_width', type=int, default=256, help='Hidden net width, s_dim-400-300-a_dim')
parser.add_argument('--a_lr', type=float, default=1e-4, help='Learning rate of actor')
parser.add_argument('--c_lr', type=float, default=1e-4, help='Learning rate of critic')
parser.add_argument('--batch_size', type=int, default=256, help='batch_size of training')
parser.add_argument('--alpha', type=float, default=0.1, help='Entropy coefficient')
parser.add_argument('--adaptive_alpha', type=str2bool, default=True, help='Use adaptive_alpha or Not')
parser.add_argument('--num_envs', type=int, default=30, help='Number of parallel environments')
opt = parser.parse_args()
opt.dvc = torch.device(opt.dvc) # from str to torch.device
print(opt)


def make_env(env_id, seed):
    def _init():
        env = gym.make(env_id)
        env.reset(seed=seed)
        return env
    return _init

def main():
    EnvName = ['sailboat-s14-v1']
    BrifEnvName = ['saclstm_s14_0517_10lstm1']

    # Build Env
    env_fns = [make_env(EnvName[opt.EnvIdex], opt.seed + i) for i in range(opt.num_envs)]
    env = SubprocVecEnv(env_fns)
    eval_env = gym.make(EnvName[opt.EnvIdex])
    opt.state_dim = env.observation_space.shape[0]
    opt.action_dim = env.action_space.shape[0]
    opt.max_action = env.action_space.high.astype(float)

    opt.max_e_steps = 900
    print(f'Env:{EnvName[opt.EnvIdex]}  state_dim:{opt.state_dim}  action_dim:{opt.action_dim}  '
          f'max_a_s:{opt.max_action[0]}  max_a_r:{opt.max_action[1]} min_a_s:{env.action_space.low[0],env.action_space.low[1]}  max_e_steps:{opt.max_e_steps}')

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

    # 修改点：创建每个 env 的状态序列
    # env.reset() 返回形状为 (num_envs, state_dim)，这里复制5次构成初始序列
    s_raw = env.reset()  # s_raw: (num_envs, state_dim)
    # current_states 保存每个 env 的连续5步状态（列表长度 = num_envs, 每项形状 (5, state_dim)）
    current_states = [np.repeat(s_raw[i][None, :], 10, axis=0) for i in range(opt.num_envs)]

    # # # 预先导入 npz 文件数据到经验池
    # pretrain_path = './initial_training_data.npz'
    # data = np.load(pretrain_path, allow_pickle=True)
    # s_list = data['s']
    # a_list = data['a']
    # r_list = data['r']
    # s_next_list = data['s_next']
    # dw_list = data['dw']

    # for s, a, r, s_next, dw in zip(s_list, a_list, r_list, s_next_list, dw_list):
    #     agent.replay_buffer.add(s, a, r, s_next, dw)
    # print("预导入 npz 数据完成，样本数:", agent.replay_buffer.size)

    # # 预先进行30000次训练更新
    # for update_iter in range(30000):
    #     agent.train()
    # print("预训练更新 30000 次完成")

    if opt.render:
        while True:
            # 在评估时也需要传入连续5步的状态序列
            score = evaluate_policy(eval_env, agent, opt.max_action, turns=3)
            print('EnvName:', BrifEnvName[opt.EnvIdex], 'score:', score)
    else:
        total_steps = 0
        start_time = time.time()
        with tqdm(total=opt.Max_train_steps, desc='Training') as pbar:
            while total_steps < opt.Max_train_steps:
                done_flags = [False] * opt.num_envs
                # 新增：每个环境的步数计数器
                env_steps = [0] * opt.num_envs

                '''Interact & train'''
                while not all(done_flags):
                    actions = []
                    # 根据 current_states 来选择动作，current_states[i] 的形状为 (10, state_dim)
                    for i in range(opt.num_envs):
                        # 修改：移除条件判断，每一步都使用实际动作
                        if total_steps < (200 * opt.max_e_steps):
                            act = env.action_space.sample()
                            a = Action_adapter_reverse(act, opt.max_action)
                        else:
                            if np.random.rand() < 0.05:
                                act = env.action_space.sample()
                                a = Action_adapter_reverse(act, opt.max_action)
                            else:
                                a = agent.select_action(current_states[i], deterministic=False, total_steps=total_steps)
                        
                        actions.append(a)
                        # 更新该环境的步数
                        env_steps[i] += 1
                    
                    # 将连续动作转换至环境所需范围
                    act_list = [Action_adapter(a, opt.max_action) for a in actions]
                    
                    # 修改这一行，处理truncated标志
                    s_next_raw, r, done_flags, info = env.step(act_list)  # s_next_raw: (num_envs, state_dim)

                    # 对每个 env 更新状态序列，并存入 ReplayBuffer
                    for i in range(opt.num_envs):
                        # 建立新的序列：丢弃当前序列中最早的状态，并附加最新观测
                        next_state_seq = np.concatenate((current_states[i][1:], s_next_raw[i][None, :]), axis=0)  # shape: (10, state_dim)
                        
                        # 存储到经验回放中，同时传递更新后的done_flags
                        agent.replay_buffer.add(current_states[i], actions[i], r[i], next_state_seq, done_flags[i])
                        # 更新当前状态序列
                        current_states[i] = next_state_seq
                        
                        # 如果环境结束或截断，重置该环境的步数计数器
                        if done_flags[i]:
                            env_steps[i] = 0

                    total_steps += opt.num_envs
                    pbar.update(opt.num_envs)

                    '''train if it's time'''
                    # 优化方案
                    update_ratio = 2.0  # 更新次数与收集样本数的比例
                    samples_per_step = opt.num_envs  # 每步收集的样本数

                    if (total_steps >= 20 * opt.max_e_steps) and (total_steps % opt.update_every == 0):
                        # 计算训练进度，用于更新beta值
                        progress = min(total_steps / 3000000, 1.0)
                        # 更新 beta 值
                        agent.replay_buffer.update_beta(progress)
                        
                        updates_to_perform = opt.update_every

                        # 记录所有训练的损失总和
                        loss_stats = {
                            'q1_loss': 0, 
                            'q2_loss': 0, 
                            'actor_loss': 0, 
                            'alpha_loss': 0,
                            'td_error_mean': 0,
                            'entropy': 0,
                            'alpha': 0
                        }
                        
                        for j in range(updates_to_perform):
                            # 收集每次训练返回的损失值
                            update_stats = agent.train()
                            for k, v in update_stats.items():
                                loss_stats[k] += v
                        
                        # 计算平均值并记录到tensorboard
                        if opt.write and updates_to_perform > 0:
                            for k, v in loss_stats.items():
                                avg_value = v / updates_to_perform
                                writer.add_scalar(f'losses/{k}', avg_value, global_step=total_steps)

                    '''record & log'''
                    if total_steps % opt.eval_interval == 0:
                        ep_r = evaluate_policy(eval_env, agent, opt.max_action, turns=3)
                        if opt.write: 
                            # 记录评估相关指标
                            writer.add_scalar('performance/episode_reward', ep_r, global_step=total_steps)
                            writer.add_scalar('hyperparams/beta', agent.replay_buffer.beta, global_step=total_steps)
                            writer.add_scalar('hyperparams/alpha', agent.alpha if not isinstance(agent.alpha, torch.Tensor) 
                                             else agent.alpha.item(), global_step=total_steps)
                            
                        #     # 记录网络梯度情况
                        #     for name, param in agent.actor.named_parameters():
                        #         if param.grad is not None:
                        #             writer.add_histogram(f'actor_grads/{name}', param.grad, global_step=total_steps)
                            
                        #     for name, param in agent.q_critic.named_parameters():
                        #         if param.grad is not None:
                        #             writer.add_histogram(f'critic_grads/{name}', param.grad, global_step=total_steps)
                                    
                        elapsed_time = time.time() - start_time
                        print(f'EnvName:{BrifEnvName[opt.EnvIdex]}, Steps: {int(total_steps/1000)}k, '
                              f'Episode Reward:{ep_r}, Beta:{agent.replay_buffer.beta:.4f}, Elapsed Time:{elapsed_time:.2f}s')
                    
                    '''save model'''
                    if total_steps % opt.save_interval == 0:
                        agent.save(BrifEnvName[opt.EnvIdex], int(total_steps/1000))
                if total_steps >= opt.Max_train_steps:
                    break
        env.close()
        eval_env.close()

if __name__ == '__main__':
    main()
