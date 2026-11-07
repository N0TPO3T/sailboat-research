# Reviewer C — Round 02

reviewer_role: persistent independent internal simulated CCDC reviewer C; not a conference official  
requested_model: gpt-6-astra  
requested_reasoning_effort: xhigh  
review_independence: same-family  
acceptance_status: provisional (internal simulation, not real conference acceptance)  
reviewed_version: immutable review_round_02_input  
manuscript_sha256: 9551e27615c08ca672968fb0ce17e503ac1b227830307a83c3763bacdcc48305  
pdf_sha256: 8bc6a5172d495db5e7987f4d9bfb61f41fc3cba01f5e856f34d6521584e0a5f8  
verdict: Major Revision

## Review coverage and current judgment

重新阅读全文和 Supplement S1–S12，并查看实际 PDF 的全部 8 页。读取自己的第一轮意见和 AUTHOR_RESPONSE_C.md；未读取 A/B 的意见或答复。审阅了 SOURCE_FOLLOWUP.md、新恢复记录、归档内的验证脚本和依赖、三个新增数值回放记录。只读核查服务器上的原始本地论文封面及实际恢复目录。没有运行模型实验、重做导航或修改科学产物。

本轮有实质修复。**C2 和 C3 关闭；C1 的可执行内部恢复子项关闭，来源归属与对外访问确认子项仍未关闭。** 当前仍判 Major Revision，原因已缩小到继承资产的责任人证据，而不是重复要求已完成的代码打包、场景说明或公式修复。没有发现新的致命有效性错误，也没有理由因三项额外数值回放而增加独立试验样本数。

论文的问题、方法和作用范围没有改变：它在理想计算、相同继承动力学、无附加传感噪声、单个低速匀速目标的仿真中，对冻结递归帆船策略的参考/保持/恢复协议进行预测与筛选。主结果仍是 R/L/S15 在 24 个任务上分别安全完成 19/23/24；S15 相对 L 多完成一个任务，但共同安全任务平均多用 7 s，保留 308 s 绕行和显著计算成本。这个有限应用结论值得保留，不支持普遍优势或实时安全。

## Checks performed on the actual revision

1. **版本与主结果未改写。** 正文、PDF、Supplement 的哈希与本轮 VERSION 相符。逐字节比较两轮的 episodes.csv、confirmation.json、freeze.json、r12_model.py、run_r12.py，均未变化。第一轮独立核对的主表统计继续有效。
2. **内部归档不是空的承诺。** 实际文件 R13_REPRODUCTION_internal.zip 为 12,383,109 字节，SHA256 为 `d0fdc80b40b5252ced7dfd15370a30e092b3232cc1b7ef65e131bedac50ce640`。在不解压写入的条件下检查了 CONTENTS_SHA256.json 的全部 183 个成员，零缺失、零哈希不符。包含 run_r8.py、r8_model.py、r8_planner.py、Actor、normalizer、requirements.lock 和 72 条 confirmation trace。
3. **恢复证据的含义清楚。** verify_recovery.py 校验包内文件、建立并关闭 CausalModel、导入 worker，再从保存 trace 的 row 重建安全完成数、CPU 总计及共同安全时间差。recovery_check.json/log 报告了实际新目录中的成功执行；通过 SSH 确认该目录存在且含 72 条轨迹。这证明现有环境中的资产加载/依赖恢复和日志汇总，不是新环境安装验证，也不是独立重新运行 72 个航程。正文与 S11 已采用这一有限表述，我没有把恢复记录扩大解释。
4. **来源跟进确实增加了证据。** 只读提取本地大论文封面，确认有署名、浙江大学及 2026 年 12 月提交日期。当前为 2026 年 10 月，不能据此认定已经发表或授予学位；本轮 S12 正确保留该限制。它也不能把 10800 权重哈希绑定到特定训练运行。
5. **数值回放保持研究样本身份。** 新 JSON 的三个 endpoint_max_error 都为 0；原任务 R/L/S15 的 substep 余量是 −0.162187/−1.117383/42.094165 m。它们是既有同一任务三种运行的数值核查，没有成为新的任务或独立统计样本。第一轮已核实 L 在 402 s 真实端点入缓冲区；此处是进一步的局部数值支持。

## Persistent issue ledger

### C1 — Partially resolved; attribution/access evidence remains open

**Classification:** necessary evidence. **Current locations:** p.1 §II-A；p.7 §VI 与 Acknowledgment；Supplement S9/S11/S12；SOURCE_FOLLOWUP.md。

**Closed portion.** 第一轮缺少可直接获得的运行依赖和权重交付，已经由真实内部归档、完整哈希检查、实际新目录恢复记录解决。不能继续把“只给了哈希、没有源文件/权重”用作本轮拒绝理由。结论也由笼统的 reproducible interface 改为 specified interface 与 internally recovery-checked artifact，符合已提供证据。

**Still unresolved.** 继承 Python port 和 Actor/normalizer 的负责提供者/创作者尚未确认正式归属及允许的提供方式。原始训练到当前权重的映射也仍未知。用户档案、PART5 入口、命名论文草稿和字节身份能说明当地资产来源线索，不能替代源作者确认。原始 MathWorks 分发的许可同样不能独自证明这份继承 Python 修改和学习权重的权限与归属。

