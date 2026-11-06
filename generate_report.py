from pathlib import Path
import json,math,html
R=Path(__file__).resolve().parent;O=R/'output'
summary=json.loads((O/'summary.json').read_text());diag=[]
for row in summary:
 d=json.loads((O/('policy_'+row['scene']+'_'+row['backend']+'.json')).read_text());rs=d['rows'][1:]
 diag.append(dict(scene=row['scene'],backend=row['backend'],opposite_sail_steps=sum(x['target_angles'][0]*x['raw'][8]<0 and abs(x['target_angles'][0])>math.radians(10) and abs(x['raw'][8])>math.radians(10) for x in rs),steps=len(rs),mean_sail_target_actual_gap_deg=sum(abs(x['target_angles'][0]-x['raw'][8]) for x in rs)/len(rs)*180/math.pi))
(O/'actuator_diagnostics.json').write_text(json.dumps(diag,indent=2))
names={'clear':'无障碍到点','single':'静态单障碍','switch':'80秒切换目标'}
reasons={'arrived':'安全到达','arrived_with_buffer_violation':'到达但安全违规','time_limit':'超时','entity_collision':'实体碰撞'}
table='|任务|后端|结果|时间(s)|最终距离(m)|最小安全净距(m)|\n|---|---|---|---:|---:|---:|\n'
for row in summary:
 clear='不适用' if row['min_safety'] is None else f"{row['min_safety']:.2f}"
 table+=f"|{names[row['scene']]}|{row['backend']}|{reasons.get(row['reason'],row['reason'])}|{row['steps']}|{row['final_distance_m']:.2f}|{clear}|\n"
