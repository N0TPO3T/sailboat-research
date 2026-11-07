# 历史Gym与Yara：环境和方法参数核对

2026-11-06。只读核对及模型参数统计，未训练。前置接口细节、复现命令见YARA_TRANSFER_AND_BASELINE_ZH.md。

## 口径

- 历史环境主列：当前项目third_party/senior/sailboat_s14.py的14D任务；这包含接力后的数值实现，不能自动认作期刊逐字节版本。
- 历史训练默认值：原资料research/weights_library/20260928_import/source_evidence/xiaolunwen/parll_lstm_normal.py与SAC_lstm.py；不是从checkpoint倒推出的实际训练账本。
- 当前实际Actor：checkpoints/actor.pth（14D），及checkpoints/obstacle_candidate/...actor10800.pth（18D）。不把两者混成一个期刊模型。
- Yara：固定commit e708703e7367993f56ff2187a06e05b09d19e696，Eboat53-v0；原文另列差异。已保存模型元数据见../yara-transfer-audit/output/checkpoint_audit.json（相对于本机项目根的兄弟目录）。

## 环境

| 项目 | 历史14D环境 | Yara当前Eboat53 |
|---|---|---|
| API/引擎 | Gymnasium+Python内置动力学 | Gymnasium+ROS Noetic+Gazebo11，ODE引擎 |
| 船体自由度 | x,y,横滚,偏航及对应速度，4DOF | 刚体6DOF及帆/舵/推进器关节 |
| 质量 | m=25900kg | eboat4tr各link惯性质量声明合计160.3356646kg，不包含附加质量 |
| 帆面积 | 170m² | 当前启用插件3.18776m² |
| 舵/龙骨面积 | 1.17/8.7m² | 当前启用插件0.10064/0.23779m²；未启用宏中的另组面积不能混用 |
| 海水/空气密度 | 1025/1.2kg/m³ | 997/1.201kg/m³ |
| 物理步进 | 手写Dormand–Prince5/4，初始0.05s，自适应1e-5至0.1s，误差阈值1e-6 | world max_step_size=0.01s；max_update_rate=100，训练helper可设0 |
| 控制步进 | 1s | 约2s观测周期，ROS解暂停/发布/取观测/暂停 |
| 初始任务 | 目标(500,0)，原点出发 | 目标(100,0)，原点出发 |
| 初始航向/速度 | 航向随机[-π,π]，u随机[0,1] | 当前reset没有航向随机化；重置到模型初态后推进再观测 |
| 风 | reset基准8m/s、随机方向；每步Dryden形式扰动，Lu=Lv=300，σu=1.2、σv=1.0 | 每回合离散5…12kn，24个方向；reset发布恒定向量，视风仍随船运动变化 |
| 成功 | 目标距离≤10m | 目标距离<5.1m |
| 截断/失败 | 原点距离≥750m、时间≥1000s或积分失败截断 | 距目标>120m/NaN终止；第302次step开始触发步数截断 |
| 障碍 | 14D无障碍；18D与routing层另加障碍 | Eboat53无障碍；Eboat103等另有激光输入 |

Gym是接口，不是动力学引擎，故不是“Gym或Yara二选一”。两者都可以通过相同API训练，但state/action的语义完全不同。三维显示与更多DOF也不自动证明所有工况更准确。

历史14D观测顺序：x,y,φ,ψ,u,v,p,r,δs,δr,距离进展,x绝对距离进展,目标x,目标y；使用Z-score。18D追加两对障碍距离/方位。Yara5D为目标距离、目标相对角、纵向速度、视风速、视风角，分别用2d/120−1、β/180、u/10、w/15−1、θ/180映射。没有记录横摇、横向速度和执行器反馈进入这个5D策略；ROS原始观测更多不代表Actor实际使用更多。

历史动作是约±10°每步增量，按1°向下取整后累加至目标帆角±90°/目标舵角±30°，实际变化上限10°/s。Yara是帆缆放开范围0…90°、绝对舵目标±60°、电机int(5a)档位。帆缆执行默认0.5rad/s，舵默认最大0.4rad/s，实际受关节约束。帆缆范围与实际有符号帆角不是同一个状态。

噪声不是笼统“3%”：来源训练代码的RATE=1使非零比例抽样经幅值裁剪后的位置误差为±1m、角度±1°、速度±0.1m/s；当前third_party/senior的RATE=5对应±5m、±5°、±0.5m/s，比例抽样恰为0时仍为0。是否启用由wrapper/config决定。当前Yara任务观测直接从仿真插件取值，未见同等噪声wrapper。比较时必须冻结实际噪声实现及开关。