我重新访问了 [Jouffroy 的软件页面](https://www.mathworks.com/matlabcentral/fileexchange/47981-sailingyachtmodel-zip) 和它的[原始许可文本](https://www.mathworks.com/matlabcentral/mlc-downloads/downloads/e5af5a09-4a80-11e4-9553-005056977bd0/7d340fc0-01b1-1f26-4a9f-f5153adf520a/licenses/license.txt)。页面标明 Jerome Jouffroy、2014-10-02 发布；许可对该原始分发规定了保留声明等条件。当前材料没有证明本地 port/权重全部属于同一许可覆盖对象。本评审不据此推断侵权，也不把公开所有权重当作未核实的会议强制规定。

**Impact on the verdict.** 该系统是论文实证对象的核心，不是无关背景。内部可以加载、汇总，与研究归属已经确认、可向哪些审稿人/读者提供，是不同事实。现在已充分修复前一事实，但后一事实仍明确缺证，因此当前版本仍不宜被判为可以发表。这不是以作者尚未完成实船或大规模泛化实验为由抬高要求。

**Minimum remaining remedy — requires human evidence.** 负责的人类作者/源资产提供者需明确这份代码修改、策略及 normalizer 的来源，确定应引用/致谢或署名的对象，并明确可以提供给哪些人、采用什么访问方式。公开分发不是唯一方案；合法且明确的受限提供方式也可以评估。对于确实无法追溯的训练细节，应如实保留 Unknown；不要求虚构训练日志、强行对应 [8] 或重新训练。现稿已声明不是已验证的训练 holdout，此限制可以保留。

**Autonomous work remaining.** 核心恢复和可读表述已经足够，进一步运行仿真不能关闭 C1。收到上述确认后，作者可据证据更新 attribution/access 条目及正文。本轮不要求在没有新证据时反复检索或继续重写免责声明。仅有一个不影响判定的小元数据核对：本次 MathWorks 页面显示版本 **1.0.0**，SOURCE_FOLLOWUP/S12 写 **1.0.0.0**，可统一为所引用页面显示值并记录检索日期。

### C2 — Closed

**Classification:** prose-layout / necessary scope specification. **Locations:** pp.3–4 §IV-A；Supplement S10。

24 个任务均为 1 km、目标速度范围、pressure 的基础风向、静态圆障碍以及五类场景的生成包络均已给出。S10 与冻结生成脚本一致，且明确 pressure 同时改变若干因素，不能从其收益中隔离单因素因果效应。正文还区分了“新生成的监督器测试场景”与“已经证明不在继承策略训练集”的不同含义。

第一轮所需信息现在无需读 Python 或 JSON 才能理解。本项不要求新增采样、额外场景、实船或扰动测试，也不再作为任何负面判定依据。

### C3 — Closed

**Classification:** prose-layout. **Locations:** p.3 Eq.(3)/(4)/(5)；p.5 Fig.2；完整 8 页 PDF。

实际 PDF 中 Eq.(3) 的两个 min 及其下标域、预测帽号已正确分层，Eq.(4) 的两个指示函数条件可辨。共同协议/障碍/时间域的 M、M̂ 与 whole-task m_real 也有明确区分。Fig.2 图注已经说明 symmetric-log，并写明 |margin|≤3 m 为线性区域。图表及公式未见裁切。

第 8 页仍有大量空白，但这不是数学错误，也不是本轮新增发表门槛。我重新请求官方投稿页仍超时，故不以转述的页限作独立违规判断。局部字体或断行还可美化，但不影响本项关闭。这里只确认实际 Word 导出的 PDF；没有把未成功编译的另附 LaTeX 源码称作已验证成品。

## Retention reasons and accepted scope

最强的保留理由仍然成立：参考不仅是一个坐标，而是带有持有与反馈恢复规则的执行协议；真实历史与候选历史隔离；t=260 s 的同状态比较解释了一次可验证的决策分歧；简单预测器表现接近且其优势未被隐藏；106 m 预测误差、308 s 绕行、同快照重复协议和窗口聚类均被保留。

本轮未引入新的夸大结论。继续接受理想计算、单目标、匀速目标和相同继承动力学的声明范围。新网络、定理、完整 COLREGs、多船、目标机动和实船测试仍属于 optional future。不要用这些额外工作替代 C1 所需的直接证据，也不要因剩余事项主要需人类确认，就将它降格为已解决的作者信息排版。

## Memory update

- **C1 executable recovery: closed.** 真实 zip，183 个成员全部校验通过，72 条主轨迹，依赖/权重齐备，已有新目录恢复记录。不得下轮重新声称“没有实际交付”。
- **C1 attribution/access: open and verdict-controlling.** 当前需要源资产负责者/人类作者确认，不存在能靠更多研究实验替代的自主修复。训练全过程不可追溯本身不是要求重训的理由；保留当前未知边界。
- **C2: closed.** 正文和 S10 完成具体场景定义与组合工况限制。
- **C3: closed.** 实际 PDF 数学层级与坐标图注修复已核实。第 8 页空白不升级为新问题。
- **Numerical evidence retained.** L 的失败首先由 t=402 s 真实端点证明；三次 substep 回放进一步支持数值标签，不能增加独立样本数。
- **Scientific comparison unchanged.** frozen manifest、episodes、R12 模型及 runner 两轮哈希相同；19/23/24、共同安全 +7 s、+308 s 反例及 106 m 误差继续保留。
- **Next review trigger.** 新的人类来源/归属/访问证据，而非又一次同内容措辞修改。只检查该证据与最终引用/访问表述是否一致；没有新回归证据时，不重新打开已关闭项。

**Final verdict: Major Revision**
