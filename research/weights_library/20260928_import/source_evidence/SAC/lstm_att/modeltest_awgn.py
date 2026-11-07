from utils_lstm_att_normal import str2bool, evaluate_policy, Action_adapter, Action_adapter_reverse, Reward_adapter
from datetime import datetime
from SAC_lstm_att_normal import SAC_lstm_countinuous
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
from matplotlib.patches import Circle
import json

# 定义命令行参数
parser = argparse.ArgumentParser()
parser.add_argument('--dvc', type=str, default='cpu', help='running device: cuda or cpu')
parser.add_argument('--EnvIdex', type=int, default=0, help='PV1, Lch_Cv2, Humanv4, HCv4, BWv3, BWHv3')
parser.add_argument('--write', type=str2bool, default=True, help='Use SummaryWriter to record the training')
parser.add_argument('--render', type=str2bool, default=False, help='Render or Not')
parser.add_argument('--Loadmodel', type=str2bool, default=True, help='Load pretrained model or Not')
parser.add_argument('--ModelIdex', type=int, default=15600, help='which model to load (in thousands of steps)')
parser.add_argument('--wind_angle', type=int, default=5, help='Wind direction angle in degrees (0-360)')

parser.add_argument('--seed', type=int, default=0, help='random seed')
parser.add_argument('--Max_train_steps', type=int, default=int(9e6), help='Max training steps')
parser.add_argument('--save_interval', type=int, default=int(9e5), help='Model saving interval, in steps.')
parser.add_argument('--eval_interval', type=int, default=int(1e5), help='Model evaluating interval, in steps.')
parser.add_argument('--update_every', type=int, default=0, help='Training Frequency, in steps')

parser.add_argument('--gamma', type=float, default=0.98, help='Discounted Factor')
parser.add_argument('--net_width', type=int, default=256, help='Hidden net width, s_dim-400-300-a_dim')
parser.add_argument('--a_lr', type=float, default=5e-5, help='Learning rate of actor')
parser.add_argument('--c_lr', type=float, default=5e-5, help='Learning rate of critic')
parser.add_argument('--batch_size', type=int, default=256, help='batch_size of training')
parser.add_argument('--alpha', type=float, default=0.2, help='Entropy coefficient')
parser.add_argument('--adaptive_alpha', type=str2bool, default=True, help='Use adaptive_alpha or Not')
parser.add_argument('--num_envs', type=int, default=1, help='Number of parallel environments')

# AWGN噪声参数
parser.add_argument('--add_sensor_noise', type=str2bool, default=True, help='Add sensor noise to observations')
parser.add_argument('--use_awgn', type=str2bool, default=True, help='Use AWGN noise model')
parser.add_argument('--snr_db', type=float, default=30.0, help='Fixed Signal-to-Noise Ratio in dB for testing')
parser.add_argument('--noise_scale_pos', type=float, default=1.0, help='Noise scale factor for position')
parser.add_argument('--noise_scale_angle', type=float, default=1.0, help='Noise scale factor for angles')
parser.add_argument('--noise_scale_vel', type=float, default=1.0, help='Noise scale factor for velocities')
parser.add_argument('--noise_scale_dist', type=float, default=1.0, help='Noise scale factor for distances')

opt = parser.parse_args()
opt.dvc = torch.device(opt.dvc)

# 定义环境名称
EnvName = ['sailboat-s14-obst-v2']
BrifEnvName = ['saclstm_s14obst_awgn_1227']  # 修改为训练文件使用的模型名称

# 创建环境
env = gym.make(EnvName[opt.EnvIdex])
env.reset(seed=opt.seed)
opt.state_dim = env.observation_space.shape[0]
opt.action_dim = env.action_space.shape[0]
opt.max_action = env.action_space.high.astype(float)
opt.max_e_steps = 1000

# 加载预训练模型
agent = SAC_lstm_countinuous(**vars(opt))

if not os.path.exists('model'): 
    print("模型文件夹不存在！")
    exit()

# 检查模型文件是否存在
model_files = [
    f'./model/{BrifEnvName[opt.EnvIdex]}_actor{opt.ModelIdex}.pth',
    f'./model/{BrifEnvName[opt.EnvIdex]}_q_critic{opt.ModelIdex}.pth'
]

