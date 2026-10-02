# Sailboat Routing V0 — 当前交接

## 隔离与版本
- SOURCE_ROOT: `/home/ot/Students/hs/sailboat-research`，只读；HEAD `b079399bfeb659c228156f767962374f95f56614`，既有未提交修改不提交、不重置、不覆盖。
- NEW_ROOT: `/home/ot/Students/hs/sailboat-routing-v0`，独立 Git main；代码版本以此仓库HEAD为准，未 push。
- 按用户 `SailBoatRL_V0_Agent_Prompt.md` 执行 A→B→C→D。低层始终冻结，全部新增代码/环境/缓存/结果位于NEW_ROOT。

## A：隔离迁移与预定原尺度能力通过
- 4个未改动运行源文件 + 匹配的14维 `saclstm_s14nowind_buf1e6_seed100@7200` Actor/normalizer。来源/哈希见 `docs/UPSTREAM_MANIFEST.md` 和 `docs/migration_identity.json`。
- 精确资产入口为 `research/smoke_baseline.py`；保留无额外传感器/执行器噪声、原生Dryden风。不是官方默认 `final@9000`，原训练环境和论文最终身份未证实，不声称论文复现。
- 独立 `.venv` 不使用system-site-packages，`requirements.lock` 已保存；`runs/audit/environment.json` 记录新旧环境及通过的pip check。
- `runs/stage_a/parity/result.json`：32步固定输入，及无额外噪声/原噪声各25步真实闭环，动作/物理动作/状态/奖励/h/c最大误差0；同前向特征旁路开关动作误差0。另在 `runs/stage_a_repeat/parity/` 验证新命名空间复跑通过。
- `runs/audit/cross_environment_parity.json`：原上游只读解释器环境与新CPU环境运行同一隔离快照，25步的动作、物理动作、状态、奖励、h/c和时间误差均为0；上游环境未安装/卸载/升级。
- 原尺度四风况各3个seed：12/12到达（`runs/stage_a/capability/result.json`、`episodes.jsonl`、`trajectories.png`）；首回合实测约4.21秒。只说明这12个固定场景，不外推总体可靠性。
- 目标坐标normalizer方差均为0，均值[500,0]；连续任务用刚性局部坐标维持此契约，不在线更新统计。

## B：实现与接口验收完成，性能门禁 BLOCKED
- `frames.py`：只平移/旋转位置与航向，不缩放长度、不重复旋转船体系速度；新目标下统一计算相邻物理状态的进度。
- `continuous.py`：仅在新适配层AST移除原750m/1000s任务限制、显式返回原integration_failed；ODE/风/执行器代码不改；全任务/分段限制另列配置。
- 目标切换不reset物理状态、仿真时间、风或随机流；循环记忆按全部已发生观测和真实历史命令在新frame下因果重编码，不假装在线10步滑窗。
- 13项接口/真实权重记忆测试通过：`runs/audit/stage_b_unittest.log`、`.json`。
- `runs/stage_b/result.json`：六个预先固定约1km场景5/6到达，5次切换的物理/time/wind/RNG完全不变。同向0/90/150度、整体45度旋转、15度转折通过；正逆风seed11第一段超时。预定6/6门槛未通过，不降低阈值、不替换失败场景。
- 区分性原入口对照：`runs/stage_b_failure_diagnostic/result.json`。原500m、同seed11/180度也在1000步超时，距目标696.689m；与B前1000步物理raw轨迹最大差0。帧进度重算有至多6.75e-5m舍入差，动作最早第1步差3.28e-7，但此对照未改变物理轨迹。故该失败已在原低层出现，不是中间换目标/重编码后才发生；尚未认定训练层根因。

## C：独立实现通过，真实数据/拟合 BLOCKED
- `wind_readout.py` 已实现sin/cos岭回归、train-only标准化、episode/scenario整组划分、时间对齐/拒绝未来观测、世界系因果圆周平滑、退化/历史不足有效性及MAE/P90/事件窗口指标。
- `fit_wind_readout.py` 实际检查B门禁、冻结资产SHA256和270维feature schema，小规模validation选择alpha，test只评一次；CPU线程/累计预算受限。当前真实调用按预期返回exit=2，拒绝拟合，不生成伪指标。

