# R13 续办：落实资产来源与已确认许可，恢复原三位审稿人的复核

## 任务性质

这是 R13 未完成事项的续办，不是新研究轮次。当前用户已经补充了来源与许可事实。先落实正文、参考文献、补充材料和材料提供说明，再交原三位模拟 CCDC 审稿人复核 A1／B1／C1。

项目目录：`/home/ot/Students/hs/sailboat-routing-v0`。

## 一、用户已确认的事实

用户明确表示：

> “是基于这个论文，也就是师兄的工作的。师兄明确告知同意我使用这些资产，并且能够提供所有源代码权重。”

对应材料为本次上传的 `main(1).pdf`：

Chao Yang, Buyu Guo, Yulu Zhang, Yanzhen Gu, Yanjun Li, Sheng Huang, Hui Huang, Jiang Dong, and Peiliang Li, “Learning to sail without wind information: reinforcement learning-based control for unmanned sailing vessels under partial observability,” Applied Ocean Research, vol. 175, Art. 105246, 2026. DOI: 10.1016/j.apor.2026.105246.

这项确认覆盖此前讨论的继承动力学实现 `sailboat_s14.py`、18D Actor 及其配套 normalizer 的本研究使用和复现材料提供。将当前状态记录为“用户确认已获原提供者同意用于本研究，可提供完整源代码及模型资产供评审复现”。确认依据是用户转述师兄的明确许可，不伪造邮件、签字或已存在的许可证文件。

不要重复要求用户就同一范围再次授权，不要通过增加实验、反复送审或重新训练来替代这项事实更新。没有收到过的正式署名、单位、资助等仍由作者确认，不从相关论文照抄。

## 二、必须准确区分论文来源与实际检查点身份

1. 期刊论文是正式相关工作来源；第19页作者贡献中 Chao Yang 列有 Software 和 Methodology，亦有其他作者参与 Software。可写“由 Chao Yang 提供、来自 Yang 等相关研究代码库”，不要没有依据地写“所有文件均由一人独立编写”。
2. 论文第2.3节、式(27)、PDF第6页明确描述14维无风输入观测。我们当前使用的是已有18输入、带时间注意力的版本。用户确认资产来自同一研究基础，并不意味着这篇期刊论文逐一报告了当前18D检查点的训练和成绩。
3. 因此，引用 Yang 等作为继承研究来源，同时在本文方法和补充材料中按实际代码独立说明18D结构、输入顺序、配套归一化、检查点和文件哈希。称“相关研究代码库提供的18D变体/资产”，不称“对期刊14D基准检查点的逐项复现”。
4. 如当前项目已有学位论文第五章与18D实现的明确对应说明，可以补充引用；没有核实的学位授予年份或正式出版状态不要猜填。缺乏另一篇正式发表的18D论文不阻塞对这份经许可提供的模型资产的如实使用与描述。
5. 期刊第18页列有公开代码与代表性权重的v1.0.3发布说明。可将其作为论文所报告的公开来源，但不据此断言本研究的actor10800和normalizer已经在该release中；只有实际核对过才写精确对应。对当前复现材料使用既有清单即可，不下载并替换实验资产。
6. 动力学理论来源继续保留 Xiao 与 Jouffroy 等实际采用的原始文献；软件实现来源与理论来源分开写。现有第三方版权/许可说明保留。不要把论文的开放获取许可自行转成全部代码或权重的MIT、Apache或其他许可证。

## 三、可用的英文正文（按当前文稿引用号与事实调整）

### Inherited implementation and policy

The sailing dynamics implementation and pretrained controller assets were supplied by Chao Yang from the research codebase associated with Yang et al. [X] and are used with permission. The local controller evaluated here is an inherited 18-input recurrent SAC policy with temporal attention and its matching normalizer. Its architecture, observation mapping, checkpoint identity, and normalization settings are specified in this paper and the supplementary material. This asset should be distinguished from the 14-dimensional wind-input-free policy formulation reported in [X]; no checkpoint-level identity or reproduction of that paper's benchmark results is claimed. No policy weights are trained in the present study.

