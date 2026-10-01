# Seed and Reward Ablation Baselines

This directory contains isolated copies of the PART4 SAC baselines for seed
ablation experiments on the 4090 machine. The original `PART4/SAC` directory is
not modified.

## Scope

- `SAC-LSTM` on `sailboat-s14-nowind`
- `SAC` on `sailboat-s14-nowind`
- `SAC` on `sailboat-s14-wind`
- Training seeds: `100`, `200`
- Replay buffer size: `int(1e6)` for both `SAC_lstm.py` and `SAC_fc.py`

## Files

- `train_saclstm_s14_nowind.py`: SAC-LSTM training on `sailboat-s14-nowind`
- `train_sac_s14_nowind.py`: SAC training on `sailboat-s14-nowind`
- `train_sac_s14_wind.py`: SAC training on `sailboat-s14-wind`
- `SAC_lstm.py`: copied SAC-LSTM agent with `ReplayBuffer=1e6`
- `SAC_fc.py`: copied SAC agent with `ReplayBuffer=1e6`
- `utils_lstm.py`, `utils_fc.py`, `noise_utils_nowind.py`, `noise_utils_wind.py`: copied helpers

Each training script changes the current working directory to this folder, so
`runs/` and `model/` are created inside `PART4/seed_reward_ablation`.

## Commands

Run from the repository root or from this directory.

```powershell
D:\anadonda3\envs\sailboat\python.exe PART4\seed_reward_ablation\train_saclstm_s14_nowind.py --seed 100
D:\anadonda3\envs\sailboat\python.exe PART4\seed_reward_ablation\train_saclstm_s14_nowind.py --seed 200

D:\anadonda3\envs\sailboat\python.exe PART4\seed_reward_ablation\train_sac_s14_nowind.py --seed 100
D:\anadonda3\envs\sailboat\python.exe PART4\seed_reward_ablation\train_sac_s14_nowind.py --seed 200

D:\anadonda3\envs\sailboat\python.exe PART4\seed_reward_ablation\train_sac_s14_wind.py --seed 100
D:\anadonda3\envs\sailboat\python.exe PART4\seed_reward_ablation\train_sac_s14_wind.py --seed 200
```

## Output Names

Model and TensorBoard prefixes are generated from the selected seed:

- `saclstm_s14nowind_buf1e6_seed100`
- `saclstm_s14nowind_buf1e6_seed200`
- `sac_s14nowind_buf1e6_seed100`
- `sac_s14nowind_buf1e6_seed200`
- `sac_s14wind_buf1e6_seed100`
- `sac_s14wind_buf1e6_seed200`

## Smoke Test

Before full training, use a short run:

```powershell
D:\anadonda3\envs\sailboat\python.exe PART4\seed_reward_ablation\train_saclstm_s14_nowind.py --seed 100 --Max_train_steps 2000 --dvc cpu
```

For the full 4090 run, use the default `--dvc cuda`.

## Evaluation Notes

ReplayBuffer size does not affect evaluation scripts directly. Testing only
needs the correct model prefix and checkpoint index.

Examples:

```powershell
D:\anadonda3\envs\sailboat\python.exe PART4\seed_reward_ablation\test_eval_lstm.py --model_prefix saclstm_s14nowind_buf1e6_seed100 --model_step 9000 --env_name sailboat-s14-nowind

D:\anadonda3\envs\sailboat\python.exe PART4\seed_reward_ablation\test_eval.py --model_prefix sac_s14nowind_buf1e6_seed100 --model_step 9000 --env_name sailboat-s14-nowind

D:\anadonda3\envs\sailboat\python.exe PART4\seed_reward_ablation\test_eval.py --model_prefix sac_s14wind_buf1e6_seed100 --model_step 9000 --env_name sailboat-s14-wind
```
