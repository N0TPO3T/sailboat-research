# 05 no penalty

This experiment removes the per-step penalty:

```python
r_penalty = -0.2
```

The truncation failure penalty is not one of the five red-box reward components
and is unchanged.

Kept reward components:

- `R_progress`
- `R_action`
- `R_checkpoint`
- `R_arrival`

Model prefix:

```text
saclstm_no_penalty_s14nowind
```

Run:

```powershell
cd D:\Project\26_4\sailboat_RL\PART4\reward_ablation_new\05_no_penalty
python train_lstm_reward_ablation.py
python test_eval_lstm_5runs.py
```
