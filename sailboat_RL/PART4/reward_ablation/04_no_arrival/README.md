# 04 no arrival

This experiment removes the target-arrival bonus:

```python
distance <= 10:  +40
```

The target-reaching termination condition is unchanged.

Kept reward components:

- Dense progress and speed shaping.
- Large sail/rudder command penalties.
- Final reward scaling.
- Checkpoint bonuses.
- Truncated penalty and per-step time cost.

Model prefix:

```text
saclstm_no_arrival_s14nowind
```

Run:

```powershell
cd D:\Project\26_4\sailboat_RL\PART4\SAC\reward_ablation\04_no_arrival
python train_lstm_reward_ablation.py
python test_eval_lstm_5runs.py
```
