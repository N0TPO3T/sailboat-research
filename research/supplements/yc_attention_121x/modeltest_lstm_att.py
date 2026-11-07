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
parser.add_argument('--ModelIdex', type=int, default=12600, help='which model to load')
parser.add_argument('--wind_angle', type=int, default=5, help='Wind direction angle in degrees (0-360)')

parser.add_argument('--seed', type=int, default=0, help='random seed')
parser.add_argument('--Max_train_steps', type=int, default=int(9e6), help='Max training steps')
parser.add_argument('--save_interval', type=int, default=int(9e5), help='Model saving interval, in steps.')
parser.add_argument('--eval_interval', type=int, default=int(1e5), help='Model evaluating interval, in steps.')
parser.add_argument('--update_every', type=int, default=0, help='Training Fraquency, in stpes')

parser.add_argument('--gamma', type=float, default=0.98, help='Discounted Factor')
parser.add_argument('--net_width', type=int, default=256, help='Hidden net width, s_dim-400-300-a_dim')
parser.add_argument('--a_lr', type=float, default=1e-4, help='Learning rate of actor')
parser.add_argument('--c_lr', type=float, default=1e-4, help='Learning rate of critic')
parser.add_argument('--batch_size', type=int, default=256, help='batch_size of training')
parser.add_argument('--alpha', type=float, default=0.2, help='Entropy coefficient')
parser.add_argument('--adaptive_alpha', type=str2bool, default=True, help='Use adaptive_alpha or Not')
parser.add_argument('--num_envs', type=int, default=1, help='Number of parallel environments')

opt = parser.parse_args()
opt.dvc = torch.device(opt.dvc)

# 定义环境名称
EnvName = ['sailboat-s14-obst-v2']
BrifEnvName = ['saclstm_s14obst_1216']  # 修改为正确的模型名称

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
    f'./model/{BrifEnvName[opt.EnvIdex]}_q_critic{opt.ModelIdex}.pth',
    f'./model/{BrifEnvName[opt.EnvIdex]}_normalizer{opt.ModelIdex}.pth'
]

for model_file in model_files:
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

# 环境初始化
s, info = env.reset()

# 初始化前一步的状态和动作（用于LSTM输入）
prev_state = s.copy()
prev_action = np.zeros(opt.action_dim)  # 初始前一动作为0

# 为测试环境分配一个唯一的环境ID，并重置隐藏状态
test_env_id = "test_env"
agent.actor.reset_hidden_state(test_env_id)

# 存储数据的列表
steps = []
actions = []
observations = []
wind_changes_v = []
wind_changes_d = []
# 与风场数据同样保存的障碍物坐标（数值列：X,Y）
obstacle_1_x_list = []
obstacle_1_y_list = []
obstacle_2_x_list = []
obstacle_2_y_list = []
obstacle_1_level_list = []  # 新增
obstacle_2_level_list = []  # 新增
rewards = []

step = 0
total_scores = 0
done = False

print("开始测试模型...")
print(f"初始状态: {s}")
print("-" * 50)

while not done and step < opt.max_e_steps:
    # 直接使用真实状态进行决策
    a = agent.select_action(prev_state, prev_action, s, deterministic=True, 
                           total_steps=None, env_id=test_env_id)
    
    # 转换动作到环境范围
    act = Action_adapter(a, opt.max_action)
    
    # 执行动作，获得下一时刻的状态（真实状态）
    s_next, r, dw, tr, info = env.step(act)
    
    # 收集数据
    steps.append(step)
    actions.append(act.copy())
    observations.append(s_next.copy())
    rewards.append(r)
    
    # 收集风变化数据（如果全局变量存在）
    try:
        wind_changes_v.append(globals.w_change_v)
        wind_changes_d.append(globals.w_change_d)
    except AttributeError:
        # 如果全局变量不存在，使用默认值
        wind_changes_v.append(0.0)
        wind_changes_d.append(0.0)
    
    # 收集障碍物坐标（使用 globals.obstacle_1 和 globals.obstacle_2），按数值列保存（X, Y）
    try:
        o1 = globals.obstacle_1
    except AttributeError:
        o1 = None
    try:
        o2 = globals.obstacle_2
    except AttributeError:
        o2 = None

    def _to_coords(o):
        # 返回 [x, y] 两个浮点数；缺失用 np.nan 填充
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
    print(f"Previous State: {prev_state}")
    print(f"Previous Action: {prev_action}")
    print(f"Current State: {s}")
    print(f"Selected Action: {a}")
    print(f"Environment Action: {act}")
    print(f"Next State: {s_next}")
    print(f"Reward: {r}")
    print(f"Terminated: {dw}")
    print(f"Truncated: {tr}")
    print(f"Info: {info}")
    print("-" * 50)
    
    # 检查是否结束
    done = (dw or tr)
    
    # 更新前一步状态和动作（使用真实状态）
    prev_state = s.copy()
    prev_action = a.copy()
    s = s_next
    
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

# 创建带风向角度的文件名后缀
file_suffix = f"_obstmodel_lstm_wind{opt.wind_angle}deg_speed_10"