text='''# SailBoatRL → Yara 18D环境迁移报告

2026-11-06。已实现独立可运行的18D任务适配层，并完成语义检查、固定动作响应和三个固定任务的配对验证。**原生Yara帆缆不能等价执行原有符号帆角；本交付不是原船动力学等效复现。** 未训练、未调整权重或归一化，未使用GPU，未push。

## 实际基准与实现

最近实际A实验的冻结副本与本次低层源码逐字节一致，见actual_loading_chain.json。基准是SeniorModules/ContinuousPhysics提供连续原物理，加0204@10800的18D循环注意力策略(eval)、boundary40障碍适配和真实历史重编码。没有混用裸V3、14D权重或其他checkpoint。原源HEAD、工作树修改、源码与资产哈希均已保存。

environment.py提供相同reset/step形式，后端选择original或yara。观测、奖励、安全净距、策略加载与记忆重编码复用冻结源码。未移植或优化高层候选预测器/Relay规划方法。本轮连续目标由预先固定的80秒切换事件提供，用于验证接口时序。

    实际位姿/速度/帆舵反馈 → 统一14D物理状态
       → 原ObstacleFrame(boundary40) → 原18D归一化与策略
       → 2D增量 → 原缩放/量化/累积/饱和
       → 原物理 或 Yara帆缆/舵 → 精确1秒推进 → 新状态
    目标切换：已执行动作后的边界 → 真实历史重编码 → 下次决策
    风真值：仅物理后端与日志可见，不进入18D策略。

## 对应程度

- 共享：18D排列、局部500m坐标、进展项、障碍排序/150m阈值/零槽、冻结Z-score、历史配对、奖励/里程碑、10m到点、实体碰撞与安全缓冲判分。
- 动作仍为增量，零增量保持目标。保留float32上限导致的+1→+9°、−1→−10°量化不对称。现用安全缓冲60m，500m诊断任务采用900s、3500m原点半径。规划地图矩形不是原ContinuousPhysics的终止边界，本轮不新增这一条件。
- 时序：策略1s，Yara积分0.01s×100，动作先装入、积分后采样。没有以sleep替代物理步进。Gazebo绝对时钟跨回合单调，环境时间reset归零；每回合重新生成模型并清空执行器与策略记忆。
- 电机插件从独立模型移除，指令与该插件贡献推力为0并逐步记录。推力0由禁用推进源保证，不是力传感器测量。原版Yara文件和入口保留。安全评分仍是原船中心弦段对圆判据，非Gazebo接触传感器；实体障碍有真实碰撞几何，但船体接触定义不完全等价。
- 物理差异：原25900kg/170m²帆/4DOF；Yara约160.34kg/3.18776m²帆/6DOF。完整参数在PHYSICS_PARAMETERS.json及boat.urdf。没有把大船质量直接塞进2.4m船体后声称同型；同船级迁移仍需要原船几何及匹配的浮力、水动力模型。
- 执行器差异：原实际帆舵10°/s；Yara缆速0.5rad/s、舵速0.4rad/s及原关节力矩/限位。帆目标映射为绝对帆缆范围，风决定实际帆侧；目标累积一致不等于实际帆角一致。
- 坐标修正：舵指令/反馈对Gazebo关节取负；帆角反馈及横滚记号按源模型约定转换。正负舵的偏航方向经无风响应复核。额外俯仰、垂荡与角速度耦合仍属于6DOF差异。
- 两后端使用相同固定风(0,8)m/s与初态。Yara物理波浪gain=0匹配原无波浪模型；水面视觉纹理不代表物理波浪。

## 验证结果

16组人工状态/边界检查通过，见output/semantic.json及edge_checks.json。离散规则精确一致，float32观测绝对容差2e-5，double动作/奖励1e-12，时钟1e-8秒。无风、初速2m/s正负舵方向门通过，见direction_gate.json。

固定响应含零增量、正负舵/回舵、帆目标变化。原始位置、航向、速度、目标角、实际角与时钟均保留。零舵横风下两模型也有不同偏航漂移；方向门通过不证明水气动力等效。

'''+table+'''
这六个回合只是固定诊断，不是成功率估计。到点但缓冲违规、保持安全却超时均记失败；未换种子、放宽标准或删除不利结果。

复算另发现旧Yara包装器进展计算存在最大2.903e-5 m的浮点路径差，已直接抽取原源码计算修复，未放宽容差。原计分日志保留，精确奖励另存reward_recomputed_*.json；audit.json证明每一步策略输入逐位相同，安全及结局一致，最大原奖励偏差约1.276e-5。最终修复版又通过真实Gazebo短回归。

config.seed控制原Python/Gym重置；Yara全局RNG本轮未显式设种子、默认值未核实。没有随机风或额外传感器/执行器噪声；同条件全新world复核逐状态相同，不推广为跨机器位级复现。

## 偏差解释与下一步

单障碍Yara的900步中，有845步在目标/实际帆角绝对值均超过10°时符号相反。帆角差不能直接等同于推力损失，但说明原有符号帆角的可控性已改变。船体尺度、气水动力、执行速度同时不同，目前不能隔离各项因果贡献。
原环境单障碍任务也有安全违规，不能将全部失败归因于迁移。训练分布变化是合理推断；原训练数据分布未完整绑定，不能写成已定位根因。

建议先确定执行器协议：保留Yara原生帆缆时，应明确接受动作并非完全等效，再讨论动作重定义或有限微调；若要求同船/有符号帆角执行，先补原船几何与执行器模型并重做响应对照。现有证据不支持直接启动重训，也不支持宣布旧18D方法无效。

## 图像、异常与复现

output/paired_trajectories.png、fixed_response.png、scene_comparison.png来自实际日志或Gazebo相机。红色圆柱为实体障碍、绿色为目标、黄色为实际航迹采样；安全缓冲在二维图以虚线绘制并真实参与判分。相机图来自计分结束后的真实继续运行，额外时钟不计入成绩，准确时间和前后位姿见capture_*.json。曾尝试用静态标记冻结，但实测没有停止船体运动，旧收据中的冻结标记无效；见capture_audit.json。当前近景相机跟随实际船体，水下检查图只隐藏水面视觉，不改变物理模型。

保留修正前舵符号响应、模型复用reset异常、截图序列化/等待出帧异常。无障碍为截图错误做过一次同配置复核，仍为123/171秒，逐状态最大差0；不是择优筛选。原始异常及首次结果见output/pre_correction、capture_failure_run、error_*.json与logs。

启动命令：服务器migration18目录执行 ./run.sh --stage smoke
验证命令：./verify.sh
逐维表：MAPPING_ZH.md、NORMALIZATION.md。
身份索引：source_identity.json、ASSET_HASHES.json、VERSIONS.json、ARTIFACT_INDEX.json。
'''
single=next(x for x in diag if x['scene']=='single' and x['backend']=='yara')
text=text.replace('900步中，有845步',str(single['steps'])+'步中，有'+str(single['opposite_sail_steps'])+'步')
(R/'REPORT_ZH.md').write_text(text,encoding='utf8')
images=[('paired_trajectories.png','实际配对航迹，含违规与超时'),('fixed_response.png','固定动作响应'),('scene_comparison.png','原环境日志场景与真实Yara相机'),('actual_single_boat.png','实际船体与帆'),('actual_single_rudder.png','真实侧面相机，水面遮挡部分水下舵'),('actual_underwater.png','实际水下船体/龙骨/舵检查：仅隐藏水面视觉'),('actual_single_scene.png','实际障碍、目标、航迹采样'),('actual_switch_scene.png','连续换点实际场景')]
body='<h1>18D → Yara 迁移验证</h1><p>未训练；原生帆缆不等价于有符号帆角执行。</p><p><a href="REPORT_ZH.md">中文报告</a> · <a href="MAPPING_ZH.md">对应表</a> · <a href="output/summary.json">汇总数据</a></p><table><tr><th>任务</th><th>后端</th><th>结果</th><th>秒</th></tr>'
for row in summary:body+='<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in [names[row['scene']],row['backend'],reasons.get(row['reason'],row['reason']),row['steps']])+'</tr>'
body+='</table>'
for file,caption in images:
 if (O/file).exists():body+='<figure><img src="output/'+file+'"><figcaption>'+caption+'</figcaption></figure>'
(R/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>18D Yara migration</title><style>body{font-family:system-ui;max-width:1200px;margin:32px auto;padding:16px;color:#172235;background:#f5f7fa}table{border-collapse:collapse}td,th{padding:10px 20px;border:1px solid #b9c6d5}img{width:100%}figure{margin:30px 0}figcaption{padding:10px}a{color:#1765a0}</style>'+body,encoding='utf8')
print('REPORT_WRITTEN')
