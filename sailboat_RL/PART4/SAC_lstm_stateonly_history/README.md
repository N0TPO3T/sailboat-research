# SAC-LSTM State-Only History 消融实验副本

本目录是第四章 SAC-LSTM 方法的第三个独立消融实验目录。原始代码仍保留在 `PART4/SAC`，previous-action 版本保留在 `PART4/SAC_lstm_actor_singlelink`，zero-action 版本保留在 `PART4/SAC_lstm_actor_zeroaction`，本目录不会修改它们。

## 实验问题

本实验用于验证：

```text
历史 LSTM 是否必须显式输入 action_sequence？
```

环境状态中已经包含实际执行后的帆角和舵角：

```text
state[8] = delta_s
state[9] = delta_r
```

而动作是帆角/舵角变化量。动作执行后，其影响会通过实际角度、速度、航向、横漂、距离变化等状态维度体现出来。因此可以测试：

```text
LSTM([s,a]) 是否真的优于 LSTM([s])
```

## 核心改动

原始 SAC-LSTM 历史分支：

```text
concat(state_sequence, action_sequence)
  -> Linear(state_dim + action_dim, hidden)
  -> LSTM
```

本实验历史分支：

```text
state_sequence
  -> Linear(state_dim, hidden)
  -> LSTM
```

函数接口保持兼容：

```text
state_sequence, action_sequence, current_state
```

但 `action_sequence` 不再进入 Actor/Critic 的历史 LSTM 分支，只作为兼容参数保留，避免改 ReplayBuffer、训练脚本和评估脚本。

## 主要文件

- `utils_lstm.py`：Actor、Double Q Critic、Replay/评估辅助函数。state-only history 改动在这里。
- `SAC_lstm.py`：SAC-LSTM agent、训练更新逻辑、ReplayBuffer。checkpoint 默认保存到本目录的 `model/`。
- `parll_lstm_normal.py`：并行环境训练入口。
- `test_eval_lstm.py`：单次测试评估脚本。
- `test_eval_lstm_5runs.py`：多次测试评估脚本。
- `batch_eval_lstm.py`：批量并行测试脚本。
- `sensitivity_analysis.py`：输入特征敏感性分析。
- `sailboat_s14.py`、`sailboat_s14_wind.py`：本实验副本使用的帆船环境实现。
- `noise_utils_nowind.py`：训练和评估使用的传感器/执行器噪声工具。

## 对照关系

```text
原始 SAC-LSTM:        LSTM([s,a]), Actor(s)
previous-action版:   LSTM([s,a]), Actor([s,a_{t-1}])
zero-action版:       LSTM([s,a]), Actor([s,0])
state-only-history:  LSTM([s]),   Actor([s,0])
```

这个版本可以直接回答：历史动作命令是否提供了状态轨迹之外的额外有效信息。

## Actor、Critic 与 LSTM 结构设计

### Actor 结构

Actor 是 SAC 的随机策略网络，输出动作高斯分布的均值和标准差。

输入接口：

```text
state_sequence:  [batch, seq_len, state_dim]
action_sequence: [batch, seq_len, action_dim]  # 兼容参数，历史分支不使用
current_state:   [batch, state_dim]
```

历史分支：

```text
state_sequence
  -> Linear(state_dim, hidden)
  -> ReLU
  -> Dropout
  -> LSTM(hidden, hidden)
  -> LayerNorm
  -> 取最后时间步输出 lstm_final
```

当前分支沿用 zero-action 设计：

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

- 不让历史动作命令直接进入 LSTM。
- 依靠状态中的帆角、舵角和船体运动响应表达动作影响。
- 与 zero-action 版本相比，唯一关键变量是历史 LSTM 是否包含 `action_sequence`。

### Critic 结构

Critic 仍使用 SAC 标准 Double Q：

```text
Q1(D_t, s_t, a_t)
Q2(D_t, s_t, a_t)
```

