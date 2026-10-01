from utils_2lstm_pri import str2bool, evaluate_policy, Action_adapter, Action_adapter_reverse, Reward_adapter
from datetime import datetime
from SAC_2lstm_pri import SAC_lstm_countinuous
import gymnasium as gym
import os, shutil
import argparse
import torch
import globals
import time
import numpy as np
from tqdm import tqdm
from stable_baselines3.common.vec_env import SubprocVecEnv
import copy
import matplotlib.pyplot as plt

# 定义命令行参数
parser = argparse.ArgumentParser()
parser.add_argument('--dvc', type=str, default='cpu', help='running device: cuda or cpu')
parser.add_argument('--EnvIdex', type=int, default=0, help='PV1, Lch_Cv2, Humanv4, HCv4, BWv3, BWHv3')
parser.add_argument('--write', type=str2bool, default=True, help='Use SummaryWriter to record the training')
parser.add_argument('--render', type=str2bool, default=False, help='Render or Not')
parser.add_argument('--Loadmodel', type=str2bool, default=False, help='Load pretrained model or Not')
parser.add_argument('--ModelIdex', type=int, default=1800, help='which model to load')

parser.add_argument('--seed', type=int, default=0, help='random seed')
parser.add_argument('--Max_train_steps', type=int, default=int(9e6), help='Max training steps')
parser.add_argument('--save_interval', type=int, default=int(9e5), help='Model saving interval, in steps.')
parser.add_argument('--eval_interval', type=int, default=int(30e3), help='Model evaluating interval, in steps.')
parser.add_argument('--update_every', type=int, default=50, help='Training Fraquency, in stpes')

parser.add_argument('--gamma', type=float, default=0.99, help='Discounted Factor')
parser.add_argument('--net_width', type=int, default=256, help='Hidden net width, s_dim-400-300-a_dim')
parser.add_argument('--a_lr', type=float, default=2e-4, help='Learning rate of actor')
parser.add_argument('--c_lr', type=float, default=2e-4, help='Learning rate of critic')
parser.add_argument('--batch_size', type=int, default=256, help='batch_size of training')
parser.add_argument('--alpha', type=float, default=0.1, help='Entropy coefficient')
parser.add_argument('--adaptive_alpha', type=str2bool, default=True, help='Use adaptive_alpha or Not')
parser.add_argument('--num_envs', type=int, default=1, help='Number of parallel environments')
opt = parser.parse_args()
opt.dvc = torch.device(opt.dvc)

# 设置设备
opt.dvc = torch.device('cpu')  # 这里假设使用 CPU，如果需要使用 GPU，请修改为 'cuda'

# 定义环境名称
EnvName = ['sailboat-s14-v1']
BrifEnvName = ['saclstm_s14_0514']
# BrifEnvName = ['saclstm_v3_2025_0424']

# 创建环境
env = gym.make(EnvName[opt.EnvIdex])
env.reset(seed=opt.seed)
opt.state_dim = env.observation_space.shape[0]
opt.action_dim = env.action_space.shape[0]
opt.max_action = env.action_space.high.astype(float)
opt.max_e_steps = 900

# 加载预训练模型
agent = SAC_lstm_countinuous(**vars(opt))

if not os.path.exists('model'): os.mkdir('model')
agent.load(BrifEnvName[opt.EnvIdex], opt.ModelIdex)
# model_path = f'./model/{BrifEnvName[opt.EnvIdex]}_actor{opt.ModelIdex}.pth'
# agent.load(model_path)

# 环境初始化
s, info = env.reset()
# 构造初始状态序列，用于网络输入，形状为 (3, state_dim)
state_seq = np.repeat(s[None, :], 10, axis=0)

steps = []
actions = []
observations = []
wind_changes_v = []
wind_changes_d = []

step = 0
total_scores = 0
done = False

while not done:
    # 每5个采样时间输出一次动作，否则输出0
    if step % 5 == 0:
        # 使用连续10个时刻的状态决策
        a = agent.select_action(state_seq, deterministic=True, total_steps=None)
        act = Action_adapter(a, opt.max_action)
    else:
        # 在非5的倍数步骤输出0动作
        act = np.zeros_like(opt.max_action)
    
    # 执行动作，获得下一时刻的单个状态 s_next
    s_next, r, dw, tr, info = env.step(act)
    
    # 收集数据：这里保存的是单步状态
    actions.append(act)
    observations.append(copy.deepcopy(s_next))
    wind_changes_v.append(globals.w_change_v)
    wind_changes_d.append(globals.w_change_d)

    # 输出当前步信息
    print(f"Step: {step}")
    print(f"Action: {act}")
    print(f"Observation: {s_next}")
    print(f"Reward: {r}")
    print(f"Terminated: {dw}")
    print(f"Truncated: {tr}")
    print(f"Info: {info}")
    print("-" * 50)
    done = (dw or tr)

    # 更新滑动窗口：丢弃最旧状态，追加最新状态
    state_seq = np.concatenate((state_seq[1:], s_next[None, :]), axis=0)
    
    # 如有需要，s 仍可用于打印或其他记录（s 为单一采样状态）
    print(s, act)
    s = s_next
    step += 1
    total_scores += r
    print(f"step:{step}")
    print(f"all_reward:{total_scores}")

# 数据保存部分保持不变
desktop_path = 'C:\\Users\\24809\\Desktop\\'
observations_array = np.array(observations)
np.savetxt(desktop_path + 'actions_model.txt', np.array(actions), delimiter=',', header='Actions', comments='')
np.savetxt(desktop_path + 'observations_model.txt', np.array(observations), delimiter=',', 
           header=','.join([f'Observation {i}' for i in range(observations_array.shape[1])]), comments='')
np.savetxt(desktop_path + 'wind_changes_model.txt', 
           np.column_stack((wind_changes_v, wind_changes_d)), delimiter=',', 
           header='Wind Change V,Wind Change D', comments='')

# 绘图部分...
x = observations_array[:, 0]
y = observations_array[:, 1]
plt.figure(figsize=(10, 6))
plt.plot(x, y, marker='o', linestyle='-', color='b')
plt.title('Trajectory of Observations')
plt.xlabel('X Coordinate')
plt.ylabel('Y Coordinate')
plt.xlim(-500, 500)
plt.ylim(-200, 200)
plt.grid(True)
plt.show()

env.close()