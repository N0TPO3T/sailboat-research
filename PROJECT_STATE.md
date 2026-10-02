# Project State

## 项目与唯一入口
- 目标：已知完整静态海图、无外部天气预报，以冻结局部SAC-LSTM完成连续多航迹点，再验证当前局部风向旁路对高层选点的价值。纯仿真、小规模V0，不保证优于基线。
- 连接：ssh donghai，ot@172.16.2.249；开发根目录 /home/ot/Students/hs/sailboat-routing-v0（NEW_ROOT），独立Git仓库main。
- 只读上游：/home/ot/Students/hs/sailboat-research（SOURCE_ROOT）；不得覆盖其代码、模型、环境和既有改动。
- Windows同步目录约定：C:/Users/74095/hs/SailBoat/sailboat-routing-v0；其他设备可选自己的本地路径，均通过SSH开发。
- 服务器尚无Git远端；未建立获准推送的托管地址。当前跨设备主要通过SSH接入，不能宣称已完成异机备份。
- 研发基点为4e86b74；其后导航、准入、风场、指标、18D候选及读出变更仍在服务器未提交工作区。文档提交不代表这些代码已入Git，克隆不能恢复未提交代码。
- 专用解释器 .venv/bin/python，Python 3.13.11；独立依赖见requirements.lock，共享Miniconda仅作为只读解释器来源。安装及命令见README。

## 实现与协议
- 当前连续低层：14D saclstm_s14nowind_buf1e6_seed100@7200，Actor/normalizer冻结；不是官方final@9000或论文最终身份的证明。
- 新集成协议：configs/navigation_contract.json；无额外sensor/actuator噪声，关闭dropout；原A/B用Dryden，新navigation改用私有SyntheticWindField，须单独验证。
- third_party/senior保存原样最小继承快照；runtime.py加载资产，continuous.py维护物理连续，frames.py负责刚性坐标与因果记忆重编码。
- navigation.py已写真实运行链：每控制步一次Actor决策，同前向旁路270维特征，高层t选点在t+1应用。实现存在不等于端到端通过。
- wind_readout.py/fit_wind_readout.py实现sin/cos岭回归、整episode/scenario划分、train-only标准化、validation选alpha、test一次评估。
- planner.py提供静态地图A*和有限候选；wind_fields.py/metrics.py提供私有时空风场与安全/换舷/配对统计。正式planner输入无环境或风场查询器。
- 三方法geometry_only/oracle_local/estimated_local共享低层与选点参数；oracle只提供当前本船局部真风方向，是诊断参照，不是全局最优上界。
- 18D 0204@10800为独立避障候选；原尺度通过，不具备已验证连续多目标接口，未替换14D。

## 已验证能力（2026-10-02核对）
| 项目 | 结果 | 相对 NEW_ROOT 的证据 |
|---|---|---|
| 14D迁移 | 32步固定输入、两组25步闭环误差0 | `runs/stage_a/parity/result.json` |
| 新旧解释器 | 25步动作/状态/记忆误差0 | `runs/audit/cross_environment_parity.json` |
| 原尺度500m | 四风况各3seed，12/12到达 | `runs/stage_a/capability/result.json` |
| 连续约1km | 5/6到达，5次切换物理/time/wind/RNG不变 | `runs/stage_b/result.json` |
| 已知失败 | 正逆风seed11原500m也超时，前1000步物理轨迹与B相同 | `runs/stage_b_failure_diagnostic/result.json` |
| 18D迁移 | legacy_training和eval各16固定输入/32闭环，动作/h/c/attention/state误差0 | `runs/obstacle_parity_legacy/results.json`、`runs/obstacle_parity_eval/results.json` |
| 18D原尺度 | legacy_training+原双噪声，四风况×无障碍/单障碍，8/8到达 | `runs/obstacle_capability_legacy/results.json` |
| 当前工作树回归 | 本次51项全部通过；不是C/D端到端验收 | `runs/audit/codex_takeover_unittest_20261002.json`及同名log |
| 上游完整性 | 既有检查1351文件无变化，Git状态一致；本次未重算全部上游 | `runs/audit/upstream_integrity.json` |

18D四个障碍场景最小安全余量约5.59/5.36/99.84/10.06m，采用原40m阈值和控制步采样线段近似，不能宣称连续曲线或船体安全保证。8场均seed0，不代表统计泛化。
旧B的6/6成功门是实现时额外设置，非用户要求；旧 `passed=false` 和全部失败结果保留，不改历史。今后的硬门检查资产匹配、接口连续性、因果记忆和可用航行，成功率另行报告。

## 当前限制与恢复材料
- 当前51项测试覆盖模块/接口，不覆盖新navigation全链路验收。原始测试日志与收据留在runs。
- admission.py已实现证据哈希验证；runs/navigation_admission.json缺失。生产拟合前还缺真实episode、可部署读出模型及专用批量采集/三方法对比入口。
- configs/development_suite.json预定义20个采集episode（train/validation/test=12/4/4）及12个配对场景；尚无真实MAE/P90或三方法闭环性能。
- docs/validation_summary.json是4e86b74阶段历史收据，保留原数值与旧阻塞原因，不代表当前准入条件。
- 来源与哈希见docs/UPSTREAM_MANIFEST.md、docs/migration_identity.json、docs/OBSTACLE_PROTOCOL.md；模型在checkpoints，运行输出在runs，均被Git忽略。
- V0完整模型/输出的异机备份尚未核实；恢复必须保留这些资产及清单，不能只克隆源码。
- 单CPU进程/单数值线程，首轮累计实验预算3600秒；运行前读取runs/computation.jsonl重新计算，账本不含安装/编辑等全部耗时。
- 不启动低层重训、高层RL、长搜索、后台无人看管任务；动态/COLREGs、外部天气、完整风场重建及3/5km扩展不在当前执行范围。
- 论文贡献是待验证的因果读出与连续选点作用；继承控制器、注意力及静态避障不能算新增贡献。下一步只在CURRENT_PLAN维护。