## D：独立实现通过，三方法真实闭环 BLOCKED
- `planner.py` 已实现完整静态圆障碍地图A*与简化、名义500m候选、风向软代价、转向/改点代价、保持与收益阈值；无有效估计时使用相同几何策略，不读取真值补位。
- `oracle_local.py` 仅暴露当前物理环境本船位置/当前时刻的风向角记录，不提供风速、任意点/时刻查询；正式planner只接收白名单可见输入，不接收env/info/seed。
- 35项回归全部通过：`runs/audit/full_unittest.log`、`.json`。`runs/independent_module_smoke/result.json` 实际运行合成岭回归保存/加载、世界/局部角转换、三模式选点API、真实物理对象当前风oracle和正式信息隔离；在相同可见输入下修改未暴露真风，正式planner输出不变。这里不是三方法闭环性能。
- 合成fixture模型明确命名 `SYNTHETIC_NOT_DEPLOYABLE_model.npz` 并使用哨兵资产身份，不可部署为真实读出。
- 真实连续数据采集、读出拟合/误差评估和三方法闭环对比均暂停。没有真实读出MAE/P90或geometry/oracle/estimated性能结果，不以合成测试冒充。
- 不重训低层、不启用高层RL、不跑3/5km演示。

## 用户新提供的最终避障权重
- 附件 `saclstm_s14obst_noise_0204_actor10800.zip` 与已有库归档SHA256完全一致：`f3d8f7c0c715fc6e2c312f8ba7656c9f8e0b726a598279bb071e03c8d561c73f`，含完整Actor/Critic/Normalizer三件套。
- 用户本次确认为最终避障版本；当前运行核验是18维观测、2动作、历史注意力SAC-LSTM，三件套有限，Actor/Critic严格加载通过，合成sequence和streaming前向通过。
- 找到同名前缀/同编号真实脚本旁证：上游 `PART5/SAC-LSTM-att/modeltest_noise.py` 与 `batchtest.py` 都指定0204@10800、`sailboat-s14-obst-v3`、双噪声0.03。默认history_window=10来自源码，不是权重元数据；实际Gym绑定、障碍观测语义、dropout/RNG和历史缓存仍需逐项绑定。未直接执行原脚本（会写原/固定输出路径或启动并行评估）。
- 核验证据：`runs/asset_0204_review/inspection.json`、`docs/obstacle_candidate_identity.json`。其角色是有价值的18D避障候选；没有自动替换14D V0、重用不匹配的normalizer或填零凑维度，没有避障闭环性能结论。

## 运行与预算
```bash
V0=/home/ot/Students/hs/sailboat-routing-v0
$V0/.venv/bin/python -B $V0/scripts/run_stage_a.py parity --run-name new_a_run
$V0/.venv/bin/python -B $V0/scripts/run_stage_a.py pilot --run-name new_a_run
$V0/.venv/bin/python -B $V0/scripts/run_stage_a.py capability --run-name new_a_run
PYTHONPATH=$V0/src $V0/.venv/bin/python -B -m unittest discover -s $V0/tests -v
$V0/.venv/bin/python -B $V0/scripts/run_stage_b.py --run-name new_b_run
```
这些入口已从NEW_ROOT外实际启动。运行目录独占创建，不覆盖旧结果；预算记在 `runs/computation.jsonl`，单CPU/单数值线程，初次累计实验预算3600秒。门禁失败时不运行下游性能实验。

## 上游完整性与当前边界
- `runs/audit/upstream_integrity.json` 核对1351个文件：无修改/新增/删除，上游Git工作树状态与迁移前相同。完整内容哈希排除`.git`、`.venv`、`__pycache__`树；没有声称完整哈希旧环境。
- 新环境、模型、日志、图、fixture均被新仓库Git忽略；没有大文件提交或自动push。机器可读结果见 `docs/validation_summary.json`。

## 下一项最小实验
优先对用户确认的18D最终避障候选绑定真实V3环境、障碍槽、在线注意力历史、dropout/RNG及原双噪声动作链，然后在独立候选目录进行小规模原尺度行为验证。当前只做过结构前向，不能直接替换14D模型或把换模型当作修复已有B失败的证据。若仍保留14D低层，则先诊断seed11正逆风锁定行为；不得通过放宽门槛、删失败场景或自动低层重训解锁C/D。
