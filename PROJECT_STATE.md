# Project State

## 项目与唯一入口
- 当前目标与有效授权：R7低速移动船舶避碰及连续任务；唯一活跃范围/预算见CURRENT_PLAN.md。历史静态/冻结控制器等条款不限制R7；旧结果不改写。
- 连接：ssh donghai，ot@172.16.2.249；开发根目录 /home/ot/Students/hs/sailboat-routing-v0（NEW_ROOT），独立Git仓库main。
- 只读上游：/home/ot/Students/hs/sailboat-research（SOURCE_ROOT）；不得覆盖其代码、模型、环境和既有改动。
- Windows同步目录约定：C:/Users/74095/hs/SailBoat/sailboat-routing-v0；其他设备可选自己的本地路径，均通过SSH开发。
- 同步方向：服务器开发/验证/提交 → 本机SSH拉取 → 本机获准后push到托管远端。服务器不承担外网推送或保存托管凭据。
- 本机origin用于从服务器拉取，向服务器push已禁用；V0托管远端尚未配置，地址未确定。源码镜像不等于完整实验备份。
- 研发基点4e86b74；V0运行实现857ff57；V0.2候选裕量实现500618a，参数默认0。源码镜像与大产物分开恢复，旧归档回执见docs/DELIVERY.json；新结果不在该历史归档中。
- 专用解释器 .venv/bin/python，Python 3.13.11；独立依赖见requirements.lock，共享Miniconda仅作为只读解释器来源。安装及命令见README。

## 实现与协议
- V0—R5参考连续低层：14D saclstm_s14nowind_buf1e6_seed100@7200，Actor/normalizer冻结；不是官方final@9000或论文最终身份的证明。
- 新集成协议：configs/navigation_contract.json；无额外sensor/actuator噪声，关闭dropout；原A/B用Dryden，新navigation改用私有SyntheticWindField，须单独验证。
- third_party/senior保存原样最小继承快照；runtime.py加载资产，continuous.py维护物理连续，frames.py负责刚性坐标与因果记忆重编码。
- navigation.py已写真实运行链：每控制步一次Actor决策，同前向旁路270维特征，高层t选点在t+1应用。已由真实闭环与旁路非干扰准入验证。
- wind_readout.py/fit_wind_readout.py实现sin/cos岭回归、整episode/scenario划分、train-only标准化、validation选alpha、test一次评估。
- planner.py提供静态地图A*和有限候选；wind_fields.py/metrics.py提供私有时空风场与安全/换舷/配对统计。正式planner输入无环境或风场查询器。
- 三方法geometry_only/oracle_local/estimated_local共享低层与选点参数；oracle只提供当前本船局部真风方向，是诊断参照，不是全局最优上界。
- V0阶段18D 0204@10800仅验证独立原尺度协议；R6连续接入与选择结果见本文件R6入口，不改写旧协议结果。

## 已验证能力与证据
- A/B原协议：迁移及新旧解释器比较误差0，500m为12/12，约1km为5/6；失败前1000步与原500m一致。证据：runs/stage_a、stage_b、stage_b_failure_diagnostic及audit/cross_environment_parity.json。
- V0阶段18D独立候选原协议8/8，当时尚未连续适配；证据runs/obstacle_capability_legacy及docs/OBSTACLE_PROTOCOL.md。
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

## R2 交付与恢复（2026-10-03）
- 方法、冻结新评估、双向退化与图表统一见docs/R2_RESEARCH_REPORT.md；运行runs/r2_autoresearch_20261003T063153Z/。主要长程提效假设未获支持，不将Forward替换为默认方法。
- 科学源码冻结3003228f6cabbf3f1b1dcaa875329fbc2d9338af；配置configs/r2_methods.json。4轮开发后一次新评估，288回合完整性复算通过；原低层、导航时序、真实安全定义未变，GPU使用0小时。
- 本轮全939个新回合均已结束，资源见run/resources.json；原始日志保留服务器，轻量预览含所有作图样本、配置、索引与源码快照，不是全量原始控制日志备份。
- seed271、371、1271均已见；未来不可再用1271作未见测试。候选压缩/较少改点不等于更快或更安全，具体适用边界以报告为准。
- 本地镜像仍保留旧工作树和原未提交修改。新源码通过fetch引用及run/source、源码归档交付；不要在旧本地入口直接运行R2清单。服务器仍为可运行开发入口。不自动push。

## R3 CCDC 收敛轮（2026-10-04）
- 最终方法、强简单对照、留量消融、负结果与英文稿入口见 docs/R3_RESEARCH_REPORT.md 和 paper/ccdc/draft.md；本轮收敛为经验路线留量与简单接力的应用研究，不主张新的风险安全滤波器或普遍长程提效。
- 冻结主方法 relay_m160；配置 configs/r3_methods.json；科学评估提交 037fe1a，完整证据 runs/r3_ccdc_20261003T121146Z/。原 R1 与 Relay120 均保留，不能声称 160 m 最优或稳定优于合理简单基线。
- 三轮开发后冻结，两批新 seed2271/3271 共 144 场、五组 720 回合完整执行；全部原始指标与信息/配对/时序复算通过。冻结实现 86 测试通过，低层、动力学、真实安全判据与因果历史不变。
- 本轮全部 1334 新回合结束，GPU/训练为 0；原预算与实际资源见 run/plan.json、resources.json。研究已完成；一次最终 ARIS 审查为 same-family/provisional，建议作者修改，不是录用或独立认证。
- seed271/371/1271/2271/3271 现均已见。完整控制日志按 raw_index.csv 保留服务器；轻量包提供作图数据、冻结清单、结果与源码，不冒充全量备份。
- 英文稿为完整内容稿，正式资产署名/发表许可、官方模板、PDF 页数及最终作者检查未完成；不宣称可以直接投稿。
- 本地交付为 R3_CCDC_preview.zip、离线图集与内容稿；源码提交通过 fetch 和 source_snapshot 恢复，旧本地工作树及既有未提交修改保留。无运行中实验，不自动 push。

