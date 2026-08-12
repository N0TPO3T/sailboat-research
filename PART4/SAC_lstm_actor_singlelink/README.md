# SAC-LSTM Actor Single-Link 实验副本

本目录是第四章 SAC-LSTM 方法的独立改版实验目录，原始代码仍保留在 `PART4/SAC`，本目录中的修改不会影响原始实现。

## 改动目标

原始 SAC-LSTM 的 Actor 使用两路输入：

```text
历史状态-动作序列 -> LSTM
当前状态          -> MLP
两路特征拼接      -> 动作分布
```

本实验把 Actor 的当前分支改成和 Critic 更一致的形式：

```text
历史状态-动作序列       -> LSTM
当前状态 + 上一时刻动作 -> MLP
两路特征拼接            -> 动作分布
```

也就是 Actor 内部使用：

```text
current_sa = concat(current_state, previous_action)
```

其中：

- 训练序列模式下，`previous_action = action_sequence[:, -1, :]`
- 单步环境交互模式下，`previous_action = prev_action`

这样 Actor 的输入表达更接近 Critic 的“历史 `(s,a)` + 当前 `(s,a)`”结构，但不会把待输出动作 `a_t` 作为 Actor 输入，避免策略网络形成循环依赖。

## 主要文件

- `utils_lstm.py`：Actor、Double Q Critic、Replay/评估辅助函数。Actor 的 single-link 改动在这里。
- `SAC_lstm.py`：SAC-LSTM agent、训练更新逻辑、ReplayBuffer。checkpoint 默认保存到本目录的 `model/`。
- `parll_lstm_normal.py`：并行环境训练入口。
- `test_eval_lstm.py`：单次测试评估脚本。
- `test_eval_lstm_5runs.py`：多次测试评估脚本。
- `batch_eval_lstm.py`：批量并行测试脚本。
- `sensitivity_analysis.py`：输入特征敏感性分析。
- `sailboat_s14.py`、`sailboat_s14_wind.py`：本实验副本使用的帆船环境实现。
- `noise_utils_nowind.py`：训练和评估使用的传感器/执行器噪声工具。

## 与原始 SAC-LSTM 的区别

原始 Actor 当前分支：

```python
current_state_processed = current_state_fc(current_state)
```

本目录 Actor 当前分支：

```python
current_sa = torch.cat([current_state, current_action_context], dim=1)
current_sa_processed = current_sa_fc(current_sa)
```

Critic 结构保持不变。

## Actor、Critic 与 LSTM 结构设计

### 总体设计思路

第四章 SAC-LSTM 的核心思想是：无人帆船在实际控制中不能总是可靠获得完整风速、风向信息，因此当前单帧状态 `s_t` 不能完整描述环境。LSTM 用来读取最近一段历史状态-动作序列，从船体运动变化中隐式估计风况、扰动、执行器滞后和航向变化趋势。

本实验保留这个思想，同时让 Actor 的当前输入分支更接近 Critic：

```text
历史分支: [(s_{t-K}, a_{t-K}), ..., (s_{t-1}, a_{t-1})]
当前分支: [s_t, a_{t-1}]
输出:     a_t
```

其中 `K=10`，也就是使用最近 10 步历史。`a_{t-1}` 表示当前决策前实际执行过的上一动作，它不是 Actor 将要输出的 `a_t`，因此不会产生循环依赖。

### Actor 结构

Actor 是随机策略网络，输出动作分布的均值和标准差，然后通过重参数采样得到动作。

输入：

```text
state_sequence:  [batch, seq_len, state_dim]
action_sequence: [batch, seq_len, action_dim]
current_state:   [batch, state_dim]
```

训练序列模式下：

```text
previous_action = action_sequence[:, -1, :]
```

单步环境交互模式下：

```text
previous_action = prev_action
```

网络流程：

```text
历史状态-动作序列
  -> concat(state_sequence, action_sequence)
  -> Linear(state_dim + action_dim, hidden)
  -> ReLU
  -> Dropout
  -> LSTM(hidden, hidden)
  -> LayerNorm
  -> 取最后时间步输出 lstm_final

当前状态-上一动作
  -> concat(current_state, previous_action)
  -> Linear(state_dim + action_dim, hidden)
  -> ReLU
  -> Dropout
  -> current_sa_processed

特征融合
  -> concat(lstm_final, current_sa_processed)
  -> Linear(2 * hidden, 256)
  -> ReLU
  -> Dropout
  -> mu_layer
  -> log_std_layer
```

输出：

```text
mu      = 动作高斯分布均值
log_std = 动作高斯分布标准差对数
std     = exp(clamp(log_std))
u       ~ Normal(mu, std)
a_t     = tanh(u)
```

`tanh` 用于把动作压缩到 `[-1, 1]`，后续再映射到环境动作范围。`with_logprob=True` 时，会计算 SAC 需要的 tanh 修正 log probability。

设计动机：

- 历史 LSTM 分支负责提取风场和船体动态的隐含信息。
- 当前 `[s_t, a_{t-1}]` 分支让 Actor 明确知道当前状态是在哪个上一动作作用后形成的。
- 对帆船而言，帆角、舵角有连续性和执行滞后，上一动作对当前控制决策有直接参考价值。
- 该结构比原 Actor 的 `current_state` 单独分支更接近 Critic 的当前 `(s,a)` 表达。

