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
# 删除 matplotlib 相关引用
# import matplotlib.pyplot as plt

# 定义命令行参数
parser = argparse.ArgumentParser()
parser.add_argument('--dvc', type=str, default='cpu', help='running device: cuda or cpu')
parser.add_argument('--EnvIdex', type=int, default=0, help='PV1, Lch_Cv2, Humanv4, HCv4, BWv3, BWHv3')
parser.add_argument('--write', type=str2bool, default=True, help='Use SummaryWriter to record the training')
parser.add_argument('--render', type=str2bool, default=False, help='Render or Not')
parser.add_argument('--Loadmodel', type=str2bool, default=False, help='Load pretrained model or Not')
parser.add_argument('--ModelIdex', type=int, default=900, help='which model to load')
parser.add_argument('--seed', type=int, default=0, help='random seed')
parser.add_argument('--Max_train_steps', type=int, default=int(9e6), help='Max training steps')
parser.add_argument('--save_interval', type=int, default=int(9e5), help='Model saving interval, in steps.')
parser.add_argument('--eval_interval', type=int, default=int(30e3), help='Model evaluating interval, in steps.')
parser.add_argument('--update_every', type=int, default=50, help='Training Frequency, in steps')
parser.add_argument('--gamma', type=float, default=0.98, help='Discounted Factor')
parser.add_argument('--net_width', type=int, default=256, help='Hidden net width, s_dim-400-300-a_dim')
parser.add_argument('--a_lr', type=float, default=1e-4, help='Learning rate of actor')
parser.add_argument('--c_lr', type=float, default=1e-4, help='Learning rate of critic')
parser.add_argument('--batch_size', type=int, default=256, help='batch_size of training')
parser.add_argument('--alpha', type=float, default=0.1, help='Entropy coefficient')
parser.add_argument('--adaptive_alpha', type=str2bool, default=True, help='Use adaptive_alpha or Not')
parser.add_argument('--num_envs', type=int, default=1, help='Number of parallel environments')
# 新增测试次数参数
parser.add_argument('--num_tests', type=int, default=100, help='Number of tests to run')
# 新增风向中值参数，用于文件命名标记
parser.add_argument('--wind_mid', type=int, default=180, help='Manually set wind direction median value')
opt = parser.parse_args()
opt.dvc = torch.device(opt.dvc)

# 设置设备
opt.dvc = torch.device('cpu')  # 如需使用 GPU，可修改为 'cuda'

# 定义环境名称
EnvName = ['sailboat-lstm-v3']
BrifEnvName = ['saclstm_v1_2025_0422']

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

# 用于统计成功到达终点（terminated为True）的测试次数
success_count = 0

for test_idx in range(opt.num_tests):
    print(f"\n===== 测试 {test_idx+1}/{opt.num_tests} =====")
    # 每次测试单独重置环境
    s, info = env.reset(seed=opt.seed)
    # 构造初始状态序列
    state_seq = np.repeat(s[None, :], 5, axis=0)
    
    # 初始化测试过程中数据的存储
    actions = []
    observations = []
    wind_changes_v = []
    wind_changes_d = []
    
    step = 0
    total_scores = 0
    done = False
    terminated_flag = False  # 记录本次测试是否因 terminated 而结束

    while not done:
        # 使用连续5个时刻的状态决策
        a = agent.select_action(state_seq, deterministic=True)
        act = Action_adapter(a, opt.max_action)
        
        # 执行动作，获得下一时刻的状态
        s_next, r, dw, tr, info = env.step(act)
        
        # 收集测试数据
        actions.append(act)
        observations.append(copy.deepcopy(s_next))
        wind_changes_v.append(globals.w_change_v)
        wind_changes_d.append(globals.w_change_d)
        
        # 输出当前步信息
        # print(f"Step: {step}")
        # print(f"Action: {act}")
        # print(f"Observation: {s_next}")
        # print(f"Reward: {r}")
        # print(f"Terminated: {dw}")
        # print(f"Truncated: {tr}")
        # print(f"Info: {info}")
        # print("-" * 50)
        done = (dw or tr)
        
        # 更新滑动窗口
        state_seq = np.concatenate((state_seq[1:], s_next[None, :]), axis=0)
        
        # 如有需要，可继续打印
        print(s, act)
        s = s_next
        step += 1
        total_scores += r
        print(f"step: {step}")
        print(f"all_reward: {total_scores}")
        
        # 如果因为 terminated 而结束，则记录为成功
        if dw:
            terminated_flag = True

    # 如果测试成功（终点达到，即 terminated 为 True），则保存该次测试数据
    if terminated_flag:
        success_count += 1
        desktop_path = 'C:\\Users\\24809\\Desktop\\success_v3\\'
        obs_array = np.array(observations)
        np.savetxt(desktop_path + f'actions_test_{test_idx+1}_wind_{opt.wind_mid}.txt', np.array(actions), delimiter=',', header='Actions', comments='')
        np.savetxt(desktop_path + f'observations_test_{test_idx+1}_wind_{opt.wind_mid}.txt', obs_array, delimiter=',', 
                   header=','.join([f'Observation {i}' for i in range(obs_array.shape[1])]), comments='')
        np.savetxt(desktop_path + f'wind_changes_test_{test_idx+1}_wind_{opt.wind_mid}.txt', 
                   np.column_stack((wind_changes_v, wind_changes_d)), delimiter=',', 
                   header='Wind Change V,Wind Change D', comments='')
        print(f"测试 {test_idx+1} 成功到达终点，数据已保存！")
    else:
        print(f"测试 {test_idx+1} 未到达终点，不保存数据。")

print(f"\n共 {opt.num_tests} 次测试中成功到达终点的次数: {success_count}")
env.close()