# 尝试查找normalizer文件（可能存在也可能不存在）
normalizer_file = f'./model/{BrifEnvName[opt.EnvIdex]}_normalizer{opt.ModelIdex}.pth'
if os.path.exists(normalizer_file):
    model_files.append(normalizer_file)

for model_file in model_files[:2]:  # 至少检查actor和critic文件
    if not os.path.exists(model_file):
        print(f"模型文件不存在: {model_file}")
        print("可用的模型文件:")
        for file in os.listdir('./model/'):
            if file.startswith(BrifEnvName[opt.EnvIdex]):
                print(f"  {file}")
        exit()

try:
    agent.load(BrifEnvName[opt.EnvIdex], opt.ModelIdex)
    print(f"成功加载模型: {BrifEnvName[opt.EnvIdex]}_{opt.ModelIdex}")
except Exception as e:
    print(f"加载模型失败: {e}")
    exit()

# ========== 第1处修改：替换噪声函数（约第100行） ==========
def add_fixed_random_noise(observation, opt):
    """
    使用固定精度的随机噪声为观测值添加噪声（推荐用于传感器建模）
    
    观测空间 (18维):
    [0-1]: x, y (位置) - GPS精度 ±1.5米
    [2]: psi (航向角) - 罗盘精度 ±0.8度
    [3]: phi (横滚角) - 陀螺仪精度 ±0.8度
    [4-7]: u, v, p, r (速度) - 速度计精度 ±0.15 m/s
    [8-9]: sail_angle, rudder_angle (帆角、舵角) - 不添加噪声
    [10-11]: 距离相关 - 距离测量精度 ±2.0米
    [12-13]: 目标位置 - 不添加噪声
    [14-17]: 障碍物位置 - 位置检测精度 ±2.0米
    """
    if not opt.add_sensor_noise:
        return observation.copy()
    
    noisy_obs = observation.copy()
    
    # GPS位置噪声：±1.5米（海上GPS典型精度）
    pos_noise_std = 1.5 * opt.noise_scale_pos
    noisy_obs[0] += np.random.normal(0, pos_noise_std)  # x
    noisy_obs[1] += np.random.normal(0, pos_noise_std)  # y
    
    # 罗盘/陀螺仪角度噪声：±0.8度
    angle_noise_std = np.deg2rad(0.8) * opt.noise_scale_angle
    noisy_obs[2] += np.random.normal(0, angle_noise_std)  # psi (航向角)
    noisy_obs[3] += np.random.normal(0, angle_noise_std)  # phi (横滚角)
    
    # 速度计噪声：±0.15 m/s
    vel_noise_std = 0.05 * opt.noise_scale_vel
    for i in range(4, 8):  # u, v, p, r
        noisy_obs[i] += np.random.normal(0, vel_noise_std)
    
    # 帆角和舵角 [8-9] - 不添加噪声（假设为精确控制量）
    
    # 距离测量噪声：±2.0米（雷达/声呐精度）
    dist_noise_std = 2.0 * opt.noise_scale_dist
    noisy_obs[10] += np.random.normal(0, dist_noise_std)
    noisy_obs[11] += np.random.normal(0, dist_noise_std)
    
    # 目标位置 [12-13] - 不添加噪声（假设为已知目标）
    
    # 障碍物位置噪声：±2.0米（视觉/雷达检测精度）
    obstacle_noise_std = 2.0 * opt.noise_scale_pos
    for i in range(14, 18):
        if noisy_obs[i] != 0.0:
            noisy_obs[i] += np.random.normal(0, obstacle_noise_std)
    
    return noisy_obs

# 环境初始化
s, info = env.reset()

# 初始化：为初始状态添加噪声
if opt.add_sensor_noise:
    s = add_fixed_random_noise(s, opt)  # 使用固定随机噪声
    
# 初始化前一步的状态和动作（用于LSTM输入）
prev_state = s.copy()  # 现在是带噪声的初始状态
prev_action = np.zeros(opt.action_dim)

# 为测试环境分配一个唯一的环境ID，并重置隐藏状态
test_env_id = "test_env"
agent.actor.reset_hidden_state(test_env_id)

