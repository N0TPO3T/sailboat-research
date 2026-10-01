"""
带噪声的SAC-LSTM模型测试脚本
整合传感器噪声和执行器噪声，模拟真实测试环境
"""

from utils_lstm_att_normal import str2bool, evaluate_policy, Action_adapter, Action_adapter_reverse, Reward_adapter
from noise_utils import NoiseManager  # 噪声模块导入
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
from matplotlib.patches import FancyArrowPatch, Circle
import json


FONT_SCALE = 1.5


def setup_chinese_font() -> None:
    plt.rcParams["font.family"] = "SimSun"
    plt.rcParams["font.sans-serif"] = [
        "SimSun",
        "NSimSun",
        "Songti SC",
        "STSong",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.weight"] = "bold"
    plt.rcParams["axes.titleweight"] = "bold"
    plt.rcParams["axes.labelweight"] = "bold"


def draw_wind_indicator(ax: plt.Axes, wind_dir_rad: float, hint_fs: float) -> None:
    inset = ax.inset_axes([0.03, 0.77, 0.18, 0.18])
    inset.set_aspect("equal")
    inset.set_xlim(-1.5, 1.5)
    inset.set_ylim(-1.5, 1.5)
    inset.axis("off")

    circle_r = 0.78
    circle = plt.Circle((0, 0), circle_r, fill=False, linewidth=1.2, color="#7f8c8d")
    inset.add_patch(circle)

    dir_x = np.cos(wind_dir_rad)
    dir_y = np.sin(wind_dir_rad)
    arrow = FancyArrowPatch(
        (0, 0),
        (0.66 * dir_x, 0.66 * dir_y),
        arrowstyle="-|>",
        mutation_scale=16,
        linewidth=3.2,
        color="black",
    )
    inset.add_patch(arrow)

    inset.text(
        0,
        -1.42,
        "风向",
        ha="center",
        va="top",
        fontsize=hint_fs,
        fontweight="bold",
        color="black",
        bbox=dict(boxstyle="round,pad=0.10", facecolor="white", edgecolor="none", alpha=0.90),
        clip_on=False,
    )

# 定义命令行参数
parser = argparse.ArgumentParser()
parser.add_argument('--dvc', type=str, default='cpu', help='running device: cuda or cpu')
parser.add_argument('--EnvIdex', type=int, default=0, help='PV1, Lch_Cv2, Humanv4, HCv4, BWv3, BWHv3')
parser.add_argument('--write', type=str2bool, default=True, help='Use SummaryWriter to record the training')
parser.add_argument('--render', type=str2bool, default=False, help='Render or Not')
parser.add_argument('--Loadmodel', type=str2bool, default=True, help='Load pretrained model or Not')
parser.add_argument('--ModelIdex', type=int, default=10800, help='which model to load')
parser.add_argument('--wind_angle', type=int, default=0, help='Wind direction angle in degrees (0-360)')

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

# ========== 噪声相关参数 ==========
parser.add_argument('--enable_sensor_noise', type=str2bool, default=True, help='Enable sensor noise')
parser.add_argument('--enable_actuator_noise', type=str2bool, default=True, help='Enable actuator noise')
parser.add_argument('--sensor_noise_ratio', type=float, default=0.03, help='Sensor noise ratio (default 3%)')
parser.add_argument('--actuator_noise_ratio', type=float, default=0.03, help='Actuator noise ratio (default 3%)')
# =================================

opt = parser.parse_args()
opt.dvc = torch.device(opt.dvc)

# 定义环境名称
EnvName = ['sailboat-s14-obst-v3']
BrifEnvName = ['saclstm_s14obst_noise_0204']  # 修改为正确的模型名称
# BrifEnvName = ['saclstm_s14obst_v3_0126_20']

# 创建环境
env = gym.make(EnvName[opt.EnvIdex])
env.reset(seed=opt.seed)
opt.state_dim = env.observation_space.shape[0]
opt.action_dim = env.action_space.shape[0]
opt.max_action = env.action_space.high.astype(float)
opt.max_e_steps = 1000

# ========== 初始化噪声管理器 ==========
noise_manager = NoiseManager(
    sensor_noise_ratio=opt.sensor_noise_ratio,
    actuator_noise_ratio=opt.actuator_noise_ratio,
    enable_sensor_noise=opt.enable_sensor_noise,
    enable_actuator_noise=opt.enable_actuator_noise,
    seed=opt.seed
)
print(f'噪声配置: 传感器噪声={opt.enable_sensor_noise}({opt.sensor_noise_ratio*100}%), '
      f'执行器噪声={opt.enable_actuator_noise}({opt.actuator_noise_ratio*100}%)')
# =====================================

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
s_raw, info = env.reset()

# ========== 对初始状态添加传感器噪声 ==========
s = noise_manager.add_observation_noise(s_raw)
# =============================================

# 初始化前一步的状态和动作（用于LSTM输入）
prev_state = s.copy()
prev_action = np.zeros(opt.action_dim)  # 初始前一动作为0

# 为测试环境分配一个唯一的环境ID，并重置隐藏状态
test_env_id = "test_env"
agent.actor.reset_hidden_state(test_env_id)

# 存储数据的列表
steps = []
actions = []
actions_noisy = []  # 新增：带噪声的动作
observations = []
observations_noisy = []  # 新增：带噪声的观测
wind_changes_v = []
wind_changes_d = []
# 与风场数据同样保存的障碍物坐标（数值列：X,Y）
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

print("开始测试模型（带噪声）...")
print(f"初始真实状态: {s_raw}")
print(f"初始带噪声状态: {s}")
print("-" * 50)

while not done and step < opt.max_e_steps:
    # 使用带噪声的状态进行决策（模拟真实传感器输入）
    a = agent.select_action(prev_state, prev_action, s, deterministic=True, 
                           total_steps=None, env_id=test_env_id)
    
    # ========== 添加执行器噪声 ==========
    a_noisy = noise_manager.add_action_noise(a, opt.max_action)
    # ===================================
    
    # 转换带噪声的动作到环境范围
    act = Action_adapter(a_noisy, opt.max_action)
    
    # 执行动作，获得下一时刻的状态（真实状态）
    s_next_raw, r, dw, tr, info = env.step(act)
    
    # ========== 对下一状态添加传感器噪声 ==========
    s_next = noise_manager.add_observation_noise(s_next_raw)
    # =============================================
    
    # 收集数据
    steps.append(step)
    actions.append(Action_adapter(a, opt.max_action).copy())  # 原始动作（转换后）
    actions_noisy.append(act.copy())  # 带噪声的动作（转换后）
    observations.append(s_next_raw.copy())  # 真实观测
    observations_noisy.append(s_next.copy())  # 带噪声观测
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
    print(f"Previous State (noisy): {prev_state}")
    print(f"Previous Action: {prev_action}")
    print(f"Current State (noisy): {s}")
    print(f"Selected Action (raw): {a}")
    print(f"Selected Action (noisy): {a_noisy}")
    print(f"Environment Action: {act}")
    print(f"Next State (raw): {s_next_raw}")
    print(f"Next State (noisy): {s_next}")
    print(f"Reward: {r}")
    print(f"Terminated: {dw}")
    print(f"Truncated: {tr}")
    print(f"Info: {info}")
    print("-" * 50)
    
    # 检查是否结束
    done = (dw or tr)
    
    # 更新前一步状态和动作（使用带噪声的状态，与训练时保持一致）
    prev_state = s.copy()
    prev_action = a.copy()  # 使用原始动作（不带噪声）
    s = s_next  # 使用带噪声的状态
    
    step += 1
    total_scores += r
    
    print(f"累计步数: {step}, 累计奖励: {total_scores:.2f}")

print(f"\n测试完成!")
print(f"总步数: {step}")
print(f"总奖励: {total_scores:.2f}")
print(f"平均奖励: {total_scores/step:.2f}")

# ========== 数据保存部分 ==========
# 创建输出文件夹
desktop_path = 'C:\\Users\\24809\\Desktop\\'
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
noise_suffix = f"_sensor{int(opt.sensor_noise_ratio*100)}_act{int(opt.actuator_noise_ratio*100)}"
output_folder = f"model_test_results_{timestamp}_wind{opt.wind_angle}deg{noise_suffix}"
output_path = os.path.join(desktop_path, output_folder)

# 创建文件夹
if not os.path.exists(output_path):
    os.makedirs(output_path)
    print(f"创建输出文件夹: {output_path}")

# 转换为numpy数组
observations_array = np.array(observations)  # 真实观测
observations_noisy_array = np.array(observations_noisy)  # 带噪声观测
actions_array = np.array(actions)  # 原始动作
actions_noisy_array = np.array(actions_noisy)  # 带噪声动作
steps_array = np.array(steps)
rewards_array = np.array(rewards)

# 创建带风向角度的文件名后缀
file_suffix = f"_obstmodel_lstm_wind{opt.wind_angle}deg_speed_10"

# 保存数据
try:
    # 原始动作
    np.savetxt(os.path.join(output_path, f'actions{file_suffix}.txt'), actions_array, delimiter=',', 
               header='Action_Sail,Action_Rudder', comments='')
    print("原始动作数据已保存")
    
    # 带噪声动作
    np.savetxt(os.path.join(output_path, f'actions_noisy{file_suffix}.txt'), actions_noisy_array, delimiter=',', 
               header='Action_Sail_Noisy,Action_Rudder_Noisy', comments='')
    print("带噪声动作数据已保存")
    
    # 真实观测
    np.savetxt(os.path.join(output_path, f'observations{file_suffix}.txt'), observations_array, delimiter=',', 
               header=','.join([f'Observation_{i}' for i in range(observations_array.shape[1])]), comments='')
    print("真实观测数据已保存")
    
    # 带噪声观测
    np.savetxt(os.path.join(output_path, f'observations_noisy{file_suffix}.txt'), observations_noisy_array, delimiter=',', 
               header=','.join([f'Observation_Noisy_{i}' for i in range(observations_noisy_array.shape[1])]), comments='')
    print("带噪声观测数据已保存")
    
    # 奖励
    np.savetxt(os.path.join(output_path, f'rewards{file_suffix}.txt'), rewards_array, delimiter=',', 
               header='Reward', comments='')
    print("奖励数据已保存")
    
    # 风变化及障碍物数据
    if len(wind_changes_v) > 0:
        arr_v = np.array(wind_changes_v, dtype=float)
        arr_d = np.array(wind_changes_d, dtype=float)
        o1x_arr = np.array(obstacle_1_x_list, dtype=float)
        o1y_arr = np.array(obstacle_1_y_list, dtype=float)
        o2x_arr = np.array(obstacle_2_x_list, dtype=float)
        o2y_arr = np.array(obstacle_2_y_list, dtype=float)
        combined = np.column_stack((arr_v, arr_d, o1x_arr, o1y_arr, o2x_arr, o2y_arr))
        np.savetxt(os.path.join(output_path, f'wind_changes{file_suffix}.txt'),
                    combined, delimiter=',',
                    header='Wind_Change_V,Wind_Change_D,Ob1_X,Ob1_Y,Ob2_X,Ob2_Y', fmt='%.6f', comments='')
        print("风变化及障碍物数据已保存")
    
    # 保存测试配置信息
    config_info = {
        'model_name': BrifEnvName[opt.EnvIdex],
        'model_index': opt.ModelIdex,
        'wind_angle': opt.wind_angle,
        'sensor_noise_enabled': opt.enable_sensor_noise,
        'sensor_noise_ratio': opt.sensor_noise_ratio,
        'actuator_noise_enabled': opt.enable_actuator_noise,
        'actuator_noise_ratio': opt.actuator_noise_ratio,
        'random_seed': opt.seed,
        'total_steps': step,
        'total_reward': total_scores,
        'average_reward': total_scores/step,
        'test_time': timestamp
    }
    with open(os.path.join(output_path, f'test_config{file_suffix}.json'), 'w', encoding='utf-8') as f:
        json.dump(config_info, f, indent=4, ensure_ascii=False)
    print("测试配置信息已保存")
    
except Exception as e:
    print(f"保存数据时出错: {e}")

# ========== 绘图部分 ==========
try:
    if observations_array.shape[1] >= 11:  # 确保有足够的观测维度
        setup_chinese_font()
        
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
        
        # ========== 总览图: 轨迹 + 帆角 + 舵角（参考 totalplot 布局） ==========
        fig_main = plt.figure(figsize=(19.5, 9), constrained_layout=True)
        gs = fig_main.add_gridspec(2, 2, width_ratios=[2.1, 1.0], height_ratios=[1, 1])

        ax_path = fig_main.add_subplot(gs[:, 0])
        ax_sail = fig_main.add_subplot(gs[0, 1])
        ax_rudder = fig_main.add_subplot(gs[1, 1])

        legend_font_size = 12 * FONT_SCALE
        legend_prop = {"family": "SimSun", "size": legend_font_size, "weight": "bold"}

        ax_path.plot(x, y, color="#1f77b4", linewidth=2.4, label="航行轨迹")
        ax_path.scatter(x[0], y[0], s=150, color="#2ca02c", marker="o", zorder=4, label="起点")
        ax_path.scatter(x[-1], y[-1], s=150, color="#d62728", marker="X", zorder=4, label="终点")
        if observations_array.shape[1] >= 14:
            target_x = float(observations_array[0, 12])
            target_y = float(observations_array[0, 13])
            ax_path.scatter(target_x, target_y, s=150, color="#ff7f0e", marker="*", zorder=4, label="目标点")

        ax_path.set_title("路径图", fontsize=15 * FONT_SCALE, pad=10, fontweight="bold")
        ax_path.set_xlabel("X 位置(米)", fontsize=12 * FONT_SCALE, fontweight="bold")
        ax_path.set_ylabel("Y 位置(米)", fontsize=12 * FONT_SCALE, fontweight="bold")
        ax_path.set_ylim(-350, 450)
        ax_path.set_xlim(-100, 600)
        ax_path.grid(True, linestyle="--", alpha=0.35)
        ax_path.set_aspect("equal", adjustable="box")

        def _unique_valid_points(raw_points):
            pts = []
            for p in raw_points:
                try:
                    arr = np.array(p, dtype=float).flatten()
                except Exception:
                    continue
                if arr.size < 2:
                    continue
                x_coord, y_coord = float(arr[0]), float(arr[1])
                if np.isnan(x_coord) or np.isnan(y_coord):
                    continue
                if abs(x_coord) < 1e-9 and abs(y_coord) < 1e-9:
                    continue
                pts.append((x_coord, y_coord))
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
        legend_flags = {"obstacle": False, "observed": False, "danger_40": False}

        for cx, cy in all_obstacles:
            label = "障碍物" if not legend_flags["obstacle"] else None
            if label:
                legend_flags["obstacle"] = True
            ax_path.plot(cx, cy, 'ro', markersize=10, label=label)

            # 40m 最小安全距离圈（保留）
            if not legend_flags["danger_40"]:
                circ_40 = Circle(
                    (cx, cy),
                    radius=40.0,
                    edgecolor='red',
                    facecolor='none',
                    linestyle='-',
                    linewidth=2.5,
                    alpha=0.8,
                    label='最小安全距离 (40m)',
                )
                legend_flags["danger_40"] = True
            else:
                circ_40 = Circle(
                    (cx, cy),
                    radius=40.0,
                    edgecolor='red',
                    facecolor='none',
                    linestyle='-',
                    linewidth=2.5,
                    alpha=0.8,
                )
            ax_path.add_patch(circ_40)
            
            if (round(cx, 6), round(cy, 6)) in observed_keys:
                obs_label = "已观测障碍物" if not legend_flags["observed"] else None
                if obs_label:
                    legend_flags["observed"] = True
                ax_path.plot(cx, cy, marker='*', color='gold', markersize=16, label=obs_label)

        draw_wind_indicator(ax_path, np.deg2rad(wind_direction), hint_fs=legend_font_size)
        ax_path.legend(loc="best", prop=legend_prop, frameon=True)

        sail_angle = np.rad2deg(observations_array[:, 8])
        ax_sail.plot(steps_array, sail_angle, color="#9467bd", linewidth=2.0, label="帆角（实际）")
        ax_sail.set_title("帆角变化", fontsize=14 * FONT_SCALE, pad=8, fontweight="bold")
        ax_sail.set_xlabel("时间步", fontsize=12 * FONT_SCALE, fontweight="bold")
        ax_sail.set_ylabel("角度(度)", fontsize=12 * FONT_SCALE, fontweight="bold")
        ax_sail.set_ylim(-95, 95)
        ax_sail.grid(True, linestyle="--", alpha=0.35)
        ax_sail.legend(loc="best", prop=legend_prop, frameon=True)

        rudder_angle = np.rad2deg(observations_array[:, 9])
        ax_rudder.plot(steps_array, rudder_angle, color="#8c564b", linewidth=2.0, label="舵角（实际）")
        ax_rudder.set_title("舵角变化", fontsize=14 * FONT_SCALE, pad=8, fontweight="bold")
        ax_rudder.set_xlabel("时间步", fontsize=12 * FONT_SCALE, fontweight="bold")
        ax_rudder.set_ylabel("角度(度)", fontsize=12 * FONT_SCALE, fontweight="bold")
        ax_rudder.set_ylim(-35, 35)
        ax_rudder.grid(True, linestyle="--", alpha=0.35)
        ax_rudder.legend(loc="best", prop=legend_prop, frameon=True)

        for ax in (ax_path, ax_sail, ax_rudder):
            ax.tick_params(axis="both", labelsize=11 * FONT_SCALE)
            for label in ax.get_xticklabels() + ax.get_yticklabels():
                label.set_fontweight("bold")

        plt.savefig(
            os.path.join(output_path, f'model_test_overview{file_suffix}.jpg'),
            format='jpg',
            dpi=600,
            bbox_inches='tight',
            pil_kwargs={'quality': 95},
        )
        print("总览图（路径+帆角+舵角）已保存")
        
        # ========== 窗口4: 风速变化 ==========
        fig4 = plt.figure(figsize=(14, 8))
        ax4 = fig4.add_subplot(111)
        wind_v_array = np.array(wind_changes_v)
        ax4.plot(steps_array, wind_v_array, color='#1E90FF', linewidth=3)
        ax4.set_title('风速变化', fontsize=24, fontweight='bold', pad=20)
        ax4.set_xlabel('时间(s)', fontsize=24, fontweight='bold')
        ax4.set_ylabel('风速(m/s)', fontsize=24, fontweight='bold')
        ax4.tick_params(axis='both', which='major', labelsize=20)
        ax4.grid(True, alpha=0.3, linewidth=1.2)
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_path, f'model_test_wind_speed{file_suffix}.png'), dpi=300, bbox_inches='tight')
        print("风速图已保存")
        
        # ========== 窗口5: 风向变化 ==========
        fig5 = plt.figure(figsize=(14, 8))
        ax5 = fig5.add_subplot(111)
        wind_d_array = np.array(wind_changes_d)
        wind_d_deg = np.rad2deg(wind_d_array) if np.max(np.abs(wind_d_array)) <= 2*np.pi else wind_d_array
        ax5.plot(steps_array, wind_d_deg, color='purple', linewidth=3)
        ax5.set_title('风向变化', fontsize=24, fontweight='bold', pad=20)
        ax5.set_xlabel('时间(s)', fontsize=24, fontweight='bold')
        ax5.set_ylabel('风向角度(度)', fontsize=24, fontweight='bold')
        ax5.tick_params(axis='both', which='major', labelsize=20)
        ax5.grid(True, alpha=0.3, linewidth=1.2)
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_path, f'model_test_wind_direction{file_suffix}.png'), dpi=300, bbox_inches='tight')
        print("风向图已保存")
        
        # ========== 窗口6: 动作对比（新增） ==========
        fig6 = plt.figure(figsize=(14, 10))
        
        # 帆角动作对比
        ax6_1 = fig6.add_subplot(211)
        ax6_1.plot(steps_array, np.rad2deg(actions_array[:, 0]), color='g', linewidth=2, label='原始帆角动作')
        ax6_1.plot(steps_array, np.rad2deg(actions_noisy_array[:, 0]), color='lime', linewidth=2, linestyle='--', label='带噪声帆角动作')
        ax6_1.set_title('帆角动作对比（原始 vs 带噪声）', fontsize=20, fontweight='bold', pad=15)
        ax6_1.set_xlabel('时间(s)', fontsize=18, fontweight='bold')
        ax6_1.set_ylabel('动作角度(度)', fontsize=18, fontweight='bold')
        ax6_1.tick_params(axis='both', which='major', labelsize=16)
        ax6_1.grid(True, alpha=0.3, linewidth=1.2)
        ax6_1.legend(fontsize=14, loc='upper right')
        
        # 舵角动作对比
        ax6_2 = fig6.add_subplot(212)
        ax6_2.plot(steps_array, np.rad2deg(actions_array[:, 1]), color='orange', linewidth=2, label='原始舵角动作')
        ax6_2.plot(steps_array, np.rad2deg(actions_noisy_array[:, 1]), color='gold', linewidth=2, linestyle='--', label='带噪声舵角动作')
        ax6_2.set_title('舵角动作对比（原始 vs 带噪声）', fontsize=20, fontweight='bold', pad=15)
        ax6_2.set_xlabel('时间(s)', fontsize=18, fontweight='bold')
        ax6_2.set_ylabel('动作角度(度)', fontsize=18, fontweight='bold')
        ax6_2.tick_params(axis='both', which='major', labelsize=16)
        ax6_2.grid(True, alpha=0.3, linewidth=1.2)
        ax6_2.legend(fontsize=14, loc='upper right')
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_path, f'model_test_action_comparison{file_suffix}.png'), dpi=300, bbox_inches='tight')
        print("动作对比图已保存")
        
        plt.show()
        print("所有图表已保存并显示")
        print(f"\n所有输出文件保存在: {output_path}")
    else:
        print(f"观测数据维度不足（当前维度: {observations_array.shape[1]}），需要至少11个维度")
        
except Exception as e:
    print(f"绘图时出错: {e}")
    import traceback
    traceback.print_exc()

# 关闭环境
env.close()
print("测试完成，环境已关闭")