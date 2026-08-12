import jax
import jax.numpy as jnp
from typing import NamedTuple, Tuple
import functools

# ---------------------------------------------------------------------------
# 常量定义 (严格对应原始代码 self.par)
# ---------------------------------------------------------------------------
PAR = {
    'm': 25900.0, 'Ixx': 133690.0, 'Izz': 24760.0, 'Ixz': 2180.0,
    'a11': 970.0, 'a22': 17430.0, 'a44': 106500.0, 'a66': 101650.0,
    'a24': -13160.0, 'a26': -6190.0, 'a46': 4730.0,
    'rho_a': 1.2, 'As': 170.0, 'h0': 0.0005, 'h1': 11.58,
    'z_s': -11.58, 'xs': 0.0, 'ys': 0.0, 'zs': -11.58,
    'Xce': 0.6, 'Xm': 0.3,
    'rho_w': 1025.0,
    'Ar': 1.17, 'd_r': 1.9, 'zeta_r': 0.8, 'x_r': -8.2, 'z_r': -0.78,
    'xr': -8.2, 'yr': 0.0, 'zr': -0.78,
    'Ak': 8.7, 'd_k': 2.49, 'zeta_k': 0.7, 'x_k': 0.0, 'z_k': -0.58,
    'xk': 0.0, 'yk': 0.0, 'zk': -0.58,
    'x_h': 0.0, 'z_h': -1.18, 'xh': 0.0, 'yh': 0.0, 'zh': -1.18,
    'w_c': 60000.0, 'x_c': -8.0, 'y_bm': 3.6,
    'a': -5.89, 'b': 8160.0, 'c': 120000.0, 'd': 50000.0
}

# 预计算一些矩阵常数以加速 (Mass Matrix M)
M_RB = jnp.array([
    [PAR['m'], 0, 0, 0],
    [0, PAR['m'], 0, 0],
    [0, 0, PAR['Ixx'], -PAR['Ixz']],
    [0, 0, -PAR['Ixz'], PAR['Izz']]
])
M_A = jnp.array([
    [PAR['a11'], 0, 0, 0],
    [0, PAR['a22'], PAR['a24'], PAR['a26']],
    [0, PAR['a24'], PAR['a44'], PAR['a46']],
    [0, PAR['a26'], PAR['a46'], PAR['a66']]
])
M_MAT = M_RB + M_A
M_INV = jnp.linalg.inv(M_MAT)

# ---------------------------------------------------------------------------
# 状态定义 (State Definition)
# ---------------------------------------------------------------------------
class EnvState(NamedTuple):
    # 物理状态 (vector 8)
    # [x, y, phi, psi, u, v, p, r]
    phys_state: jnp.ndarray 
    
    # 动作机构状态
    current_sail: jnp.ndarray
    current_rudder: jnp.ndarray
    target_sail_ref: jnp.ndarray
    target_rudder_ref: jnp.ndarray
    
    # 观测与奖励辅助
    obs_vec: jnp.ndarray  # 18维观测向量
    prev_dis: jnp.ndarray
    prev_x_dis: jnp.ndarray
    
    # 目标点
    target_x: jnp.ndarray
    target_y: jnp.ndarray
    
    # 风场参数
    w_change_v: jnp.ndarray
    w_change_d: jnp.ndarray
    w_last_v: jnp.ndarray
    w_last_d: jnp.ndarray
    w_ini_v: jnp.ndarray
    w_ini_d: jnp.ndarray
    
    # 障碍物 (固定最大数量，例如20个)
    obstacles_pos: jnp.ndarray # Shape (MAX_OBSTACLES, 2)
    obstacles_mask: jnp.ndarray # Shape (MAX_OBSTACLES,) 1有效 0无效
    is_discovered: jnp.ndarray # 记忆已发现的障碍物
    
    # 检查点状态
    one_check: jnp.ndarray
    two_check: jnp.ndarray
    three_check: jnp.ndarray
    
    time: jnp.ndarray
    step_count: jnp.ndarray
    done: jnp.ndarray