# 存储数据的列表
steps = []
actions = []
observations = []
noisy_observations = []
wind_changes_v = []
wind_changes_d = []
obstacle_1_x_list = []
obstacle_1_y_list = []
obstacle_2_x_list = []
obstacle_2_y_list = []
obstacle_1_level_list = []
obstacle_2_level_list = []
rewards = []

step = 0
total_scores = 0
done = False

print("开始测试模型...")
print(f"初始状态 (带噪声): {s}")
if opt.add_sensor_noise:
    print(f"固定随机噪声传感器模型已启用:")
    print(f"  GPS位置精度: ±{1.5 * opt.noise_scale_pos:.2f}米")
    print(f"  罗盘/陀螺仪精度: ±{0.8 * opt.noise_scale_angle:.2f}度")
    print(f"  速度计精度: ±{0.15 * opt.noise_scale_vel:.3f} m/s")
    print(f"  距离测量精度: ±{2.0 * opt.noise_scale_dist:.2f}米")
    print(f"  障碍物检测精度: ±{2.0 * opt.noise_scale_pos:.2f}米")
    print(f"  注意: 帆角、舵角和目标位置不添加噪声")
else:
    print("传感器噪声未启用")
print("-" * 50)

while not done and step < opt.max_e_steps:
    # 注意：现在 s 已经是带噪声的状态了
    s_noisy = s  # 直接使用（已经带噪声）
    
    # 使用带噪声的状态进行决策
    a = agent.select_action(prev_state, prev_action, s_noisy, deterministic=True, 
                           total_steps=None, env_id=test_env_id)
    
    # 转换动作到环境范围
    act = Action_adapter(a, opt.max_action)
    
    # 执行动作，获得下一时刻的状态（环境的真实状态）
    s_next, r, dw, tr, info = env.step(act)
    
    # 为下一状态添加噪声（智能体观测到的下一状态）
    if opt.add_sensor_noise:
        s_next_noisy = add_fixed_random_noise(s_next, opt)
    else:
        s_next_noisy = s_next.copy()
    
    # 收集数据
    steps.append(step)
    actions.append(act.copy())
    observations.append(s_next.copy())  # 保存真实观测（用于分析）
    noisy_observations.append(s_next_noisy.copy())  # 保存带噪声的观测
    rewards.append(r)
    
    # 收集风变化数据
    try:
        wind_changes_v.append(globals.w_change_v)
        wind_changes_d.append(globals.w_change_d)
    except AttributeError:
        wind_changes_v.append(0.0)
        wind_changes_d.append(0.0)
    
    # 收集障碍物坐标
    try:
        o1 = globals.obstacle_1
    except AttributeError:
        o1 = None
    try:
        o2 = globals.obstacle_2
    except AttributeError:
        o2 = None

    def _to_coords(o):
        if o is None:
            return [np.nan, np.nan]
        try:
            arr = np.array(o, dtype=float)
        except Exception:
            return [np.nan, np.nan]
        if arr.size == 1:
            return [float(arr.item()), np.nan]
        else:
            return [float(arr.flat[0]), float(arr.flat[1])]

    o1x, o1y = _to_coords(o1)
    o2x, o2y = _to_coords(o2)
    obstacle_1_x_list.append(o1x)
    obstacle_1_y_list.append(o1y)
    obstacle_2_x_list.append(o2x)
    obstacle_2_y_list.append(o2y)

    # 收集障碍物 level
    try:
        o1_level = globals.obstacle1_level
    except AttributeError:
        o1_level = 0
    obstacle_1_level_list.append(o1_level)
    
    try:
        o2_level = globals.obstacle2_level
    except AttributeError:
        o2_level = 0
    obstacle_2_level_list.append(o2_level)

    # 输出当前步信息
    print(f"Step: {step}")
    print(f"Previous State (noisy): {prev_state}")
    print(f"Previous Action: {prev_action}")
    print(f"Current State (noisy): {s_noisy}")
    print(f"Current State (true): {s_next if step > 0 else 'N/A'}")  # 当前真实状态在上一步已经获得
    print(f"Selected Action: {a}")
    print(f"Environment Action: {act}")
    print(f"Next State (true): {s_next}")
    print(f"Next State (noisy): {s_next_noisy}")
    if opt.add_sensor_noise:
        noise_diff = s_next_noisy - s_next
        print(f"Noise difference: pos=({noise_diff[0]:.3f}, {noise_diff[1]:.3f}), "
              f"angles=({np.rad2deg(noise_diff[2]):.2f}°, {np.rad2deg(noise_diff[3]):.2f}°), "
              f"vel=({noise_diff[4]:.3f}, {noise_diff[5]:.3f})")
    print(f"Reward: {r}")
    print(f"Terminated: {dw}")
    print(f"Truncated: {tr}")
    print("-" * 50)
    
    # 检查是否结束
    done = (dw or tr)
    
    # ========== 关键修改：使用已经计算好的带噪声状态 ==========
    prev_state = s_noisy.copy()  # 当前的带噪声观测成为下一步的prev_state
    prev_action = a.copy()
    s = s_next_noisy.copy()  # 下一个带噪声观测成为下一轮的当前状态
    
    step += 1
    total_scores += r
    
    print(f"累计步数: {step}, 累计奖励: {total_scores:.2f}")