奖励详式见前置报告。历史包含进展、速度、动作、里程碑、到达和截断惩罚；Yara奖励用距离进展并惩罚电机。不能直接比较return，也不能把500m里程碑移进100m任务。

## 算法参数

下表Yara以保存权重为主；历史列中训练参数为来源脚本默认，模型结构由当前checkpoint核实。默认配置不能替代实际训练日志。

| 参数 | Yara PPO | Yara SAC | 历史14D循环SAC |
|---|---|---|---|
| 观测/动作维数 | 5/3 | 5/3 | 14/2 |
| Actor | 32→32 ReLU MLP | 32→32 ReLU MLP | 历史16→256→LSTM256；当前14→256；拼接512→256→均值/方差头 |
| Critic | 32→32 value MLP | 双32→32 Q | 两路循环Q；当前状态动作并入；末层宽256/128（来源代码） |
| 历史长度 | 无 | 无 | 训练序列10步；单步推理维护隐状态，不能称只看最近10步 |
| Actor参数量 | 1350，含log_std | 1446 | 667396 |
| 学习率 | 3e-4 | 3e-4 | Actor/Critic默认3e-4 |
| gamma | .99 | .99 | 默认.98 |
| batch | 64 | 64 | 默认256个序列样本 |
| 熵 | 固定.001 | 固定.001 | 初始.2、自适应；目标熵−2；α学习率c_lr×.1 |
| tau | 不适用 | .005 | .002 |
| replay | 无长期off-policy replay | 1e6条 | 1e6容量的序列replay，优先采样 |
| 更新 | rollout2048，10epochs | 每步1梯度更新 | 默认15并行环境；total_steps%20==0时做8次train；Actor每4次critic更新一次 |
| 随机探索 | 按PPO策略采样 | learning_starts=100 | 默认20×max_e_steps=20000总采样步 |
| 梯度裁剪 | .5 | 未见对应显式裁剪 | 1.0 |
| 正则 | 无此循环正则结构 | 无此循环正则结构 | LayerNorm、Dropout默认.05、Adam weight_decay=1e-5 |
| 训练计数 | 保存501760 | 保存501760 | 来源脚本预算9e6，不能当当前权重已完成步数 |
| seed | 保存null | 保存null | 来源默认2026，环境seed+i；不推定是权重实际seed |

Yara PPO另有GAE λ=.95、vf_coef=.5、normalize_advantage=True。旧clip_range和lr_schedule在当前SB3 2.3.2出现反序列化警告；不能把加载后fallback当成原训练精确证明。旧策略张量已经核实完全一致。原权重保存SB3版本2.0.0。

历史更新频率按执行条件解释：默认每次采样累计15步，整除20每4批才触发，即60条环境transition后8次train调用；每4次critic更新一次Actor，即约60条transition后2次Actor更新。不要采用代码中“4次更新”的过期注释。序列样本和单步样本的计算量也不同。

当前18D注意力Actor为866820参数。它比14D增加了障碍输入和Q/K/V投影，不能把“14D LSTM”和“18D LSTM-Attention”统称同一模型。14D Actor约为Yara SAC的462倍参数；匹配大MLP及历史堆叠是必要对照，否则提升不能独立归因于记忆。

## 论文和仓库差异

Yara论文算法2用Dmax=1.25D0、到达<5m、后退项Δd/Dmax；当前仓库用1.2D0、5.1m、后退2Δd/Dmax。论文描述连续随机风速/方向与航向；当前环境使用离散风并未随机航向。论文的训练量为500k，保存文件计数501760。须分为“论文协议”和“固定仓库协议”。[论文](https://link.springer.com/content/pdf/10.1007/s10846-024-02212-1.pdf)

## 对迁移的结论

现在迁移的是“利用因果历史的控制方法”，不是已被验证的跨船体权重。首先统一Yara的任务、风输入条件、帆缆/舵/电机接口、时序、奖励和评价，比较无记忆MLP、历史堆叠与LSTM；匹配网络容量/训练量并记录计算成本。原有R13高层候选预测是另一层方法，未在本轮搬到Yara，也没有新的Yara训练结果。旧Gym成绩不能沿用为Yara成绩。

来源：third_party/senior/{sailboat_s14.py,utils_lstm.py,noise_utils_nowind.py,globals.py}；source_evidence/xiaolunwen/{parll_lstm_normal.py,SAC_lstm.py,noise_utils_nowind.py}；Yara esailor_gym/envs/eboatEnvs.py、yara_description/urdf/eboat4tr.urdf.xacro、eboat4_physics_plugins.xacro、eboat4_control_plugins.xacro、yara_control/src/{missionControl.cc,sailController.cc,rudderController.cc}。物理参数针对当前启用分支，不是所有Yara模型通用常数。
