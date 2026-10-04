# Project Memory

仅保存遗忘会影响决策的经验；实验结果与当前能力统一见STATE及原始收据。

## 固定目标统计不能直接接世界坐标远目标
**Tags:** normalization, waypoint, frame, recurrent-memory
**Conclusion** 已核查14D和18D资产的目标坐标统计均固定于[500,0]且方差为0；直接输入世界系长距离目标会破坏输入语义。在原冻结接口中，刚性局部坐标变更需一致重算进度及因果历史，不能只改终点就宣称等价。R6允许把有限窗口、重置或持续状态作为显式算法变量检验；该历史经验不构成禁止。
**Evidence** docs/migration_identity.json、docs/obstacle_candidate_identity.json、src/sailboat_routing/frames.py、tests/test_frames.py；具体迁移契约见docs/FRAME_PROTOCOL.md。
**Implication** 使用旧资产时验证统计与接口语义；R6可配套改变或训练归一化/记忆协议，不宣称新协议与旧协议等价。

## deterministic动作不等于关闭dropout
**Tags:** obstacle-candidate, dropout, inference, reproducibility
**Conclusion** 0204@10800对应原推理脚本保留训练模式及p=0.1 dropout；eval是不同协议，不能当成无影响的推理清理。
**Evidence** docs/OBSTACLE_PROTOCOL.md、third_party/obstacle_candidate/modeltest_noise.py及batchtest.py；runs/obstacle_parity_legacy/results.json、runs/obstacle_parity_eval/results.json分别核验各自协议。
**Implication** 绑定模式及RNG，能力结果按协议分开解释；切换模式必须独立验证，不能混用统计。

## 单个能力失败不能自动升级为接口失效
**Tags:** admission, capability, continuity, evaluation
**Conclusion** 曾自行增加B的6/6门槛而阻塞全部下游。失败发生在首次换目标前，同条件原入口亦失败且前1000步物理轨迹相同；这不支持把失败归因于连续换目标，也不证明新导航协议已通过。
**Evidence** runs/stage_b/result.json、runs/stage_b_failure_diagnostic/result.json；configs/navigation_contract.json的admission_policy。
**Implication** 接口/信息边界作为硬门，策略能力按全部场景如实报告；保留失败与旧passed，不增设全成功要求，不以新规则跳过真实验收。

## 局部真风不保证闭环收益
**Tags:** planner, oracle, safety, evaluation
**Conclusion** 固定V0的同状态诊断表明：风项在候选排序不变时仍可通过改点收益阈值触发执行差异。该单例真风航段在决策/下发时几何合法，实际跟踪随后侵入缓冲区；几何连线安全不保证冻结低层的实际航迹安全。
**Evidence** docs/ep_result/V0_1_DIAGNOSIS.md及runs/v0_1_diagnosis_20261002/中的同状态评分、补跑一致性与安全时间线；原结果见runs/v0_comparison_20261002/fast_single_obstacle__*.json。
**Implication** 先诊断评分机制与实际跟踪约束，再扩大读出数据或训练；不能把oracle当上界，也不能由此推断所有局部风信息无用。

## 同状态候选过滤通过不代表整回合可完成
**Tags:** tracking-margin, candidate-feasibility, closed-loop, stopping-gate
**Conclusion** 固定裕量从初态启用会提前改变航迹；挡住旧状态的危险候选，不足以推出完整导航成功。有限候选清空时即使尚未侵入安全域，也必须记任务失败。
**Evidence** docs/V0_2_RESULTS.md及runs/v0_2_margin_20261002T142441Z/main_gate.json、same_state_t70.json、main/。
**Implication** 将同状态机制核验和闭环结果分开；不把失败截断时间/航程当效率收益，不因负结果降低预设回归门槛。
## 有限候选耗尽不等于地图或物理无解
**Tags:** candidate-coverage, planning-margin, feasibility, closed-loop
**Conclusion** V0.2 t=165的有限候选全被25m过滤；R1在同一旧状态扩展候选后存在36条至少25m余量的候选航段。原失败至少包含候选覆盖限制；该快照不证明这些候选可被低层安全执行。
**Evidence** docs/R1_RESEARCH_REPORT.md，runs/r1_autoresearch_20261003T021913Z/old_t165_coverage.json；闭环对照独立保存在各round与final。
**Implication** 区分候选集合为空、几何路径不可行与真实闭环不可达。放宽或扩展候选后仍需完整回合验证，不能用几何存在性替代安全成功。

## 目标有效性阈值不是单一切换时机干预
**Tags:** waypoint, validity, hysteresis, ablation
**Conclusion** R2将非终点有效距离门从40m改100m，同时改变urgent、旧目标注入、改点代价和保持/改善门；同坐标路线顶点仍可再次选中。它不保证100m内切换，也不能仅解释为“提前换点”。
**Evidence** src/sailboat_routing/r2_planner.py:35–86；runs/r2_autoresearch_20261003T063153Z/round4_interpretation_note.json、round4_case009_divergence.json；docs/R2_RESEARCH_REPORT.md。
**Implication** 做时机消融前拆清valid变量的全部使用点；同状态评分改善不推出整回合获救。R2具体参数结果只保留于报告。

## 额外规划调用可能推迟普通改点
**Tags:** waypoint, scheduling, hold, intervention, ablation
**Conclusion** R1 在一次完整规划调用结束时更新 last_plan，即使接受门槛保持原目标。R3 的 replan_only 风险请求因此不等于“只提前干预”：一次保持目标的额外调用可重置周期，推迟下一次普通目标应用。
**Evidence** src/sailboat_routing/r1_planner.py:85–89、src/sailboat_routing/r3_planner.py:49–70；runs/r3_ccdc_20261003T121146Z/round1/case_r1_replan60_rescue034.json：364 s 请求后保持，普通应用由 372 s 移至 375 s；分歧前完整原始前缀相等见 development_case_prefixes.json。
**Implication** 分开记录检测、请求、建议变化与实际应用；时机研究必须检查规划时钟副作用。回合获救不能直接归因于更早实际干预。

## 目标保持的归因与覆盖窗口
Tags: waypoint, commitment, timing, paired-evidence
Conclusion: 目标提出、生效、后续普通管理与新增保持规则应分别归因；保持窗口不等于目标实际寿命，完整策略获益也不等于保持有独立收益。
Evidence: docs/R4_RESEARCH_REPORT.md；runs/r4_method_20261004T034532Z/final/behavior_equivalence.json、final/adverse_case001.json及confirmation原始记录。开发局部保持有效，但新实例主方法和无保持全轨迹一致；一个误干预案例中普通基线随后还自行改点6次。
Implication: 研究保持机制必须统计真正被保持规则改变的执行，区分规划调用、提案、下一步应用和后续管理；不能把少量新增干预之外的基线成功归因于新模块。

## 航向监督迁移为位置目标必须重定义执行协议
Tags: literature-adaptation, heading-reference, clipping, timing
Conclusion: 原文的绕行侧承诺不等于世界坐标目标保持。R5的目标更新周期同时阻止退出检查；原切线公式在规划圆内截断为径向垂直方向，多数实际提案落在此分支。不能只按模块名称归因或移植其他控制器的安全性质。
Evidence: docs/R5_METHOD_NOTE.md；runs/r5_literature_20261004T080700Z/literature/R5_WFRS_SOURCE_READOUT.md、final/mechanism_summary.json、frozen_exit_ablation_cases.json；src/sailboat_routing/r5_planner.py。
Implication: 文献接入时先明确参考量、实际生效时序、公式分支和管理器所有状态更新点，再做等接口比较；整体收益不自动识别方向、长度或保持的独立贡献。
