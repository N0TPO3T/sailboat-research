"""
传感器噪声和执行器噪声模块

用于帆船控制训练中的噪声注入:
1. 传感器噪声 - 模拟GPS、IMU、测速仪等传感器误差
2. 执行器噪声 - 模拟帆角和舵角执行机构的不精确性
"""

import numpy as np


class SensorNoise:
    """
    传感器噪声类
    
    观测空间(14维)噪声配置:
    - state[0:2]: x, y 位置 (GPS噪声, 3%)
    - state[2]: phi 横摇角 (IMU噪声, 3%)
    - state[3]: psi 艏向角 (罗盘噪声, 3%)
    - state[4:6]: u, v 速度 (测速仪噪声, 3%)
    - state[6:8]: p, r 角速度 (陀螺仪噪声, 3%)
    - state[8]: 帆角 δs (不加噪声 - 执行器反馈)
    - state[9]: 舵角 δr (不加噪声 - 执行器反馈)
    - state[10:12]: 距离差 (计算值, 3%)
    - state[12:14]: 终点坐标 (不加噪声 - 预设值)
    """
    
    def __init__(self, noise_ratio=0.03, seed=None):
        """
        初始化传感器噪声
        
        Args:
            noise_ratio: 噪声比例，默认3%
            seed: 随机种子
        """
        self.noise_ratio = noise_ratio
        self.rng = np.random.RandomState(seed)
        
        RATE = 5
        # 各传感器的特征参数
        self.sensor_params = {
            # 位置传感器 (GPS) - 典型精度 1-5m
            'position': {
                'min_noise': 1.0 * RATE,      # 最小噪声 0.5m
                'max_noise': 1.0 * RATE,      # 最大噪声 5m
                'bias': 0.0,           # 偏置
            },
            # 角度传感器 (IMU/罗盘) - 典型精度 0.1-1度
            'angle': {
                'min_noise': np.deg2rad(1.0 * RATE),  # 最小噪声 0.1度
                'max_noise': np.deg2rad(1.0 * RATE),  # 最大噪声 2度
                'bias': 0.0,
            },
            # 速度传感器 - 典型精度 0.05-0.2 m/s
            'velocity': {
                'min_noise': 0.1 * RATE,
                'max_noise': 0.1 * RATE,
                'bias': 0.0,
            },
            # 角速度传感器 (陀螺仪)
            'angular_velocity': {
                'min_noise': np.deg2rad(0.1 * RATE),
                'max_noise': np.deg2rad(0.1 * RATE),
                'bias': 0.0,
            },
            # 距离传感器 (雷达/激光)
            'distance': {
                'min_noise': 0.5,
                'max_noise': 5.0,
                'bias': 0.0,
            },
        }
    
    def _add_proportional_noise(self, value, sensor_type, ratio=None):
        """
        添加比例噪声，同时考虑传感器特性
        
        Args:
            value: 原始值
            sensor_type: 传感器类型
            ratio: 噪声比例，None则使用默认值
        
        Returns:
            添加噪声后的值
        """
        if ratio is None:
            ratio = self.noise_ratio
        
        params = self.sensor_params.get(sensor_type, {})
        min_noise = params.get('min_noise', 0.0)
        max_noise = params.get('max_noise', float('inf'))
        bias = params.get('bias', 0.0)
        
        # 比例噪声
        proportional_noise = abs(value) * ratio * self.rng.randn()
        
        # 限制噪声范围
        noise_magnitude = np.clip(abs(proportional_noise), min_noise, max_noise)
        noise = np.sign(proportional_noise) * noise_magnitude if proportional_noise != 0 else 0
        
        return value + noise + bias
    
    def add_observation_noise(self, state):
        """
        为观测状态添加传感器噪声
        
        Args:
            state: 原始状态向量 (14,)
        
        Returns:
            添加噪声后的状态向量
        """
        noisy_state = state.copy()
        
        # state[0:2]: x, y 位置 (GPS噪声)
        noisy_state[0] = self._add_proportional_noise(state[0], 'position')
        noisy_state[1] = self._add_proportional_noise(state[1], 'position')
        
        # state[2]: phi 横摇角 (IMU噪声)
        noisy_state[2] = self._add_proportional_noise(state[2], 'angle')
        
        # state[3]: psi 艏向角 (罗盘噪声)
        noisy_state[3] = self._add_proportional_noise(state[3], 'angle')
        # 规范化角度到 [-pi, pi]
        noisy_state[3] = np.arctan2(np.sin(noisy_state[3]), np.cos(noisy_state[3]))
        
        # state[4:6]: u, v 速度 (测速仪噪声)
        noisy_state[4] = self._add_proportional_noise(state[4], 'velocity')
        noisy_state[5] = self._add_proportional_noise(state[5], 'velocity')
        
        # state[6:8]: p, r 角速度 (陀螺仪噪声)
        noisy_state[6] = self._add_proportional_noise(state[6], 'angular_velocity')
        noisy_state[7] = self._add_proportional_noise(state[7], 'angular_velocity')
        
        # state[8]: 帆角 δs - 不加噪声
        # state[9]: 舵角 δr - 不加噪声
        
        # state[10:12]: 距离差 (计算值噪声)
        noisy_state[10] = self._add_proportional_noise(state[10], 'distance')
        noisy_state[11] = self._add_proportional_noise(state[11], 'distance')
        
        # state[12:14]: 终点坐标 - 不加噪声
        
        return noisy_state.astype(np.float32)


