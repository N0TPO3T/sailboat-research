# 02 no action penalty

This experiment removes the large action penalties for sail and rudder commands:

```python
reward -= abs(sail) // (np.pi / 180) * 0.5
reward -= abs(rudder) // (np.pi / 180) * 0.5
```

Kept reward components:

- Dense progress and speed shaping.
- Small-action scaling bonuses and final reward scaling.
- Milestone and arrival bonuses.
- Truncated penalty and per-step time cost.

Model prefix:

```text
saclstm_no_action_penalty_s14nowind
```

Run:

```powershell
cd D:\Project\26_4\sailboat_RL\PART4\SAC\reward_ablation\02_no_action_penalty
python train_lstm_reward_ablation.py
python test_eval_lstm_5runs.py
```

