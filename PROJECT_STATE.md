# Project State

## 避障研究交接（2026-11-05，本机）
- A停止决策保持；用户要求重新从师兄避障方法找问题。交接：discovery_obstacle_20261105/SENIOR_OBSTACLE_HANDOFF_ZH.md、idea-stage/IDEA_REPORT.md。
- 已读131页《大论文-Final.pdf》第五章；晚探测条件的模型排序反转是论文报告，原日志/checkpoint映射尚未闭合，不称已复现。优先诊断物理可行性、信息可辨识性与策略响应三者。
- 只读复核既有CSV：低阶重编码最大2.195秒、8/16新任务超过1秒；4个反应式失败均NoRouteError，未发生记录内实体碰撞。核查脚本和来源哈希在交接目录。
- 本轮无新增训练/导航；文档仅本机，未同步服务器。另一个并行工作的Yara安装状态保留如下，本轮未操作该任务。

## Yara独立环境（2026-11-06）
- 环境对比资料：../yara-comparison-html/index.html（6部分：平台、Yara论文纯风力实验（主图23，电机辅助图27–28折叠保留，含离线PDF）、18D环境、迁移困难、收益代价、先迁移场景与接口再测试旧权重；旧历史成绩展示页已删除），离线包YARA_COMPARISON.zip；生成器与来源随包保留。18D原日志重绘三场轨迹；Edge实际渲染检查和翻页自检通过；未新增训练或实验。
- 环境/方法详细对照：docs/YARA_ENV_METHOD_COMPARISON_ZH.md。实测Actor参数量：Yara PPO1350、SAC1446、继承14D667396、18D866820。来源噪声RATE=1与当前14D副本RATE=5有差异，不能用“3%”概括或自动归于同一历史训练配置；详表区分checkpoint事实与脚本默认值。
- 迁移接口核验及真实可视化已完成：docs/YARA_TRANSFER_AND_BASELINE_ZH.md；本机交付 ../yara-transfer-audit/YARA_TRANSFER_PREVIEW.zip，服务器 yara-env/transfer_audit。迁移路线尚未实施：保留原物理与接口仅接显示原则上不必重训；更换动力学需先对齐18D接口并做旧权重闭环测试，再决定微调或重训；5D/3动作原版与14D/2动作资产、帆缆/帆角语义不等价。
- 官方PPO/SAC保存SB3 2.0.0，实际使用2.3.2加载有调度对象兼容警告，但策略张量13/32项逐项相同；SAC8步探测通过，PPO固定风可视化24步到达，只是接口/展示材料，不是性能评估。专用noetic-visual镜像支持CPU虚拟显示及真实相机PNG，作业已退出。
- 用户明确授权删除 hs/pi05_runtime、hs/act-dp-playground，并允许现有 Docker 存储写入；两目录已核对真实路径、进程和挂载后删除，约释放55.68 GiB。授权仅针对本次安装，不改变其他学生目录只读边界。
- /home/ot/Students/hs/yara-env 已安装官方固定源码 e708703e7367993f56ff2187a06e05b09d19e696；独立标签 hs-yara:noetic-base，ROS Noetic/Gazebo11、Python3.8、CPU Torch1.13.1、Gymnasium0.29.1/SB3 2.3.2。非原论文训练环境逐项复现。
- catkin 全量编译及复核通过；真实 Eboat53-v0 完成8次步进、仿真时钟4.05→18.06秒，有限观测/奖励/位置。没有训练或使用GPU，不支持模型性能结论。任务容器已退出；安装后根盘剩约57GiB。
- 入口、限制、来源和日志：docs/YARA_INSTALL_STATUS_ZH.md；服务器 yara-env/README_ZH.md、logs/SMOKE_RESULT.json、docker/IMAGE_RECEIPT.json。旧预检为历史；未改共享系统包、旧研究源码/权重/结果。

## 当前 A 线决策（2026-11-05）
- 投稿保持暂停。公平低阶对照及冻结新任务验证已完成，按预设门槛停止当前详细预测安全收益路线；不追加调参、样本或模块。
- 权威结果：runs/a_fair_20261105/RESULTS_ZH.md、RESULTS.json、AUDIT.json、completion.json；所有原稿和旧结果保留，B线不变。
- 本轮72次完整航行指标复算通过，全部进程退出；汇总null格式报错及只读分析修复记录均保留，无导航重跑。


## 当前阶段（B3，2026-10-09）
- 用户已授权扩大应用范围、改变切入点；以具体任务和成熟强对照筛选CCDC题目。B2结束状态不限制本轮。
- 独立工作目录 ../sailboat-track-b/discovery_b3；三个实际pilot完成，无直接进入新论文的入选题。条件性首选R的已知单侧降额换线任务可完成性，保留成熟简单方法，不采用动态余量调速；具体数值与边界见该目录idea-stage/IDEA_REPORT.md。
- 服务器根盘可用空间为0，本轮使用本机既有Anaconda单线程CPU；不清理共享数据、不安装环境、GPU0。A/旧B/B2保持原资产。
- 全部实验已退出、资源释放；独立证据复算完成，同家族provisional。完整代码/原始结果/图集/预览包见discovery_b3/RESULTS_INDEX.md；未启动写作或第四pilot。下述各阶段均为历史快照。

## 当前阶段（B2，2026-10-08）
- B2自主选题筛选完成：3个pilot，未选中值得扩大投入的方向；无活跃实验，GPU使用0。
- F指定指标接近上限；I对强简单路线优化增量不足；U修复失稳后历史更新仍无足够增量，但当前重构偏差仍大，不能称应用已解决。
- 权威报告、全部证据、原始审查与交接：../sailboat-track-b/discovery_b2/idea-stage/IDEA_REPORT.md、RESULTS_INDEX.md、HANDOFF.md。
- A与旧B保持原交付；下述AB和R1–R6为历史快照，不恢复旧阶段限制。

## 当前已核对事实（AB续办，2026-10-07）
- AB工作包已完成：A稿件在paper/ccdc/track_A_submit；B在兄弟目录sailboat-track-b，完成有限恢复研究、三位独立首审与复核、实际包交付。无运行实验。最新事实和证据入口见docs/AB_STATUS.md。
- 服务器实际稿件已到R13，round04原A/B/C均模拟Accept；这是内部意见，非正式录用。主证据19/23/24，联合压力3/7/8，其余16场均成功；范围为理想计算单船会遇仿真。
- 本轮独立A/B授权已执行完成，预算记录docs/ab_20261007/SHARED_BUDGET.json；B实际采用传统控制与当前风观测，无训练。历史阶段禁令不恢复为永久限制。
- A/B目录分离，旧科学资产及未提交代码不修改。Chao Yang继承资产的研究使用和评审材料提供权限已由用户确认。
- 本文件后续R1—R6段落为本机历史快照，最新论文事实见paper/ccdc/r13_revision。已保留本次同步前原文，未reset/clean/pull覆盖。


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
- V0阶段18D仅验证独立原尺度协议；R6连续接入及选择结果见下，不改写旧结果。

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

