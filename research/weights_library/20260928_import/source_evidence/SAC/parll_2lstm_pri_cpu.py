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
parser.add_argument('--dvc', type=str, default='cpu', help='running device: cuda or cpu')
parser.add_argument('--EnvIdex', type=int, default=0, help='PV1, Lch_Cv2, Humanv4, HCv4, BWv3, BWHv3')
parser.add_argument('--write', type=str2bool, default=False, help='Use SummaryWriter to record the training')
parser.add_argument('--render', type=str2bool, default=False, help='Render or Not')
parser.add_argument('--Loadmodel', type=str2bool, default=False, help='Load pretrained model or Not')
parser.add_argument('--ModelIdex', type=int, default=0, help='which model to load')

parser.add_argument('--seed', type=int, default=0, help='random seed')
parser.add_argument('--Max_train_steps', type=int, default=int(9e6), help='Max training steps')
parser.add_argument('--save_interval', type=int, default=int(3e6), help='Model saving interval, in steps.')
parser.add_argument('--eval_interval', type=int, default=int(3e4), help='Model evaluating interval, in steps.')
parser.add_argument('--update_every', type=int, default=50, help='Training Fraquency, in stpes')

parser.add_argument('--gamma', type=float, default=0.98, help='Discounted Factor')
parser.add_argument('--net_width', type=int, default=256, help='Hidden net width, s_dim-400-300-a_dim')
parser.add_argument('--a_lr', type=float, default=1e-4, help='Learning rate of actor')
parser.add_argument('--c_lr', type=float, default=1e-4, help='Learning rate of critic')
parser.add_argument('--batch_size', type=int, default=256, help='batch_size of training')
parser.add_argument('--alpha', type=float, default=0.1, help='Entropy coefficient')
parser.add_argument('--adaptive_alpha', type=str2bool, default=True, help='Use adaptive_alpha or Not')
parser.add_argument('--num_envs', type=int, default=1, help='Number of parallel environments')
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
    BrifEnvName = ['test_20250506']

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
    # actor = agent.actor
    # critic = agent.q_critic

    # # 生成网络计算图
    # dummy_state = torch.randn(1, opt.state_dim).to(opt.dvc)
    # dummy_action = torch.randn(1, opt.action_dim).to(opt.dvc)
    # actor_graph = make_dot(actor.summary_forward(dummy_state), params=dict(actor.named_parameters()))
    # actor_graph.format = 'png'
    # actor_graph.render('actor_network_1')
    # critic_graph = make_dot(critic(dummy_state, dummy_action), params=dict(critic.named_parameters()))
    # critic_graph.format = 'png'
    # critic_graph.render('critic_network_1')
    if opt.Loadmodel: agent.load(BrifEnvName[opt.EnvIdex], opt.ModelIdex)

    # 修改点：创建每个 env 的状态序列
    # env.reset() 返回形状为 (num_envs, state_dim)，这里复制5次构成初始序列
    s_raw = env.reset()  # s_raw: (num_envs, state_dim)
    # current_states 保存每个 env 的连续5步状态（列表长度 = num_envs, 每项形状 (5, state_dim)）
    current_states = [np.repeat(s_raw[i][None, :], 5, axis=0) for i in range(opt.num_envs)]

    # # 预先导入 npz 文件数据到经验池
    # pretrain_path = 'C:\\Users\\24809\\Desktop\\success\\initial_training_data.npz'
    # data = np.load(pretrain_path, allow_pickle=True)
    # s_list = data['s']
    # a_list = data['a']
    # r_list = data['r']
    # s_next_list = data['s_next']
    # dw_list = data['dw']

    # for s, a, r, s_next, dw in zip(s_list, a_list, r_list, s_next_list, dw_list):
    #     agent.replay_buffer.add(s, a, r, s_next, dw)
    # print("预导入 npz 数据完成，样本数:", agent.replay_buffer.size)

    # # 预先进行1000次训练更新
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

                '''Interact & train'''
                while not all(done_flags):
                    actions = []
                    # 根据 current_states 来选择动作，current_states[i] 的形状为 (3, state_dim)
                    for i in range(opt.num_envs):
                        # 在训练初期可选随机动作，否则使用 agent.select_action
                        # if total_steps < (5 * opt.max_e_steps):
                        #     act = env.action_space.sample()
                        #     a = Action_adapter_reverse(act, opt.max_action)
                        # else:
                        a = agent.select_action(current_states[i], deterministic=False)
                        actions.append(a)
                    # 将连续动作转换至环境所需范围
                    act_list = [Action_adapter(a, opt.max_action) for a in actions]
                    s_next_raw, r, done_flags, info = env.step(act_list)  # s_next_raw: (num_envs, state_dim)
                    
                    # 对每个 env 更新状态序列，并存入 ReplayBuffer
                    for i in range(opt.num_envs):
                        # 建立新的序列：丢弃当前序列中最早的状态，并附加最新观测
                        next_state_seq = np.concatenate((current_states[i][1:], s_next_raw[i][None, :]), axis=0)  # shape: (3, state_dim)
                        
                        # 假设动作也需要序列，若 agent.replay_buffer.add 要求 a_seq，则可以采用同样策略
                        # 此处假设 a 为单步动作，不要求序列，可根据实际需求修改
                        agent.replay_buffer.add(current_states[i], actions[i], r[i], next_state_seq, done_flags[i])
                        # 更新当前状态序列
                        current_states[i] = next_state_seq

                    total_steps += opt.num_envs
                    pbar.update(opt.num_envs)

                    '''train if it's time'''
                    if (total_steps >= 2*opt.max_e_steps) and (total_steps % opt.update_every == 0):
                        for j in range(opt.update_every):
                            agent.train()

                    '''record & log'''
                    if total_steps % opt.eval_interval == 0:
                        ep_r = evaluate_policy(eval_env, agent, opt.max_action, turns=3)
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