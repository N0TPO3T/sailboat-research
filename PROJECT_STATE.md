# Project State

## 项目与唯一入口
- 目标：已知完整静态海图、无外部天气预报或直接风传感器，以冻结局部SAC-LSTM验证未知风场下可执行的连续航迹点选择。R1已完成合成1/3/5km评估，结论不外推至实船或其他控制器。
- 连接：ssh donghai，ot@172.16.2.249；开发根目录 /home/ot/Students/hs/sailboat-routing-v0（NEW_ROOT），独立Git仓库main。
- 只读上游：/home/ot/Students/hs/sailboat-research（SOURCE_ROOT）；不得覆盖其代码、模型、环境和既有改动。
- Windows同步目录约定：C:/Users/74095/hs/SailBoat/sailboat-routing-v0；其他设备可选自己的本地路径，均通过SSH开发。
- 同步方向：服务器开发/验证/提交 → 本机SSH拉取 → 本机获准后push到托管远端。服务器不承担外网推送或保存托管凭据。
- 本机origin用于从服务器拉取，向服务器push已禁用；V0托管远端尚未配置，地址未确定。源码镜像不等于完整实验备份。
- 研发基点4e86b74；V0运行实现857ff57；V0.2候选裕量实现500618a，参数默认0。源码镜像与大产物分开恢复，旧归档回执见docs/DELIVERY.json；新结果不在该历史归档中。
- 专用解释器 .venv/bin/python，Python 3.13.11；独立依赖见requirements.lock，共享Miniconda仅作为只读解释器来源。安装及命令见README。

## 实现与协议
- 当前连续低层：14D saclstm_s14nowind_buf1e6_seed100@7200，Actor/normalizer冻结；不是官方final@9000或论文最终身份的证明。
- 新集成协议：configs/navigation_contract.json；无额外sensor/actuator噪声，关闭dropout；原A/B用Dryden，新navigation改用私有SyntheticWindField，须单独验证。
- third_party/senior保存原样最小继承快照；runtime.py加载资产，continuous.py维护物理连续，frames.py负责刚性坐标与因果记忆重编码。
- navigation.py已写真实运行链：每控制步一次Actor决策，同前向旁路270维特征，高层t选点在t+1应用。已由真实闭环与旁路非干扰准入验证。
- wind_readout.py/fit_wind_readout.py实现sin/cos岭回归、整episode/scenario划分、train-only标准化、validation选alpha、test一次评估。
- planner.py提供静态地图A*和有限候选；wind_fields.py/metrics.py提供私有时空风场与安全/换舷/配对统计。正式planner输入无环境或风场查询器。
- 三方法geometry_only/oracle_local/estimated_local共享低层与选点参数；oracle只提供当前本船局部真风方向，是诊断参照，不是全局最优上界。
- 18D 0204@10800为独立避障候选；原尺度通过，不具备已验证连续多目标接口，未替换14D。

## 已验证能力与证据
- A/B原协议：迁移及新旧解释器比较误差0，500m为12/12，约1km为5/6；失败前1000步与原500m一致。证据：runs/stage_a、stage_b、stage_b_failure_diagnostic及audit/cross_environment_parity.json。
- 18D独立候选原协议8/8，尚未连续适配，不替换14D；证据runs/obstacle_capability_legacy及docs/OBSTACLE_PROTOCOL.md。
- 新导航准入54项测试通过，完整274步旁路开/关轨迹及动作一致，2次目标切换连续；140步变风标签检查通过。证据runs/v0_admission_final_20261002、runs/navigation_admission.json。
- 20个完整采集episode按12/4/4划分，2个训练超时保留；已冻结读出器并完成一次test评估。离线误差、36次闭环结果及全部失败统一见docs/ep_result/V0_RESULTS.md及其原始证据链接。
- V0交付时上游1351文件与Git状态无变化：runs/audit/upstream_integrity_v0_final_20261002.json。
- V0规定的最小工程/开发诊断已完成；未证实估计风优于几何基线，不等于论文方法已成立。几何路径安全未保证真实闭环安全。

## 限制与恢复
- 模型在checkpoints、运行产物在runs，Git忽略；已提交来源清单见docs/UPSTREAM_MANIFEST.md、migration_identity.json。完整本地资产位置与校验见docs/DELIVERY.json。
- docs/validation_summary.json和旧B passed=false保留历史含义，不代表当前准入；R1未篡改旧结果。
- 代码/协议/权重改变后重新验收；源码身份和特征schema不匹配时拒绝使用既有读出器。
- 历史V0预算见runs/computation.jsonl。R1在12小时/最多8轮授权内完成4轮开发与最终评估，共564回合、至多4个单数值线程CPU工作进程、GPU0。实际资源及原预算见runs/r1_autoresearch_20261003T021913Z/resources.json与plan.json。
- R1已验证连续1/3/5km实验执行，实际能力与失败边界见下方R1结果入口。动态/COLREGs、外部天气预报不在R1范围。
- V0.1诊断为当时未改算法的同状态分析，见docs/ep_result/V0_1_DIAGNOSIS.md。
- V0.2已完成6回合固定0/25m对照：0m逐值复现，25m三方法均未安全到达，预设门槛未通过，18回归未运行。数字、代价与证据统一见docs/V0_2_RESULTS.md；产物runs/v0_2_margin_20261002T142441Z。
- 原navigation_admission.json仍绑定旧planner；通用旧入口对当前代码会拒绝准入。V0.2的run_v0_2.py单独验证冻结特征/模型身份和唯一planner变化，不篡改原收据。一次限定同家族review已完成（provisional）；V0.2按原门槛结束；其停止条件未用于限制后续R1。
## R1 交付与恢复（2026-10-03）
- 完整方法、对照/消融、失败分析及结论统一见docs/R1_RESEARCH_REPORT.md；原始证据runs/r1_autoresearch_20261003T021913Z/。不在状态文件重复维护数值表。
- 冻结实验代码fa6fecdaf849cda12160cadad2d3c7c7206283da；主方案r1_planner.py的geom80，强简化narrow及去留量/风诊断保留可运行配置。低层、归一化、动力学和因果历史协议未改。
- 4轮开发后冻结72新实例、336最终回合；所有回合与清单齐全、配对输入一致，原始轨迹指标复算通过。冻结实现67测试、后续分析3测试通过。
- 支持固定合成评估中的规划适配与留量经验价值；不支持宽候选必要性、80m最优或风/历史额外收益。仍有缓冲侵入、超时及部分长程效率代价，不能视为安全保证。
- 最终result-to-claim限定主张为yes；同家族/provisional，正式完整性审计不可用，自有复算单列。证据见run/review-stage/CLAIMS_FROM_RESULTS.md。
- seed271结果已经读过，后续不能再称未见测试；元数据继承字段的歧义及种子默认标记风险在报告解释，冻结清单不改写。
- 本轮研究完成，无运行中实验；未来建议仅在报告中，不自动启动。服务器已保存源码提交，本地镜像只fetch新源码引用并新增报告/本轮产物，保留原有未提交修改，不自动push。

## R2 当前研究
- R2新授权已启动；目标、边界和恢复入口见CURRENT_PLAN.md及runs/r2_autoresearch_20261003T063153Z/plan.json。12小时/8轮/4 CPU工作进程/GPU0，历史R1已完成状态不代表R2停止。
- 初始实现为独立r2_planner.py，原R1规划器、导航时序和低层源文件/资产未改；入口run_r1.py仅增加规划器工厂选项。能力尚待R2闭环实验。
