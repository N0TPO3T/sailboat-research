# Reviewer C — Round 04 focused final review

reviewer_role: persistent independent internal simulated CCDC reviewer C; not a conference official  
requested_model: gpt-6-astra  
requested_reasoning_effort: xhigh  
review_independence: same-family  
acceptance_status: provisional (internal simulation, not real conference acceptance)  
reviewed_version: immutable review_round_04_input  
manuscript_sha256: 5d104c82ab58c402ff09bbac34015a8c59052cd63f55bb87a58dc4828dc5cb0c  
pdf_sha256: 859c8226cb0abe5e9048fdc11fd3eb4953448534e3b8519f06a81728e7caff43  
supplement_sha256: fd974d3ddec2adb58a257e3376215cf952e902f4e1b271c84bd2de0a351ae08c  
verdict: Accept

## Current decision

**C1 已关闭；本轮判定 Accept。** 这个判断适用于稿件声明的理想计算、单目标帆船仿真范围，表示当前研究内容与证据支持发表，不是真实会议录用或已经完成投稿的声明。

改变判断的原因是此前明确缺失的事实已经补齐：用户确认 Chao Yang 提供并同意本研究使用继承动力学、18D Actor 和配套 normalizer，同时能够向编辑与审稿人提供完整源码、权重及复现材料。正文和补充材料已按该确认落实归属与提供方式。它不是单纯把“未确认”改成肯定语气，而是有新的明确确认作为依据，且与此前已经核验的实际恢复包对应。

该依据是用户转述提供者的明确同意，不是我独立取得的签署文件。对本次已确认的研究使用及评审提供范围，我不另设必须公开全部权重、取得新许可证或重复提交书面同意的门槛。

## Checks performed

- 阅读完整当前 manuscript.md、Supplement S1–S12、USER_CONFIRMATION.md、SOURCE_FOLLOWUP.md、AUTHOR_RESPONSE.md 及两份实际 diff；逐页查看当前 PDF 的全部 8 页。没有读取 A/B 的意见。
- 正文、DOCX、PDF、Supplement 四项哈希全部符合 VERSION.json。实际正文从参考映射段至结论的科学内容与 Round03 完全一致；此次变化集中在来源、可提供方式和新增参考文献 [9]。
- 读取项目实际 main.pdf 的第 1、6、18、19 页。文件为 19 页，SHA256 为 `9bc5165d59141e64c32cea5f4fbc2f4464c6fe0f88b40334de85703b92d356b9`。第 1 页的作者、题名、期刊、卷号、文章号和 DOI 与新增 [9] 一致；第 6 页 §2.3、式（27）明确为 14 维无直接风输入观测；第 18 页给出该文 v1.0.3 公开发布声明；第 19 页包含 Chao Yang 的 Software/Methodology 贡献，也列有其他 Software 贡献者。
- 这次只核对上述论文内容，没有把论文所列 GitHub release 当作当前 18D 权重已经公开的证明。现稿 §II-A 和 S12 明确区分相关研究来源、14D 发表方法及实际 18D attention 资产，没有移用期刊 benchmark 成绩，也没有声称所有文件由一人独立编写。
- 读取 canonical `paper/ccdc/r13_revision/evidence/asset_resume_check.json`。它记录 183 个索引成员、72 条主轨迹以及动力学、Actor、normalizer、freeze、calibration 的精确身份。最初查找 review_round_04_input/evidence 未找到该文件，随后在所指 R13 根目录 evidence 中找到并读取；未把评审快照中的缺少副本误判为资产丢失。
- 实际内部归档 SHA256 仍为 `d0fdc80b40b5252ced7dfd15370a30e092b3232cc1b7ef65e131bedac50ce640`，与第二轮我逐项验证 183 个成员时完全相同。本轮无需重跑已有恢复或导航实验；没有下载替换资产、训练、重算航程或修改科学产物。
- 最终 PDF 的 [9]、来源区别和 Code and Model Availability 均已实际出现，图表和已修复数学层级未见裁切或回归。

