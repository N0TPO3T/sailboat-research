# Project State

## 项目目标
- 基于师兄的无人帆船强化学习工作，完成一篇有独立增量的小论文；仅纯仿真。
- 优先可实现、可复现与投稿可行性；候选CCDC / ICAUS / ICCA / DDCLS，期望约2027-09-14前录用，不保证录用。
- 具体届次、学校认定要求、计算资源和训练预算未确认；ICCA具体全称待确认。
- 已授权资料审计、检查点兼容性检查和上下文维护；训练、正式实验、投稿尚未启动。

## 项目根目录与职责边界
- 项目根目录是本文件所在目录；本机路径`/Users/poet/Documents/研究生/小论文`，其他机器可使用不同克隆路径。四个核心文件只在根目录维护。
- `research/`：用户自己的独立研究工作目录，当前仅含目录占位文件，尚无研究实现。后续新代码、配置与实验产物在此按实际需要创建。
- `sailboat_RL/`：师兄的参考源码仓库，保留原状，不作为用户新增工作的默认修改入口。
- 参考仓库origin：`https://github.com/N0TPO3T/sailboat_RL.git`；参考main提交 `19422525cb337831ca68f53a45661d34f3683ee1`。
- `model/`：已收到的师兄检查点；`师兄大论文.pdf`、`yara.pdf`：参考论文。
- 复用遵循最小必要原则：先明确需用的动力学、网络或评估接口，再选取必要文件，记录源路径和版本；不整仓复制师兄实现。
- 新研究与参考基线的改动、配置、结果应可区分；不得将师兄的已有贡献或结果标成新研究成果。
- 根目录为独立私有Git项目`N0TPO3T/sailboat-research`；`research/`属于该项目。师兄仓库以固定提交的Git子模块引用，禁止自动追踪其最新main。
- 本文以项目根目录为路径基准；段落内“同目录”和简写文件名相对其明确引用的参考模块。

## 研究基础与目录
- 大论文：《基于强化学习的无人帆船控制模型研究》；正式提交/发表情况未核实。
- 第四章：无显式风场输入的SAC-LSTM控制；`sailboat_RL/PART4/SAC/`为基础实现，另有PPO、TD3和MPC对比。
- `sailboat_RL/PART4/seed_reward_ablation/`包含三类基线的seed/奖励消融入口，生成前缀与已收到检查点一致；是否为原始训练源码尚未完全核实。
- 第五章：静态避障和历史状态注意力；`sailboat_RL/PART5/SAC-LSTM-att/`为注意力实现，`SAC-LSTM-deep/`和`SAC-LSTM-meanpool/`为对照。
- `sailboat_RL/gymnasium/envs/sailboat/`存多版本自定义环境；根目录 `sailboat_RL/sailboat_s14_obst_V3.py`与其中同名文件正文相同。
- `sailboat_RL/docs/refs/`为参考论文；Yara是仿真平台参考文献，不表示本项目采用Gazebo/ROS。
- 数据由仿真交互生成；代码使用四自由度帆船动力学、风扰动以及传感器/执行器噪声模块。
- 各实验README及已有分析报告承担实验说明职责，保留；它们不是当前研究计划。

## 训练与评估路径（尚未闭环运行）
- 第四章入口：`sailboat_RL/PART4/SAC/parll_lstm_normal.py`、`parll_SAC_normal.py`；模型为`SAC_lstm.py`/`SAC_fc.py`，网络为`utils_lstm.py`/`utils_fc.py`。
- 第四章评估：`sailboat_RL/PART4/SAC/test_eval_lstm.py`；三类seed实验另见 `sailboat_RL/PART4/seed_reward_ablation/README.md`。
- 第五章入口：`sailboat_RL/PART5/SAC-LSTM-att/parll_lstm_att_normal.py` → `gym.make('sailboat-s14-obst-v3')` → `SAC_lstm_att_normal.py`/`utils_lstm_att_normal.py`；评估为同目录`batchtest.py`。
- 第五章观测18维：船体状态、目标、最近两个已观测障碍的距离/相对角；动作两维帆/舵增量，界限±π/18。
- 环境dt=0.05s，每动作20次积分；到达阈值10m、障碍距离阈值40m。
- 第五章训练默认9e6步、2个子进程环境、序列长度10，均为代码默认值而非已验证训练记录。
- 配置来自argparse和硬编码环境参数；`model/`存权重/normalizer，`runs/`存TensorBoard，评估输出文本、CSV、JSON、NumPy数组和图像。
- 路径依赖脚本工作目录及`globals`裸导入；不能把根目录启动命令视为已验证canonical command。
- 参考仓库的`sailboat_RL/requirements.txt`固定依赖版本；README要求复制环境到Gymnasium并手动注册，尚未在隔离环境验证安装或第五章注册参数。

