import gymnasium
import numpy as np
import globals
import time
import sys
import matplotlib.pyplot as plt
import copy

env = gymnasium.make('sailboat-s14-wind',render_mode = 'human')

observation, info = env.reset()

steps = []
actions = []
observations = []
wind_changes_v = []
wind_changes_d = []

done = False

for step in range(300):
    action = [0, 0]
    observation, reward, terminated, truncated, info = env.step(action)

    # 收集数据
    steps.append(step)
    actions.append(action)
    observations.append(copy.deepcopy(observation))
    wind_changes_v.append(globals.w_change_v)
    wind_changes_d.append(globals.w_change_d)

    # 输出当前步的信息
    print(f"Step: {step}")
    print(f"Action: {action}")
    print(f"Observation: {observation}")
    print(f"Reward: {reward}")
    print(f"Terminated: {terminated}")
    print(f"Truncated: {truncated}")
    print(f"Info: {info}")
    print("-" * 50)

    # 输出风场信息
    print(f"Wind: {globals.w_change_v},{globals.w_change_d}")

    if terminated or truncated:
        observation, info = env.reset()

# 将数据保存到桌面
desktop_path = 'C:\\Users\\24809\\Desktop\\'
# 将 observations 转换为 NumPy 数组
observations_array = np.array(observations)
np.savetxt(desktop_path + 'actions.txt', np.array(actions), delimiter=',', header='Actions', comments='')
np.savetxt(desktop_path + 'observations.txt', np.array(observations), delimiter=',', header=','.join([f'Observation {i}' for i in range(observations_array.shape[1])]), comments='')
np.savetxt(desktop_path + 'wind_changes.txt', np.column_stack((wind_changes_v, wind_changes_d)), delimiter=',', header='Wind Change V,Wind Change D', comments='')

env.close()

