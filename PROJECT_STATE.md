# Project Overview

SailBoatRL 是基于 Gymnasium 的无人帆船连续控制研究代码库。目标是在随机风场、传感器/执行器噪声和障碍物条件下学习到达 `(500, 0)` 的控制策略，并比较显式风信息、时序历史和不同策略结构对鲁棒性的影响。

本快照基于当前 `main` 源码和已提交 artifacts。接手前历史只有提交 `1942252`，无法据此恢复更早研究进程。

# Current Research Scope

- README 指定的核心方法是 `PART4/SAC` 中的 SAC 与 SAC-LSTM；PPO、TD3、MPC 是对照实现。
- `PART4` 还包含 actor 输入、reward 和 random-seed 消融。
- `PART5` 包含障碍物任务上的 SAC-LSTM attention、deeper network 和 mean-pooling 变体。
- 哪个方向当前正在推进无法从仓库可靠确认；见 `CURRENT_PLAN.md`。

# Repository Map

- `sailboat_rl/`：当前唯一 canonical package；包含基础环境、SAC-FC、SAC-LSTM、三个训练入口和正式 seed evaluation。
- `tests/test_canonical_core.py`：canonical core 的最小环境/网络/replay/evaluation regression smoke test。
- `gymnasium/envs/sailboat/`：自定义环境源码；包含多个 V1/V2/V3 和 old/fail 副本。
- `PART4/SAC/`：README 指定的主 SAC/SAC-LSTM 训练与评估代码。
- `PART4/PPO/`、`PART4/TD3/`、`PART4/MPC/`：基线。
- `PART4/SAC_lstm_actor_*`、`PART4/SAC_lstm_stateonly_history/`：actor/history 消融副本。
- `PART4/reward_ablation*`：reward component 消融；`reward_ablation_new` 是文档标记的 active rerun 版本。
- `PART4/seed_reward_ablation/`：多 checkpoint、多风向批量评估与结果分析。
- `PART5/`：障碍物场景的 attention/deep/meanpool 实验分支。
- `docs/refs/`：参考论文 PDF；不是运行时文档。
- `EP_image/` 和各 `test_results*`/`outputs`：已提交实验 artifacts。

`PART4/SAC/code_fake/` 以及大量 old/fail/V1/V2 环境副本的当前用途未验证；不要将其作为 canonical implementation。

# Runtime and Environment Registration

- `import sailboat_rl` 会在项目代码内注册 `sailboat-s14-nowind` 和 `sailboat-s14-wind`；不再修改外部 Gymnasium 安装目录。
- canonical 环境位于 `sailboat_rl/envs/`，从根目录确认的 `sailboat_s14.py` / `sailboat_s14_wind.py` 提取而来；环境和正式 evaluator 都显式使用 `sailboat_rl.envs.globals`，不再由 working directory 选择裸 `globals.py`。
- 项目根 `.venv` 使用 `--system-site-packages` 复用服务器 base 的 Python 3.12、PyTorch 2.6/CUDA 12.4、Gymnasium 1.0、SB3 2.4、NumPy 2.2 和 SciPy 1.16。canonical 非渲染 regression tests 和三模型端到端短训练已通过。
- 当前 runtime 仍缺 `pygame`；canonical 训练和正式评测的 `render_mode=None` 路径可运行，显式 rendering 会给出缺依赖错误。根 `requirements.txt` 仍声明 `pygame==2.6.1`。

# Shared Server Infrastructure

- 主要共享服务器 workspace 是 `/media/user/68fdd01e-c642-4deb-9661-23b76592afb1/hs_worksapce`；服务器由多人共用。
- 服务器直连外网不可靠。当前用户已有用户态 Mihomo，目录为 `/media/user/68fdd01e-c642-4deb-9661-23b76592afb1/hs_worksapce/mihomo`。
- 该目录内的既有 runtime 是 binary `mihomo`、配置 `config.yaml`、PID file `run/mihomo.pid` 和日志 `logs/mihomo.log`；配置可能含敏感凭据，不应读取或复制其内容。
- mixed proxy 为 `http://127.0.0.1:17890`，controller 为 `127.0.0.1:19090`；二者仅监听 localhost，`allow-lan=false`。
- 代理按命令显式 opt in，不修改系统路由或 DNS；TUN、TProxy、redir 和透明代理均未启用。GitHub 的 `curl` 与 `git ls-remote` 已通过显式代理验证。
- 敏感订阅和节点凭据故意不进入项目文档。安全检查、启动/停止约束及标准联网协议以 `AGENTS.md` 为 canonical source。

