# Sailboat Routing V0

实际开发与实验仅在 `ssh donghai` 的 `/home/ot/Students/hs/sailboat-routing-v0`。同级 `sailboat-research` 是只读上游，不能修改或清理。此项目独立 Git 仓库，不自动 push；模型、环境、缓存与运行输出不提交。

当前状态及接力入口：[`docs/HANDOFF.md`](docs/HANDOFF.md)。完整来源与必要适配：[`docs/UPSTREAM_MANIFEST.md`](docs/UPSTREAM_MANIFEST.md)。机器可读验收摘要：[`docs/validation_summary.json`](docs/validation_summary.json)。

## 已实现与实际结果

- **A：通过预定运行验收。** 迁移4个原样代码文件，冻结第四章14维 SAC-LSTM `seed100@7200` Actor/Normalizer。32步固定输入和双噪声模式各25步闭环迁移误差0；原解释器环境与独立环境25步闭环误差0。四风况各3seed的500m开发任务12/12到达。不是论文最终模型身份或总体成功率证明。
- **B：代码/接口通过，性能门禁未过。** 连续世界动力学、局部刚性坐标、固定归一化、完整因果记忆重编码；六个约1km开发场景5/6成功。五次换目标物理/time/wind/RNG不变。正逆风seed11原500m也失败，不是在中间换目标后才失败；原失败保留，不降低预定6/6门槛。
- **C：独立代码及单测完成，真实数据/拟合未执行。** sin/cos岭回归、整episode/scenario划分、train-only标准化、时间对齐、世界系因果圆周平滑及有效性；正式拟合CLI会拒绝当前失败的B门禁。
- **D：独立代码及API冒烟完成，三方法闭环未执行。** 静态地图A*、几何简化、有限局部候选、局部风软代价、保持时间/收益阈值，以及仅当前局部方向的诊断oracle。几何安全不代表实际船轨迹安全；无风场重建、外部天气、动态避障或高层RL。
- 35项独立模块/真实权重接口测试通过。合成读出fixture和三模式API演示**不是实际风向误差或三方法性能**，fixture模型不可部署。
- 用户提供的0204@10800是另外的18维注意力避障候选，结构核验通过且存在同名推理脚本；未替换当前14维控制器，未进行其避障闭环。见 `docs/obstacle_candidate_identity.json`。

## 目录

```text
third_party/senior/     4个原样继承运行文件；Git按字节保留
src/sailboat_routing/   冻结推理、连续物理、局部坐标/记忆、读出、规划、oracle
configs/               预先固定的A/B场景与选点参数
scripts/               有界验收、失败诊断、拟合门禁与资产/完整性检查
tests/                 数学、信息边界、真实控制器与动力学接口回归
docs/                  HANDOFF、来源清单、协议与小型证据摘要
checkpoints/           仅运行所需actor/normalizer；Git忽略
runs/                  原始JSON/JSONL、航迹图、诊断与候选快照；Git忽略
.venv/ .cache/ .tmp/    独立环境、缓存和临时文件；Git忽略
```

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

## 实际可用命令

以下命令可从NEW_ROOT之外启动，全部在服务器执行。新运行名不可复用已有输出目录，避免覆盖历史证据。

```bash
V0=/home/ot/Students/hs/sailboat-routing-v0
export TMPDIR="$V0/.tmp" XDG_CACHE_HOME="$V0/.cache" MPLCONFIGDIR="$V0/.cache/matplotlib"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=''
"$V0/.venv/bin/python" -B "$V0/scripts/run_stage_a.py" parity --run-name a_recheck
"$V0/.venv/bin/python" -B "$V0/scripts/run_stage_a.py" pilot --run-name a_recheck
"$V0/.venv/bin/python" -B "$V0/scripts/run_stage_a.py" capability --run-name a_recheck
PYTHONPATH="$V0/src" "$V0/.venv/bin/python" -B -m unittest discover -s "$V0/tests" -v
"$V0/.venv/bin/python" -B "$V0/scripts/run_stage_b.py" --run-name b_recheck
"$V0/.venv/bin/python" -B "$V0/scripts/verify_upstream.py"
```

B运行器读取保存的A验收门，不重新训练策略。当前正式读出拟合会因B门禁失败退出，不能伪造passed字段解锁；数据格式和拟合命令见 `docs/WIND_READOUT.md`，规划API见 `docs/PLANNER.md`。C数据采集与D真实场景执行器尚未开展；不把独立模块当作端到端V0已通过。

## 计算与证据

单CPU进程、单数值线程，初次累计实验预算3600秒；`runs/computation.jsonl`记录已执行实验。未启动低层/高层RL、长时间调参或无人看管训练。

关键真实输出：
- `runs/stage_a/capability/trajectories.png`：原尺度12条航迹。
- `runs/stage_b/trajectories.png`：六条连续任务航迹，包含失败。
- `runs/stage_b_failure_diagnostic/result.json`：同条件原500m失败与物理轨迹一致性。
- `runs/audit/cross_environment_parity.json`：原/新解释器环境25步真实闭环一致性。
- `runs/audit/full_unittest.log`：35项测试记录。
- `runs/independent_module_smoke/result.json`：明确标记为合成数学/API验证，不可作为性能指标。
- `runs/asset_0204_review/inspection.json`：新附件身份、严格加载和适用边界。
- `runs/audit/upstream_integrity.json`：源文件完整性与原Git工作树状态核对。

下一项最小研究动作：对18维最终避障候选的实际V3环境、历史注意力、dropout/噪声协议做独立绑定验证；或保留14维基线继续诊断正逆风失败。更换控制器必须重新过迁移/原尺度/连续性关卡，不能把换模型冒充修复已有失败。
