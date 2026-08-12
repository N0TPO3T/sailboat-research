# 03 no checkpoint

This experiment removes the checkpoint bonuses:

```python
distance <= 375: +3
distance <= 250: +5
distance <= 125: +12
```

Kept reward components:

- `R_progress`
- `R_action`
- `R_arrival`
- `R_penalty`

Model prefix:

```text
saclstm_no_checkpoint_s14nowind
```

Run:

```powershell
cd D:\Project\26_4\sailboat_RL\PART4\reward_ablation_new\03_no_checkpoint
python train_lstm_reward_ablation.py
python test_eval_lstm_5runs.py
```