但这里的历史上下文 `D_t` 只包含状态序列：

```text
D_t = [s_{t-K}, ..., s_{t-1}]
```

历史分支：

```text
state_sequence
  -> Linear(state_dim, hidden)
  -> ReLU
  -> Dropout
  -> LSTM(hidden, hidden)
  -> LayerNorm
  -> 取最后时间步输出 lstm_final
```

当前状态-动作分支保留：

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

Critic 当前动作 `current_action` 必须保留，因为 Critic 的职责是评价当前动作 `a_t` 的长期价值。

### LSTM 结构与作用

Actor 和 Critic 都使用单层 LSTM：

```text
input_size  = hidden
hidden_size = hidden
num_layers  = 1
batch_first = True
```

和原始版本的区别是，LSTM 输入来自状态序列而不是状态-动作拼接：

```text
s_i -> Linear -> ReLU -> Dropout -> LSTM
```

训练时输入完整历史窗口：

```text
[batch, 10, state_dim]
```

并取最后时间步作为历史摘要：

```text
lstm_final = lstm_out[:, -1, :]
```

环境交互时使用单步模式：

```text
prev_state -> LSTM
```

`prev_action` 仍作为函数参数传入，但只为接口兼容保留，不参与历史 LSTM 编码。

## 运行说明

建议从本目录运行脚本，避免相对路径混淆：

```powershell
cd D:\Project\26_4\sailboat_RL\PART4\SAC_lstm_stateonly_history
D:\anadonda3\envs\sailboat\python.exe parll_lstm_normal.py
```

训练默认模型前缀为：

```text
saclstm_stateonly_history_s14nowind_final
```

模型默认保存到：

```text
PART4/SAC_lstm_stateonly_history/model/
```

TensorBoard 日志默认保存到：

```text
PART4/SAC_lstm_stateonly_history/runs/
```

## 验证命令

静态导入：

```powershell
$env:KMP_DUPLICATE_LIB_OK='TRUE'
D:\anadonda3\envs\sailboat\python.exe -c "import sys; sys.path.insert(0, r'D:\Project\26_4\sailboat_RL\PART4\SAC_lstm_stateonly_history'); from SAC_lstm import SAC_lstm_countinuous; print('ok')"
```

Actor shape 验证：

```powershell
$env:KMP_DUPLICATE_LIB_OK='TRUE'
D:\anadonda3\envs\sailboat\python.exe -c "import sys, torch; sys.path.insert(0, r'D:\Project\26_4\sailboat_RL\PART4\SAC_lstm_stateonly_history'); from utils_lstm import Actor; actor=Actor(14,2,(256,256)); sseq=torch.randn(4,10,14); aseq=torch.randn(4,10,2); scur=torch.randn(4,14); a,logp=actor(state_sequence=sseq, action_sequence=aseq, current_state=scur, with_logprob=True); print(a.shape, logp.shape)"
```

Critic shape 验证：

```powershell
$env:KMP_DUPLICATE_LIB_OK='TRUE'
D:\anadonda3\envs\sailboat\python.exe -c "import sys, torch; sys.path.insert(0, r'D:\Project\26_4\sailboat_RL\PART4\SAC_lstm_stateonly_history'); from utils_lstm import Double_Q_Critic; q=Double_Q_Critic(14,2,(256,256),(256,128)); sseq=torch.randn(4,10,14); aseq=torch.randn(4,10,2); scur=torch.randn(4,14); acur=torch.randn(4,2); q1,q2=q(state_sequence=sseq, action_sequence=aseq, current_state=scur, current_action=acur); print(q1.shape, q2.shape)"
```

## 注意事项

- 本目录 Actor/Critic 结构与之前所有 checkpoint 都不兼容，旧 checkpoint 不能直接加载。
- 需要重新训练 `saclstm_stateonly_history_s14nowind_final`。
- 本实验只覆盖第四章 SAC-LSTM，不包含 `PART5` attention 版本。
