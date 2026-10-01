# Seed Ablation Evaluation Suite

This folder contains the batch evaluation entrypoint, model config, and all
evaluation outputs for the seed ablation tests.

## Files

- `batch_eval_seed_ablation.py`: CSV-only batch evaluator for SAC-LSTM, SAC-nowind, and SAC-wind checkpoints.
- `seed_eval_models.csv`: checkpoint config table. Add more rows here when seed300/seed400 checkpoints are available.
- `seed_eval_results/`: smoke-test and formal evaluation outputs.

The evaluator uses the parent folder for shared code and checkpoints:

- `../model/`
- `../utils_lstm.py`, `../utils_fc.py`
- `../noise_utils_nowind.py`, `../noise_utils_wind.py`
- `../globals.py`

## Commands

Dry run:

```powershell
D:\anadonda3\envs\sailboat\python.exe -B PART4\seed_reward_ablation\seed_eval_suite\batch_eval_seed_ablation.py --dry_run
```

Formal evaluation:

```powershell
D:\anadonda3\envs\sailboat\python.exe -B PART4\seed_reward_ablation\seed_eval_suite\batch_eval_seed_ablation.py --num_workers 8
```
