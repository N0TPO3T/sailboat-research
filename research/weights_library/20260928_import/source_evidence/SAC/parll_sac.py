import os, shutil
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # 只显示错误信息

from utils import str2bool, evaluate_policy, Action_adapter, Action_adapter_reverse, Reward_adapter
from datetime import datetime
from SAC import SAC
import gymnasium as gym
import argparse
import torch
import time
import numpy as np
from tqdm import tqdm
from stable_baselines3.common.vec_env import SubprocVecEnv
import globals
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
parser.add_argument('--eval_interval', type=int, default=int(9e4), help='Model evaluating interval, in steps.')
parser.add_argument('--update_every', type=int, default=30, help='Training Fraquency, in stpes')

parser.add_argument('--gamma', type=float, default=0.99, help='Discounted Factor')
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
    BrifEnvName = ['sac_s14_0523_test']  # 修改名称以反映模型变化

    # Build Env
    env_fns = [make_env(EnvName[opt.EnvIdex], opt.seed + i) for i in range(opt.num_envs)]
    env = SubprocVecEnv(env_fns)
    eval_env = gym.make(EnvName[opt.EnvIdex])
    opt.state_dim = env.observation_space.shape[0]
    opt.action_dim = env.action_space.shape[0]
    opt.max_action = env.action_space.high.astype(float)

    opt.max_e_steps = 500
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
    agent = SAC(**vars(opt)) # 传入所有参数

    if opt.Loadmodel: agent.load(BrifEnvName[opt.EnvIdex], opt.ModelIdex)

    # 获取初始状态 (不再需要构建序列)
    s_raw = env.reset()  # s_raw: (num_envs, state_dim)

    if opt.render:
        while True:
            # 评估时直接使用当前状态
            score = evaluate_policy(eval_env, agent, opt.max_action, turns=3)
            print('EnvName:', BrifEnvName[opt.EnvIdex], 'score:', score)
    else:
        total_steps = 0
        start_time = time.time()
        with tqdm(total=opt.Max_train_steps, desc='Training') as pbar:
            while total_steps < opt.Max_train_steps:
                done_flags = [False] * opt.num_envs

                '''Interact & train'''
                while not all(done_flags):
                    actions = []
                    # 基于当前状态选择动作
                    for i in range(opt.num_envs):
                        # 在训练初期可选随机动作，否则使用 agent.select_action
                        if total_steps < (30 * opt.max_e_steps):
                            act = env.action_space.sample()
                            a = Action_adapter_reverse(act, opt.max_action)
                        else:
                            a = agent.select_action(s_raw[i], deterministic=False, total_steps=total_steps)
                        actions.append(a)
                    # 将连续动作转换至环境所需范围
                    act_list = [Action_adapter(a, opt.max_action) for a in actions]
                    s_next_raw, r, done_flags, info = env.step(act_list)  # s_next_raw: (num_envs, state_dim)
                    
                    # 对每个环境添加经验到缓冲区
                    for i in range(opt.num_envs):
                        agent.replay_buffer.add(s_raw[i], actions[i], r[i], s_next_raw[i], done_flags[i])
                    
                    # 更新当前状态
                    s_raw = s_next_raw

                    total_steps += opt.num_envs
                    pbar.update(opt.num_envs)

                    '''train if it's time'''
                    # 优化方案
                    update_ratio = 10  # 更新次数与收集样本数的比例

                    if (total_steps >= 30 * opt.max_e_steps) and (total_steps % opt.update_every == 0):
                        # 计算训练进度，用于更新beta值
                        progress = min(total_steps / 3000000, 1.0)
                        # 更新 beta 值
                        agent.replay_buffer.update_beta(progress)

                        updates_to_perform = opt.update_every
                        avg_q_loss = 0
                        avg_a_loss = 0
                        avg_alpha_loss = 0
                        avg_alpha = 0
                        for j in range(updates_to_perform):
                            loss_info = agent.train()
                            # 累积各种loss信息
                            avg_q_loss += loss_info['q_loss']
                            avg_a_loss += loss_info['a_loss']
                            avg_alpha_loss += loss_info['alpha_loss']
                            avg_alpha += loss_info['alpha']
                        
                        # 计算平均值
                        avg_q_loss /= updates_to_perform
                        avg_a_loss /= updates_to_perform
                        avg_alpha_loss /= updates_to_perform
                        avg_alpha /= updates_to_perform
                        
                        # 记录到TensorBoard
                        if opt.write:
                            writer.add_scalar('losses/critic_loss', avg_q_loss, global_step=total_steps)
                            writer.add_scalar('losses/actor_loss', avg_a_loss, global_step=total_steps)
                            writer.add_scalar('losses/alpha_loss', avg_alpha_loss, global_step=total_steps)
                            writer.add_scalar('params/alpha', avg_alpha, global_step=total_steps)

                    '''record & log'''
                    if total_steps % opt.eval_interval == 0:
                        ep_r = evaluate_policy(eval_env, agent, opt.max_action, turns=3, total_steps=total_steps)
                        if opt.write: writer.add_scalar('ep_r', ep_r, global_step=total_steps)
                        elapsed_time = time.time() - start_time
                        print(f'EnvName:{BrifEnvName[opt.EnvIdex]}, Steps: {int(total_steps/1000)}k, '
                              f'Episode Reward:{ep_r}, Elapsed Time:{elapsed_time:.2f}s')

                    '''save model'''
                    if total_steps % opt.save_interval == 0:
                        agent.save(BrifEnvName[opt.EnvIdex], int(total_steps/1000))
                if total_steps >= opt.Max_train_steps:
                    break
        env.close()
        eval_env.close()

if __name__ == '__main__':
    main()
