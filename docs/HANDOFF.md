# 接力入口

项目上下文已合并到根目录四文件，不在本页独立维护状态：

1. [AGENTS.md](../AGENTS.md)：操作边界与跨设备协议。
2. [PROJECT_STATE.md](../PROJECT_STATE.md)：当前事实、证据和恢复材料。
3. [CURRENT_PLAN.md](../CURRENT_PLAN.md)：当前目标与下一步。
4. [PROJECT_MEMORY.md](../PROJECT_MEMORY.md)：按需检索的长期经验。

运行与同步命令见[README](../README.md)。服务器工作区为开发入口，本地镜像需先核对版本及服务器未提交工作。

## V0.1 诊断完成（2026-10-02）

已完成同状态评分与已有日志统计，详见 [V0_1_DIAGNOSIS.md](ep_result/V0_1_DIAGNOSIS.md)。仅一次估计风补日志且完整复现；新产物在 `runs/v0_1_diagnosis_20261002/`。本轮到此停止，未实施下一轮建议。

## V0.2 计划冻结

产物 runs/v0_2_margin_20261002T142441Z/；总预算2小时、实验30分钟、正式24/总启动26、review一次。先核验及6回合，通过门槛才18回归。计时起点和当前版本见plan.json；当前尚未启动实验。

V0.2主实验6回合完成；继续门槛=False，详见runs/v0_2_margin_20261002T142441Z/main_gate.json；本轮进程累计约60.5秒。

V0.2交付完成：57测试、同状态核验、6正式回合、一次同家族review（provisional）；运行进程54.76秒，含核验/分析账本62.27秒，截至review总历时11.40分钟。25m三方法均无候选失败，18回归按门槛跳过；完整报告 [V0_2_RESULTS.md](V0_2_RESULTS.md)。唯一下一步建议是离线检查t=165候选覆盖，不在本轮实施。

R1新授权已启动：r1_autoresearch_20261003T021913Z；恢复见CURRENT_PLAN.md及run/plan.json，历史V0.2停止状态不限制R1。

R1完成4轮开发，冻结版本fa6fecd；67测试通过，72场/336回合新评估即将运行，详见runs/r1_autoresearch_20261003T021913Z/final_protocol.json。不得用测试结果调参；恢复检查final/completion.json及本任务进程。
R1交付完成：4轮开发228回合 + 冻结72场336回合，共564回合；主方法65/72，锚点/去留量39/72，窄候选63/72。详见[R1研究报告](R1_RESEARCH_REPORT.md)，数值与适用边界以报告为准。
冻结代码fa6fecd，67项实现测试和3项分析测试通过；336原始轨迹复算与最终同家族result-to-claim review完成（限定claim=yes，provisional，正式审计不可用）。预算与证据在runs/r1_autoresearch_20261003T021913Z/；所有实验已结束，未push。后续不能复用seed271作为未见测试。
本地保留原有未提交改动；新源码通过fetch进入origin/main，新增报告及完整R1产物单独同步。CURRENT_PLAN已关闭本轮，下一轮建议尚未实施。

R2新授权启动：r2_autoresearch_20261003T063153Z；12小时/8轮/4 CPU/GPU0，目标与开发/冻结划分见docs/R2_PLAN.md。R1旧72场本轮仅作开发，历史结果不覆盖。

R2交付完成（2026-10-03）：四轮开发后冻结forward500，完成72新实例×4方法；研究结论、真实航迹、消融及失败证据见[R2研究报告](R2_RESEARCH_REPORT.md)。主要长程提效假设未获支持，不替换R1默认方案。
全部939新回合结束；冻结科学源码3003228，288回合原始指标复算通过，最终result-to-claim=no（same-family/provisional，正式审计不可用）。原始产物runs/r2_autoresearch_20261003T063153Z/；figures/index.html与R2_results_preview.zip供本地查看。
seed271/371/1271均已见；不再自动调参、补跑或push。源码通过fetch、冻结快照及Git bundle恢复，本地旧工作树与原未提交修改保留。下一轮建议仅在报告中，尚未实施。

## R3 交付完成（2026-10-04）

结论、完整收益/代价与失败边界见 [R3研究报告](R3_RESEARCH_REPORT.md)；英文完整内容稿 [paper/ccdc/draft.md](../paper/ccdc/draft.md)。冻结主方法 Relay160，合理 Relay120 与原 R1 仍保留，不能宣称稳定提效或安全保证。
证据 `runs/r3_ccdc_20261003T121146Z/`；配置 `configs/r3_methods.json`，冻结评估提交 `037fe1a`；720 回合原始复算与一次最终 same-family/provisional 审查完成。研究停止，seed2271/3271 也已见。
本地 `R3_CCDC_preview.zip` 与 run/figures/index.html 包含真实图、作图数据、索引和源码快照；全量控制日志仍在服务器。保留旧本地修改，只 fetch，不 push。作者须处理资产署名/发表许可和官方模板/PDF，尚未投稿。

