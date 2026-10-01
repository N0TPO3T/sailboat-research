# SAC-LSTM Actor Zero-Action 实验副本

本目录是第四章 SAC-LSTM 方法的第二个独立改版实验目录。原始代码仍保留在 `PART4/SAC`，上一动作上下文版本保留在 `PART4/SAC_lstm_actor_singlelink`，本目录不会修改它们。

## 改动目标

本实验用于验证一个更纯粹的结构对齐思路：

```text
Critic: Q(D_t, s_t, a_t)
Actor:  pi(D_t, s_t, 0)
```

也就是 Actor 和 Critic 都保留“历史状态-动作序列 + 当前状态-动作对”的输入组织形式，但 Actor 当前还没有待输出动作 `a_t`，所以在当前分支中使用零动作占位：

```text
current_sa = concat(current_state, zero_action)
```

其中：

- `zero_action` 的形状是 `[batch, action_dim]`
- `zero_action` 的值全部为 0
- `prev_action` 和 `action_sequence` 仍用于历史 LSTM 分支
- Actor 当前分支不使用 `a_{t-1}`，只使用零动作占位保持维度和结构对齐

## 主要文件

- `utils_lstm.py`：Actor、Double Q Critic、Replay/评估辅助函数。Actor 的 zero-action 改动在这里。
- `SAC_lstm.py`：SAC-LSTM agent、训练更新逻辑、ReplayBuffer。checkpoint 默认保存到本目录的 `model/`。
- `parll_lstm_normal.py`：并行环境训练入口。
- `test_eval_lstm.py`：单次测试评估脚本。
- `test_eval_lstm_5runs.py`：多次测试评估脚本。
- `batch_eval_lstm.py`：批量并行测试脚本。
- `sensitivity_analysis.py`：输入特征敏感性分析。
- `sailboat_s14.py`、`sailboat_s14_wind.py`：本实验副本使用的帆船环境实现。
- `noise_utils_nowind.py`：训练和评估使用的传感器/执行器噪声工具。

## 与其他版本的区别

原始 SAC-LSTM Actor：

```text
Actor(D_t, s_t)
  = policy(LSTM(D_t), MLP(s_t))
```

上一动作上下文版本：

```text
Actor(D_t, s_t, a_{t-1})
  = policy(LSTM(D_t), MLP([s_t, a_{t-1}]))
```

本 zero-action 版本：

```text
Actor(D_t, s_t, 0)
  = policy(LSTM(D_t), MLP([s_t, 0]))
```

Critic 保持不变：

```text
Critic(D_t, s_t, a_t)
  = Q(LSTM(D_t), MLP([s_t, a_t]))
```

这个版本更适合验证“Actor/Critic 当前分支结构维度对齐本身是否有帮助”；上一动作上下文版本更适合验证“上一动作物理上下文是否有帮助”。

## Actor、Critic 与 LSTM 结构设计

### 总体设计思路

第四章 SAC-LSTM 的核心问题是部分可观测性：无人帆船控制中，风速、风向、执行器滞后和环境扰动不能总是直接可靠观测。LSTM 读取最近一段历史状态-动作序列，用运动变化间接补偿当前单帧状态的信息不足。

本实验保留历史 LSTM 设计，但把 Actor 当前分支改成零动作占位：

```text
历史分支: [(s_{t-K}, a_{t-K}), ..., (s_{t-1}, a_{t-1})]
当前分支: [s_t, 0]
输出:     a_t
```

其中 `K=10`。零动作占位只用于 Actor 当前分支，不代表环境真实执行了零动作。

### Actor 结构

Actor 是 SAC 的随机策略网络，输出动作高斯分布的均值和标准差。

输入：

```text
state_sequence:  [batch, seq_len, state_dim]
action_sequence: [batch, seq_len, action_dim]
current_state:   [batch, state_dim]
```

历史分支：

```text
concat(state_sequence, action_sequence)
  -> Linear(state_dim + action_dim, hidden)
  -> ReLU
  -> Dropout
  -> LSTM(hidden, hidden)
  -> LayerNorm
  -> 取最后时间步输出 lstm_final
```

当前分支：

```text
zero_action = zeros([batch, action_dim])
concat(current_state, zero_action)
  -> Linear(state_dim + action_dim, hidden)
  -> ReLU
  -> Dropout
  -> current_sa_processed
```

融合与输出：

```text
concat(lstm_final, current_sa_processed)
  -> Linear(2 * hidden, 256)
  -> ReLU
  -> Dropout
  -> mu_layer
  -> log_std_layer
```

动作采样：

