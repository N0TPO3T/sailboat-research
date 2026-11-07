# R8 原始证据与复现

科学冻结：`29124b8`；主方法文件为`src/sailboat_routing/r8_model.py`、`r8_planner.py`，runner为`scripts/run_r8.py`。每个批次`provenance.json`保存实际commit和源码SHA256，`source/`保存运行时源码。后续分析与排版提交不改变冻结方法。

运行根：`runs/r8_closedloop_20261005T062543Z/`。

| 子目录／文件 | 身份与用途 |
|---|---|
| `development/` | 中断的实现缺陷批次，不进入效果汇总；错误与修复见`implementation_correction.md` |
| `smoke/`, `smoke_parity.json` | 有界40秒协议检查，不算完整任务失败 |
| `development2/` | 六个已知开发场景的完整闭环比较 |
| `branches/`, `branch_validation.json` | 同一115秒前缀的四个175秒有界分支，非四个独立场景 |
| `predictor_witness.json` | 早期固定参考外推诊断，后续真实参考变化混杂误差；不作为同协议预测精度 |
| `active_sensitivity/` | 已知mixed3的激活转向、共同3秒交付开发检验 |
| `hold_ablation_development/`, `joint_active_turn/` | 60秒协议和共同激活期间195秒转向开发检验 |
| `timing_controls/` | 已知mixed3同目标路径／速度、通过时刻偏移±150秒；开发对照 |
| `fresh_scene_pool.json`, `fresh_geometry.json`, `freeze.json` | 先冻结的30个新实例生成结果及物理几何检查，全部保留 |
| `confirmation/` | 30场×3组，独立于开发源回合；各分层分开统计 |
| `long/` | 3/5km连续任务×中段横穿／追越×3组 |
| `static_regression/` | 六个已见静态场景的两组回归 |
| `all_rows.csv`, `analysis.json`, `strata.json` | 离线摘要，不替代单回合日志 |
| `protocol_prediction_diagnostics.json` | 按实际决策周期比较预测执行段；窗口相关，非独立试验 |
| `figures/` | PNG、SVG、来源数据和可离线打开的HTML图集 |
| `review-stage/` | 同家族辅助审查；不是科学认证 |

每个场景目录包含`job.json`、`row.json`和`trace.json`。trace保存双方同步轨迹、真实历史观测、实际动作、目标交付事件、候选预测及选择、安全余量。原始风诊断仅供离线核验，选择器不读取它。

资产继承R6，R8训练步数0、GPU小时0。所需actor SHA256：`6092d4543c003793f4cd3f21c5ed722f0978eebfdba2f62d77892af333085bd6`；normalizer：`3baf7d1d9d4c9e4505fc991f339221e9e0dc64e9777c6f1c568413a2846b63b6`。完整现有包为`runs/r6_reset_20261004T115808Z/R6_controller_assets.zip`，解包在源码根保留`checkpoints/`相对路径。第三方动力学／策略源码随源码归档保存，来源沿用项目原始资产记录。

## 离线分析与绘图

在现有项目环境中运行：

```bash
.venv/bin/python scripts/analyze_r8.py runs/r8_closedloop_20261005T062543Z
.venv/bin/python scripts/plot_r8.py runs/r8_closedloop_20261005T062543Z
```

## 独立复跑

旧运行目录有截止时间且禁止覆盖。复制指定批次配置到新运行根，再启动；不要修改原始日志或旧plan。以下示例复跑完整新实例比较，仍最多4个CPU进程、每进程单数值线程、GPU隐藏。仅在有相应资源授权时执行，运行时间不属于原始证据。

```bash
.venv/bin/python - <<'PY'
from pathlib import Path
import json,time,datetime
root=Path.cwd().resolve()
old=root/'runs/r8_closedloop_20261005T062543Z'
new=root/'runs'/('r8_reproduction_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
new.mkdir()
plan=json.loads((old/'plan.json').read_text())
plan.update(started_epoch=time.time(),deadline_epoch=time.time()+24*3600)
(new/'plan.json').write_text(json.dumps(plan,indent=2))
batch=json.loads((old/'confirmation.json').read_text());batch['run']=str(new)
(new/'confirmation.json').write_text(json.dumps(batch,indent=2))
print(new/'confirmation.json')
PY
# 使用上行实际输出的路径：
.venv/bin/python scripts/run_r8.py runs/r8_reproduction_<实际时间>/confirmation.json
```

要复跑其他批次，只替换配置名。开发分支包含branch字段；正式评估不包含。`.venv`及`requirements.lock`沿用现有环境，不要求重新安装服务。首次准备新机器须遵守其资源与目录权限，源码和权重一致并不自动意味着跨硬件逐位确定性。