## R4 方法机制轮（2026-10-04）
- 首要解释入口 docs/R4_METHOD_NOTE.md；实验与完整边界见 docs/R4_RESEARCH_REPORT.md；证据 runs/r4_method_20261004T034532Z/。已形成径向退让与条件保持的可运行候选 commit_away，仍推荐 Relay160 为默认方案。
- 科学冻结 3c5e44f3bd4186b4f5a3ec012b1a8d9fd728d617；配置 configs/r4_methods.json。新增机制只用因果位置历史和静态地图，低层、动力学、真实安全判据与目标 t→t+1 时序未变。
- 5轮、626新回合全部结束；含完整状态核对的22闭环分支与72新实例×5方法。最终原始复算、配对、时序和冻结源码检查通过；GPU0。资源与原预算见 run/resources.json、plan.json。
- 局部开发证据支持给退让指令执行机会；新实例未证实相对 Relay160 的新增安全收益，72场保持消融全轨迹相同，仅4场相对 Relay160 改变轨迹且利弊并存。数值与分母只在正式报告维护，不升级为安全保证或普遍提效。
- 一次有限 ARIS 主张—证据审查完成，yes仅针对收窄结论，same-family/provisional；正式独立完整性审计不可用。原始评语及边界见 run/review-stage/CLAIMS_FROM_RESULTS.md。
- seed4271/5271 已见，不能复用为未见测试。原 final_protocol 的旧方法段保留，冻结前方案变更说明见 run/protocol_reconciliation.md；没有根据新实例重调参数。
- R3英文稿和旧结果保留；轻量预览含作图样本与源码，不含全量控制日志、权重或环境。本地旧工作树和未提交修改保留，使用预览内冻结源码或服务器入口；不自动 push。

## R5 文献接入与应用验证（2026-10-04）
- 首要入口 docs/R5_METHOD_NOTE.md，完整对照/退化/原始索引见 docs/R5_RESEARCH_REPORT.md；运行 runs/r5_literature_20261004T080700Z/。采用Jambak等2026恢复方向与侧承诺的部分位置接口适配，不是完整WF-RS复现或安全理论。
- 科学冻结822817495ac9ddae06a2743a021b8aa0d160f2d7；配置configs/r5_methods.json，主研究候选tangent_exit90；默认参考仍Relay160，Relay120与固定位置强对照保留。低层、真实安全判据、无直接风输入及t→t+1时序未变。
- 六轮、796新回合全部结束，432冻结回合原始复算/配对/时序/源码核对通过；4单线程CPU进程上限、GPU0。资源及原12小时预算见run/resources.json、plan.json；无运行中实验，不自动扩展。
- 证据支持本批预定义风险工况中的条件性应用价值；常规没有相对160新增安全完成，相对120仍有安全损失和效率代价。多数恢复提案使用圆内截断的径向垂直方向；不能称真实切线或各组件普遍有效。数值分母由正式报告维护。
- 一次有限ARIS审查已完成，yes只针对收窄描述性结论；same-family/provisional，独立完整性审计不可用。原始评语和统计单位修正见run/review-stage/，不代表投稿充分性认证。
- seed6271/7371及开发risk6101现已见。五张关键真实图、一张开发补充图、逐点数据、离线gallery.html、冻结源码归档和索引在R5_METHOD_preview.zip；传输与校验以docs/R5_DELIVERY.json包外收据为准，不是全量日志/资产备份。
- R3初稿不变，仅paper/ccdc/R5_METHOD_UPDATE.md提供更新建议。本地旧工作树/修改保留，只fetch及新增产物，不push。下一轮机制隔离建议未实施。

## R6 完成（2026-10-04）
- 首读 docs/R6_METHOD_NOTE.md 和 docs/R6_RESEARCH_REPORT.md。当前推荐研究主线为继承18D循环注意力资产＋边界距离输入适配＋Relay120，替换原14D资产但不训练新权重；旧冻结约束不再是研究前提。
- 科学冻结 f572dac20e3e8a13bda57ebac0c6bf2343d384f2；configs/r6_methods.json；全部开发/确认/原始证据 runs/r6_reset_20261004T115808Z/。新确认及匹配输入消融支持当前合成协议中的条件性收益，具体分母、代价和开发侵入只在报告维护。不支持架构单因素、普遍安全或实时部署。
- 实验和有限same-family/provisional审阅结束，原始指标/冻结/输入行为复算通过。未训练、未使用GPU，无运行中实验。资源见run/resources.json，完整预算与停止状态见run/plan.json。
- seed8371/9471现已见。R3稿与原模型保留，论文定位另存paper/ccdc/R6_POSITIONING.md。源码bundle、继承权重、完整日志分别交付，轻量图集不冒充完整备份；同步核验以docs/R6_DELIVERY.json为准。本机旧工作树与修改保留，不push。