class ActuatorNoise:
    """
    执行器噪声类
    
    模拟帆角和舵角执行机构的实际特性:
    1. 死区效应 - 调节幅度过小不生效
    2. 执行精度误差 - 无法调节到精确角度
    3. 响应滞后 - 执行器响应不完全
    4. 非线性特性 - 大幅度调节时精度下降
    """
    
    def __init__(self, noise_ratio=0.03, seed=None):
        """
        初始化执行器噪声
        
        Args:
            noise_ratio: 基础噪声比例，默认3%
            seed: 随机种子
        """
        self.noise_ratio = noise_ratio
        self.rng = np.random.RandomState(seed)
        
        # 帆角执行器参数 (max_action = pi/18 ≈ 10度)
        self.sail_params = {
            'deadzone': np.deg2rad(0.5),       # 死区: <0.5度的调节不生效
            'resolution': np.deg2rad(0.2),     # 分辨率: 0.2度的倍数
            'max_error': np.deg2rad(1.5),      # 最大执行误差: 1.5度
            'response_factor': 0.95,           # 响应系数: 95%响应
            'large_action_threshold': 0.7,     # 大幅度调节阈值 (相对于max)
            'large_action_error_mult': 1.5,    # 大幅度调节误差放大系数
        }
        
        # 舵角执行器参数 (max_action = pi/18 ≈ 10度)
        self.rudder_params = {
            'deadzone': np.deg2rad(0.3),       # 死区: <0.3度的调节不生效
            'resolution': np.deg2rad(0.15),    # 分辨率: 0.15度的倍数
            'max_error': np.deg2rad(1.0),      # 最大执行误差: 1.0度
            'response_factor': 0.97,           # 响应系数: 97%响应
            'large_action_threshold': 0.7,     # 大幅度调节阈值
            'large_action_error_mult': 1.3,    # 大幅度调节误差放大系数
        }
    
    def _apply_deadzone(self, action, deadzone):
        """
        应用死区效应
        
        Args:
            action: 原始动作值
            deadzone: 死区阈值
        
        Returns:
            处理后的动作值
        """
        if abs(action) < deadzone:
            return 0.0
        return action
    
    def _quantize_action(self, action, resolution):
        """
        量化动作到分辨率的倍数
        
        Args:
            action: 原始动作值
            resolution: 分辨率
        
        Returns:
            量化后的动作值
        """
        if resolution <= 0:
            return action
        return round(action / resolution) * resolution
    
    def _add_execution_noise(self, action, params, max_action):
        """
        添加执行噪声
        
        Args:
            action: 原始动作值
            params: 执行器参数
            max_action: 动作最大值
        
        Returns:
            添加噪声后的动作值
        """
        if action == 0:
            return 0.0
        
        # 基础比例噪声
        base_noise = abs(action) * self.noise_ratio * self.rng.randn()
        
        # 大幅度调节时误差放大
        action_ratio = abs(action) / max_action
        if action_ratio > params['large_action_threshold']:
            base_noise *= params['large_action_error_mult']
        
        # 限制最大误差
        noise = np.clip(base_noise, -params['max_error'], params['max_error'])
        
        # 应用响应系数 (模拟不完全响应)
        response_variation = 1.0 + (self.rng.rand() - 0.5) * 0.1  # ±5%响应变化
        effective_response = params['response_factor'] * response_variation
        
        return action * effective_response + noise
    
    def apply_action_noise(self, action, max_action):
        """
        为动作添加执行器噪声
        
        处理流程:
        1. 死区检测 - 过小的调节不生效
        2. 量化 - 模拟执行器分辨率
        3. 执行噪声 - 添加随机误差
        
        Args:
            action: 原始动作向量 [帆角调节, 舵角调节]，范围 [-1, 1]
            max_action: 动作最大值向量 [max_sail, max_rudder]
        
        Returns:
            处理后的动作向量，范围 [-1, 1]
        """
        noisy_action = np.zeros_like(action)
        
        # 帆角动作处理
        sail_action = action[0] * max_action[0]  # 转换到实际角度
        sail_action = self._apply_deadzone(sail_action, self.sail_params['deadzone'])
        sail_action = self._quantize_action(sail_action, self.sail_params['resolution'])
        sail_action = self._add_execution_noise(sail_action, self.sail_params, max_action[0])
        noisy_action[0] = np.clip(sail_action / max_action[0], -1.0, 1.0)  # 转回 [-1, 1]
        
        # 舵角动作处理
        rudder_action = action[1] * max_action[1]  # 转换到实际角度
        rudder_action = self._apply_deadzone(rudder_action, self.rudder_params['deadzone'])
        rudder_action = self._quantize_action(rudder_action, self.rudder_params['resolution'])
        rudder_action = self._add_execution_noise(rudder_action, self.rudder_params, max_action[1])
        noisy_action[1] = np.clip(rudder_action / max_action[1], -1.0, 1.0)  # 转回 [-1, 1]
        
        return noisy_action