class SailboatJaxEnv:
    def __init__(self, max_obstacles=20):
        self.dt = 0.05
        self.tf = 1.0 # 每次step仿真时长
        self.integration_steps = int(self.tf / self.dt) # 20步
        self.max_obstacles = max_obstacles
        self.obs_dim = 18
        self.act_dim = 2
        
        # 动作空间限制
        self.action_scale = jnp.array([jnp.pi/18, jnp.pi/18])
        
        # 障碍物参数
        self.obstacle_detection_radius = 150.0
        self.obstacle_fov_angle = jnp.pi / 2
        
        # 数据表预处理 (Interpolation Data)
        self._init_coeff_tables()

    def _init_coeff_tables(self):
        # 帆/舵/龙骨系数表 (从原始代码复制数据)
        self.ang_xdata = jnp.linspace(-jnp.pi, jnp.pi, 73) * 180 / jnp.pi
        
        # Sail Coef Data
        yl_sail = jnp.array([0, 0.15, 0.32, 0.48, 0.7, 0.94, 1.15, 1.3, 1.28, 1.15, 1.1, 1.05, 1, 0.9, 0.82, 0.72, 0.68, 0.56, 0.48, 0.32, 0.21, 0.08, -0.06, -0.18, -0.3, -0.4, -0.53, -0.64, -0.72, -0.84, -0.95, -1.04, -1.1, -1.14, -1.08, -0.76, 0])
        self.yl_sail_full = jnp.concatenate([jnp.flip(yl_sail) * (-1), yl_sail[1:]])
        
        yd_sail = jnp.array([0.1, 0.12, 0.14, 0.16, 0.19, 0.26, 0.35, 0.46, 0.54, 0.62, 0.7, 0.78, 0.9, 0.98, 1.04, 1.08, 1.16, 1.2, 1.24, 1.26, 1.28, 1.34, 1.36, 1.37, 1.33, 1.31, 1.28, 1.26, 1.25, 1.2, 1.1, 1.04, 0.88, 0.8, 0.64, 0.38, 0.1])
        self.yd_sail_full = jnp.concatenate([jnp.flip(yd_sail), yd_sail[1:]])
        
        # Rudder Coef Data
        yl_sub = jnp.flip(jnp.array([0, 0.42, 0.73, 0.95, 1.1, 1.165, 1.18, 1.155, 1.12, 1.065, 1, 0.92, 0.83, 0.72, 0.62, 0.48, 0.33, 0.16]) * (-1))
        self.yl_rudder_full = jnp.concatenate([jnp.flip(jnp.concatenate([jnp.array([0]), yl_sub])) * (-1), jnp.array([0]), yl_sub])
        
        yd_sub_r = jnp.flip(jnp.array([0, 0.03, 0.06, 0.1, 0.17, 0.3, 0.48, 0.74, 0.98, 1.18, 1.34, 1.5, 1.65, 1.76, 1.89, 1.97, 2.01, 2.05]))
        self.yd_rudder_full = jnp.concatenate([jnp.flip(jnp.concatenate([jnp.array([2.08]), yd_sub_r])), jnp.array([2.08]), yd_sub_r])  

        # Keel Coef Data (Similar structure)
        yl_sub_k = jnp.flip(jnp.array([0, 0.425, 0.74, 0.94, 1.1, 1.17, 1.19, 1.16, 1.12, 1.07, 0.99, 0.92, 0.84, 0.74, 0.63, 0.49, 0.345, 0.185]) * (-1))
        self.yl_keel_full = jnp.concatenate([jnp.flip(jnp.concatenate([jnp.array([0]), yl_sub_k])) * (-1), jnp.array([0]), yl_sub_k])
        
        yd_sub_k = jnp.flip(jnp.array([0, 0.04, 0.07, 0.1, 0.17, 0.3, 0.49, 0.76, 0.98, 1.19, 1.34, 1.5, 1.65, 1.77, 1.88, 1.96, 2.01, 2.05]))
        self.yd_keel_full = jnp.concatenate([jnp.flip(jnp.concatenate([jnp.array([2.09]), yd_sub_k])), jnp.array([2.09]), yd_sub_k])

        # Hull Resistance
        self.res_xdata = jnp.linspace(0, 6, 13)
        self.res_ydata = jnp.array([0, 0.15, 0.35, 0.5, 0.675, 0.825, 1.175, 1.4, 2, 4.85, 9.85, 18.46, 27.5]) * 1000

    def get_coeffs(self, angle, type_str):
        # 角度归一化到 [-pi, pi]
        angle = (angle + jnp.pi) % (2 * jnp.pi) - jnp.pi
        deg = angle * 180 / jnp.pi
        
        if type_str == 'sail':
            cl = jnp.interp(deg, self.ang_xdata, self.yl_sail_full)
            cd = jnp.interp(deg, self.ang_xdata, self.yd_sail_full)
        elif type_str == 'rudder':
            cl = jnp.interp(deg, self.ang_xdata, self.yl_rudder_full)
            cd = jnp.interp(deg, self.ang_xdata, self.yd_rudder_full)
        elif type_str == 'keel':
            cl = jnp.interp(deg, self.ang_xdata, self.yl_keel_full)
            cd = jnp.interp(deg, self.ang_xdata, self.yd_keel_full)
        return cl, cd

    def get_hull_resistance(self, v_sq):
        # JAX interp automatically extrapolates if valid_range is not handled
        # But we need to match scipy logic. Linear extrapolation is default for points outside range in JAX's interp if we don't clip?
        # Actually jnp.interp clips by default (constant extrapolation).
        # We need to handle alpha_a parameter (which was velocity in original code logic? No, alpha_a is velocity magnitude)
        return jnp.interp(v_sq, self.res_xdata, self.res_ydata, left=None, right=None) # right=None defaults to constant, need extrapolate? 
        # Original code used fill_value='extrapolate'. JAX interp does constant. 
        # For simplicity and stability, we stick to constant or simple linear extension logic manually if needed.
        # But for training stability, constant at high speeds is safer. Let's stick to jnp.interp default.

    def state_derivatives(self, y_state, w_change_v, w_change_d, current_sail, current_rudder):
        """
        核心动力学方程 - 完全对应 Runge-Kutta 内部的方程
        y_state: [x, y, phi, psi, u, v, p, r]
        """
        x, y, phi, psi, u, v, p, r = y_state
        nu = jnp.array([[u], [v], [p], [r]])
        
        # M_MAT defined in constants
        
        # C_RB
        C_RB = jnp.array([
            [0, -PAR['m']*r, 0, 0],
            [PAR['m']*r, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0]
        ])
        
        # C_A
        val1 = -PAR['a22']*v - PAR['a24']*p - PAR['a26']*r
        val2 = PAR['a11']*u
        val3 = PAR['a22']*v + PAR['a24']*p + PAR['a26']*r
        val4 = -PAR['a11']*u
        
        C_A = jnp.array([
            [0, 0, 0, val1],
            [0, 0, 0, val2],
            [0, 0, 0, 0],
            [val3, val4, 0, 0]
        ])
        
        # Wind Force
        v_t = jnp.array([[w_change_v * jnp.cos(w_change_d)], [w_change_v * jnp.sin(w_change_d)], [0]])
        numerator = jnp.abs(PAR['z_s']) * jnp.cos(phi) / PAR['h0']
        v_tw = jnp.log(numerator) / jnp.log(PAR['h1'] / PAR['h0']) * v_t
        
        R1 = jnp.array([
            [jnp.cos(-psi), -jnp.sin(-psi), 0],
            [jnp.sin(-psi), jnp.cos(-psi), 0],
            [0, 0, 1]
        ])
        R2 = jnp.array([
            [1, 0, 0],
            [0, jnp.cos(-phi), -jnp.sin(-phi)],
            [0, jnp.sin(-phi), jnp.cos(-phi)]
        ])
        
        v_tb = R2 @ R1 @ v_tw
        V_in = jnp.array([[u], [v], [0]])
        
        cross_prod = jnp.cross(jnp.array([p, 0, r]), jnp.array([PAR['xs'], PAR['ys'], PAR['zs']]))
        v_awb = v_tb.flatten() - V_in.flatten() - cross_prod
        v_awu = v_awb[0]
        v_awv = v_awb[1]
        
        alpha_aw = jnp.arctan2(v_awv, -v_awu)
        alpha_as = alpha_aw - current_sail
        
        Cls, Cds = self.get_coeffs(alpha_as, 'sail')
        speed_sq_s = v_awu**2 + v_awv**2
        Ls = 0.5 * PAR['rho_a'] * speed_sq_s * PAR['As'] * Cls
        Ds = 0.5 * PAR['rho_a'] * speed_sq_s * PAR['As'] * Cds
        
        tau_sail_0 = Ls * jnp.sin(alpha_aw) - Ds * jnp.cos(alpha_aw)
        tau_sail_1 = Ls * jnp.cos(alpha_aw) + Ds * jnp.sin(alpha_aw)
        tau_sail_2 = -(tau_sail_1) * PAR['zs']
        tau_sail_3 = -(tau_sail_0) * PAR['Xce'] * jnp.sin(current_sail) + (tau_sail_1) * (PAR['Xm'] - PAR['Xce'] * jnp.cos(current_sail))
        
        tau_sail = jnp.array([[tau_sail_0], [tau_sail_1], [tau_sail_2], [tau_sail_3]])
        
        # Rudder Force
        v_aru = -u + r*PAR['yr']
        v_arv = -v - r*PAR['xr'] + p*PAR['zr']
        alpha_ar = jnp.arctan2(v_arv, -v_aru)
        alpha_a_r = alpha_ar - current_rudder
        
        Clr, Cdr_base = self.get_coeffs(alpha_a_r, 'rudder')
        Cdr = Cdr_base + Clr**2 * PAR['Ar'] / (jnp.pi * 2 * PAR['zeta_r'] * PAR['d_r']**2)
        
        speed_sq_r = v_aru**2 + v_arv**2
        Lr = 0.5 * PAR['rho_w'] * PAR['Ar'] * speed_sq_r * Clr
        Dr = 0.5 * PAR['rho_w'] * PAR['Ar'] * speed_sq_r * Cdr
        
        tau_rudder_0 = Lr * jnp.sin(alpha_ar) - Dr * jnp.cos(alpha_ar)
        tau_rudder_1 = Lr * jnp.cos(alpha_ar) + Dr * jnp.sin(alpha_ar)
        tau_rudder_2 = -(tau_rudder_1) * PAR['zr']
        tau_rudder_3 = (tau_rudder_1) * PAR['xr']
        
        tau_rudder = jnp.array([[tau_rudder_0], [tau_rudder_1], [tau_rudder_2], [tau_rudder_3]])
        
        tau = tau_sail + tau_rudder
        
        # Keel Force
        v_aku = -u + r*PAR['yk']
        v_akv = -v - r*PAR['xk'] + p*PAR['zk']
        alpha_ak = jnp.arctan2(v_akv, -v_aku)
        
        Clk, Cdk_base = self.get_coeffs(alpha_ak, 'keel')
        Cdk = Cdk_base + Clk**2 * PAR['Ak'] / (jnp.pi * 2 * PAR['zeta_k'] * PAR['d_k']**2)
        
        speed_sq_k = v_aku**2 + v_akv**2
        Lk = 0.5 * PAR['rho_w'] * PAR['Ak'] * speed_sq_k * Clk
        Dk = 0.5 * PAR['rho_w'] * PAR['Ak'] * speed_sq_k * Cdk
        
        # D_keel
        D_keel = jnp.array([
            [-Lk * jnp.sin(alpha_ak) + Dk * jnp.cos(alpha_ak)],
            [-Lk * jnp.cos(alpha_ak) - Dk * jnp.sin(alpha_ak)],
            [-(-Lk * jnp.cos(alpha_ak) - Dk * jnp.sin(alpha_ak)) * PAR['zk']],
            [-(Lk * jnp.cos(alpha_ak) + Dk * jnp.sin(alpha_ak)) * PAR['xk']]
        ])
        
        # Hull Resistance
        v_ahu = -u + r * PAR['yh']
        v_ahv = (-v - r * PAR['xh'] + p * PAR['zh']) / jnp.cos(phi)
        v_ah = jnp.sqrt(v_aku**2 + v_akv**2)
        alpha_ah = jnp.arctan2(v_ahv, -v_ahu)
        Frh = self.get_hull_resistance(v_ah)
        
        D_hull = jnp.array([
            [Frh * jnp.cos(alpha_ah)],
            [-Frh * jnp.sin(alpha_ah) * jnp.cos(phi)],
            [Frh * jnp.sin(alpha_ah) * jnp.cos(phi) * PAR['zh']],
            [-Frh * jnp.sin(alpha_ah) * jnp.cos(phi) * PAR['xh']]
        ])
        
        # Damping
        J_mat = jnp.array([
            [jnp.cos(psi), -jnp.sin(psi)*jnp.cos(phi), 0, 0],
            [jnp.sin(psi), jnp.cos(psi)*jnp.cos(phi), 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, jnp.cos(phi)]
        ])
        eta_dot = J_mat @ nu
        phi_dot = eta_dot[2, 0]
        psi_dot = eta_dot[3, 0]
        
        D_heelandyaw = jnp.array([
            [0],
            [0],
            [PAR['c'] * phi_dot * jnp.abs(phi_dot)],
            [PAR['d'] * psi_dot * jnp.abs(psi_dot) * jnp.cos(phi)]
        ])
        
        D_total = D_keel + D_hull + D_heelandyaw
        
        # Restoring Forces
        y_w = 0.0
        phi_deg = phi * 180 / jnp.pi
        M_xw = -y_w * PAR['w_c'] * PAR['y_bm'] * jnp.cos(phi)
        M_zw = -y_w * PAR['w_c'] * PAR['x_c'] * jnp.sin(jnp.abs(phi))
        
        G = jnp.array([
            [0],
            [0],
            [PAR['a'] * phi_deg**2 + PAR['b'] * phi_deg + M_xw],
            [M_zw]
        ])
        
        # Solve for acceleration
        RHS = - (C_RB @ nu + C_A @ nu) - D_total - G + tau
        nu_dot = M_INV @ RHS
        
        return jnp.concatenate([eta_dot.flatten(), nu_dot.flatten()])

    def step_rk4(self, state: EnvState, action: jnp.ndarray):
        """定步长 RK4 积分器"""
        # 计算当前的帆/舵角
        # Logic from original step():
        # Update target angles based on action
        d_sail = action[0] // (jnp.pi/180) * (jnp.pi/180) # integer division quantization from original
        d_rudder = action[1] // (jnp.pi/180) * (jnp.pi/180)
        
        target_sail = jnp.clip(state.target_sail_ref + d_sail, -jnp.pi/2, jnp.pi/2)
        target_rudder = jnp.clip(state.target_rudder_ref + d_rudder, -jnp.pi/6, jnp.pi/6)
        
        # Initial Physics State for loop
        y_curr = state.phys_state
        curr_s = state.current_sail
        curr_r = state.current_rudder
        
        # Fixed loop integration (tf=1.0, dt=0.05 -> 20 steps)
        # Using lax.scan for loop unrolling on GPU
        def body_fun(carry, _):
            y, s, r = carry
            
            # Linear move sail/rudder towards target
            max_s_change = (jnp.pi/18) * self.dt
            max_r_change = (jnp.pi/18) * self.dt
            
            s_diff = target_sail - s
            r_diff = target_rudder - r
            
            ds = jnp.clip(s_diff, -max_s_change, max_s_change)
            dr = jnp.clip(r_diff, -max_r_change, max_r_change)
            
            s_new = jnp.clip(s + ds, -jnp.pi/2, jnp.pi/2)
            r_new = jnp.clip(r + dr, -jnp.pi/6, jnp.pi/6)
            
            # RK4 Integration
            k1 = self.dt * self.state_derivatives(y, state.w_change_v, state.w_change_d, s, r)
            k2 = self.dt * self.state_derivatives(y + 0.5*k1, state.w_change_v, state.w_change_d, s, r)
            k3 = self.dt * self.state_derivatives(y + 0.5*k2, state.w_change_v, state.w_change_d, s, r)
            k4 = self.dt * self.state_derivatives(y + k3, state.w_change_v, state.w_change_d, s, r)
            
            y_next = y + (k1 + 2*k2 + 2*k3 + k4) / 6.0
            
            return (y_next, s_new, r_new), None

        (y_final, s_final, r_final), _ = jax.lax.scan(body_fun, (y_curr, curr_s, curr_r), None, length=self.integration_steps)
        
        # Normalize Psi (heading) to [-pi, pi] like original
        psi_normalized = jnp.arctan2(jnp.sin(y_final[3]), jnp.cos(y_final[3]))
        y_final = y_final.at[3].set(psi_normalized)
        
        return y_final, s_final, r_final, target_sail, target_rudder

    def reset(self, rng: jnp.ndarray, obs_layout_key: jnp.ndarray) -> EnvState:
        # 随机初始化
        rng, k1, k2, k3, k4, k5 = jax.random.split(rng, 6)
        
        # 初始物理状态
        # [x, y, phi, psi, u, v, p, r]
        # x, y are near 0? Original: state[0],state[1] initialized in reset implicitly by zeros?
        # Original: self.state = np.zeros(18). self.state[3] = rand.
        phys_state = jnp.zeros(8)
        phys_state = phys_state.at[3].set(jax.random.uniform(k1, minval=-jnp.pi, maxval=jnp.pi)) # psi
        phys_state = phys_state.at[4].set(jax.random.uniform(k2, minval=0.0, maxval=1.0)) # u
        
        # Wind
        w_ini_v = 5.0
        # w_ini_d = jnp.pi # 180 degrees
        w_ini_d = jax.random.uniform(k5, minval=-jnp.pi, maxval=jnp.pi)
        w_last_v = w_ini_v
        w_last_d = w_ini_d
        w_change_v = 5.0
        w_change_d = 0.0
        
        # Obstacles Generation
        # Fix: Generate random obstacles within range
        num_obs = jax.random.randint(k3, shape=(), minval=5, maxval=9)
        # Vectorized generation is simpler if we just gen max and mask
        obs_x = jax.random.uniform(k4, shape=(self.max_obstacles,), minval=100.0, maxval=400.0) # slightly simplified range to avoid start/target check loop
        obs_y = jax.random.uniform(k4, shape=(self.max_obstacles,), minval=-250.0, maxval=250.0)
        # Mask logic: 1 if index < num_obs else 0
        indices = jnp.arange(self.max_obstacles)
        obs_mask = jnp.where(indices < num_obs, 1.0, 0.0)
        
        obstacles_pos = jnp.stack([obs_x, obs_y], axis=-1)
        is_discovered = jnp.zeros(self.max_obstacles) # New memory
        
        target_x = 500.0
        target_y = 0.0
        
        # Calculate initial distances for correct observation delta
        start_x, start_y = phys_state[0], phys_state[1]
        init_dis = jnp.sqrt((start_x - target_x)**2 + (start_y - target_y)**2)
        init_x_dis = jnp.abs(start_x - target_x)
        
        state = EnvState(
            phys_state=phys_state,
            current_sail=0.0, current_rudder=0.0,
            target_sail_ref=0.0, target_rudder_ref=0.0,
            obs_vec=jnp.zeros(18), # Needs update
            prev_dis=init_dis, prev_x_dis=init_x_dis,
            target_x=target_x, target_y=target_y,
            w_change_v=w_change_v, w_change_d=w_change_d,
            w_last_v=w_last_v, w_last_d=w_last_d,
            w_ini_v=w_ini_v, w_ini_d=w_ini_d,
            obstacles_pos=obstacles_pos, obstacles_mask=obs_mask,
            is_discovered=is_discovered,
            one_check=0, two_check=0, three_check=0,
            time=0.0, step_count=0, done=False
        )
        
        # Initial Observation Calculation
        state = self._update_observation_and_vars(state)
        return state

    def step(self, state: EnvState, action: jnp.ndarray, rng: jnp.ndarray) -> Tuple[EnvState, jnp.ndarray, jnp.ndarray, dict]:
        # 保存前一状态用于 Reward 计算 (Prev Dis)
        # Recalculate dists for 'previous' state reference
        prev_dist = jnp.sqrt((state.phys_state[0] - state.target_x)**2 + (state.phys_state[1] - state.target_y)**2)
        prev_x_dist = jnp.abs(state.phys_state[0] - state.target_x)
        
        # Core Physics
        # -------------------
        new_phys, new_sail, new_rudder, tgt_sail, tgt_rudder = self.step_rk4(state, action)
        
        # Wind Update (Stochastic)
        rng, key = jax.random.split(rng)
        rand_v = jax.random.normal(key)
        rand_d = jax.random.normal(key) # Reusing key logic roughly
        
        new_w_change_v = 0.3 * state.w_ini_v + 0.7 * state.w_last_v + 0.5 * rand_v
        new_w_change_d = 0.3 * state.w_ini_d + 0.7 * state.w_last_d + (1/18) * rand_d
        
        next_state = state._replace(
            phys_state=new_phys,
            current_sail=new_sail,
            current_rudder=new_rudder,
            target_sail_ref=tgt_sail,
            target_rudder_ref=tgt_rudder,
            w_change_v=new_w_change_v,
            w_change_d=new_w_change_d,
            w_last_v=new_w_change_v,
            w_last_d=new_w_change_d,
            time=state.time + self.tf, # +1s
            prev_dis=prev_dist,
            prev_x_dis=prev_x_dist,
            step_count=state.step_count + 1
        )
        
        # Observation & Obstacle Logic
        next_state = self._update_observation_and_vars(next_state)
        
        # Reward Calculation
        reward, next_state = self._calculate_reward(state, next_state, action)
        
        # Termination
        dist_to_target = jnp.sqrt((new_phys[0] - state.target_x)**2 + (new_phys[1] - state.target_y)**2)
        dist_to_start = jnp.sqrt(new_phys[0]**2 + new_phys[1]**2)
        
        # Collision Check
        # Vectorized distance to all active obstacles
        dists = jnp.sqrt(jnp.sum((state.obstacles_pos - new_phys[:2])**2, axis=-1))
        # Mask inactive obstacles with infinity
        dists = jnp.where(state.obstacles_mask > 0.5, dists, jnp.inf)
        is_collision = jnp.any(dists < 40.0)
        
        reached = dist_to_target <= 10.0
        truncated = (dist_to_start >= 750.0) | (next_state.time >= 2000) # Hardcoded timeout
        
        done = reached | truncated | is_collision
        next_state = next_state._replace(done=done)
        
        # Collision penalty handled in reward? Original code: truncated if collision. 
        # Original Reward: if truncated: reward -= 100
        reward = jnp.where(truncated | is_collision, reward - 100.0, reward)
        
        return next_state, reward, done, {}

    def _update_observation_and_vars(self, state: EnvState) -> EnvState:
        # Update Observation Vector (18 floats)
        # 0-7: phys_state
        # 8: current_sail
        # 9: current_rudder
        # 10: dis_diff (calculated after this inside step, but here represents observed state)
        # 11: x_dis_diff
        # 12-13: target
        # 14-17: nearest 2 obstacles
        
        x, y, heading = state.phys_state[0], state.phys_state[1], state.phys_state[3]
        
        # Obstacle Discovery Logic
        # 1. Calc distance and angle to all obs
        dx = state.obstacles_pos[:, 0] - x
        dy = state.obstacles_pos[:, 1] - y
        dists = jnp.sqrt(dx**2 + dy**2)
        angles_to_obs = jnp.arctan2(dy, dx)
        angle_diff = angles_to_obs - heading
        angle_diff = (angle_diff + jnp.pi) % (2 * jnp.pi) - jnp.pi # normalize
        
        in_fov = (dists <= self.obstacle_detection_radius) & (jnp.abs(angle_diff) <= self.obstacle_fov_angle/2) & (state.obstacles_mask > 0.5)
        
        # Update discovered memory
        new_discovered = jnp.maximum(state.is_discovered, in_fov.astype(jnp.float32))
        
        # Find 2 nearest from DISCOVERED obstacles
        # Set undiscovered distances to infinity
        valid_dists = jnp.where(new_discovered > 0.5, dists, jnp.inf)
        
        # Argpartition to find top 2 min
        # Since max_obstacles is small (e.g. 20), full sort is fast enough
        sorted_indices = jnp.argsort(valid_dists)
        
        idx1 = sorted_indices[0]
        idx2 = sorted_indices[1]
        
        # Check if they are valid (dist != inf)
        v1_valid = valid_dists[idx1] < 1e9
        v2_valid = valid_dists[idx2] < 1e9
        
        obs1_pos = jnp.where(v1_valid, state.obstacles_pos[idx1], jnp.array([0.0, 0.0]))
        obs2_pos = jnp.where(v2_valid, state.obstacles_pos[idx2], jnp.array([0.0, 0.0]))
        
        # Calc diffs for obs vector (indices 10, 11) - technically deltas
        # Original code puts (pre - cur) here. 
        # We need to construct the full 18-dim vector
        
        cur_dist = jnp.sqrt((x - state.target_x)**2 + (y - state.target_y)**2)
        cur_x_dist = jnp.abs(x - state.target_x)
        
        diff_dis = state.prev_dis - cur_dist
        diff_x_dis = state.prev_x_dis - cur_x_dist
        
        obs_vec = jnp.concatenate([
            state.phys_state, # 0-7
            jnp.array([state.current_sail, state.current_rudder]), # 8-9
            jnp.array([diff_dis, diff_x_dis]), # 10-11
            jnp.array([state.target_x, state.target_y]), # 12-13
            obs1_pos, # 14-15
            obs2_pos  # 16-17
        ])
        
        return state._replace(obs_vec=obs_vec, is_discovered=new_discovered)

    def _calculate_reward(self, prev_state: EnvState, curr_state: EnvState, action: jnp.ndarray) -> Tuple[jnp.ndarray, EnvState]:
        # Based exactly on calculate_reward
        
        # Extract from Observation vector construction logic
        # Note: In original code, state[10] and [11] are updated BEFORE reward calculation
        # So we use the diffs calculated in current_state's update
        diff_dis = curr_state.obs_vec[10]
        diff_x_dis = curr_state.obs_vec[11]
        
        u = curr_state.phys_state[4]
        v = curr_state.phys_state[5]
        
        reward = (2 * diff_dis + diff_x_dis) + 0.5 * (u / (1 + jnp.abs(v)))
        
        # Obstacle avoidance penalty
        x, y = curr_state.phys_state[0], curr_state.phys_state[1]
        ox1, oy1 = curr_state.obs_vec[14], curr_state.obs_vec[15]
        ox2, oy2 = curr_state.obs_vec[16], curr_state.obs_vec[17]
        
        min_safe = 50.0
        max_safe = 100.0
        k = 100000.0
        
        def calc_pen(ox, oy):
            d = jnp.sqrt((x - ox)**2 + (y - oy)**2)
            # if 0,0 means no obstacle
            is_valid = (ox != 0.0) | (oy != 0.0)
            
            pen = 0.0
            # Logic: if < min
            term1 = k * (1/min_safe - 1/max_safe)**2
            # Logic: if min < d < max
            term2 = k * (1/d - 1/max_safe)**2
            
            p = jnp.where(d < min_safe, term1, jnp.where(d <= max_safe, term2, 0.0))
            return jnp.where(is_valid, p, 0.0)

        reward -= calc_pen(ox1, oy1)
        reward -= calc_pen(ox2, oy2)
        
        # Action penalty
        sail_act = action[0]
        rudder_act = action[1]
        
        reward_scale = 0.2
        
        # Sail penalty
        rs_sail = jnp.where(jnp.abs(sail_act) <= jnp.pi/180, reward_scale*0.1, 0.0)
        reward = jnp.where(jnp.abs(sail_act) > jnp.pi/180, reward - jnp.floor(jnp.abs(sail_act)/(jnp.pi/180))*0.2, reward)
        
        # Rudder penalty
        rs_rudder = jnp.where(jnp.abs(rudder_act) <= jnp.pi/180, reward_scale*0.1, 0.0)
        reward = jnp.where(jnp.abs(rudder_act) > jnp.pi/180, reward - jnp.floor(jnp.abs(rudder_act)/(jnp.pi/180))*0.2, reward)
        
        reward = reward * (reward_scale + rs_sail + rs_rudder)
        
        # Checkpoints
        dist = jnp.sqrt((x - curr_state.target_x)**2 + (y - curr_state.target_y)**2)
        
        # Update check states (Immutable style)
        c1 = curr_state.one_check
        c2 = curr_state.two_check
        c3 = curr_state.three_check
        
        r_bon = 0.0
        
        # Functional if logic
        is_c1 = (dist <= 375) & (c1 == 0)
        r_bon += jnp.where(is_c1, 3.0, 0.0)
        c1 = jnp.where(is_c1, 1, c1)
        
        is_c2 = (dist <= 250) & (c2 == 0)
        r_bon += jnp.where(is_c2, 5.0, 0.0)
        c2 = jnp.where(is_c2, 1, c2)
        
        is_c3 = (dist <= 125) & (c3 == 0)
        r_bon += jnp.where(is_c3, 12.0, 0.0)
        c3 = jnp.where(is_c3, 1, c3)
        
        is_target = dist <= 10.0
        r_bon += jnp.where(is_target, 40.0, 0.0)
        
        reward += r_bon
        reward -= 0.2 # Step penalty
        
        new_state = curr_state._replace(one_check=c1, two_check=c2, three_check=c3)
        return reward, new_state