## R4 完成（2026-10-04）
- 先读 R4_METHOD_NOTE.md，再读 R4_RESEARCH_REPORT.md。方法候选为因果运动触发的径向退让+条件保持，默认仍推荐 Relay160；新实例未证实新增安全或保持收益，正反例均保留。
- 科学冻结 3c5e44f3bd4186b4f5a3ec012b1a8d9fd728d617；configs/r4_methods.json；全部证据 runs/r4_method_20261004T034532Z/，其中 raw_index.csv 索引626回合，final/raw_index.csv 索引冻结360回合。
- 五张关键真实图、两张补充图和离线图集见 run/figures/；R4_METHOD_preview.zip 为含选中作图原始日志的轻量包。完整物理复跑依赖服务器现有资产；新运行另用输出目录及预算。
- 一次有限审查完成，same-family/provisional；报告记录负结果与冻结前方案变更。4271/5271现为已见种子，无运行中实验；R3英文稿未改，不自动push或追加实验。

## R5 完成（2026-10-04）
- 先读 [R5中文方法说明](R5_METHOD_NOTE.md)，再读 [R5研究报告](R5_RESEARCH_REPORT.md)。保留文献恢复方向的位置接口候选tangent_exit90；风险工况有条件性收益，默认参考仍Relay160，不能忽略Relay120的优势与新方法代价。
- 科学冻结822817495ac9ddae06a2743a021b8aa0d160f2d7；configs/r5_methods.json；run为runs/r5_literature_20261004T080700Z。796新回合已结束，432冻结回合复算完成，有限审查为same-family/provisional，无追加实验。
- 五张关键图＋开发补充图、逐点数据、可运行配置/源码及原始索引在R5_METHOD_preview.zip与run/preview/gallery.html；包外同步校验见R5_DELIVERY.json。本机无需模型即可重绘，完整物理复跑仍依赖原服务器资产及新预算。
- 6271/7371和risk6101均已见；R3初稿与旧结果保留。本地旧修改保留，只fetch、不push；本轮关闭，未来建议未启动。

## R6 新研究授权
旧冻结低层、只改高层、排除18D及固定记忆/时序的阶段条件已撤销。当前有效范围、预算及恢复入口仅见 CURRENT_PLAN.md 和 runs/r6_reset_20261004T115808Z/plan.json；历史结论不改写。启动时GPU分配待确认；本轮最终未使用GPU，完成状态见下。

## R6 完成（2026-10-04）
- 首读 [R6中文方法](R6_METHOD_NOTE.md) 与 [R6研究报告](R6_RESEARCH_REPORT.md)。采用已有18D控制器＋安全边界输入＋Relay120；本轮更换控制器资产，未训练新权重。旧冻结规则不再生效，不能把未训练解释为禁止或无效。
- 科学冻结f572dac20e3e8a13bda57ebac0c6bf2343d384f2；configs/r6_methods.json；runs/r6_reset_20261004T115808Z/保存开发、匹配消融、冻结新实例与有限审阅。资源/完整分母/失败边界见报告，不宣称普遍安全或实时部署。
- 五张真实图与index.html；R6_RESEARCH_preview.zip为轻量包，source bundle、继承权重和完整原始日志另存run下，复现见run/REPRODUCE.md，传输校验以R6_DELIVERY.json为准。本机旧修改保留，无push。
- seed8371/9471现已见。研究完成、无运行中实验；R3稿不变，仅paper/ccdc/R6_POSITIONING.md另存定位更新，未来训练/扩展建议未自动执行。

## R7 启动（2026-10-05）
动态低速目标、控制器/输入/记忆/时序及必要训练均可研究；旧静态或18D限定不再适用。唯一当前范围见CURRENT_PLAN.md，运行入口runs/r7_dynamic_20261005T033700Z/plan.json；R6为对照，保护旧资产。

## R7 completed — 2026-10-05
- 科学实现b29e459：当前位置动态接入+终点占用时间窗接力；无新训练。
- 方法/主张边界见R7_METHOD_NOTE.md、R7_RESEARCH_REPORT.md；全部证据runs/r7_dynamic_20261005T033700Z/RAW_INDEX.json。
- 新实例收益是两个临时终点无路恢复，保留740秒误干预反例；建议仅作有限扩展，非完整避碰/规则/实时保证。
- 原始source/config/旧失败保留，离线图集与R7_DYNAMIC_preview.zip交付；没有自动push。当前实验已结束。

## R8启动
R8: executable underway dynamic avoidance with candidate-conditioned prediction and rolling feedback. R6/R7 are baselines, not frozen constraints. High/low-level, causal memory, interface and training may change; no future truth online, no unassigned GPU, no automatic push.
当前入口CURRENT_PLAN.md；runs/r8_closedloop_20261005T062543Z/plan.json。R7 confirmation85真实侵入、最终终点恢复与740秒代价分别验证，全部R7数据现为开发材料。