class NoiseManager:
    """
    噪声管理器 - 统一管理传感器和执行器噪声
    """
    
    def __init__(self, sensor_noise_ratio=0.1, actuator_noise_ratio=0.03, 
                 enable_sensor_noise=True, enable_actuator_noise=True, seed=None):
        """
        初始化噪声管理器
        
        Args:
            sensor_noise_ratio: 传感器噪声比例
            actuator_noise_ratio: 执行器噪声比例
            enable_sensor_noise: 是否启用传感器噪声
            enable_actuator_noise: 是否启用执行器噪声
            seed: 随机种子
        """
        self.enable_sensor_noise = enable_sensor_noise
        self.enable_actuator_noise = enable_actuator_noise
        
        # 为传感器和执行器噪声使用不同的随机种子
        sensor_seed = seed if seed is None else seed
        actuator_seed = seed if seed is None else seed + 1000
        
        self.sensor_noise = SensorNoise(noise_ratio=sensor_noise_ratio, seed=sensor_seed)
        self.actuator_noise = ActuatorNoise(noise_ratio=actuator_noise_ratio, seed=actuator_seed)
    
    def add_observation_noise(self, state):
        """为观测添加传感器噪声"""
        if self.enable_sensor_noise:
            return self.sensor_noise.add_observation_noise(state)
        return state
    
    def add_action_noise(self, action, max_action):
        """为动作添加执行器噪声"""
        if self.enable_actuator_noise:
            return self.actuator_noise.apply_action_noise(action, max_action)
        return action
    
    def set_noise_enabled(self, sensor=None, actuator=None):
        """
        动态设置噪声开关
        
        Args:
            sensor: 传感器噪声开关 (True/False/None保持不变)
            actuator: 执行器噪声开关 (True/False/None保持不变)
        """
        if sensor is not None:
            self.enable_sensor_noise = sensor
        if actuator is not None:
            self.enable_actuator_noise = actuator
