# R4 方法预览包

从 docs/R4_METHOD_NOTE.md 开始；完整证据范围见 docs/R4_RESEARCH_REPORT.md。
离线图集：runs/r4_method_20261004T034532Z/figures/index.html，双击即可，无外网依赖。

包内包含冻结方法源码、配置、批次清单、全部回合结果表/索引、复算收据、
图源和作图数据，以及图中选中案例的原始日志。它不是所有控制日志的备份。
全部原始日志仍在服务器 /home/ot/Students/hs/sailboat-routing-v0/，由结果索引定位。
没有打包权重、环境或凭据。源码与当前服务器运行匹配，不要用本地旧工作树覆盖。

离线重画关键图（在解压目录运行，已有 Python/numpy/matplotlib 即可）：
```
python scripts/plot_r4.py runs/r4_method_20261004T034532Z --figure branches
python scripts/plot_r4.py runs/r4_method_20261004T034532Z --figure commitment
python scripts/plot_r4.py runs/r4_method_20261004T034532Z --figure statistics
python scripts/plot_r4.py runs/r4_method_20261004T034532Z --figure paths
python scripts/plot_r4.py runs/r4_method_20261004T034532Z --figure effects
```
完整物理复跑使用服务器原项目，还需要匹配权重、环境、third_party运行文件和原准入记录，
以及新的预算、输出目录；本包不是自包含运行环境或训练包。
全量原始复算命令需要服务器完整日志。审核是同模型家族的有限检查，不是独立认证。
manifest.json 记录本包每个内容文件的字节数及 SHA256（manifest 自身除外）。
