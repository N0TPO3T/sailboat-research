# 01 no progress

This experiment removes `R_progress`:

```python
(2 * dis_diff + x_dis_diff) + 0.5 * (u / (1 + abs(v)))
```

Kept reward components:

- `R_action`
- `R_checkpoint`
- `R_arrival`
- `R_penalty`

Model prefix:

```text
saclstm_no_dense_progress_speed_s14nowind
```

Run:

```powershell
cd D:\Project\26_4\sailboat_RL\PART4\reward_ablation_new\01_no_dense_progress_speed
python train_lstm_reward_ablation.py
python test_eval_lstm_5runs.py
```
