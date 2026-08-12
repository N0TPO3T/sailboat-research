# 01 no dense progress speed

This experiment removes the dense progress and speed shaping term:

```python
(2 * dis_diff + x_dis_diff) + 0.5 * (u / (1 + abs(v)))
```

Kept reward components:

- Large sail/rudder command penalties.
- Final reward scaling.
- Milestone and arrival bonuses.
- Truncated penalty and per-step time cost.

Model prefix:

```text
saclstm_no_dense_progress_speed_s14nowind
```

Run:

```powershell
cd D:\Project\26_4\sailboat_RL\PART4\SAC\reward_ablation\01_no_dense_progress_speed
python train_lstm_reward_ablation.py
python test_eval_lstm_5runs.py
```

