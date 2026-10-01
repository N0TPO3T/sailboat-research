# 05 no terminal step cost

This experiment removes the truncated penalty and per-step time cost:

```python
if truncated:
    reward -= 100

reward -= 0.2
```

Termination and truncation conditions are unchanged.

Kept reward components:

- Dense progress and speed shaping.
- Large sail/rudder command penalties.
- Final reward scaling.
- Milestone and arrival bonuses.

Model prefix:

```text
saclstm_no_terminal_step_cost_s14nowind
```

Run:

```powershell
cd D:\Project\26_4\sailboat_RL\PART4\SAC\reward_ablation\05_no_terminal_step_cost
python train_lstm_reward_ablation.py
python test_eval_lstm_5runs.py
```

