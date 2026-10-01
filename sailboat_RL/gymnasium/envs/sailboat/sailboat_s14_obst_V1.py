import numpy as np
import pygame
from typing import Optional
import globals

import math
import random
import time
import gymnasium as gym
from gymnasium import spaces
from gymnasium.utils import EzPickle
from scipy.interpolate import interp1d

from scipy.integrate import solve_ivp
from scipy.integrate import ode

FPS = 60

class Sailboat_obst(gym.Env,EzPickle):
    metadata = {
        "render_modes": ["human", "rgb_array"],
        "render_Fps": FPS,
    }

    def __init__(
            self,
            render_mode: Optional[str] = None,
            ):

        EzPickle.__init__(
            self,
            render_mode,) 

        # 定义常量
        super(Sailboat_obst, self).__init__()
        # global current_state, current_action, previous_state, previous_action, current_time, total_time
        # global path, end_pos, w0, var_v, var_d, w_change_v, w_change_d, w_last_v, w_last_d, w_ini_v, w_ini_d
        
        #仿真时间相关
        self.dt = 0.05
        self.step_per_action = int(1.0 / self.dt)   

        self.par = {
            'm': 25900,                         # (kg),mass of the vehicle
            'Ixx': 133690,          
            'Izz': 24760,      
            'Ixz': 2180,                        # moment of inertia
            'a11': 970,   
            'a22': 17430, 
            'a44': 106500,
            'a66': 101650,
            'a24': -13160,
            'a26': -6190, 
            'a46': 4730,                        # (kg),added mass coef.
            'rho_a': 1.2,                       # (kg/m^3), air density
            'As': 170,                          # (m^2), sail area, ini_area is 170
            'h0': 0.0005,                       # (m), roughness height ini is 0.0005
            'h1': 11.58,                        # (m), reference height
            'z_s': -11.58,                      # (m), (x,y,z) is the CoE
            'xs': 0,
            'ys': 0,
            'zs': -11.58,                       # (m), (x,y,z) is the CoE
            'Xce': 0.6,                         # (m), distance along the mast to the CoE
            'Xm': 0.3,                          # (m), x-coordinate of the mast 
            'rho_w': 1025,                      # (kg/m^3), water density
            'Ar': 1.17,                         # (m^2), rudder area
            'd_r': 1.9,                         # rudder draft
            'zeta_r': 0.8,                      # rudder efficiency
            'x_r': -8.2,
            'z_r': -0.78,                       # (m), (x,y,z) is the CoE
            'xr': -8.2,
            'yr': 0,
            'zr': -0.78,                        # (m), (x,y,z) is the CoE
            'Ak': 8.7,                          # (m^2), keel area
            'd_k': 2.49,                        # keel draft
            'zeta_k': 0.7,                      # keel efficiency
            'x_k': 0,
            'z_k': -0.58,                       # (m), (x,y,z) is the CoE
            'xk': 0,
            'yk': 0,
            'zk': -0.58,                        # (m), (x,y,z) is the CoE
            'x_h': 0,
            'z_h': -1.18,                       # (m), (x,y,z) is the CoE
            'xh': 0,
            'yh': 0,
            'zh': -1.18,                        # (m), (x,y,z) is the CoE
            'w_c': 60000,                       # (N), crew weight 20000
            'x_c': -8,                          # (m), crew position
            'y_bm': 3.6,                        # (m), yacht beam
            'a': -5.89,
            'b': 8160,
            'c': 120000,
            'd': 50000
        }

        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(18,), dtype=np.float32)
        self.action_space = spaces.Box(low=np.array([-np.pi/18, -np.pi/18]), high=np.array([np.pi/18, np.pi/18]), dtype=np.float32)
        self.max_sail_rate = np.pi/18  # 每步最大帆角变化量（弧度)
        self.max_rudder_rate = np.pi/18  # 每步最大舵角变化量（弧度)
        self.target_sail_angle = 0.0
        self.target_rudder_angle = 0.0
        self.state = None
        self.screen = None

        self.reset()

        self.viewer = None
        self.clock = pygame.time.Clock()


    def step(self, action):
        # global current_state, current_action, previous_state, previous_action,current_time, total_time
        # global path, end_pos, w0, var_v, var_d, w_change_v, w_change_d, w_last_v, w_last_d, w_ini_v, w_ini_d 
        t = 0
        tf = 1
        dt = 0.05
        tol = 1e-6
        flag = True
        sail_error = False
        rudder_error = False
        pre_dis = 0
        cur_dis = 0
        pre_x_dis = 0
        cur_x_dis = 0
        #采样时间与仿真时间
        if flag:
            previous_state = np.copy(self.state[0:12])
            flag = False
        globals.current_state = self.state[0:12]
        globals.current_action = action
        globals.state = np.copy(self.state[0:18])
        globals.path.append((self.state[0], self.state[1]))
        self.target_sail_angle = np.clip(self.target_sail_angle + action[0] // (np.pi/180) * (np.pi/180), -np.pi/2, np.pi/2)
        self.target_rudder_angle = np.clip(self.target_rudder_angle + action[1] // (np.pi/180) * (np.pi/180), -np.pi/6, np.pi/6)

        def state_derivatives(state, action):
            x, y, phi, psi, u, v, p, r = state[0:8]
            nu = np.array([[u], [v], [p], [r]])
            delta_s, delta_r = action[0:2]
            y_w = 0
            current_sail = globals.current_state[8]
            current_rudder = globals.current_state[9]

            sail_diff = self.target_sail_angle - current_sail
            rudder_diff = self.target_rudder_angle - current_rudder

            max_sail_change = self.max_sail_rate * dt
            max_rudder_change = self.max_rudder_rate * dt

            delta_sail = np.clip(sail_diff, -max_sail_change, max_sail_change)
            delta_rudder = np.clip(rudder_diff, -max_rudder_change, max_rudder_change)

            sail = current_sail + delta_sail
            rudder = current_rudder + delta_rudder

            sail = np.clip(sail, -np.pi/2, np.pi/2)
            rudder = np.clip(rudder, -np.pi/6, np.pi/6)
            
            M_RB = np.array([
                [self.par['m'], 0, 0, 0],
                [0, self.par['m'], 0, 0],
                [0, 0, self.par['Ixx'], -self.par['Ixz']],
                [0, 0, -self.par['Ixz'], self.par['Izz']]
            ])

            C_RB = np.array([
                [0,-self.par['m']*r,0,0],
                [self.par['m']*r,0,0,0],
                [0,0,0,0],
                [0,0,0,0]
            ])

            M_A = np.array([
                [self.par['a11'], 0, 0, 0],
                [0, self.par['a22'], self.par['a24'], self.par['a26']],
                [0, self.par['a24'], self.par['a44'], self.par['a46']],
                [0, self.par['a26'], self.par['a46'], self.par['a66']]
            ])

            C_A = np.array([
                [0,0,0,-self.par['a22']*nu[1,0] - self.par['a24']*nu[2,0] - self.par['a26']*nu[3,0]],
                [0, 0, 0, self.par['a11']*nu[0,0]],
                [0, 0, 0, 0],
                [self.par['a22']*nu[1,0] + self.par['a24']*nu[2,0] + self.par['a26']*nu[3,0], -self.par['a11']*nu[0,0], 0, 0]
                ])
            
            M = M_RB + M_A

            v_t = np.array([
                [globals.w_change_v*np.cos(globals.w_change_d)], 
                [globals.w_change_v*np.sin(globals.w_change_d)],
                [0]
                  ])
            
            numerator = abs(self.par['z_s']) * np.cos(phi) / self.par['h0']
            # numerator = np.where(numerator <= 0, 1e-10, numerator)

            v_tw = np.log(numerator)/np.log(self.par['h1']/self.par['h0'])*v_t
            R1 = np.array([
                [np.cos(-psi), -np.sin(-psi), 0],
                [np.sin(-psi), np.cos(-psi), 0],
                [0, 0, 1]
            ])
            R2 = np.array([
                [1, 0, 0],
                [0, np.cos(-phi), -np.sin(-phi)],
                [0, np.sin(-phi), np.cos(-phi)]
            ])

            v_tb = R2 @ R1 @ v_tw
            V_in = np.array([[u], [v], [0]])

            cross_1 = np.array([[p],[0],[r]])
            cross_2 = np.array([[self.par['xs']],[self.par['ys']],[self.par['zs']]])
            v_awb = v_tb - V_in - np.cross(cross_1.flatten(),cross_2.flatten())
            v_awu = v_awb[0][0]
            v_awv = v_awb[1][0]
            alpha_aw = np.arctan2(v_awv,-v_awu)

            alpha_as = alpha_aw - sail

            Cls,Cds = sailcoef(alpha_as)
            Ls = 0.5 * self.par['rho_a'] * (v_awu**2 + v_awv**2) * self.par['As'] * Cls
            Ds = 0.5 * self.par['rho_a'] * (v_awu**2 + v_awv**2) * self.par['As'] * Cds
            tau_sail = np.array([
                [Ls * np.sin(alpha_aw) - Ds * np.cos(alpha_aw)],
                [Ls * np.cos(alpha_aw) + Ds * np.sin(alpha_aw)],
                [-(Ls * np.cos(alpha_aw) + Ds * np.sin(alpha_aw)) * self.par['zs']],
                [-(Ls * np.sin(alpha_aw) - Ds * np.cos(alpha_aw)) * self.par['Xce'] * np.sin(sail) + (Ls * np.cos(alpha_aw) + Ds * np.sin(alpha_aw)) * (self.par['Xm'] - self.par['Xce'] * np.cos(sail))]
            ])

            Mzs = tau_sail[3]

            v_aru = -u+r*self.par['yr']
            v_arv = -v-r*self.par['xr']+p*self.par['zr']
            alpha_ar = np.arctan2(v_arv,-v_aru)
            alpha_a = alpha_ar - rudder
            Clr, Cdr = ruddercoef(alpha_a)
            Cdr = Cdr+Clr**2*self.par['Ar']/(np.pi*2*self.par['zeta_r']*self.par['d_r']**2)
            Lr = 0.5*self.par['rho_w']*self.par['Ar']*(v_aru**2+v_arv**2)*Clr
            Dr = 0.5*self.par['rho_w']*self.par['Ar']*(v_aru**2+v_arv**2)*Cdr

            tau_rudder = np.array([
                [Lr*np.sin(alpha_ar)-Dr*np.cos(alpha_ar)],
                [Lr*np.cos(alpha_ar)+Dr*np.sin(alpha_ar)],
                [-(Lr*np.cos(alpha_ar)+Dr*np.sin(alpha_ar))*self.par['zr']],
                [(Lr*np.cos(alpha_ar)+Dr*np.sin(alpha_ar))*self.par['xr']]
            ])
            
            Mzr = tau_rudder[3]

            tau = tau_sail + tau_rudder

            v_aku = -u+r*self.par['yk']
            v_akv = -v-r*self.par['xk']+p*self.par['zk']
            alpha_ak = np.arctan2(v_akv,-v_aku)
            alpha_e = alpha_ak
            clk, cdk = keelcoef(alpha_e)
            cdk = cdk + (clk**2)*self.par['Ak']/(np.pi*2*self.par['zeta_k']*(self.par['d_k']**2))

            Lk = 0.5 * self.par['rho_w'] * self.par['Ak'] * (v_aku**2 + v_akv**2) * clk
            Dk = 0.5 * self.par['rho_w'] * self.par['Ak'] * (v_aku**2 + v_akv**2) * cdk

            # 计算 D_keel
            D_keel = np.array([
                [-Lk * np.sin(alpha_ak) + Dk * np.cos(alpha_ak)],
                [-Lk * np.cos(alpha_ak) - Dk * np.sin(alpha_ak)],
                [-(-Lk * np.cos(alpha_ak) - Dk * np.sin(alpha_ak)) * self.par['zk']],
                [-(Lk * np.cos(alpha_ak) + Dk * np.sin(alpha_ak)) * self.par['xk']]
            ])

            v_ahu = -u + r * self.par['yh']
            v_ahv = (-v - r * self.par['xh'] + p * self.par['zh'])/np.cos(phi)
            v_ah = np.sqrt(v_aku**2 + v_akv**2)
            alpha_ah = np.arctan2(v_ahv, -v_ahu)
            Frh = resistancehull(v_ah)
            
            # 计算 D_hull
            D_hull = np.array([
                [Frh * np.cos(alpha_ah)],
                [-Frh * np.sin(alpha_ah) * np.cos(phi)],
                [Frh * np.sin(alpha_ah) * np.cos(phi) * self.par['zh']],
                [-Frh * np.sin(alpha_ah) * np.cos(phi) * self.par['xh']]
            ])

            # 计算 heel 和 yaw 的阻尼力
            J = np.array([
                [np.cos(psi), -np.sin(psi) * np.cos(phi), 0, 0],
                [np.sin(psi), np.cos(psi) * np.cos(phi), 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, np.cos(phi)]
            ])
            eta_dot = J @ nu
            phi_dot = eta_dot[2,0]
            psi_dot = eta_dot[3,0]

            D_heelandyaw = np.array([
                [0],
                [0],
                [self.par['c'] * phi_dot * abs(phi_dot)],
                [self.par['d'] * psi_dot * abs(psi_dot) * np.cos(phi)]
            ])

            # 计算总阻尼向量 D
            D = D_keel + D_hull + D_heelandyaw

            # 计算复原力矩和内部移动质量系统（即横向重量）
            phi_deg = phi * 180 / np.pi
            M_xw = -y_w * self.par['w_c'] * self.par['y_bm'] * np.cos(phi)
            M_zw = -y_w * self.par['w_c'] * self.par['x_c'] * np.sin(abs(phi))
            G = np.array([
                [0],
                [0],
                [self.par['a'] * phi_deg**2 + self.par['b'] * phi_deg + M_xw],
                [M_zw]
            ])

            # 计算 nu_dot
            nu_dot = -np.linalg.solve(M, C_RB @ nu + C_A @ nu) - np.linalg.solve(M, D) - np.linalg.solve(M, G) + np.linalg.solve(M, tau)

            # 输出状态导数扩展与帆角
            X_dot_ext = np.concatenate([eta_dot.flatten(), nu_dot.flatten()])

            return X_dot_ext


        def sailcoef(attack):
            # 生成升力/阻力系数的查找表并使用插值计算 Cls/Cds

            # 查找表
            xdata = np.linspace(-np.pi, np.pi, 73)  # 每 5 度
            xdata = xdata / np.pi * 180

            # 升力曲线
            yldata = np.concatenate([
                np.flip([0, 0.15, 0.32, 0.48, 0.7, 0.94, 1.15, 1.3, 1.28, 1.15, 1.1, 1.05, 1, 0.9, 0.82, 0.72, 0.68, 0.56, 0.48, 0.32, 0.21, 0.08, -0.06, -0.18, -0.3, -0.4, -0.53, -0.64, -0.72, -0.84, -0.95, -1.04, -1.1, -1.14, -1.08, -0.76, 0]) * (-1),
                [0.15, 0.32, 0.48, 0.7, 0.94, 1.15, 1.3, 1.28, 1.15, 1.1, 1.05, 1, 0.9, 0.82, 0.72, 0.68, 0.56, 0.48, 0.32, 0.21, 0.08, -0.06, -0.18, -0.3, -0.4, -0.53, -0.64, -0.72, -0.84, -0.95, -1.04, -1.1, -1.14, -1.08, -0.76, 0]
            ])

            # 阻力曲线
            yddata = np.concatenate([
                np.flip([0.1, 0.12, 0.14, 0.16, 0.19, 0.26, 0.35, 0.46, 0.54, 0.62, 0.7, 0.78, 0.9, 0.98, 1.04, 1.08, 1.16, 1.2, 1.24, 1.26, 1.28, 1.34, 1.36, 1.37, 1.33, 1.31, 1.28, 1.26, 1.25, 1.2, 1.1, 1.04, 0.88, 0.8, 0.64, 0.38, 0.1]),
                [0.12, 0.14, 0.16, 0.19, 0.26, 0.35, 0.46, 0.54, 0.62, 0.7, 0.78, 0.9, 0.98, 1.04, 1.08, 1.16, 1.2, 1.24, 1.26, 1.28, 1.34, 1.36, 1.37, 1.33, 1.31, 1.28, 1.26, 1.25, 1.2, 1.1, 1.04, 0.88, 0.8, 0.64, 0.38, 0.1]
            ])

            # 将输入的攻角调整到 [-pi, pi] 范围内
            if attack > np.pi:
                attack = (attack + np.pi) % (2 * np.pi) - np.pi
            elif attack < -np.pi:
                attack = (attack - np.pi) % (-2 * np.pi) + np.pi

            # 插值计算
            attack = attack / np.pi * 180
            Cls = interp1d(xdata, yldata, kind='cubic')(attack)
            Cds = interp1d(xdata, yddata, kind='cubic')(attack)

            return Cls, Cds
        
        def ruddercoef(attack):
            # 生成升力/阻力系数的查找表并使用插值计算 Clr/Cdr

            # 查找表
            xdata = np.linspace(-np.pi, np.pi, 73)  # 每 5 度
            xdata = xdata / np.pi * 180

            # 升力曲线
            yl = np.flip([0, 0.42, 0.73, 0.95, 1.1, 1.165, 1.18, 1.155, 1.12, 1.065, 1, 0.92, 0.83, 0.72, 0.62, 0.48, 0.33, 0.16]) * (-1)
            yldata = np.concatenate([
                np.flip([0, 0.42, 0.73, 0.95, 1.1, 1.165, 1.18, 1.155, 1.12, 1.065, 1, 0.92, 0.83, 0.72, 0.62, 0.48, 0.33, 0.16, 0, *yl]) * (-1),
                [0.42, 0.73, 0.95, 1.1, 1.165, 1.18, 1.155, 1.12, 1.065, 1, 0.92, 0.83, 0.72, 0.62, 0.48, 0.33, 0.16, 0, *yl]
            ])

            # 阻力曲线
            yd = np.flip([0, 0.03, 0.06, 0.1, 0.17, 0.3, 0.48, 0.74, 0.98, 1.18, 1.34, 1.5, 1.65, 1.76, 1.89, 1.97, 2.01, 2.05])
            yddata = np.concatenate([
                np.flip([0, 0.03, 0.06, 0.1, 0.17, 0.3, 0.48, 0.74, 0.98, 1.18, 1.34, 1.5, 1.65, 1.76, 1.89, 1.97, 2.01, 2.05, 2.08, *yd]),
                [0.03, 0.06, 0.1, 0.17, 0.3, 0.48, 0.74, 0.98, 1.18, 1.34, 1.5, 1.65, 1.76, 1.89, 1.97, 2.01, 2.05, 2.08, *yd]
            ])

            # 将输入的攻角调整到 [-pi, pi] 范围内
            if attack > np.pi:
                attack = (attack + np.pi) % (2 * np.pi) - np.pi
            elif attack < -np.pi:
                attack = (attack - np.pi) % (-2 * np.pi) + np.pi

            # 插值计算
            attack = attack / np.pi * 180
            Clr = interp1d(xdata, yldata, kind='cubic')(attack)
            Cdr = interp1d(xdata, yddata, kind='cubic')(attack)

            return Clr, Cdr
        
        def keelcoef(attack):
            # 生成升力/阻力系数的查找表并使用插值计算 Clk/Cdk

            # 查找表
            xdata = np.linspace(-np.pi, np.pi, 73)  # 每 5 度
            xdata = xdata / np.pi * 180

            # 升力曲线
            yl = np.flip([0, 0.425, 0.74, 0.94, 1.1, 1.17, 1.19, 1.16, 1.12, 1.07, 0.99, 0.92, 0.84, 0.74, 0.63, 0.49, 0.345, 0.185]) * (-1)
            yldata = np.concatenate([
                np.flip([0, 0.425, 0.74, 0.94, 1.1, 1.17, 1.19, 1.16, 1.12, 1.07, 0.99, 0.92, 0.84, 0.74, 0.63, 0.49, 0.345, 0.185, 0, *yl]) * (-1),
                [0.425, 0.74, 0.94, 1.1, 1.17, 1.19, 1.16, 1.12, 1.07, 0.99, 0.92, 0.84, 0.74, 0.63, 0.49, 0.345, 0.185, 0, *yl]
            ])

            # 阻力曲线
            yd = np.flip([0, 0.04, 0.07, 0.1, 0.17, 0.3, 0.49, 0.76, 0.98, 1.19, 1.34, 1.5, 1.65, 1.77, 1.88, 1.96, 2.01, 2.05])
            yddata = np.concatenate([
                np.flip([0, 0.04, 0.07, 0.1, 0.17, 0.3, 0.49, 0.76, 0.98, 1.19, 1.34, 1.5, 1.65, 1.77, 1.88, 1.96, 2.01, 2.05, 2.09, *yd]),
                [0.04, 0.07, 0.1, 0.17, 0.3, 0.49, 0.76, 0.98, 1.19, 1.34, 1.5, 1.65, 1.77, 1.88, 1.96, 2.01, 2.05, 2.09, *yd]
            ])

            # 将输入的攻角调整到 [-pi, pi] 范围内
            if attack > np.pi:
                attack = (attack + np.pi) % (2 * np.pi) - np.pi
            elif attack < -np.pi:
                attack = (attack - np.pi) % (-2 * np.pi) + np.pi

            # 插值计算
            attack = attack / np.pi * 180
            Clk = interp1d(xdata, yldata, kind='cubic')(attack)
            Cdk = interp1d(xdata, yddata, kind='cubic')(attack)

            return Clk, Cdk

        def resistancehull(alpha_a):
            # 生成船体阻力的查找表并使用插值计算 F

            # 查找表
            xdata = np.linspace(0, 6, 13)  # 每 0.5 m/s
            ydata = np.array([0, 0.15, 0.35, 0.5, 0.675, 0.825, 1.175, 1.4, 2, 4.85, 9.85, 18.46, 27.5]) * 1000

            # 插值计算
            if alpha_a <= 6:
                F = interp1d(xdata, ydata, kind='cubic')(alpha_a)
            else:
                F = interp1d(xdata, ydata, kind='cubic', fill_value='extrapolate')(alpha_a)

            return F   
                


        while t < tf:
            y = globals.current_state[0:8]

            # Dormand-Prince coefficients (from MATLAB ode45)
            k1 = dt * state_derivatives(y, action)
            k2 = dt * state_derivatives(y + (1/5) * k1, action)
            k3 = dt * state_derivatives(y + (3/40) * k1 + (9/40) * k2, action)
            k4 = dt * state_derivatives(y + (44/45) * k1 - (56/15) * k2 + (32/9) * k3, action)
            k5 = dt * state_derivatives(y + (19372/6561) * k1 - (25360/2187) * k2 +
                                        (64448/6561) * k3 - (212/729) * k4, action)
            k6 = dt * state_derivatives(y + (9017/3168) * k1 - (355/33) * k2 +
                                        (46732/5247) * k3 + (49/176) * k4 -
                                        (5103/18656) * k5, action)

            # 5th-order accurate solution
            y_high = y + (35/384) * k1 + (500/1113) * k3 + (125/192) * k4 - \
                    (2187/6784) * k5 + (11/84) * k6

            # 4th-order embedded solution for error estimate
            k7 = dt * state_derivatives(y_high, action)
            y_low = y + (5179/57600) * k1 + (7571/16695) * k3 + (393/640) * k4 - \
                    (92097/339200) * k5 + (187/2100) * k6 + (1/40) * k7

            # Error estimation
            error = np.abs(y_high - y_low)

            if np.max(error) > tol:
                # Error too large, reduce timestep
                dt *= 0.9 * (tol / np.max(error))**0.2
            else:
                # Accept step
                t += dt
                globals.current_state[0:8] = y_high
                self.state[0:8] = y_high
                # Adjust step for next iteration
                dt *= 0.9 * (tol / np.max(error))**0.25

            # Prevent overshooting final time
            if t + dt > tf:
                dt = tf - t


        globals.current_time += tf
        globals.current_state[3] = np.arctan2(np.sin(globals.current_state[3]), np.cos(globals.current_state[3]))  # 确保航向角在[-pi, pi]范围内
        pre_dis = math.sqrt((previous_state[0] - globals.state[12])**2 + (previous_state[1] - globals.state[13])**2)
        cur_dis = math.sqrt((globals.current_state[0] - globals.state[12])**2 + (globals.current_state[1] - globals.state[13])**2)
        globals.current_state[10] = pre_dis - cur_dis
        pre_x_dis = abs(previous_state[0] - globals.state[12])
        cur_x_dis = abs(globals.current_state[0] - globals.state[12])
        globals.current_state[11] = pre_x_dis - cur_x_dis
        globals.current_state[8] = np.copy(globals.current_state[8]) + np.copy(globals.current_action[0]) // (np.pi/180) * (np.pi/180)
        globals.current_state[9] = np.copy(globals.current_state[9]) + np.copy(globals.current_action[1]) // (np.pi/180) * (np.pi/180)
        

        #障碍物设定
        # globals.obstacle_1 = [150.0, 0.0]
        # globals.obstacle_2 = [200.0, 50.0]
        # globals.obstacle1_set = True
        # globals.obstacle2_set = True
        # try:
        #     x_prev = previous_state[0]
        #     x_cur = globals.current_state[0]
        #     psi = globals.current_state[3]
        #     fov_half = np.pi / 4 # 45度视野范围
        #     # obstacle 1 at x=125
        #     if (not globals.obstacle1_set) and (x_prev < 125 <= x_cur):
        #         angle = psi + np.random.uniform(-fov_half, fov_half)
        #         # angle = psi
        #         dist = random.uniform(100.0, 150.0)
        #         obs1_x = globals.current_state[0] + dist * np.cos(angle)
        #         obs1_y = globals.current_state[1] + dist * np.sin(angle)
        #         globals.obstacle_1 = [float(obs1_x), float(obs1_y)]
        #         globals.obstacle1_set = True
        #     # # obstacle 2 at x=250
        #     # if (not globals.obstacle2_set) and (x_prev < 250 <= x_cur):
        #     #     obs2_x = globals.current_state[0] + 100.0 * np.cos(psi)
        #     #     obs2_y = globals.current_state[1] + 100.0 * np.sin(psi)
        #     #     globals.obstacle_2 = [float(obs2_x), float(obs2_y)]
        #     #     globals.obstacle2_set = True
        # except Exception:
        #     pass


        # globals.current_state[10] = 1
        # self.state[10] = globals.current_state[10]

        if globals.current_state[8] > np.pi/2:
            globals.current_state[8] = np.pi/2
            sail_error = True
        elif globals.current_state[8] < -np.pi/2:
            globals.current_state[8] = -np.pi/2
            sail_error = True

        if globals.current_state[9] > np.pi/6:
            globals.current_state[9] = np.pi/6
            # rudder_error = True
        elif globals.current_state[9] < -np.pi/6:
            globals.current_state[9] = -np.pi/6
            # rudder_error = True

        # globals.total_energy = globals.total_energy + abs((action[1]) / (np.pi/6)) * 30 * 0.1 + abs((action[0]) / (np.pi/2)) * 90 * 0.4
        dis_to_yuandian = math.sqrt((globals.current_state[0])**2 + (globals.current_state[1])**2)
        dis_to_obsta1 = math.hypot(globals.current_state[0]-globals.obstacle_1[0], globals.current_state[1]-globals.obstacle_1[1]) if globals.obstacle1_set else float('inf')
        dis_to_obsta2 = math.hypot(globals.current_state[0]-globals.obstacle_2[0], globals.current_state[1]-globals.obstacle_2[1]) if globals.obstacle2_set else float('inf')
        if dis_to_yuandian >= 750 or globals.current_time >= globals.total_time:
            truncated = True
        else:
            truncated = False


        # if globals.obstacle1_set:
        #     dx1 = globals.obstacle_1[0] - globals.current_state[0]
        #     dy1 = globals.obstacle_1[1] - globals.current_state[1]
        #     d1 = math.hypot(dx1, dy1)
        #     if d1 <= 150.0:
        #         self.state[14] = np.copy(globals.obstacle_1[0])
        #         self.state[15] = np.copy(globals.obstacle_1[1])
        #     else:
        #         self.state[14] = 0.0
        #         self.state[15] = 0.0
        # else:
        #     self.state[14] = 0.0
        #     self.state[15] = 0.0
        # # obstacle2
        # if globals.obstacle2_set:
        #     dx2 = globals.obstacle_2[0] - globals.current_state[0]
        #     dy2 = globals.obstacle_2[1] - globals.current_state[1]
        #     d2 = math.hypot(dx2, dy2)
        #     if d2 <= 100.0:
        #         self.state[16] = np.copy(globals.obstacle_2[0])
        #         self.state[17] = np.copy(globals.obstacle_2[1])
        #     else:
        #         self.state[16] = 0.0
        #         self.state[17] = 0.0
        # else:
        #     self.state[16] = 0.0
        #     self.state[17] = 0.0

        globals.state[14:18] = np.copy(self.state[14:18])

        self.update_wind()
        reward = self.calculate_reward(previous_state,truncated)
        terminated = self.check_done()

        globals.state[0:12] = np.copy(globals.current_state)
        # globals.state[13:24] = np.copy(previous_state)

        if terminated or truncated:
            globals.path.append((self.state[0], self.state[1]))
        
        if self.render_mode == 'human':
            self.render()

        return globals.state, reward, terminated, truncated, {}
    
    def update_wind(self):          
            globals.w_change_v = 0.3 * globals.w_ini_v + 0.7 * globals.w_last_v + globals.var_v * np.random.randn()
            globals.w_change_d = 0.3 * globals.w_ini_d + 0.7 * globals.w_last_d + globals.var_d * np.random.randn()
            globals.w_last_v = globals.w_change_v
            globals.w_last_d = globals.w_change_d
            # if globals.current_time == 60:
            #     globals.w_ini_d += np.pi / 6 * 3


    def calculate_reward(self,laststate,truncated):
        reward = 0
        reward_scale = 0.1
        reward_scale_sail = 0
        reward_scale_rudder = 0
        dis_diff = 0
        x_dis_diff = 0
        x = np.copy(globals.current_state[0])
        y = np.copy(globals.current_state[1])
        pre_x = laststate[0]
        pre_y = laststate[1]

        dis_diff = np.copy(globals.current_state[10])
        x_dis_diff = np.copy(globals.current_state[11])
        p = np.copy(globals.current_state[6])
        r = np.copy(globals.current_state[7])
        psi = np.copy(globals.current_state[3])
        u = np.copy(globals.current_state[4])
        v = np.copy(globals.current_state[5])
        ox1, oy1 = np.copy(globals.state[14]), np.copy(globals.state[15])
        ox2, oy2 = np.copy(globals.state[16]), np.copy(globals.state[17])

        # angle_to_target = math.atan2(globals.state[13] - y, globals.state[12] - x)
        # angle_diff = angle_to_target - psi
        # angle_diff = math.atan2(math.sin(angle_diff), math.cos(angle_diff))  # 归一化到[-pi, pi]
        # u_proj = u * math.cos(angle_diff)
        # ox1, oy1 = globals.obstacle_1
        # ox2, oy2 = globals.obstacle_2
        reward += (2 * dis_diff + x_dis_diff) + 0.5 * (u / (1 + abs(v)))
        # reward += u_proj * 4

        # 障碍物距离变化的奖励/惩罚逻辑：
        # 当障碍物坐标均为0时，视为未检测到障碍物，不计算惩罚/奖励。
        # 若出现非0值，计算上一时刻到障碍物的距离与当前时刻的距离之差：
        # 势场斥力
        yuanli_reward_scale = 1
        kaojin_reward_scale = 2
        min_safe_dist = 50.0
        max_safe_dist = 100.0
        close_penalty_scale = 0.4
        k = 15
        
        # if not (ox1 == 0.0 and oy1 == 0.0):
        #     cur_dist1 = math.hypot(x - ox1, y - oy1)
        #     reward -= k * ((max_safe_dist - cur_dist1 + min_safe_dist) / max_safe_dist) ** 2 if cur_dist1 <= max_safe_dist else 0


        sail = np.copy(globals.current_action[0])
        rudder = np.copy(globals.current_action[1])

        if abs(sail) <= np.pi/180:
            reward_scale_sail = reward_scale * 0.1
        else:
            reward -= abs(sail) // (np.pi/180) * 0.2
        
        if abs(rudder) <= np.pi/180:
            reward_scale_rudder = reward_scale * 0.1
        else:
            reward -= abs(rudder) // (np.pi/180) * 0.2


        # cur_sail = np.copy(laststate[8])
        # cur_rudder = np.copy(laststate[9])

        # sail_limit = np.pi/2
        # rudder_limit = np.pi/6
        # rudder_warn_limit = 25 * np.pi/180

        # sail_overshoot = max(0, abs(cur_sail + sail) - sail_limit)
        # rudder_overshoot = max(0, abs(cur_rudder + rudder) - rudder_limit)

        # if sail_overshoot >= np.pi/180:
        #     reward -= sail_overshoot // (np.pi/180) * 0.2
        # if rudder_overshoot >= np.pi/180:
        #     reward -= rudder_overshoot // (np.pi/180) * 0.2

        # if rudder_warn_limit <= abs(cur_rudder) <= rudder_limit:
        #     reward -= 0.5

        reward = reward * (reward_scale + reward_scale_sail + reward_scale_rudder) 

        dis_to_target = math.sqrt((x - globals.state[12])**2 + (y - globals.state[13])**2)
        if dis_to_target <= 375 and globals.one_check == 0:
            reward += 5
            globals.one_check = 1
        if dis_to_target <= 250 and globals.two_check == 0:
            reward += 10
            globals.two_check = 1
        if dis_to_target <= 125 and globals.three_check == 0:
            reward += 15
            globals.three_check = 1

        if dis_to_target <= 5.0:
            reward += 50

        if truncated:
            reward -= 100

        reward -= 0.1
         
        return reward

    def check_done(self):
        # 检查是否结束的逻辑
        x = np.copy(globals.current_state[0])
        y = np.copy(globals.current_state[1])

        distance_to_target = np.sqrt((x - self.state[12])**2 + (y - self.state[13])**2)
        reached_target = distance_to_target <= 5.0

        return reached_target

    def reset(
            self,
            *,
            seed: Optional[int] = None,
            options: Optional[dict] = None,
            ):
        super().reset(seed=seed)

        globals.current_state = None
        globals.current_action = None
        globals.previous_state = None
        globals.state = None
        globals.previous_action = [0, 0]
        globals.current_time = 0

        globals.path = []

        # 风场状态
        globals.w0 = [5, 0]
        globals.w0[1] = random.uniform(-np.pi, np.pi)
        # globals.w0[1] = np.pi * 0 / 180

        globals.var_v = 0.5
        globals.var_d = 1/18
        globals.w_change_v = 5
        globals.w_change_d = 0
        globals.w_last_v = globals.w0[0]
        globals.w_last_d = globals.w0[1]
        globals.w_ini_v = globals.w0[0]
        globals.w_ini_d = globals.w0[1]
        globals.one_check = 0
        globals.two_check = 0
        globals.three_check = 0
        globals.total_energy = 0
        globals.obstacle_1 = [0.0, 0.0]
        globals.obstacle_2 = [0.0, 0.0]
        globals.obstacle1_set = False
        globals.obstacle2_set = False

        self.target_rudder_angle = 0.0
        self.target_sail_angle = 0.0


        # 初始化状态
        self.state = np.zeros(18,dtype=np.float32)



        #设定(x,y)到目标(0,0)为固定值200
        # theta = random.uniform(0, 2*np.pi)
        # self.state[0] = 200 * np.cos(theta)
        # self.state[1] = 200 * np.sin(theta)

        # theta = random.uniform(0, 2*np.pi)
        # self.state[11] = 200 * np.cos(theta)
        # self.state[12] = 200 * np.sin(theta)
        self.state[12] = 500
        self.state[13] = 0

        # # 立即在 reset 时生成两个障碍物：在以起点(0,0)和终点(self.state[12], self.state[13])为对角的菱形内随机采样
        # def sample_in_diamond(A, B, min_sep=75.0, max_attempts=1000):
        #     A = np.array(A, dtype=float)
        #     B = np.array(B, dtype=float)
        #     d = B - A
        #     L = np.linalg.norm(d)
        #     if L <= 0:
        #         return None
        #     mid = (A + B) / 2.0
        #     # 垂直单位向量
        #     n = np.array([-d[1], d[0]])
        #     n_norm = np.linalg.norm(n)
        #     if n_norm == 0:
        #         return None
        #     n = n / n_norm
        #     # 等边三角形高 h = sqrt(3)/2 * side (side = L)
        #     h = math.sqrt(3.0) / 2.0 * L
        #     apex1 = mid + n * h
        #     apex2 = mid - n * h

        #     for _ in range(max_attempts):
        #         if random.random() < 0.5:
        #             v0, v1, v2 = A, apex1, B
        #         else:
        #             v0, v1, v2 = A, apex2, B
        #         r1 = random.random()
        #         r2 = random.random()
        #         if r1 + r2 > 1:
        #             r1 = 1 - r1
        #             r2 = 1 - r2
        #         p = v0 + r1 * (v1 - v0) + r2 * (v2 - v0)
        #         if np.linalg.norm(p - A) >= min_sep and np.linalg.norm(p - B) >= min_sep:
        #             return p
        #     return None

        # start = np.array([0.0, 0.0])
        # end = np.array([float(self.state[12]), float(self.state[13])])
        # p1 = sample_in_diamond(start, end, min_sep=75.0)
        # p2 = sample_in_diamond(start, end, min_sep=75.0)
        # # 若采样失败则保留默认(0,0)并标记未设置；成功则写入 globals 并标记已设置
        # if p1 is not None:
        #     globals.obstacle_1 = [float(p1[0]), float(p1[1])]
        #     globals.obstacle1_set = True
        # else:
        #     globals.obstacle_1 = [0.0, 0.0]
        #     globals.obstacle1_set = False
        # if p2 is not None:
        #     globals.obstacle_2 = [float(p2[0]), float(p2[1])]
        #     globals.obstacle2_set = True
        # else:
        #     globals.obstacle_2 = [0.0, 0.0]
        #     globals.obstacle2_set = False

        #设定船的朝向
        self.state[3] = random.uniform(-np.pi, np.pi)
        self.state[4] = random.uniform(0, 1)

        # self.state[16] = self.state[3]
        # self.state[3] = np.pi * 6 / 6
        globals.state = np.copy(self.state)

        return self.state, {}
    
    
    def render(self):

        global path, end_pos, current_state
        # 渲染环境
        if self.screen is None and self.render_mode == 'human':
            pygame.init()
            pygame.display.init()
            self.screen = pygame.display.set_mode((800, 600))
        
        if self.clock is None:
            self.clock = pygame.time.Clock()
        
        self.surf = pygame.Surface((800, 600))

        # 绘制背景
        pygame.draw.rect(self.surf, (255, 255, 255), self.surf.get_rect())

        # 绘制起点和终点
        # pygame.draw.circle(self.surf, (0, 255, 0), self.start_pos, 10)  # 起点为绿色圆点
        pygame.draw.circle(self.surf, (255, 0, 0), self.state[11:13], 10)  # 终点为红色圆点

        # 绘制帆船
        boat_pos = (int(self.state[0]), int(self.state[1]))
        pygame.draw.circle(self.surf, (0, 0, 255), boat_pos, 5)  # 帆船为蓝色小圆点

        # 绘制运动路径
        if len(self.path) > 1:
            pygame.draw.lines(self.surf, (255, 0, 0), False, globals.path, 2)  # 路径为红色线条

        if self.render_mode == 'human':
            self.screen.blit(self.surf, (0, 0))
            pygame.display.flip()
            self.clock.tick(60)  # 控制帧率为 60 FPS
        elif self.render_mode == 'rgb_array':
            return np.array(pygame.surfarray.pixels3d(self.surf))

    def close(self):
        if self.screen is not None:
            pygame.display.quit()
            pygame.quit()