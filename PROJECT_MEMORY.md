# Project Memory

仅保存遗忘会影响决策的经验；实验结果与当前能力统一见STATE及原始收据。

## 固定目标统计不能直接接世界坐标远目标
**Tags:** normalization, waypoint, frame, recurrent-memory
**Conclusion** 已核查14D和18D资产的目标坐标统计均固定于[500,0]且方差为0；直接输入世界系长距离目标会破坏输入语义。刚性局部坐标变更还需一致重算进度及因果历史，不能只改终点或清空记忆。
**Evidence** docs/migration_identity.json、docs/obstacle_candidate_identity.json、src/sailboat_routing/frames.py、tests/test_frames.py；具体迁移契约见docs/FRAME_PROTOCOL.md。
**Implication** 冻结统计并验证目标/记忆适配；换新资产时重新检查，不把该结论泛化到所有模型。

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