## 检查点与验证边界
- `model/`共12个pth文件，三组前缀：
  - `sac_s14nowind_buf1e6_seed100`：14维FC。
  - `sac_s14wind_buf1e6_seed100`：16维FC。
  - `saclstm_s14nowind_buf1e6_seed100`：14维LSTM，历史状态+动作合计16维。
- 每组有actor7200、q_critic7200、normalizer7200、training_stats_7200；统计记录7200000步，seed100仍需独立运行配置佐证。
- 已用CPU PyTorch2.10.0、weights_only=True读取；张量有限，normalizer维度匹配且方差非负。
- 三组actor/critic均strict=True加载到第四章对应网络通过；eval模式合成输入actor前向通过。
- 以上仅证明参数结构/最小前向兼容；未运行仿真闭环，未复现成功率。没有完整optimizer/replay buffer/RNG状态，不能精确续训。
- 本批不含第五章18维注意力检查点；用户表示可向师兄索取，尚待交付匹配权重、normalizer及运行配置。

## 实验结果与限制
- 大论文表5.1（PDF80页/印刷68页）报告注意力/深层对照/平均池化综合成功率95.3%/93.3%/80.8%；已渲染核对，属于论文报告，非本地复现结果。
- 仓库有第四章运行文本、第五章注意力/轨迹和摘要，不能据部分产物外推全部seed或论文统计。
- 第五章outputs中model_id14400摘要记录367步、attention_shape=[367,20]；文件名K10不能单独确定实际窗口。
- 当前obst_V3 reset固定风向0°和7个障碍，随机混合生成代码被注释；参数间距100m与论文140m不一致。训练/评估原版本待核实。
- reset虽调用Gym seed，但Python random和全局np.random未在该reset中同步设种子。
- 碰撞/超时/出界合并到truncated且info为空；batchtest按距目标≤10m回退判断成功，失败分类与终止语义需核查。
- 对照入口有obst-v2，主模型为v3；不能默认环境公平一致。这些是当前快照问题，不推断师兄原实验无效。
- 参考仓库267个Python文件AST解析通过；这不等于依赖、环境或实验运行通过。

## 研究恢复
- 主要线程、候选假设、下一步及Go/Kill见 `CURRENT_PLAN.md`；历史陷阱按关键词查 `PROJECT_MEMORY.md`。
- ARIS采用research-pipeline分阶段推进，当前仅Stage1审计/选题；未完成pilot或深入查新。
- 用户选择Codex执行、DeepSeek审查。此前会话未暴露llm-chat工具，未完成独立复核；新会话应重新发现工具，不把旧的不可用状态当永久事实。

## 组内服务器（用户提供，尚未现场核验）
- SSH：`ot@172.16.2.249`；密码不写入项目文档、配置、脚本、命令行或Git。
- 共享学生根目录：`/home/ot/Students`；用户自己的工作范围：`/home/ot/Students/hs`。
- Conda入口：`/home/ot/miniconda3/condabin/conda`。仅为本项目创建独立环境，先核对已有环境归属，避免名称冲突；不修改base或他人环境。
- `/home/ot/Students/yc`可能有师兄早期代码；用户明确提醒后期开发不在该服务器，故其版本未经完整审查不能作为最终实现或论文基线。
- 即使同用ot账号，也不能按Unix用户名认定进程/文件属于本任务；需要工作目录、命令、日志、启动记录等精确归属证据。
- 实际操作前只读核查目录权限、磁盘、CPU/GPU占用及课题组调度规则；资源空闲不等于可独占，算力额度/时长未确认前不启动训练。
- 默认只向hs下已确认的项目路径写入；不修改/删除yc或其他学生目录，不停止他人进程，不清理共享缓存、不全局升级依赖、不改系统配置。
- 停止本任务作业前核对精确PID/作业与授权并保全产物；SSH失联先恢复状态和日志，不据此重启、重复启动或结束作业。
- yc仅作为待审查参考；使用前比对Git版本、代码、配置、模型和实验产物，不覆盖当前GitHub参考子模块。
- 服务器连通性、GPU型号、可用容量、hs/yc实际内容和环境版本均未核实；本次记录没有连接、建环境或启动远程工作。

## 多机同步
- 远程：`https://github.com/N0TPO3T/sailboat-research`（私有）。克隆：`git clone --recurse-submodules https://github.com/N0TPO3T/sailboat-research.git`。
- 已有克隆仅在工作区干净且没有正在运行的实验时执行`git pull --ff-only`，然后`git submodule update --init --recursive`。有分叉或本地修改时先检查，不自动reset/rebase。
- 同步四个上下文文件、research源码/配置、固定参考子模块、两份参考PDF及本次12个基线检查点；该批pth已显式跟踪，未来新权重和日志默认忽略。
- 需要使用GitHub账号访问两个私有仓库；本机Python环境、API密钥、Codex/ARIS安装不随Git同步。
- 未来提交显式选择路径，推送前检查凭据和大文件，推送后核对远端SHA。避免两台电脑同时修改同一分支；不强制推送。