print(f"\n测试完成!")
print(f"总步数: {step}")
print(f"总奖励: {total_scores:.2f}")
print(f"平均奖励: {total_scores/step:.2f}")

# 数据保存部分
desktop_path = 'C:\\Users\\24809\\Desktop\\'

# 转换为numpy数组
observations_array = np.array(observations)
actions_array = np.array(actions)
steps_array = np.array(steps)
rewards_array = np.array(rewards)

# 创建带风向角度和噪声标识的文件名后缀
if opt.add_sensor_noise:
    file_suffix = f"_obstmodel_lstm_wind{opt.wind_angle}deg_fixed_noise"
else:
    file_suffix = f"_obstmodel_lstm_wind{opt.wind_angle}deg_no_noise"

# 保存数据
try:
    np.savetxt(desktop_path + f'actions{file_suffix}.txt', actions_array, delimiter=',', 
               header='Action_Sail,Action_Rudder', comments='')
    print("动作数据已保存")
    
    np.savetxt(desktop_path + f'observations{file_suffix}.txt', observations_array, delimiter=',', 
               header=','.join([f'Observation_{i}' for i in range(observations_array.shape[1])]), comments='')
    print("观测数据已保存（真实值）")
    
    # 如果启用了噪声，也保存带噪声的观测
    if opt.add_sensor_noise and len(noisy_observations) > 0:
        noisy_observations_array = np.array(noisy_observations)
        np.savetxt(desktop_path + f'observations_noisy{file_suffix}.txt', noisy_observations_array, delimiter=',', 
                   header=','.join([f'Observation_{i}' for i in range(noisy_observations_array.shape[1])]), comments='')
        print("观测数据已保存（带噪声）")
    
    np.savetxt(desktop_path + f'rewards{file_suffix}.txt', rewards_array, delimiter=',', 
               header='Reward', comments='')
    print("奖励数据已保存")
    
    if len(wind_changes_v) > 0:
        arr_v = np.array(wind_changes_v, dtype=float)
        arr_d = np.array(wind_changes_d, dtype=float)
        o1x = np.array(obstacle_1_x_list, dtype=float)
        o1y = np.array(obstacle_1_y_list, dtype=float)
        o2x = np.array(obstacle_2_x_list, dtype=float)
        o2y = np.array(obstacle_2_y_list, dtype=float)
        combined = np.column_stack((arr_v, arr_d, o1x, o1y, o2x, o2y))
        np.savetxt(desktop_path + f'wind_changes{file_suffix}.txt',
                    combined, delimiter=',',
                    header='Wind_Change_V,Wind_Change_D,Ob1_X,Ob1_Y,Ob2_X,Ob2_Y', fmt='%.6f', comments='')
        print("风变化及障碍物数据已保存")
    
except Exception as e:
    print(f"保存数据时出错: {e}")

