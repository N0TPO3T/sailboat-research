# 04 no arrival

This experiment removes the target-arrival bonus:

```python
distance <= 10: +40
```

The target-reaching termination radius follows the paper formula at 5 m.

Kept reward components:

- `R_progress`
- `R_action`
- `R_checkpoint`
- `R_penalty`

Model prefix:

```text
saclstm_no_arrival_s14nowind
```

Run:

```powershell
cd D:\Project\26_4\sailboat_RL\PART4\reward_ablation_new\04_no_arrival
python train_lstm_reward_ablation.py
python test_eval_lstm_5runs.py
```