```text
std = exp(clamp(log_std))
u   ~ Normal(mu, std)
a_t = tanh(u)
```

设计动机：

- 保持 Actor 当前分支输入维度为 `state_dim + action_dim`，和 Critic 一致。
- 不引入 `a_{t-1}` 的物理偏置，用零动作只做结构占位。
- 便于和原始 Actor、上一动作上下文 Actor 做消融对比。
- 如果性能提升，说明结构对齐本身可能有帮助；如果不如上一动作版本，说明上一动作上下文携带了有效物理信息。

### Critic 结构

Critic 使用 SAC 标准 Double Q：

```text
Q1(D_t, s_t, a_t)
Q2(D_t, s_t, a_t)
```

每个 Q 网络都有历史分支和当前分支。

历史分支：

```text
concat(state_sequence, action_sequence)
  -> Linear(state_dim + action_dim, hidden)
  -> ReLU
  -> Dropout
  -> LSTM(hidden, hidden)
  -> LayerNorm
  -> 取最后时间步输出 lstm_final
```

当前状态-动作分支：

```text
concat(current_state, current_action)
  -> Linear(state_dim + action_dim, hidden)
  -> ReLU
  -> Dropout
  -> current_sa_processed
```

融合与输出：

```text
concat(lstm_final, current_sa_processed)
  -> Linear(2 * hidden, hidden_out)
  -> ReLU
  -> Dropout
  -> Linear(hidden_out, 1)
  -> Q value
```

训练 target 中使用：

```text
min(Q1, Q2)
```

用于降低 Q 值过估计。

### LSTM 结构与作用

Actor 和 Critic 都使用单层 LSTM：

```text
input_size  = hidden
hidden_size = hidden
num_layers  = 1
batch_first = True
```

LSTM 的输入是历史状态-动作拼接后的特征：

```text
[s_i, a_i] -> Linear -> ReLU -> Dropout -> LSTM
```

训练时输入完整历史窗口：

```text
[batch, 10, state_dim + action_dim]
```

并取最后一个时间步作为历史摘要：

```text
lstm_final = lstm_out[:, -1, :]
```

环境交互时使用单步模式：

```text
[prev_state, prev_action] -> LSTM
```

同时按 `env_id` 维护 hidden state，使并行环境中的每条轨迹都有自己的时序记忆。episode 结束后需要调用 `reset_hidden_state(env_id)` 或清空全部 hidden state。

LSTM 在本任务中的作用：

- 从过去航向、速度、横向漂移和控制动作变化中隐式推断风场影响。
- 捕捉帆船动力学惯性、控制滞后和连续控制趋势。
- 在缺少显式风观测时，为 Actor 和 Critic 提供历史动态上下文。

## 运行说明

建议从本目录运行脚本，避免相对路径混淆：

```powershell
cd D:\Project\26_4\sailboat_RL\PART4\SAC_lstm_actor_zeroaction
D:\anadonda3\envs\sailboat\python.exe parll_lstm_normal.py
```

训练默认模型前缀为：

```text
saclstm_zeroaction_s14nowind_final
```

模型默认保存到：

```text
PART4/SAC_lstm_actor_zeroaction/model/
```

TensorBoard 日志默认保存到：

```text
PART4/SAC_lstm_actor_zeroaction/runs/
```

## 验证命令

静态导入：

```powershell
$env:KMP_DUPLICATE_LIB_OK='TRUE'
D:\anadonda3\envs\sailboat\python.exe -c "import sys; sys.path.insert(0, r'D:\Project\26_4\sailboat_RL\PART4\SAC_lstm_actor_zeroaction'); from SAC_lstm import SAC_lstm_countinuous; print('ok')"
```

Actor shape 验证：

```powershell
$env:KMP_DUPLICATE_LIB_OK='TRUE'
D:\anadonda3\envs\sailboat\python.exe -c "import sys, torch; sys.path.insert(0, r'D:\Project\26_4\sailboat_RL\PART4\SAC_lstm_actor_zeroaction'); from utils_lstm import Actor; actor=Actor(14,2,(256,256)); sseq=torch.randn(4,10,14); aseq=torch.randn(4,10,2); scur=torch.randn(4,14); a,logp=actor(state_sequence=sseq, action_sequence=aseq, current_state=scur, with_logprob=True); print(a.shape, logp.shape)"
```

## 注意事项

- 本目录 Actor 结构与原始 Actor、上一动作上下文 Actor 都不兼容，旧 checkpoint 不能直接加载。
- 需要重新训练 `saclstm_zeroaction_s14nowind_final`。
- 本实验只覆盖第四章 SAC-LSTM，不包含 `PART5` attention 版本。
