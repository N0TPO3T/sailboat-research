from environment import *
from validate import clean
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
D=R/'signed_20261107'
def load(name):return json.loads((D/name).read_text())
reference=load('response_original.json')['rows']
response=[]
fig,ax=plt.subplots(2,1,figsize=(11,6),sharex=True)
for mode,color in [('original','black'),('native','#1874ae'),('signed','#dd6327')]:
 rows=load('response_'+mode+'.json')['rows'];actual=np.array([x['raw'][8:10] for x in rows]);desired=np.array([x['target_angles'] for x in rows]);expected=np.array([x['raw'][8:10] for x in reference])
 response.append(dict(mode=mode,max_sail_angle_error_deg=float(np.rad2deg(np.abs(actual[:,0]-expected[:,0])).max()),max_rudder_angle_error_deg=float(np.rad2deg(np.abs(actual[:,1]-expected[:,1])).max())))
 for j in [0,1]:
  ax[j].plot(np.arange(1,len(rows)+1),np.rad2deg(actual[:,j]),color=color,label=mode)
  if mode=='original':ax[j].plot(np.arange(1,len(rows)+1),np.rad2deg(desired[:,j]),'--',color='gray',label='Accumulated target')
for a,title in zip(ax,['Actual signed sail angle','Actual signed rudder angle']):
 a.set_ylabel('deg');a.set_title(title);a.grid(alpha=.25);a.legend()
ax[-1].set_xlabel('Simulation time (s)');fig.tight_layout();fig.savefig(D/'response.png',dpi=150);plt.close(fig)
(D/'response_summary.json').write_text(json.dumps(response,indent=2))
summary=[]
fig,axs=plt.subplots(1,3,figsize=(15,5))
for ax,scene in zip(axs,CONFIG['scenes']):
 circles=tuple(CircleObstacle(tuple(x['center_xy']),x['entity_radius'],x['safety_buffer']) for x in scene['obstacles'])
 for o in circles:
  ax.add_patch(Circle(o.center_xy,o.entity_radius,color='red',alpha=.3));ax.add_patch(Circle(o.center_xy,o.exclusion_radius,fill=False,linestyle='--',edgecolor='red'))
 for mode,color in [('native','#1874ae'),('signed','#dd6327')]:
  d=load('policy_'+mode+'_'+scene['name']+'.json');rows=d['rows'];raw=np.array([x['raw'] for x in rows]);safe=math.inf
  for a,b in zip(raw,raw[1:]):safe=min(safe,segment_circle_clearance(a[:2],b[:2],circles)['safety_m'])
  arrived=np.linalg.norm(raw[-1,:2]-scene['goals'][-1])<=CONFIG['goal_radius_m']
  assert d['success']==bool(arrived and safe>0)
  summary.append(dict(mode=mode,scene=scene['name'],reason=d['reason'],success=d['success'],time_s=rows[-1]['time'],min_safety_m=safe,final_distance_m=float(np.linalg.norm(raw[-1,:2]-scene['goals'][-1])),target_changes=len(d['switches']),opposite_sail_steps=sum(x['target_angles'][0]*x['raw'][8]<0 and abs(x['target_angles'][0])>np.deg2rad(10) and abs(x['raw'][8])>np.deg2rad(10) for x in rows[1:])))
  ax.plot(raw[:,0],raw[:,1],color=color,label=mode+' / '+d['reason']);ax.scatter(*raw[-1,:2],marker='x',color=color)
 for g in scene['goals']:ax.scatter(*g,marker='*',s=80,color='green')
 ax.set_title(scene['name']);ax.set_xlabel('x (m)');ax.set_ylabel('y (m)');ax.set_aspect('equal',adjustable='datalim');ax.grid(alpha=.2);ax.legend(fontsize=7)
fig.suptitle('Same 18D policy and Yara hull: native cable vs signed rate-limited actuators')
fig.tight_layout();fig.savefig(D/'paired.png',dpi=150);plt.close(fig)
(D/'summary.json').write_text(json.dumps(clean(summary),indent=2))
text='''# 有符号执行器适配与固定任务复测
2026-11-07。未训练。新增独立 signed 模式，native 帆缆模式仍是默认入口。

## 执行器对应
归一化动作缩放、1度向下量化、目标累积和饱和继续共用原函数；帆±90°、舵±30°。signed 模式在每个0.01秒积分步内执行1秒线性限速轨迹，帆舵均10°/s，有符号目标与实际关节通过既有符号映射对应。零增量保持累计目标，reset 清空目标与状态。

这是与原环境一致的理想规定角度执行器，采用Gazebo关节位置和限位约束；没有模拟真实伺服器的力矩/功率上限。更改执行器约束会改变其反力及闭环运动；船体质量、惯量、几何、气水动力参数和物理步长没有更改。native仍使用原生帆缆和舵规律。

本次干预同时对齐帆侧可控性和帆舵执行速率，隔离的是整套执行器适配的影响，不能单独归因为帆角正负号。

## 响应核验
同一动作序列包含正负累计、保持、反向和双侧饱和。目标累计与原环境double容差1e-12；signed实际角与每秒速率预设容差0.05°。response_gate.json已通过；逐项误差从原始日志重算于response_summary.json，图见response.png。初版response_native.json的误差字段未计算（零值不是native等价证据），以response_summary.json为准。

## 同权重闭环结果
两模式各从新世界开始，按同一顺序运行原三个固定任务。config_policy.json保存原冻结配置；同一18D Actor/normalizer、boundary40、真实历史及80秒换点、固定风、900秒上限和60m安全缓冲均不变。计分任务间不取图。

|场景|模式|结果|时间(s)|最小安全净距(m)|最终距离(m)|
|---|---|---|---:|---:|---:|
'''
for x in summary:
 margin='不适用' if math.isinf(x['min_safety_m']) else format(x['min_safety_m'],'.2f')
 text+=f"|{x['scene']}|{x['mode']}|{x['reason']}|{x['time_s']}|{margin}|{x['final_distance_m']:.2f}|\n"
text+='\n全部失败和超时保留。安全成功要求到点且全过程安全净距严格大于0。原始逐步记录为policy_*.json，实际执行源码快照保存在本目录，原帆缆交付数据保留在../output/。\n'
text+='\n## 结论与边界\n有符号模式在三个闭环任务中均保持规定角度跟踪，误差见tracking.json；显著帆侧反向步数均为0。原生对应步数为6/845/865。\n两模式均仅完成无障碍任务，有符号模式用时由171秒增加到291秒；单障碍与换点仍在900秒超时。单障碍有符号模式最小安全净距1.51m，低于原生17.93m；虽未触发缓冲违规，仍未完成任务。\n执行器语义不对应确实存在，但本次对齐角度与速率不足以恢复这两个固定任务。剩余偏差需要结合船体响应及观测量跨船含义诊断，不能直接认定为训练不足。此次理想伺服干预不等于真实有限力矩执行器，也不支持把全部差异单独归因于帆角符号。\n\n## 使用\n原入口./run.sh继续默认native；独立配置config_signed.json将actuator_mode设为signed，交给同一MigrationEnv加载。\n核验入口：./run-signed.sh response；其门通过后执行./run-signed.sh policy（固定三个任务、两模式）。结果写signed_20261107；再次执行前应保留已有该目录，避免覆盖本次数据。\n船体模型、物理world、原任务配置、Actor及归一化文件已做字节一致性核对，见unchanged_inputs.json。无训练、无GPU、无push。\n'
(D/'REPORT_ZH.md').write_text(text,encoding='utf8')
print(json.dumps(clean(summary),indent=2))