# Environments and Data Flow

项目是在线仿真 RL，没有独立静态 dataset 或 preprocessing pipeline。

- `sailboat-s14-nowind` 对应 14 维观测：前 12 维为船体/控制与进度状态，`[12:14]` 为目标坐标；风被仿真但不进入 observation。
- `sailboat-s14-wind` 为 16 维观测，在上述状态后加入当前风速和风向。
- `sailboat-s14-obst-v3` 为 18 维观测，加入视野内最近障碍物特征；当前 reset 使用 7 个固定障碍物，碰撞阈值为 40 m。
- 动作为帆和舵的增量命令，两个维度的 action space 都是 `[-pi/18, pi/18]`；环境内部按 1 度单位量化目标角变化。
- 每个 agent action 驱动约 1 秒仿真；动力学使用自适应 Dormand-Prince 积分。基础风速 8 m/s，Dryden 一阶随机过程生成扰动。
- 目标距离不超过 10 m 时 terminated；越界、超时、积分失败（障碍物环境还包括碰撞）时 truncated。
- 主 reward 包含距离/沿 x 进度、前向速度、动作惩罚、375/250/125 m milestone、到达奖励、每步代价和截断惩罚。
- 主训练路径在 observation 与 action 上默认加入 3% sensor/actuator noise。

# Canonical SAC/SAC-LSTM Pipeline

当前训练入口是 `sailboat_rl.training.train_sac_nowind`、`train_sac_wind` 和 `train_sac_lstm`。算法源自 `PART4/seed_reward_ablation` 的正式 seed 版本；历史 `PART4/PART5` 保留为实验 provenance。

主 SAC-LSTM 当前实现：

- 15 个 `SubprocVecEnv` 环境；默认累计 9e6 transitions。脚本把 `max_e_steps=1000` 用于 warm-up/evaluation 假设，但训练环境的实际 TimeLimit 由外部 Gym registry 决定；README 的注册示例是 3000，当前安装值未验证。
- history window `K=10`。Replay transition 同时保存历史 state/action sequence、当前 state/action、next sequence/state、reward 和 done。
- Actor：历史 `[state, action]` 经 FC + 单层 LSTM + LayerNorm；当前 state 经独立 MLP；两支 concat 后输出 tanh-Gaussian policy。
- Double-Q critic：历史分支同样使用 LSTM，当前 `[state, action]` 使用 MLP；target critic 用 Polyak update。
- 使用 Z-score state normalizer、prioritized replay、gradient clipping 和 adaptive entropy coefficient。
- canonical SAC-FC 和 SAC-LSTM replay capacity 均为正式 seed 版本的 `1e6`；`PART4/SAC` 的旧 `1e3` 版本不是当前主干。
- 默认 `gamma=0.98`、hidden width 256、actor/critic learning rate `5e-5`、batch 256。代码条件是 `total_steps % 20 == 0` 时执行 8 次 critic update；因 `total_steps` 每轮增加 15，当前默认下实际每 60 个 aggregate transitions 命中一次。actor/alpha 每 4 次 critic update 更新一次。
- checkpoints 保存 actor、Q critic、normalizer 三个 `.pth` 文件；不保存 target critic、alpha 或 optimizer state。TensorBoard 写入 `runs/`。
- SAC-nowind、SAC-wind、SAC-LSTM 已分别完成 280-transition 短训练；每个模型实际执行 104 次 critic、26 次 actor/alpha update，参数变化、有限 loss、save/load 和 canonical evaluator 均已验证。该 smoke 结果不代表模型性能。

# Evaluation and Reference Results

