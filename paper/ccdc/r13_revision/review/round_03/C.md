# Reviewer C — Round 03 final copyedit check

reviewer_role: persistent independent internal simulated CCDC reviewer C; not a conference official  
requested_model: gpt-6-astra  
requested_reasoning_effort: xhigh  
review_independence: same-family  
acceptance_status: provisional (internal simulation, not real conference acceptance)  
reviewed_version: immutable review_round_03_input  
manuscript_sha256: 76f439b1db00e1de17cf79e50f3bff15114cbad25f0a751c916403965244e12b  
pdf_sha256: 2f70eee906366143c518551ad54035f55ccd0c0fffbef235b441b93bd872e1d2  
supplement_sha256: bb22b3664068d80a59f6ea04a0226b650f1fc681b200ae645e5b646956c0c330  
verdict: Major Revision

## Actual final-version check

读取 FINAL_COPYEDIT_RESPONSE.md 和自己的第二轮 C.md，未读取其他评审意见。核验本轮正文、DOCX、PDF、Supplement 的四项哈希，全部符合 VERSION.json。完整逐行比较两轮正文与补充材料；差异仅为 §II-A 的补充材料指针和 S12 的版本显示字符串说明。再次查看最终 PDF 的全部 8 页，未见这次修改导致公式、图表或正文裁切；C3 已完成的数学修复仍然保留。

§II-A 现明确指向 S9 与 S11–S12，读者可以找到内部恢复及来源跟进记录。S12 以 2014-10-02 发布日期定位同一原始软件发行，并报告两种检索页面的版本字符串，而没有将其解释为两套不同模型。第一轮以来的核心来源/访问限制仍保留；这两处修改没有被写成新增授权证据。可选元数据问题无需继续阻塞文字定稿。

本轮不重新运行实验，也不将回放计为新样本。科学判断继承第二轮已经核验的证据：主比较 24 个任务、72 条运行，19/23/24 安全完成；共同安全 +7 s、308 s 绕行和 106 m 预测误差仍公开保留。内部恢复包的 183 个成员哈希与 72 条轨迹已在第二轮实际核对，不因最终文字更新重新否定。

## Current unresolved ledger and Memory update

| ID / 子项 | 状态 | 本轮判断与所需动作 |
| --- | --- | --- |
| C1 — 内部依赖/权重/日志恢复 | Closed | 实际归档和新目录恢复证据已足够支撑当前内部恢复表述，无需再做同一检查。 |
| C1 — 来源归属和允许的访问/提供方式 | Open; necessary evidence | 没有新的人类确认。仍需负责作者/源资产提供者明确 port、Actor、normalizer 的来源、应有引用/致谢/署名及允许提供的对象与方式。 |
| C2 — 场景物理定义 | Closed | 正文与 S10 已充分说明；不重开。 |
| C3 — 数学/坐标排版 | Closed | 最终实际 PDF 保留修复；不重开。 |
| 可选版本字符串和交叉引用 | Closed | 两处文字修改已实际落地，不影响科学结论。 |

唯一控制当前判定的仍是 C1 的人类来源/归属/访问证据。内部可执行恢复不等于已经获得面向审稿人或读者提供资产的确认。公开释放不是唯一可接受形式；明确、获准的受限访问也可评估。未知训练全过程本身不构成要求重训的理由；继续保留既有 Unknown 与非训练 holdout 的限制即可。

没有新增必须自主修复的算法、实验或文字项。更多仿真、重复审稿或再次改写免责声明不能代替上述确认。下一次实质复核应由新的人类证据触发，再核对最终归属与访问表述，而不是要求改变已经接受的理想计算、单目标仿真范围。

研究的有限应用价值和已验证结果仍值得保留，但当前最终文件尚不足以支持发表就绪判定。没有推断其他评审人的投票。

**Final verdict: Major Revision**