# 绘图部分
try:
    if observations_array.shape[1] >= 11:
        # 配置中文字体支持
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False
        
        x = observations_array[:, 0]
        y = observations_array[:, 1]
        
        # 手动输入风向角度
        try:
            wind_direction_input = input("\n请输入风向角度 (0-360度，直接回车使用命令行参数值): ").strip()
            if wind_direction_input:
                wind_direction = float(wind_direction_input)
                print(f"使用输入的风向角度: {wind_direction}°")
            else:
                wind_direction = opt.wind_angle
                print(f"使用命令行参数的风向角度: {wind_direction}°")
        except ValueError:
            print("输入无效，使用命令行参数的风向角度")
            wind_direction = opt.wind_angle
        except Exception:
            wind_direction = opt.wind_angle
        
        # ========== 窗口1: 轨迹图、帆角图、舵角图 ==========
        fig1 = plt.figure(figsize=(20, 12))
        import matplotlib.gridspec as gridspec
        gs1 = gridspec.GridSpec(2, 3, figure=fig1, hspace=0.3, wspace=0.3)
        
        # 子图1: 轨迹图
        ax1 = fig1.add_subplot(gs1[:, 0:2])
        ax1.plot(x, y, marker='o', linestyle='-', color='b', markersize=3, label='智能体轨迹')
        
        # 绘制起点和终点
        ax1.plot(x[0], y[0], marker='s', color='green', markersize=12, label='起点', zorder=5)
        ax1.plot(x[-1], y[-1], marker='^', color='red', markersize=12, label='终点', zorder=5)
        
        # 标题添加噪声信息
        title_text = '智能体运动轨迹'
        if opt.add_sensor_noise:
            title_text += ' (固定随机噪声)'
        ax1.set_title(title_text, fontsize=14, fontweight='bold')
        ax1.set_xlabel('X 坐标', fontsize=12)
        ax1.set_ylabel('Y 坐标', fontsize=12)
        ax1.grid(True, alpha=0.3)
        ax1.set_aspect('equal', adjustable='box')

        def _unique_valid_points(raw_points):
            pts = []
            for p in raw_points:
                try:
                    arr = np.array(p, dtype=float).flatten()
                except Exception:
                    continue
                if arr.size < 2:
                    continue
                x, y = float(arr[0]), float(arr[1])
                if np.isnan(x) or np.isnan(y):
                    continue
                if abs(x) < 1e-9 and abs(y) < 1e-9:
                    continue
                pts.append((x, y))
            dedup = {}
            for px, py in pts:
                key = (round(px, 6), round(py, 6))
                dedup[key] = (px, py)
            return list(dedup.values())

        all_obstacles = _unique_valid_points(getattr(globals, "obstacles", []))
        observed_points = _unique_valid_points(getattr(globals, "observed_obstacles", []))

        existing_keys = {(round(px, 6), round(py, 6)) for px, py in all_obstacles}
        for px, py in observed_points:
            key = (round(px, 6), round(py, 6))
            if key not in existing_keys:
                all_obstacles.append((px, py))
                existing_keys.add(key)

        observed_keys = {(round(px, 6), round(py, 6)) for px, py in observed_points}
        legend_flags = {"obstacle": False, "observed": False, "danger_50": False, "avoid_100": False}

        for cx, cy in all_obstacles:
            label = "障碍物" if not legend_flags["obstacle"] else None
            if label:
                legend_flags["obstacle"] = True
            ax1.plot(cx, cy, 'ro', markersize=6, label=label)
            
            # 40m危险半径圈
            if not legend_flags["danger_50"]:
                circ_50 = Circle((cx, cy), radius=40.0, edgecolor='red', facecolor='none',
                                linestyle='-', linewidth=1.5, alpha=0.8, label='危险半径 (40m)')
                legend_flags["danger_50"] = True
            else:
                circ_50 = Circle((cx, cy), radius=40.0, edgecolor='red', facecolor='none',
                                linestyle='-', linewidth=1.5, alpha=0.8)
            ax1.add_patch(circ_50)
            
            # 100m避障半径圈
            if not legend_flags["avoid_100"]:
                circ_100 = Circle((cx, cy), radius=100.0, edgecolor='orange', facecolor='none',
                                 linestyle='--', linewidth=1.5, alpha=0.8, label='避障半径 (100m)')
                legend_flags["avoid_100"] = True
            else:
                circ_100 = Circle((cx, cy), radius=100.0, edgecolor='orange', facecolor='none',
                                 linestyle='--', linewidth=1.5, alpha=0.8)
            ax1.add_patch(circ_100)
            
            if (round(cx, 6), round(cy, 6)) in observed_keys:
                obs_label = "已观测障碍物" if not legend_flags["observed"] else None
                if obs_label:
                    legend_flags["observed"] = True
                ax1.plot(cx, cy, marker='*', color='gold', markersize=10, label=obs_label)

        # 绘制风向标
        xlim = ax1.get_xlim()
        ylim = ax1.get_ylim()
        compass_x = xlim[0] + (xlim[1] - xlim[0]) * 0.1
        compass_y = ylim[1] - (ylim[1] - ylim[0]) * 0.1
        compass_radius = (xlim[1] - xlim[0]) * 0.04
        compass_circle = Circle((compass_x, compass_y), radius=compass_radius, 
                               edgecolor='black', facecolor='white', linewidth=2, alpha=0.9, zorder=10)
        ax1.add_patch(compass_circle)
        
        wind_rad = np.deg2rad(wind_direction)
        arrow_length = compass_radius * 0.7
        dx = arrow_length * np.cos(wind_rad)
        dy = arrow_length * np.sin(wind_rad)
        
        ax1.arrow(compass_x, compass_y, dx, dy,
                 head_width=compass_radius*0.4, head_length=compass_radius*0.35,
                 fc='#1E90FF', ec='navy', linewidth=2, alpha=1,
                 length_includes_head=True, zorder=11)
        
        ax1.text(compass_x, compass_y + compass_radius * 1.5, '风向',
                ha='center', va='bottom', fontsize=14, fontweight='bold',
                color='black')

        ax1.legend(fontsize=10, loc='upper right')

        # 子图2: 帆角变化
        ax2 = fig1.add_subplot(gs1[0, 2])
        sail_angle = np.rad2deg(observations_array[:, 8])
        ax2.plot(steps_array, sail_angle, color='g', linewidth=1.5)
        ax2.set_title('帆角变化', fontsize=12, fontweight='bold')
        ax2.set_xlabel('步数', fontsize=10)
        ax2.set_ylabel('角度 (度)', fontsize=10)
        ax2.grid(True, alpha=0.3)
        
        # 子图3: 舵角变化
        ax3 = fig1.add_subplot(gs1[1, 2])
        rudder_angle = np.rad2deg(observations_array[:, 9])
        ax3.plot(steps_array, rudder_angle, color='orange', linewidth=1.5)
        ax3.set_title('舵角变化', fontsize=12, fontweight='bold')
        ax3.set_xlabel('步数', fontsize=10)
        ax3.set_ylabel('角度 (度)', fontsize=10)
        ax3.grid(True, alpha=0.3)
        
        plt.savefig(desktop_path + f'model_test_trajectory_angles{file_suffix}.png', dpi=300, bbox_inches='tight')
        
        # ========== 窗口2: 时刻奖励和累计奖励 ==========
        fig2 = plt.figure(figsize=(12, 10))
        gs2 = gridspec.GridSpec(2, 1, figure=fig2, hspace=0.3)
        
        # 子图1: 瞬时奖励
        ax4 = fig2.add_subplot(gs2[0, 0])
        ax4.plot(steps_array, rewards_array, color='r', linewidth=1.5)
        ax4.set_title('瞬时奖励', fontsize=14, fontweight='bold')
        ax4.set_xlabel('步数', fontsize=12)
        ax4.set_ylabel('奖励', fontsize=12)
        ax4.grid(True, alpha=0.3)
        
        # 子图2: 累计奖励
        ax5 = fig2.add_subplot(gs2[1, 0])
        cumulative_rewards = np.cumsum(rewards_array)
        ax5.plot(steps_array, cumulative_rewards, color='purple', linewidth=1.5)
        ax5.set_title('累计奖励', fontsize=14, fontweight='bold')
        ax5.set_xlabel('步数', fontsize=12)
        ax5.set_ylabel('累计奖励', fontsize=12)
        ax5.grid(True, alpha=0.3)
        
        plt.savefig(desktop_path + f'model_test_rewards{file_suffix}.png', dpi=300, bbox_inches='tight')
        
        plt.show()
        print("图表已保存并显示")
    else:
        print(f"观测数据维度不足（当前维度: {observations_array.shape[1]}），需要至少11个维度")
        
except Exception as e:
    print(f"绘图时出错: {e}")
    import traceback
    traceback.print_exc()

# 关闭环境
env.close()
print("测试完成，环境已关闭")