## Whole-paper scope judgment

稿件的贡献是具体控制接口与有边界的应用评估：位置参考连同保持、反馈恢复、待执行动作和因果记忆重建，构成需要预测的完整协议；它不是宣称新发明了控制诱导预测或一般安全保证。GVO、reference governors、BC-MPC 和反馈运动预测等先例已被承认。继承 SAC、注意力和动力学不再被混同为本文新方法。

主要收益虽小，但证据与表述相符：R/L/S15 为 19/23/24 安全完成；S15 对 L 多完成一个任务，而共同安全任务平均多用 7 s，并保留 308 s 绕行和显著计算成本。同输入决策差异、固定协议对照和数值核查给出了总成功率之外的解释；106 m 大误差、聚类窗口、重复快照协议、历史任务重叠以及计算暂停假设没有被隐藏。

在既定 CCDC 应用研究范围内，这足以形成可保留的有限贡献。我没有发现需要以新网络、新定理、大规模新增实验、实船或完整 COLREGs 系统为条件才能修复的当前科学错误。简单预测器仍是有竞争力的替代方案；稿件没有声称已证明普遍优势。

## Persistent issue ledger

| Issue | Status | Evidence and boundary |
| --- | --- | --- |
| C1：可执行内部恢复 | Closed | 已有实际完整归档、183 个成员校验、72 条轨迹、新目录模型加载/worker 导入/日志汇总记录；本轮归档字节身份不变。 |
| C1：来源归属和研究/评审提供方式 | Closed | 新的明确用户确认，§II-A 的 Chao Yang / Yang et al. [9] 归属，Code and Model Availability，S9/S11/S12 的提供范围。无需再次索取同范围授权。 |
| C2：场景物理定义 | Closed | §IV-A 与 S10 保留五类具体包络及 pressure 组合工况限制。 |
| C3：数学与坐标排版 | Closed | 公式层级、共同定义域、Fig.2 对称对数刻度说明和全部最终页面保持可读。 |

**无未关闭的实质科学审稿项。** 精确 18D 检查点与原训练运行的关系仍未知，且不能证明其属于期刊公开 release；现稿已准确披露。对一个使用冻结资产、无重训且不声称复现 14D benchmark 的研究，这些未知不再构成 C1 的发表阻碍。真实海上表现、目标机动、多船和实时交付仍是 accepted scope / optional future。

有一个不影响接受判断的支持文档交叉引用小问题：SOURCE_FOLLOWUP.md 写“Supplement S1”提供实际 mapping/structure，而 S1 是数学解释。可在最终整理时改为正文 §II-A 与相应实现/资产索引。正文、S9 和实际资产足以确定对象，不需要就此再开实验或审稿轮次。

本稿作者顺序、单位、通讯信息及资助仍需负责作者在真实提交时填写。不得复制 [9] 的作者/资助信息，也不得把本轮 Accept 解释成这些投稿元数据已完成；这属于提交准备事项，不重开已解决的科学来源问题。

## Memory update

- **Supersede Round01–03 的 C1 未确认状态。** 新确认明确覆盖继承动力学、18D Actor/normalizer 的本研究使用与编辑/审稿人复现材料提供；保留其用户转述证据性质，不虚构签章或许可证。
- **C1/C2/C3 全部关闭。** 不再要求公开 release、新许可证、再次授权或重复运行原实验作为接受条件。
- **版本界限必须保留。** Yang et al. [9] 的 14D 方法是正式研究来源；当前 18D 变体有独立资产身份，不是已证明相同的期刊检查点。
- **恢复与结果证据继续有效。** 同一归档、183 个文件、72 条主运行；19/23/24、+7 s、+308 s 和 106 m 反例不能在最终稿中被扩大或删去。
- **本轮 Accept 是独立内部模拟意见。** 不代表真实 CCDC 录用；未推断其他评审人的意见。只有后续发生新的科学修改、证据矛盾或资产身份变化时才需要重新打开对应问题。

**Final verdict: Accept**
