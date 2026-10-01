import numpy as np
import random


a = np.array([[0],[0],[1],[2]])

b = np.array([
    [1],[2],[3],[4]
])

xray = np.array([
    [0,1,0,3],
    [0,1,0,3],
    [0,1,0,3],
    [0,1,0,3],
])

# state = np.array([0,0,0,np.pi,0,0,0,0])

state_init = np.zeros(8,dtype=np.float32)

state_change = np.concatenate([a.flatten(),b.flatten()])

state_new = state_init + state_change * 2

# x,y,phi,psi,u,v,p,r = state[0:8]

# v_tw = np.log(abs(-11.5)*np.cos(phi)/0.0005)/np.log(11.5/0.0005)*a

state = np.zeros(8,dtype=np.float32)

#设定(x,y)到目标(0,0)为固定值200
theta = random.uniform(0, 2*np.pi)
state[0] = 200 * np.cos(theta)
state[1] = 200 * np.sin(theta)

start_pos = (state[0], state[1])

c = a[0]*7

b = np.array([
    1,
    2,
    3])

d = np.array([[0],[2],[0]])


ju = xray @ a

print(start_pos)

print(ju.flatten())

# print(v_tw)

