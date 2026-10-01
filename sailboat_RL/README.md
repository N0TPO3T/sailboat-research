# Sailboat RL — 帆船强化学习控制

基于 **Gymnasium** 的帆船仿真与深度强化学习控制研究项目，核心方法是 **SAC / SAC-LSTM**，并包含 PPO、TD3、MPC 等基线方法及多组消融实验。

## 项目结构

```
sailboat_RL/
├── gymnasium/envs/sailboat/     # 自定义帆船 Gym 环境（核心，V1~V3、含风场/障碍物/航路点）
├── PART4/
│   ├── SAC/                     # 主实验：SAC_fc、SAC_lstm + 并行训练脚本（parll_*）
│   ├── SAC_lstm_actor_singlelink/   # 消融：actor 仅单连接
│   ├── SAC_lstm_actor_zeroaction/   # 消融：actor 零动作输入
│   ├── SAC_lstm_stateonly_history/  # 消融：仅状态历史
│   ├── reward_ablation/         # 奖励函数消融（进度/动作惩罚/航点/到达/终止代价）
│   ├── reward_ablation_new/     # 奖励消融（新版）
│   ├── seed_reward_ablation/    # 多随机种子 × 奖励消融
│   ├── MPC/                     # MPC 基线 + 与 SAC-LSTM 对比
│   ├── PPO/                     # PPO 基线
│   └── TD3/                     # TD3 基线
├── PART5/
│   ├── SAC-LSTM-att/            # SAC-LSTM + 注意力机制
│   ├── SAC-LSTM-deep/           # 加深网络
│   └── SAC-LSTM-meanpool/       # mean-pool 变体
├── EP_image/                    # 实验过程截图
├── docs/refs/                   # 参考文献（论文 PDF）
└── sailboat_s14_obst_V3.py      # 障碍物场景主环境（Dryden 风场模型）
```

## 环境安装

```bash
# 1. 创建虚拟环境并安装依赖（requirements 见 PART4/SAC/requirements_sac_local.txt）
python -m venv .venv
pip install -r PART4/SAC/requirements_sac_local.txt   # 或根目录 requirements.txt

# 2. 安装自定义帆船环境
#    gymnasium 中未内置 sailboat 环境，需将 gymnasium/envs/sailboat/ 复制到
#    站点包 gymnasium/envs/ 下，并在 gymnasium/envs/__init__.py 中注册，例如：
from gymnasium.envs.sailboat import Sailboat_nowind_last
register(id="sailboat-s14-nowind", entry_point="gymnasium.envs.sailboat:Sailboat_nowind_last", max_episode_steps=3000)
```

## 运行

```bash
# 训练 SAC-LSTM（无风场景）
python PART4/SAC/parll_lstm_normal.py

# 训练 SAC（FC 版本）
python PART4/SAC/parll_SAC_normal.py

# 评估
python PART4/SAC/test_eval_lstm.py
```

> 注意：脚本通过 `gym.make("sailboat-s14-nowind")` 等方式创建环境，
> 依赖项目根目录下的定制 `gymnasium`（建议将项目根加入 PYTHONPATH，
> 或使用 PyCharm 打开项目根目录运行）。

## 已上传内容说明

- ✅ 源码、训练/评估脚本、README、配置文件、实验图片、参考论文（docs/refs）
- ❌ 模型检查点（`.pth`）、TensorBoard 日志（`runs/`）、压缩包（`.zip/.rar`）——体积过大，不入库

各实验目录下的 `README.md`（如 `PART4/reward_ablation/README.md`）含该实验的详细说明。
