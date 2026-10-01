# SAC-LSTM reward ablation experiments

This folder contains five independent SAC-LSTM reward ablation experiments for
`sailboat-s14-nowind`. Each subfolder removes exactly one reward component and
keeps the original SAC-LSTM architecture, noise settings, and training defaults.

The environment is loaded from each subfolder's local `reward_env.py`, not from
the global Gym registration. This prevents accidental use of the baseline reward.

| Folder | Removed reward component | Model prefix |
| --- | --- | --- |
| `01_no_dense_progress_speed` | Dense progress and speed shaping | `saclstm_no_dense_progress_speed_s14nowind` |
| `02_no_action_penalty` | Large sail/rudder command penalties | `saclstm_no_action_penalty_s14nowind` |
| `03_no_checkpoint` | Checkpoint bonuses | `saclstm_no_checkpoint_s14nowind` |
| `04_no_arrival` | Target-arrival bonus | `saclstm_no_arrival_s14nowind` |
| `05_no_terminal_step_cost` | Truncated penalty and per-step cost | `saclstm_no_terminal_step_cost_s14nowind` |

Default run pattern:

```powershell
cd D:\Project\26_4\sailboat_RL\PART4\SAC\reward_ablation\01_no_dense_progress_speed
python train_lstm_reward_ablation.py
python test_eval_lstm_5runs.py
```