# 保存数据
try:
    np.savetxt(desktop_path + f'actions{file_suffix}.txt', actions_array, delimiter=',', 
               header='Action_Sail,Action_Rudder', comments='')
    print("动作数据已保存")
    
    np.savetxt(desktop_path + f'observations{file_suffix}.txt', observations_array, delimiter=',', 
               header=','.join([f'Observation_{i}' for i in range(observations_array.shape[1])]), comments='')
    print("观测数据已保存")
    
    np.savetxt(desktop_path + f'rewards{file_suffix}.txt', rewards_array, delimiter=',', 
               header='Reward', comments='')
    print("奖励数据已保存")
    
    if len(wind_changes_v) > 0:
        # 将风场数据与障碍物坐标一并保存（数值列）
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
    if observations_array.shape[1] >= 11:  # 确保有足够的观测维度
        # 配置中文字体支持
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']  # 用来正常显示中文标签
        plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号
        
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
        
        # 子图1: 轨迹图 - 占据左侧两行
        ax1 = fig1.add_subplot(gs1[:, 0:2])
        ax1.plot(x, y, marker='o', linestyle='-', color='b', markersize=3, label='智能体轨迹')
        
        # 绘制起点
        ax1.plot(x[0], y[0], marker='s', color='green', markersize=12, label='起点', zorder=5)
        
        # 绘制终点
        ax1.plot(x[-1], y[-1], marker='^', color='red', markersize=12, label='终点', zorder=5)
        
        # 标题
        ax1.set_title('智能体运动轨迹', fontsize=14, fontweight='bold')
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
        # 修改：只绘制50m和100m半径的圈
        legend_flags = {"obstacle": False, "observed": False, "danger_50": False, "avoid_100": False}

        for cx, cy in all_obstacles:
            label = "障碍物" if not legend_flags["obstacle"] else None
            if label:
                legend_flags["obstacle"] = True
            ax1.plot(cx, cy, 'ro', markersize=6, label=label)
            
            # 50m危险半径圈 - 实线
            if not legend_flags["danger_50"]:
                circ_50 = Circle((cx, cy), radius=40.0, edgecolor='red', facecolor='none',
                                linestyle='-', linewidth=1.5, alpha=0.8, label='危险半径 (40m)')
                legend_flags["danger_50"] = True
            else:
                circ_50 = Circle((cx, cy), radius=40.0, edgecolor='red', facecolor='none',
                                linestyle='-', linewidth=1.5, alpha=0.8)
            ax1.add_patch(circ_50)
            
            # 100m避障半径圈 - 虚线
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

        # 优化后的风向标绘制
        # 获取图的范围来确定风向标的位置
        xlim = ax1.get_xlim()
        ylim = ax1.get_ylim()
        
        # 将风向标放在图的左上角
        compass_x = xlim[0] + (xlim[1] - xlim[0]) * 0.1
        compass_y = ylim[1] - (ylim[1] - ylim[0]) * 0.1
        
        # 绘制指南针底盘（圆形）
        compass_radius = (xlim[1] - xlim[0]) * 0.04
        compass_circle = Circle((compass_x, compass_y), radius=compass_radius, 
                               edgecolor='black', facecolor='white', linewidth=2, alpha=0.9, zorder=10)
        ax1.add_patch(compass_circle)
        
        # 计算风向箭头方向
        wind_rad = np.deg2rad(wind_direction)
        arrow_length = compass_radius * 0.7
        dx = arrow_length * np.cos(wind_rad)
        dy = arrow_length * np.sin(wind_rad)
        
        # 绘制风向箭头（从中心指向风吹来的方向）
        ax1.arrow(compass_x, compass_y, dx, dy,
                 head_width=compass_radius*0.4, head_length=compass_radius*0.35,
                 fc='#1E90FF', ec='navy', linewidth=2, alpha=1,
                 length_includes_head=True, zorder=11)
        
        # 在指南针上方添加"风向"标签
        ax1.text(compass_x, compass_y + compass_radius * 1.5, '风向',
                ha='center', va='bottom', fontsize=14, fontweight='bold',
                color='black')

        ax1.legend(fontsize=10, loc='upper right')

        # 子图2: 帆角变化 - 右上
        ax2 = fig1.add_subplot(gs1[0, 2])
        # 从观测空间的8号元素获取帆角（弧度转角度）
        sail_angle = np.rad2deg(observations_array[:, 8])
        ax2.plot(steps_array, sail_angle, color='g', linewidth=1.5)
        ax2.set_title('帆角变化', fontsize=12, fontweight='bold')
        ax2.set_xlabel('步数', fontsize=10)
        ax2.set_ylabel('角度 (度)', fontsize=10)
        ax2.grid(True, alpha=0.3)
        
        # 子图3: 舵角变化 - 右下
        ax3 = fig1.add_subplot(gs1[1, 2])
        # 从观测空间的9号元素获取舵角（弧度转角度）
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
        
        # 子图1: 时刻奖励
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