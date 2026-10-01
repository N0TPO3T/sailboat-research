# Reward Ablation Batch Evaluation

- Episodes per experiment: 1000
- Parallel envs: 15
- Model step: 8400
- Max steps: 1000
- Device: cpu
- Sensor noise: True (0.03)
- Actuator noise: True (0.03)
- Elapsed seconds: 2336.3

| Experiment | Success | Success Rate 95% CI | Time mean s | Distance mean m | Sail rate deg/s | Rudder rate deg/s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| no_progress | 12/1000 | 0.0120 [0.0069, 0.0209] | 313.00 | 609.86 | 0.0377 | 0.0305 |
| no_action | 980/1000 | 0.9800 [0.9693, 0.9870] | 190.28 | 592.07 | 1.5864 | 1.5299 |
| no_checkpoint | 997/1000 | 0.9970 [0.9912, 0.9990] | 183.41 | 607.74 | 1.0148 | 0.7817 |
| no_arrival | 996/1000 | 0.9960 [0.9898, 0.9984] | 178.93 | 590.45 | 1.0434 | 0.7580 |