上述最后一句与本篇实际没有训练一致时保留。正式正文可以压缩，把检查点区别放入补充材料，但不能省略继承来源或造成版本误认。

### Code and model availability

With permission from the provider of the inherited assets, the source code, pretrained policy weights, matching normalizer, and the configurations and records required to reproduce the reported experiments can be provided to the editors and reviewers upon request. The supplementary material identifies the exact experimental versions and reproduction commands.

这段表示能够提供，不表示已经上传公开仓库或已经送交真实会议审稿人。若已在实际评审附件中放入复现包，则根据真实交付方式改成“provided as supplementary material”，并检查附件可读性。不要编造DOI、仓库或链接，不自行push或投稿。

### 可用参考文献

C. Yang, B. Guo, Y. Zhang, Y. Gu, Y. Li, S. Huang, H. Huang, J. Dong, and P. Li, “Learning to sail without wind information: reinforcement learning-based control for unmanned sailing vessels under partial observability,” Applied Ocean Research, vol. 175, Art. no. 105246, 2026, doi: 10.1016/j.apor.2026.105246.

```bibtex
@article{Yang2026WindInputFreeSailing,
  author  = {Yang, Chao and Guo, Buyu and Zhang, Yulu and Gu, Yanzhen and Li, Yanjun and Huang, Sheng and Huang, Hui and Dong, Jiang and Li, Peiliang},
  title   = {Learning to sail without wind information: reinforcement learning-based control for unmanned sailing vessels under partial observability},
  journal = {Applied Ocean Research},
  volume  = {175},
  pages   = {105246},
  year    = {2026},
  doi     = {10.1016/j.apor.2026.105246}
}
```

## 四、实际执行范围

1. 读取当前 R13 稿件与原三位意见，按实际 A1／B1／C1 对应位置修改，不重做全仓审计。
2. 在现有来源表/作者资产清单中更新许可依据、提供者和参考文献；撤销“资产使用许可仍未确认”的过期状态。保留尚未确认的其他作者事项，不扩大范围。
3. 在正文和补充材料中准确落地继承关系、14D文献与18D实际资产区别、可提供方式；移除已过期的来源占位句。不要据此改变科学方法、检查点、归一化器、参数或历史成绩。
4. 复用已有复现包与哈希索引，检查当前稿件对应的动力学、Actor、normalizer、运行配置及必要记录均有确切位置。若只缺某个实际文件，按文件名说明缺件，不重新询问已确认的许可，也不临时替换模型。
5. 重新生成当前模板下的 Word/LaTeX 与 PDF（以项目实际维护格式为准），检查新增引用、编号、页面和材料指向。不无端重画图或补新实验。
6. 给原三位审稿人同一最终版本、实际改动位置、来源引用、材料索引与用户许可确认。继续复核现有 A1／B1／C1；不替换不利审稿人，不要求必须改为接收。
7. 作者回应可以写明：此前缺失的来源与提供范围现已明确，正文和补充材料已据此修改；精确资产身份由清单说明，论文方法来源与具体checkpoint不混同。只有完成实际修改后才能写“已修改”。
8. 若复核提出真正新增的科学矛盾，按原 R13 规则回应；不能把“尚无公开网址/新许可证”重新扩大成默认必须公开发布的要求。仅据现有状态复核，不机械开启新一轮实验矩阵。

## 五、收尾交付

复用现有R13目录和文件，不另建审批平台：
- 更新后的论文与PDF、补充材料和参考文献；
- 一份集中回应A1／B1／C1的作者回复；
- 原三位的真实复核意见和同版本标识；
- `FINAL_REVIEW_STATUS.md`与`HANDOFF.md`；
- 更新后的预览包和复现材料索引。

实验性审查状态与真实会议录用状态分开。三位的最终意见以实际返回为准，不预写“已接收”。本次工作主要是来源与提供说明的事实更新，不新增科研目标。