评估入口包括 `PART4/SAC/test_eval*.py`、`batch_eval*.py` 以及 `PART4/seed_reward_ablation/seed_eval_suite/batch_eval_seed_ablation.py`。常用输出包括 episode CSV、summary CSV/Markdown、trajectory/action plots 和 manifest。

成功的 canonical metric 是 episode 末目标距离 `<= 10 m`。seed evaluation 中成功率在全部 episodes 上计算；时间、路径长度和控制变化率只在成功子集上统计。

当前最强的已提交聚合证据是 `seed_eval_20260518_002624`：6 个 checkpoints（SAC-LSTM、无风观测 FC SAC、显式风观测 FC SAC，各 2 个训练 seed），共 10,800 episodes，sensor/actuator noise 都为 3%。聚合结果：

- random wind：SAC-wind 94.65%，SAC-LSTM 93.65%，SAC-nowind 43.60%。
- fixed 150° / 180°：SAC-wind 99.50% / 93.75%，SAC-LSTM 82.75% / 82.75%，SAC-nowind 0% / 0%。

这些是 committed artifacts 支持的 reference results，不是本 clone 上已复现的结果；对应 model checkpoints 未提交。

`reward_ablation_new/test_results_batch/20260521_163928` 使用 step 8400、每个可用实验 1000 episodes、3% noise：no-progress 成功率 1.2%，no-action 98.0%，no-checkpoint 99.7%，no-arrival 99.6%。该 summary 没有 baseline 和 no-penalty row，不能据此声称所有非 progress reward 都无用。

PART5 attention outputs 是少量单 episode attention/trajectory artifacts；不能作为 attention 优于其他结构的总体性能证据。

# Experiment and Artifact Conventions

- canonical training 默认将 checkpoints 写入根 `canonical_runs/model/`，TensorBoard 写入 `canonical_runs/runs/`；路径由模块位置确定，也可用 `--output_dir` 显式覆盖。
- 多数训练脚本使用相对路径 `./model` 和 `runs/`；输出位置由启动时 working directory 决定。
- `.gitignore` 排除 `canonical_runs/`、`*.pth`、`*.pt`、`runs/`、压缩包和虚拟环境。
- 当前仓库没有任何 `.pth/.pt` checkpoint 或 TensorBoard event；已提交的是图片、CSV/NPY/JSON、summary 和部分日志。
- 一些 committed config/manifest 保存 Windows 绝对路径；迁移到新机器时必须通过 CLI 参数或本地配置重定位。
- `tests/test_canonical_core.py` 是 canonical regression suite；历史目录中的其他 `test_*.py` 主要仍是交互式/评估脚本。当前没有 CI 配置。
- 接手前 Git 只有一次初始化提交，因此不能用历史 commit 判断变体先后、active work 或失败路线。

# Known Constraints and Unknowns

- 历史训练 checkpoint 和原始 TensorBoard logs 不在仓库；canonical 短训练闭环已验证，但完整 9M training 和正式 10,800-episode evaluation 仍未重跑。
- 各复制实验目录存在代码漂移；更改一个环境或模型副本不会自动传播到其他实验。
- 主 README 的从根目录启动示例与脚本的相对输出路径组合，会把 `model/`、`runs/` 写到当前目录；实验目录 README 通常要求先 `cd` 到对应目录。
- PART5 attention/deep/meanpool 的公平对照、训练 seeds 和总体 benchmark 状态 unknown / not yet verified。
- actor-input 变体只有已提交的 5-run summaries；样本量和条件不足以建立稳定机制结论。

# Important Commands

从仓库根目录使用项目隔离环境：

```bash
.venv/bin/python -m sailboat_rl.training.train_sac_nowind
.venv/bin/python -m sailboat_rl.training.train_sac_wind
.venv/bin/python -m sailboat_rl.training.train_sac_lstm
```

正式 seed evaluation：

```bash
.venv/bin/python -m sailboat_rl.evaluation.batch_eval --model_dir /path/to/checkpoints --dvc cpu
```

最小 regression/smoke tests：

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_canonical_core.py' -v
```
