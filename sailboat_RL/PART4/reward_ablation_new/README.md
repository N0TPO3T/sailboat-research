# SAC-LSTM reward ablation experiments

This folder contains five independent SAC-LSTM reward ablation experiments for
`sailboat-s14-nowind`. Each active subfolder removes exactly one red-box reward
component from:

```text
R = gamma * (R_progress + R_action) + R_checkpoint + R_arrival + R_penalty
```

The environment is loaded from each subfolder's local `reward_env.py`, not from
the global Gym registration. This prevents accidental use of the baseline reward.
Checkpoint and arrival thresholds follow the original SAC-LSTM model:
`375/250/125` for checkpoint bonuses and `10m` for arrival/done.

| Folder | Removed reward component | Model prefix |
| --- | --- | --- |
| `01_no_dense_progress_speed` | `R_progress` | `saclstm_no_dense_progress_speed_s14nowind` |
| `02_no_action_penalty` | `R_action` | `saclstm_no_action_penalty_s14nowind` |
| `03_no_checkpoint` | `R_checkpoint` | `saclstm_no_checkpoint_s14nowind` |
| `04_no_arrival` | `R_arrival` | `saclstm_no_arrival_s14nowind` |
| `05_no_penalty` | `R_penalty` | `saclstm_no_penalty_s14nowind` |

Old `model_1e3` checkpoints, generated test results, cache files, and the
incorrect `05_no_terminal_step_cost` experiment have been removed from this
folder. Regenerate formal outputs from the five active experiments above.

Default run pattern:

```powershell
cd D:\Project\26_4\sailboat_RL\PART4\reward_ablation_new\01_no_dense_progress_speed
python train_lstm_reward_ablation.py
python test_eval_lstm_5runs.py
```

Imported checkpoint note:

The active rerun uses replay buffer `int(1e6)` and writes checkpoints to
`model_buf1e6/`. The final training statistics can report
`total_steps=9000000`, while saved actor/q/normalizer checkpoint files may stop
at step `8400`. Use the latest matching actor/q checkpoint that actually
exists; do not fabricate a `9000` checkpoint from the final statistics file.
