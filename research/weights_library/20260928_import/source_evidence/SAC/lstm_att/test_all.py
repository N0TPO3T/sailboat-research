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

# ===== 新增：李雅普诺夫稳定性分析函数 =====
def analyze_lyapunov_stability(observations, target_position, steps_array, rewards_array):
    """
    李雅普诺夫稳定性的近似验证
    分析系统能量函数（到目标距离）的变化趋势
    """
    print("\n" + "="*60)
    print("李雅普诺夫稳定性分析")
    print("="*60)
    
    # 1. 计算到目标的欧几里得距离（李雅普诺夫函数候选）
    distances = np.linalg.norm(observations[:, :2] - target_position, axis=1)
    
    # 2. 计算距离的时间导数（近似）
    distance_derivative = np.diff(distances) / 1.0  # 假设每步时间间隔为1
    
    # 3. 基本统计量
    initial_distance = distances[0]
    final_distance = distances[-1]
    min_distance = np.min(distances)
    max_distance = np.max(distances)
    mean_distance = np.mean(distances)
    
    print(f"\n距离统计:")
    print(f"  初始距离: {initial_distance:.2f} m")
    print(f"  最终距离: {final_distance:.2f} m")
    print(f"  最小距离: {min_distance:.2f} m")
    print(f"  最大距离: {max_distance:.2f} m")
    print(f"  平均距离: {mean_distance:.2f} m")
    print(f"  距离减小率: {(1 - final_distance/initial_distance)*100:.2f}%")
    
    # 4. 李雅普诺夫导数分析（V̇ < 0 意味着稳定）
    negative_derivative_ratio = np.sum(distance_derivative < 0) / len(distance_derivative)
    mean_derivative = np.mean(distance_derivative)
    
    print(f"\n李雅普诺夫导数分析 (dV/dt):")
    print(f"  平均导数: {mean_derivative:.4f} m/step")
    print(f"  负导数比例: {negative_derivative_ratio*100:.2f}%")
    
    # 5. 分段分析（检查收敛性）
    segment_size = len(distances) // 5
    if segment_size > 0:
        print(f"\n分段距离分析 (每段{segment_size}步):")
        for i in range(5):
            start_idx = i * segment_size
            end_idx = (i + 1) * segment_size if i < 4 else len(distances)
            segment = distances[start_idx:end_idx]
            segment_mean = np.mean(segment)
            segment_trend = np.polyfit(range(len(segment)), segment, 1)[0]
            print(f"  段{i+1}: 平均距离={segment_mean:.2f}m, 趋势斜率={segment_trend:.4f}")
    
    # 6. 收敛性判断
    convergence_window = min(50, len(distances) // 5)
    convergence_status = "未知"
    if convergence_window > 0:
        final_segment_derivative = distance_derivative[-convergence_window:]
        final_mean_derivative = np.mean(final_segment_derivative)
        final_std_derivative = np.std(final_segment_derivative)
        
        print(f"\n收敛性分析 (最后{convergence_window}步):")
        print(f"  平均导数: {final_mean_derivative:.4f} m/step")
        print(f"  导数标准差: {final_std_derivative:.4f}")
        
        # 判断收敛类型
        if final_mean_derivative < -0.01:
            convergence_status = "渐近稳定 (继续收敛)"
        elif abs(final_mean_derivative) < 0.01 and final_std_derivative < 0.5:
            convergence_status = "稳定 (已收敛)"
        elif final_mean_derivative > 0.01:
            convergence_status = "不稳定 (发散)"
        else:
            convergence_status = "边界稳定 (有界振荡)"
        
        print(f"  稳定性状态: {convergence_status}")
    
    # 7. ISS (Input-to-State Stability) 相关分析
    # 分析奖励与距离变化的关系
    if len(rewards_array) > 0:
        print(f"\n输入-状态稳定性分析:")
        # 计算距离变化与奖励的相关性
        distance_changes = -distance_derivative  # 负号使得距离减小为正
        
        # ===== 修复：确保维度匹配 =====
        # distance_derivative 的长度是 len(distances) - 1
        # rewards_array 的长度是 len(distances)
        # 需要对齐它们的长度
        min_len = min(len(distance_changes), len(rewards_array) - 1)
        distance_changes_aligned = distance_changes[:min_len]
        rewards_aligned = rewards_array[:min_len]
        
        reward_correlation = np.corrcoef(distance_changes_aligned, rewards_aligned)[0, 1]
        print(f"  距离减小与奖励相关性: {reward_correlation:.4f}")
        
        # 分析奖励变化对距离稳定性的影响
        reward_changes = np.diff(rewards_array)
        # 确保 reward_changes 和 distance_derivative 长度一致
        min_len_changes = min(len(reward_changes), len(distance_derivative))
        reward_changes_aligned = reward_changes[:min_len_changes]
        distance_derivative_aligned = distance_derivative[:min_len_changes]
        
        large_reward_changes = np.abs(reward_changes_aligned) > np.std(reward_changes_aligned)
        
        if np.sum(large_reward_changes) > 0:
            distance_stability_during_perturbation = np.std(distance_derivative_aligned[large_reward_changes])
            distance_stability_normal = np.std(distance_derivative_aligned[~large_reward_changes])
            print(f"  大奖励变化时距离稳定性: {distance_stability_during_perturbation:.4f}")
            print(f"  正常情况距离稳定性: {distance_stability_normal:.4f}")
        else:
            print(f"  未检测到显著的大奖励变化")
    
    # 8. 李雅普诺夫稳定性总结
    print(f"\n李雅普诺夫稳定性总结:")
    
    # 评分系统
    score = 0
    max_score = 5
    
    # 评分项1: 最终距离是否接近目标
    if final_distance < 50:
        score += 1
        print(f"  ✓ 最终接近目标 (距离<50m)")
    else:
        print(f"  ✗ 未能充分接近目标")
    
    # 评分项2: 总体是否收敛
    if final_distance < initial_distance * 0.5:
        score += 1
        print(f"  ✓ 显著收敛 (距离减小>50%)")
    elif final_distance < initial_distance:
        score += 0.5
        print(f"  ~ 部分收敛 (距离有所减小)")
    else:
        print(f"  ✗ 未收敛或发散")
    
    # 评分项3: 李雅普诺夫导数主要为负
    if negative_derivative_ratio > 0.7:
        score += 1
        print(f"  ✓ 李雅普诺夫导数主要为负 (>70%)")
    elif negative_derivative_ratio > 0.5:
        score += 0.5
        print(f"  ~ 李雅普诺夫导数部分为负 (>50%)")
    else:
        print(f"  ✗ 李雅普诺夫导数为正过多")
    
    # 评分项4: 无显著发散趋势
    if max_distance < initial_distance * 1.5:
        score += 1
        print(f"  ✓ 轨迹有界 (最大距离<1.5倍初始)")
    else:
        print(f"  ✗ 出现显著偏离")
    
    # 评分项5: 末段稳定
    if convergence_window > 0:
        if abs(final_mean_derivative) < 0.1:
            score += 1
            print(f"  ✓ 末段趋于稳定")
        else:
            print(f"  ✗ 末段未充分稳定")
    
    print(f"\n稳定性评分: {score:.1f}/{max_score}")
    
    if score >= 4:
        overall_stability = "优秀 - 系统具有强李雅普诺夫稳定性"
    elif score >= 3:
        overall_stability = "良好 - 系统基本稳定"
    elif score >= 2:
        overall_stability = "及格 - 系统部分稳定"
    else:
        overall_stability = "不足 - 系统稳定性需改进"
    
    print(f"总体评价: {overall_stability}")
    print("="*60)
    
    # 返回分析结果用于绘图
    return {
        'distances': distances,
        'distance_derivative': distance_derivative,
        'initial_distance': initial_distance,
        'final_distance': final_distance,
        'mean_derivative': mean_derivative,
        'negative_derivative_ratio': negative_derivative_ratio,
        'convergence_status': convergence_status,
        'stability_score': score
    }

# ===== 新增：控制信号平滑性分析函数 =====
def analyze_control_smoothness(actions_array, steps_array):
    """
    分析控制信号的平滑性和有界性
    """
    print("\n" + "="*60)
    print("控制信号平滑性分析")
    print("="*60)
    
    action_names = ['帆角 (Sail)', '舵角 (Rudder)']
    
    # 计算动作变化率
    action_changes = np.diff(actions_array, axis=0)
    
    for i, name in enumerate(action_names):
        print(f"\n{name} 控制信号:")
        print(f"  均值: {np.mean(actions_array[:, i]):.4f} rad")
        print(f"  标准差: {np.std(actions_array[:, i]):.4f} rad")
        print(f"  最大值: {np.max(actions_array[:, i]):.4f} rad")
        print(f"  最小值: {np.min(actions_array[:, i]):.4f} rad")
        print(f"  平均变化率: {np.mean(np.abs(action_changes[:, i])):.4f} rad/step")
        print(f"  变化率标准差: {np.std(action_changes[:, i]):.4f} rad/step")
        print(f"  最大单步变化: {np.max(np.abs(action_changes[:, i])):.4f} rad/step")
        
        # 检测异常大的跳变
        threshold = np.mean(np.abs(action_changes[:, i])) + 2 * np.std(action_changes[:, i])
        large_changes = np.abs(action_changes[:, i]) > threshold
        num_large_changes = np.sum(large_changes)
        
        print(f"  异常跳变次数 (>μ+2σ): {num_large_changes} ({num_large_changes/len(action_changes)*100:.2f}%)")
        
        if num_large_changes > 0:
            print(f"  异常跳变发生位置: {np.where(large_changes)[0][:10]}...")  # 只显示前10个
    
    # 控制信号的连续性评估
    print(f"\n控制信号连续性评估:")
    for i, name in enumerate(action_names):
        # 计算总变差 (Total Variation)
        tv = np.sum(np.abs(action_changes[:, i]))
        print(f"  {name} 总变差: {tv:.4f}")
        
        # 平滑度指标：变化率的方差
        smoothness = np.var(action_changes[:, i])
        print(f"  {name} 平滑度 (方差越小越平滑): {smoothness:.6f}")
    
    print("="*60)
    
    return action_changes

# ===== 新增：值函数一致性分析 =====
def analyze_value_consistency(q_values, rewards, gamma=0.98):
    """
    检查时序差分一致性（Bellman残差）
    """
    print("\n" + "="*60)
    print("值函数一致性分析 (Bellman残差)")
    print("="*60)
    
    if len(q_values) < 2:
        print("数据不足，无法分析")
        return None
    
    # 计算TD目标: r(t) + γ*Q(s_{t+1}, a_{t+1})
    q_values = np.array(q_values)
    rewards = np.array(rewards)
    
    td_targets = rewards[:-1] + gamma * q_values[1:]
    td_errors = q_values[:-1] - td_targets
    
    print(f"\nTD误差统计:")
    print(f"  均值: {np.mean(td_errors):.4f}")
    print(f"  标准差: {np.std(td_errors):.4f}")
    print(f"  平均绝对误差: {np.mean(np.abs(td_errors)):.4f}")
    print(f"  最大正误差: {np.max(td_errors):.4f}")
    print(f"  最大负误差: {np.min(td_errors):.4f}")
    
    # Q值的单调性分析
    q_increases = np.sum(np.diff(q_values) > 0)
    q_decreases = np.sum(np.diff(q_values) < 0)
    
    print(f"\nQ值单调性:")
    print(f"  上升次数: {q_increases}")
    print(f"  下降次数: {q_decreases}")
    print(f"  下降比例: {q_decreases/(q_increases+q_decreases)*100:.2f}%")
    
    # 判断值函数是否稳定
    if np.mean(np.abs(td_errors)) < 1.0:
        print(f"\n值函数评价: 稳定 (TD误差较小)")
    elif np.mean(np.abs(td_errors)) < 5.0:
        print(f"\n值函数评价: 基本稳定 (TD误差中等)")
    else:
        print(f"\n值函数评价: 不稳定 (TD误差较大)")
    
    print("="*60)
    
    return td_errors


# 定义命令行参数
parser = argparse.ArgumentParser()
parser.add_argument('--dvc', type=str, default='cpu', help='running device: cuda or cpu')
parser.add_argument('--EnvIdex', type=int, default=0, help='PV1, Lch_Cv2, Humanv4, HCv4, BWv3, BWHv3')
parser.add_argument('--write', type=str2bool, default=True, help='Use SummaryWriter to record the training')
parser.add_argument('--render', type=str2bool, default=False, help='Render or Not')
parser.add_argument('--Loadmodel', type=str2bool, default=True, help='Load pretrained model or Not')
parser.add_argument('--ModelIdex', type=int, default=12600, help='which model to load')
parser.add_argument('--wind_angle', type=int, default=1, help='Wind direction angle in degrees (0-360)')

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
BrifEnvName = ['saclstm_s14obst_1216']

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
prev_action = np.zeros(opt.action_dim)

# 为测试环境分配一个唯一的环境ID，并重置隐藏状态
test_env_id = "test_env"
agent.actor.reset_hidden_state(test_env_id)

# 存储数据的列表
steps = []
actions = []
observations = []
wind_changes_v = []
wind_changes_d = []
obstacle_1_x_list = []
obstacle_1_y_list = []
obstacle_2_x_list = []
obstacle_2_y_list = []
obstacle_1_level_list = []
obstacle_2_level_list = []
rewards = []

# 用于存储Q值预期收益的列表
q_values = []
q1_values = []
q2_values = []

step = 0
total_scores = 0
done = False

print("开始测试模型...")
print(f"初始状态: {s}")
print("-" * 50)

while not done and step < opt.max_e_steps:
    # 使用修正后的select_action方法
    a = agent.select_action(prev_state, prev_action, s, deterministic=True, 
                           total_steps=None, env_id=test_env_id)
    
    # 获取Q值（预期未来收益）
    with torch.no_grad():
        prev_state_tensor = torch.FloatTensor(prev_state).unsqueeze(0).to(opt.dvc)
        prev_action_tensor = torch.FloatTensor(prev_action).unsqueeze(0).to(opt.dvc)
        current_state_tensor = torch.FloatTensor(s).unsqueeze(0).to(opt.dvc)
        action_tensor = torch.FloatTensor(a).unsqueeze(0).to(opt.dvc)
        
        prev_state_norm = agent.state_normalizer.normalize(prev_state_tensor)
        current_state_norm = agent.state_normalizer.normalize(current_state_tensor)
        
        q1, q2 = agent.q_critic(
            prev_state=prev_state_norm, 
            prev_action=prev_action_tensor,
            current_state=current_state_norm, 
            current_action=action_tensor,
            single_step_mode=True,
            env_ids=[test_env_id]
        )
        
        q1_val = q1.item()
        q2_val = q2.item()
        q_value = min(q1_val, q2_val)
        
        q_values.append(q_value)
        q1_values.append(q1_val)
        q2_values.append(q2_val)
    
    # 转换动作到环境范围
    act = Action_adapter(a, opt.max_action)
    
    # 执行动作，获得下一时刻的状态
    s_next, r, dw, tr, info = env.step(act)
    
    # 收集数据
    steps.append(step)
    actions.append(act.copy())
    observations.append(s_next.copy())
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
    print(f"Q1 Value: {q1_val:.4f}, Q2 Value: {q2_val:.4f}, Min Q Value: {q_value:.4f}")
    print(f"Next State: {s_next}")
    print(f"Reward: {r}")
    print(f"Terminated: {dw}")
    print(f"Truncated: {tr}")
    print(f"Info: {info}")
    print("-" * 50)
    
    done = (dw or tr)
    
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

# 计算实际累积回报的函数
def calculate_actual_returns(rewards, gamma=0.98):
    """计算每一步的实际累积折扣回报"""
    returns = []
    G = 0
    for r in reversed(rewards):
        G = r + gamma * G
        returns.insert(0, G)
    return returns

# 计算实际累积回报
actual_returns = calculate_actual_returns(rewards, opt.gamma)

# Q值预测准确性统计
q_values_array = np.array(q_values)
actual_returns_array = np.array(actual_returns)
prediction_errors = q_values_array - actual_returns_array

mse = np.mean(prediction_errors**2)
mae = np.mean(np.abs(prediction_errors))
correlation = np.corrcoef(q_values_array, actual_returns_array)[0, 1]

print(f"\n===== Q值预期收益分析 =====")
print(f"均方误差 (MSE): {mse:.4f}")
print(f"平均绝对误差 (MAE): {mae:.4f}")
print(f"相关系数: {correlation:.4f}")
print(f"平均Q值: {np.mean(q_values_array):.4f}")
print(f"平均实际回报: {np.mean(actual_returns_array):.4f}")
print(f"Q值标准差: {np.std(q_values_array):.4f}")
print(f"实际回报标准差: {np.std(actual_returns_array):.4f}")

# ===== 新增：执行稳定性分析 =====
observations_array = np.array(observations)
actions_array = np.array(actions)
steps_array = np.array(steps)
rewards_array = np.array(rewards)

# 获取目标位置（从环境状态中读取）
try:
    # 假设目标位置在状态的索引12和13
    target_position = np.array([observations_array[0, 12], observations_array[0, 13]])
    print(f"\n目标位置: ({target_position[0]:.2f}, {target_position[1]:.2f})")
except:
    # 如果无法获取，使用默认目标位置
    target_position = np.array([0.0, 0.0])
    print(f"\n警告：无法从状态中获取目标位置，使用默认值: {target_position}")

# 1. 李雅普诺夫稳定性分析
lyapunov_results = analyze_lyapunov_stability(
    observations_array, 
    target_position, 
    steps_array, 
    rewards_array
)

# 2. 控制信号平滑性分析
action_changes = analyze_control_smoothness(actions_array, steps_array)

# 3. 值函数一致性分析
td_errors = analyze_value_consistency(q_values, rewards, opt.gamma)

# 数据保存部分
desktop_path = 'C:\\Users\\24809\\Desktop\\'

# 创建带风向角度标识的文件名后缀
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
    
    # 保存Q值分析数据
    q_analysis_data = np.column_stack((
        steps_array, 
        q_values_array, 
        q1_values, 
        q2_values,
        actual_returns_array, 
        prediction_errors
    ))
    np.savetxt(desktop_path + f'q_value_analysis{file_suffix}.txt', 
               q_analysis_data, delimiter=',',
               header='Step,Q_Value,Q1_Value,Q2_Value,Actual_Return,Prediction_Error', 
               comments='')
    print("Q值分析数据已保存")
    
    # ===== 新增：保存稳定性分析数据 =====
    stability_data = np.column_stack((
        steps_array,
        lyapunov_results['distances'],
        np.concatenate([[0], lyapunov_results['distance_derivative']]),  # 第一个点没有导数
        actions_array[:, 0],
        actions_array[:, 1],
        np.concatenate([[0, 0], action_changes[:, 0]]),  # 帆角变化率
        np.concatenate([[0, 0], action_changes[:, 1]])   # 舵角变化率
    ))
    np.savetxt(desktop_path + f'stability_analysis{file_suffix}.txt',
               stability_data, delimiter=',',
               header='Step,Distance_to_Target,Distance_Derivative,Sail_Action,Rudder_Action,Sail_Change_Rate,Rudder_Change_Rate',
               comments='')
    print("稳定性分析数据已保存")
    
    # 保存稳定性分析摘要
    summary_file = desktop_path + f'stability_summary{file_suffix}.json'
    summary_data = {
        'lyapunov_stability': {
            'initial_distance': float(lyapunov_results['initial_distance']),
            'final_distance': float(lyapunov_results['final_distance']),
            'mean_derivative': float(lyapunov_results['mean_derivative']),
            'negative_derivative_ratio': float(lyapunov_results['negative_derivative_ratio']),
            'convergence_status': lyapunov_results['convergence_status'],
            'stability_score': float(lyapunov_results['stability_score'])
        },
        'q_value_analysis': {
            'mse': float(mse),
            'mae': float(mae),
            'correlation': float(correlation),
            'mean_q_value': float(np.mean(q_values_array)),
            'mean_actual_return': float(np.mean(actual_returns_array))
        },
        'control_smoothness': {
            'sail_mean_change': float(np.mean(np.abs(action_changes[:, 0]))),
            'rudder_mean_change': float(np.mean(np.abs(action_changes[:, 1]))),
            'sail_max_change': float(np.max(np.abs(action_changes[:, 0]))),
            'rudder_max_change': float(np.max(np.abs(action_changes[:, 1])))
        },
        'performance': {
            'total_steps': int(step),
            'total_reward': float(total_scores),
            'average_reward': float(total_scores/step)
        }
    }
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, indent=4, ensure_ascii=False)
    print("稳定性分析摘要已保存")
    
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
    if observations_array.shape[1] >= 2:
        x = observations_array[:, 0]
        y = observations_array[:, 1]
        
        # ===== 修改：创建包含李雅普诺夫分析的更大图形 =====
        fig = plt.figure(figsize=(24, 16))
        import matplotlib.gridspec as gridspec
        gs = gridspec.GridSpec(4, 3, figure=fig, hspace=0.35, wspace=0.3)
        
        # 子图1: 轨迹图 - 占据左上两格
        ax1 = fig.add_subplot(gs[:2, 0:2])
        ax1.plot(x, y, marker='o', linestyle='-', color='b', markersize=3, label='Trajectory')
        # 标记起点和终点
        ax1.plot(x[0], y[0], 'go', markersize=12, label='Start', zorder=5)
        ax1.plot(x[-1], y[-1], 'rs', markersize=12, label='End', zorder=5)
        # 标记目标点
        ax1.plot(target_position[0], target_position[1], 'y*', markersize=20, label='Target', zorder=5)
        
        ax1.set_title('Trajectory of Agent', fontsize=14, fontweight='bold')
        ax1.set_xlabel('X Coordinate', fontsize=12)
        ax1.set_ylabel('Y Coordinate', fontsize=12)
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
        base_radii = [50.0, 100.0, 150.0]
        legend_flags = {"obstacle": False, "observed": False}

        for cx, cy in all_obstacles:
            label = "Obstacle" if not legend_flags["obstacle"] else None
            if label:
                legend_flags["obstacle"] = True
            ax1.plot(cx, cy, 'ro', markersize=6, label=label)
            for r in base_radii:
                circ = Circle((cx, cy), radius=r, edgecolor='red', facecolor='none',
                              linestyle='--', linewidth=1, alpha=0.6)
                ax1.add_patch(circ)
            if (round(cx, 6), round(cy, 6)) in observed_keys:
                obs_label = "Observed obstacle" if not legend_flags["observed"] else None
                if obs_label:
                    legend_flags["observed"] = True
                ax1.plot(cx, cy, marker='*', color='gold', markersize=10, label=obs_label)

        ax1.legend(fontsize=9, loc='best')

        # ===== 新增：子图2: 李雅普诺夫函数(距离)随时间变化 - 右上 =====
        ax2 = fig.add_subplot(gs[0, 2])
        ax2.plot(steps_array, lyapunov_results['distances'], color='darkblue', linewidth=2)
        ax2.axhline(y=50, color='green', linestyle='--', alpha=0.5, label='Success threshold')
        ax2.set_title(f'Lyapunov Function V(t)\n(Score: {lyapunov_results["stability_score"]:.1f}/5)', 
                      fontsize=12, fontweight='bold')
        ax2.set_xlabel('Step', fontsize=10)
        ax2.set_ylabel('Distance to Target (m)', fontsize=10)
        ax2.legend(fontsize=8)
        ax2.grid(True, alpha=0.3)
        
        # ===== 新增：子图3: 李雅普诺夫导数 dV/dt - 右中上 =====
        ax3 = fig.add_subplot(gs[1, 2])
        derivative_steps = steps_array[1:]
        ax3.plot(derivative_steps, lyapunov_results['distance_derivative'], 
                 color='purple', linewidth=1.5, alpha=0.7)
        ax3.axhline(y=0, color='red', linestyle='--', linewidth=2, label='Stability line (dV/dt=0)')
        ax3.fill_between(derivative_steps, 0, lyapunov_results['distance_derivative'], 
                         where=(lyapunov_results['distance_derivative']<0), 
                         color='green', alpha=0.3, label='Stable region')
        ax3.fill_between(derivative_steps, 0, lyapunov_results['distance_derivative'], 
                         where=(lyapunov_results['distance_derivative']>0), 
                         color='red', alpha=0.3, label='Unstable region')
        ax3.set_title(f'Lyapunov Derivative dV/dt\n(Neg ratio: {lyapunov_results["negative_derivative_ratio"]*100:.1f}%)', 
                      fontsize=12, fontweight='bold')
        ax3.set_xlabel('Step', fontsize=10)
        ax3.set_ylabel('dV/dt (m/step)', fontsize=10)
        ax3.legend(fontsize=8)
        ax3.grid(True, alpha=0.3)
        
        # 子图4: 奖励曲线
        ax4 = fig.add_subplot(gs[2, 0])
        ax4.plot(steps_array, rewards_array, color='r', linewidth=1.5)
        ax4.set_title('Reward over Time', fontsize=12, fontweight='bold')
        ax4.set_xlabel('Step', fontsize=10)
        ax4.set_ylabel('Reward', fontsize=10)
        ax4.grid(True, alpha=0.3)
        
        # 子图5: 动作曲线
        ax5 = fig.add_subplot(gs[2, 1])
        ax5.plot(steps_array, actions_array[:, 0], label='Sail Action', color='g', linewidth=1.5)
        if actions_array.shape[1] > 1:
            ax5.plot(steps_array, actions_array[:, 1], label='Rudder Action', color='orange', linewidth=1.5)
        ax5.set_title('Actions over Time', fontsize=12, fontweight='bold')
        ax5.set_xlabel('Step', fontsize=10)
        ax5.set_ylabel('Action Value', fontsize=10)
        ax5.legend(fontsize=9)
        ax5.grid(True, alpha=0.3)
        
        # ===== 新增：子图6: 控制信号变化率 =====
        ax6 = fig.add_subplot(gs[2, 2])
        change_steps = steps_array[1:]
        ax6.plot(change_steps, np.abs(action_changes[:, 0]), 
                 label='|Sail Change|', color='g', linewidth=1.5, alpha=0.7)
        ax6.plot(change_steps, np.abs(action_changes[:, 1]), 
                 label='|Rudder Change|', color='orange', linewidth=1.5, alpha=0.7)
        ax6.set_title('Control Signal Change Rate', fontsize=12, fontweight='bold')
        ax6.set_xlabel('Step', fontsize=10)
        ax6.set_ylabel('|Change| (rad/step)', fontsize=10)
        ax6.legend(fontsize=9)
        ax6.grid(True, alpha=0.3)
        
        # 子图7: Q值vs实际回报对比
        ax7 = fig.add_subplot(gs[3, 0])
        ax7.plot(steps_array, q_values_array, label='Predicted Q-Value', color='blue', linewidth=2, alpha=0.8)
        ax7.plot(steps_array, actual_returns_array, label='Actual Return', color='red', linewidth=2, alpha=0.7)
        ax7.set_title('Expected vs Actual Returns', fontsize=12, fontweight='bold')
        ax7.set_xlabel('Step', fontsize=10)
        ax7.set_ylabel('Value', fontsize=10)
        ax7.legend(fontsize=9)
        ax7.grid(True, alpha=0.3)
        
        # 子图8: 预测误差
        ax8 = fig.add_subplot(gs[3, 1])
        ax8.plot(steps_array, prediction_errors, color='green', linewidth=2)
        ax8.axhline(y=0, color='black', linestyle='--', alpha=0.5)
        ax8.set_title('Prediction Error (Q - Actual)', fontsize=12, fontweight='bold')
        ax8.set_xlabel('Step', fontsize=10)
        ax8.set_ylabel('Error', fontsize=10)
        ax8.grid(True, alpha=0.3)
        
        # 子图9: Q1和Q2对比
        ax9 = fig.add_subplot(gs[3, 2])
        ax9.plot(steps_array, q1_values, label='Q1 Value', color='cyan', linewidth=1.5, alpha=0.7)
        ax9.plot(steps_array, q2_values, label='Q2 Value', color='magenta', linewidth=1.5, alpha=0.7)
        ax9.plot(steps_array, q_values_array, label='Min Q (used)', color='blue', linewidth=2)
        ax9.set_title('Q1 vs Q2 Values', fontsize=12, fontweight='bold')
        ax9.set_xlabel('Step', fontsize=10)
        ax9.set_ylabel('Q Value', fontsize=10)
        ax9.legend(fontsize=9)
        ax9.grid(True, alpha=0.3)
        
        plt.savefig(desktop_path + f'model_test_results{file_suffix}.png', dpi=300, bbox_inches='tight')
        
        # 创建单独的累计奖励图
        fig2 = plt.figure(figsize=(10, 6))
        cumulative_rewards = np.cumsum(rewards_array)
        plt.plot(steps_array, cumulative_rewards, color='purple', linewidth=2)
        plt.title('Cumulative Reward', fontsize=14, fontweight='bold')
        plt.xlabel('Step', fontsize=12)
        plt.ylabel('Cumulative Reward', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(desktop_path + f'cumulative_reward{file_suffix}.png', dpi=300, bbox_inches='tight')
        
        # Q值详细分析图
        fig3 = plt.figure(figsize=(14, 10))
        
        # 散点图：Q值vs实际回报
        ax_scatter = plt.subplot(2, 2, 1)
        ax_scatter.scatter(actual_returns_array, q_values_array, alpha=0.5, s=20)
        min_val = min(actual_returns_array.min(), q_values_array.min())
        max_val = max(actual_returns_array.max(), q_values_array.max())
        ax_scatter.plot([min_val, max_val], [min_val, max_val], 'r--', linewidth=2, label='Perfect Prediction')
        ax_scatter.set_xlabel('Actual Return', fontsize=11)
        ax_scatter.set_ylabel('Predicted Q-Value', fontsize=11)
        ax_scatter.set_title(f'Q-Value vs Actual Return (Corr: {correlation:.3f})', fontsize=12, fontweight='bold')
        ax_scatter.legend()
        ax_scatter.grid(True, alpha=0.3)
        
        # 误差分布直方图
        ax_hist = plt.subplot(2, 2, 2)
        ax_hist.hist(prediction_errors, bins=30, color='skyblue', edgecolor='black', alpha=0.7)
        ax_hist.axvline(x=0, color='red', linestyle='--', linewidth=2)
        ax_hist.set_xlabel('Prediction Error', fontsize=11)
        ax_hist.set_ylabel('Frequency', fontsize=11)
        ax_hist.set_title(f'Error Distribution (MAE: {mae:.3f})', fontsize=12, fontweight='bold')
        ax_hist.grid(True, alpha=0.3, axis='y')
        
        # 误差的绝对值随时间变化
        ax_abs_error = plt.subplot(2, 2, 3)
        ax_abs_error.plot(steps_array, np.abs(prediction_errors), color='orange', linewidth=1.5)
        ax_abs_error.set_xlabel('Step', fontsize=11)
        ax_abs_error.set_ylabel('Absolute Error', fontsize=11)
        ax_abs_error.set_title('Absolute Prediction Error over Time', fontsize=12, fontweight='bold')
        ax_abs_error.grid(True, alpha=0.3)
        
        # Q值的不确定性
        ax_uncertainty = plt.subplot(2, 2, 4)
        q_uncertainty = np.abs(np.array(q1_values) - np.array(q2_values))
        ax_uncertainty.plot(steps_array, q_uncertainty, color='purple', linewidth=1.5)
        ax_uncertainty.set_xlabel('Step', fontsize=11)
        ax_uncertainty.set_ylabel('|Q1 - Q2|', fontsize=11)
        ax_uncertainty.set_title('Q-Value Uncertainty', fontsize=12, fontweight='bold')
        ax_uncertainty.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(desktop_path + f'q_value_detailed_analysis{file_suffix}.png', dpi=300, bbox_inches='tight')
        
        plt.show()
        print("图表已保存并显示")
    else:
        print("观测数据维度不足，无法绘制轨迹图")
        
except Exception as e:
    print(f"绘图时出错: {e}")
    import traceback
    traceback.print_exc()

# 关闭环境
env.close()
print("测试完成，环境已关闭")