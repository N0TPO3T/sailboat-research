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
