# 02 no action

This experiment removes `R_action`:

```python
r_action = -(abs(sail) // delta) * 0.1 - (abs(rudder) // delta) * 0.1
```

Kept reward components:

- `R_progress`
- `R_checkpoint`
- `R_arrival`
- `R_penalty`

Model prefix:

```text
saclstm_no_action_penalty_s14nowind
```

Run:

```powershell
cd D:\Project\26_4\sailboat_RL\PART4\reward_ablation\02_no_action_penalty
python train_lstm_reward_ablation.py
python test_eval_lstm_5runs.py
```
