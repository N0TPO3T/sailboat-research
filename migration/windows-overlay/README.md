# Sailboat Routing V0

冻结局部SAC-LSTM的连续多航迹点与局部风向旁路研究。服务器、路径、当前能力与证据见[PROJECT_STATE](PROJECT_STATE.md)；下一步见[CURRENT_PLAN](CURRENT_PLAN.md)，Agent首先遵循[AGENTS](AGENTS.md)。本页只维护操作方法。

## 项目结构
- third_party：原样继承的最小运行快照；来源见docs/UPSTREAM_MANIFEST.md。
- src/sailboat_routing：控制器、物理/坐标适配、读出、规划与评估模块。
- configs、scripts、tests：配置、运行入口及模块/接口回归。
- docs：长期接口协议、来源清单和明确标为历史的收据。
- checkpoints、runs、.venv、.cache、.tmp：本机运行资产，Git忽略，需另行备份。

## 环境

现有专用解释器：`/home/ot/Students/hs/sailboat-routing-v0/.venv/bin/python`，Python3.13.11。由共享Miniconda的Python创建独立venv，未复制旧环境、未启用system-site-packages；共享解释器/标准库只读，其余推理依赖独立安装。

如需在**新恢复副本**重建环境，先核对真实目录在hs内，再执行：

```bash
V0=/home/ot/Students/hs/sailboat-routing-v0
export PIP_CONFIG_FILE=/dev/null
export PIP_CACHE_DIR="$V0/.cache/pip" TMPDIR="$V0/.tmp"
export XDG_CACHE_HOME="$V0/.cache" MPLCONFIGDIR="$V0/.cache/matplotlib"
export CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
mkdir -p "$PIP_CACHE_DIR" "$TMPDIR" "$MPLCONFIGDIR"
/home/ot/miniconda3/bin/python -B -m venv "$V0/.venv"
"$V0/.venv/bin/python" -B -m pip install -r "$V0/requirements.lock"
```

仅两个必需推理资产不在Git中：`checkpoints/actor.pth` 与 `normalizer.pth`。其原始位置和SHA256见manifest；恢复时从只读上游复制这两个文件后核对SHA256，不按名称猜测或替换版本。原比较快照位于 `runs/audit/reference/`，来源清单列出每个文件；恢复A比较需要一并按清单复制，不在源目录执行旧脚本。

## 核对与运行
```bash
ssh donghai
V0=/home/ot/Students/hs/sailboat-routing-v0
cd "$V0"
realpath .
git branch --show-current
git rev-parse HEAD
git status --short
export TMPDIR="$V0/.tmp" XDG_CACHE_HOME="$V0/.cache" MPLCONFIGDIR="$V0/.cache/matplotlib"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=''
PYTHONPATH="$V0/src" "$V0/.venv/bin/python" -B -m unittest discover -s "$V0/tests" -v
"$V0/.venv/bin/python" -B "$V0/scripts/fit_wind_readout.py" --help
```
A/B和18D入口分别为scripts/run_stage_a.py、run_stage_b.py、evaluate_obstacle_candidate.py，先读--help，使用未存在的run目录。拟合接口见docs/WIND_READOUT.md；先具备真实验收和数据，不手工伪造准入。当前是否可运行及证据统一见STATE，不因命令存在推定验收通过。

## 跨设备同步与备份
- 每次接入按上述命令核对服务器工作区，先确认无其他Agent主写。真实开发与上下文维护均在服务器。
- 服务器以git diff审查后仅stage本次明确范围，提交代码及必要上下文；不要git add .混入不明改动。
- 本机工作区干净、分支正确时通过SSH从服务器origin执行git pull --ff-only；分叉或未提交修改先核实，不能强行覆盖。
- 本机另设托管远端（如github），地址确定且推送获准后才由本机push；服务器不连接托管平台，不保存其凭据。
- 共享服务器的Git作者身份使用命令级参数（或项目内配置），不修改全局配置；不得把不属于本任务的文件混入提交。
- 本机也可通过SSH克隆服务器已提交历史作为查看镜像；该镜像不含服务器未提交修改、checkpoints或runs，不从本机向服务器push。
- 长任务断线先检查明确归属的进程和退出收据；不要仅因SSH中断重跑实验。
- 新run记录实际源码版本（未提交时附差异及必要源码快照）、配置、资产哈希、命令、日志与退出结果。大产物只向获准目的地备份，保存位置和SHA256并验证恢复。
- 不同步.venv、缓存、凭据；异机恢复按requirements.lock独立建环境，再按来源清单取回模型及必要输出。

## V0 全链路入口

正式结果及适用边界见 [docs/V0_RESULTS.md](docs/V0_RESULTS.md)。以下为本轮实际运行命令（在 NEW_ROOT 执行）：

```bash
.venv/bin/python -B scripts/run_v0.py admit --run-name v0_admission_final_20261002
.venv/bin/python -B scripts/run_v0.py capture --run-name v0_capture_20261002
.venv/bin/python -B scripts/fit_wind_readout.py --episodes runs/v0_capture_20261002/episodes --manifest runs/v0_capture_20261002/splits.json --output runs/v0_fit_20261002 --alphas 0.1 1 10
.venv/bin/python -B scripts/run_v0.py compare --run-name v0_comparison_20261002 --model runs/v0_fit_20261002/model.npz
.venv/bin/python -B scripts/report_v0.py --comparison runs/v0_comparison_20261002 --fit runs/v0_fit_20261002
```

前四条创建独占输出，不能在已有结果上原地重跑。重现实验需在独立恢复副本中，保留旧证据、使用新 run 名称；admit 只在该副本不存在 runs/navigation_admission.json 时生成收据。现有未改变的代码/资产可沿用通过哈希核验的收据。源码或协议改变后须重新验收，不能手改收据。账本累计预算为3600秒，复制旧账本不等于获得额外计算授权。

report_v0 只读取已保存结果并重绘图，不重新评估测试集。3/5km目标序列见 configs/distance_demos.json，仅配置、未运行；使用前需显式选定任务限制与预算。