### Critic 结构

Critic 使用 SAC 标准的 Double Q 结构，包含两个独立的 Q 网络：

```text
Q1(D_t, s_t, a_t)
Q2(D_t, s_t, a_t)
```

其中：

```text
D_t = [(s_{t-K}, a_{t-K}), ..., (s_{t-1}, a_{t-1})]
```

每个 Q 网络都有两条输入分支。

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

Q1 和 Q2 的结构相同，但参数独立。训练 target 中使用：

```text
min(Q1, Q2)
```

这样可以减少 Q 值过估计，这是 SAC 的常规设计。

设计动机：

- Critic 需要判断“在当前历史上下文和当前状态下，执行动作 `a_t` 的长期价值”。
- 历史 LSTM 分支提供动态背景，当前 `(s_t, a_t)` 分支提供被评价的具体动作。
- Double Q 通过两个独立估计器降低过估计风险，使 Actor 更新更稳定。

### LSTM 结构与作用

Actor 和 Critic 都使用单层 LSTM：

```text
input_size  = hidden
hidden_size = hidden
num_layers  = 1
batch_first = True
```

LSTM 的输入不是原始状态，而是每个历史时刻的状态-动作拼接经过一层 FC 后的特征：

```text
[s_i, a_i] -> Linear -> ReLU -> Dropout -> LSTM
```

训练时使用完整历史窗口：

```text
[batch, 10, state_dim + action_dim]
```

并取最后一个时间步输出作为历史摘要：

```text
lstm_final = lstm_out[:, -1, :]
```

环境交互时使用单步模式：

```text
[prev_state, prev_action] -> LSTM
```

同时按 `env_id` 维护 hidden state，使并行环境中的每条轨迹都有自己的时序记忆。episode 结束后需要调用 `reset_hidden_state(env_id)` 或清空全部 hidden state。

LSTM 在这个任务中的作用不是简单增加网络层数，而是处理部分可观测性：

- 根据过去的航向、速度、横向漂移和控制动作变化，隐式推断风向/风速影响。
- 捕捉帆船动力学中的惯性、滞后和连续控制趋势。
- 让策略在缺少显式风观测时，仍能利用历史运动轨迹补偿信息不足。

### 本实验结构与原结构的关键差异

原始 Actor：

```text
Actor(D_t, s_t)
  = policy(LSTM(D_t), MLP(s_t))
```

本实验 Actor：

```text
Actor(D_t, s_t, a_{t-1})
  = policy(LSTM(D_t), MLP([s_t, a_{t-1}]))
```

Critic 仍然是：

```text
Critic(D_t, s_t, a_t)
  = Q(LSTM(D_t), MLP([s_t, a_t]))
```

因此本实验让 Actor 和 Critic 的输入组织方式更一致，但两者语义仍然不同：

- Actor 使用 `a_{t-1}` 作为上一动作上下文，并输出 `a_t`。
- Critic 使用 `a_t` 作为待评价动作，并输出 Q 值。

## 运行说明

建议从本目录运行脚本，避免相对路径混淆：

```powershell
cd D:\Project\26_4\sailboat_RL\PART4\SAC_lstm_actor_singlelink
D:\anadonda3\envs\sailboat\python.exe parll_lstm_normal.py
```

训练默认模型前缀为：

```text
saclstm_singlelink_s14nowind_final
```

模型默认保存到：

```text
PART4/SAC_lstm_actor_singlelink/model/
```

TensorBoard 日志默认保存到：

```text
PART4/SAC_lstm_actor_singlelink/runs/
```

## 验证命令

静态导入：

```powershell
$env:KMP_DUPLICATE_LIB_OK='TRUE'
D:\anadonda3\envs\sailboat\python.exe -c "import sys; sys.path.insert(0, r'D:\Project\26_4\sailboat_RL\PART4\SAC_lstm_actor_singlelink'); from SAC_lstm import SAC_lstm_countinuous; print('ok')"
```

Actor shape 验证：

```powershell
$env:KMP_DUPLICATE_LIB_OK='TRUE'
D:\anadonda3\envs\sailboat\python.exe -c "import sys, torch; sys.path.insert(0, r'D:\Project\26_4\sailboat_RL\PART4\SAC_lstm_actor_singlelink'); from utils_lstm import Actor; actor=Actor(14,2,(256,256)); sseq=torch.randn(4,10,14); aseq=torch.randn(4,10,2); scur=torch.randn(4,14); a,logp=actor(state_sequence=sseq, action_sequence=aseq, current_state=scur, with_logprob=True); print(a.shape, logp.shape)"
```

## 注意事项

- 本目录 Actor 结构与原始 Actor 不兼容，不能直接加载原始 `saclstm_s14nowind_final_actor*.pth`。
- 需要重新训练 `saclstm_singlelink_s14nowind_final`。
- 本实验只覆盖第四章 SAC-LSTM，不包含 `PART5` attention 版本。
