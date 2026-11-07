# Reviewer C — Round 01

reviewer_role: independent internal simulated CCDC reviewer C; not a conference official  
requested_model: gpt-6-astra  
requested_reasoning_effort: xhigh  
review_independence: same-family  
acceptance_status: provisional (internal simulation, not real conference acceptance)  
reviewed_version: immutable review_round_01_input; manuscript SHA256 f300ac8d2c6a781832ec810b72be2ecb21e8ed3066cd2b2644c68a3e8b15435d  
verdict: Major Revision

## Review coverage and independence

已阅读全文、Supplement S1–S9，并逐页查看 rendered/page-1.png 至 page-8.png。复核了 VERSION 中正文、PDF、补充材料的 SHA256。读取了场景生成与校准脚本、run_r12.py、主要 JSON/CSV 证据和继承资产哈希。未读取其他审稿人意见或既往审稿结论；未运行实验、修改科学源码或原始产物。

独立从 episodes.csv 按 confirmation 分组得到 R/L/S15 安全完成 19/23/24，总 CPU 分别为 270.677/378.445/2133.232 s，与 Table I 一致。通过只读 SSH 检查了唯一 L 失败的原始 trace.json 在 402 s 的状态和目标真值。查阅 GVO、BC-MPC、feedback motion prediction 的一手文本。未独立复现所有物理轨迹，也未从零重建继承策略的训练过程。本评审的执行模型身份不可由稿件证据验证；上方记录的是 requested_model，不将其冒充另一个模型家族的独立审查。

## Overall assessment

论文研究一个具体且合理的接口问题：位置参考的几何可行性不能直接代表固定递归帆船控制器实际执行该参考时的动态避障结果。方法将参考坐标、保持时间、反馈恢复、已计算动作和记忆重编码一起定义为候选协议，在独立控制器/动力学实例中预测，再按 nominal-first guard 和有限候选排序选择参考。

假设包括同一继承动力学、无附加观测噪声、完整静态地图、单个低速匀速目标、运动反演得到的局部恒定预测风，以及规划时物理时钟暂停。这是明确限定的仿真研究。它没有证明一般安全、实时能力、海上部署性能或广泛泛化。按该范围评价，不要求新增神经网络、定理、实船实验或完整 COLREGs 系统。

现有结果支持一个有限但具有应用研究价值的结论：更详细地模拟既有闭环，在部分困难参考决策上提供了有用预测，但可能付出显著航行与计算成本。它尚未证明详细预测总体优于简单预测。作者已正确保留这一边界。我的 Major Revision 主要由继承系统的可归属性和可交付复现链条尚未闭合决定，而不是由缺少大型实验或高等级算法创新决定。没有发现足以直接推翻 Table I 的致命数值错误。

## Strongest reasons to retain the paper

1. **机制和真实执行接口匹配。** 当前动作先执行、参考次步交付、保持/释放计时、管理器状态和实际历史重编码均有明确规定。候选不是互换的几何点；相同坐标的 nominal 与 continuation 可能对应不同协议。这比仅报告一个避障网络或总成功率更有实质内容。
2. **简单基线有竞争力且没有被隐藏。** 同一监督器下 L 完成 23/24，S15 为 24/24；共同安全任务平均多用 7 s，并有 +308 s 个例。L 的校准范围和被同时省略的机制已披露，不能把差异解释成单独某一阶动力学的消融。
3. **决策对照有直接证据。** t=260 s 的 S15/L 真实历史和命令相同，nominal 的预测余量分别为 11.893/59.832 m；有限候选表能够复核不同选择。稿件没有把整个后续航程收益全部归因于第一次参考改变。
4. **独立核查排除了一个重要疑点。** L 在 402 s 的实际位置为 (698.517517, −245.296814) m，目标为 (674.125176, −165.036905) m。原始记录距离 83.884678 m，余量 −1.115322 m，最小点 fraction=1。因此这次 incursion 已发生在真实采样端点，不是单纯的一秒线段内部插值误报。不能因 substep_safety.json 只检查历史任务，就把这一失败标签当作未证实。
5. **负结果与依赖关系处理良好。** 106.064 m 预测误差、历史新任务无额外成功、守卫导致的时间成本、fallback 非保证、1083 个窗口的聚类、两个协议共享一个快照、58 s 共同区间均已明确。没有用这些诊断样本膨胀独立任务数。

## Material issues, in priority order

### C1 — 继承系统的归属和可执行复现交付仍未闭合

**Classification:** necessary evidence. **Location:** p.1 §II-A；p.7 §VI 和 Acknowledgment；Supplement S5/S9；EVIDENCE_INDEX.md。

**Evidence.** 正文明确承认原始发表/训练记录、正式归属及再分发许可尚未核实。ASSET_HASHES.json 给出 Actor/normalizer 身份，INHERITED_SOURCE_CHECK.json 给出源文件一致性，但哈希不能回答来源归属。当前评审包的 run_r12.py 直接导入 run_r8 和 r8_planner，而包中 code/ 只包含 R12 局部源码；其余依赖指向服务器和既往恢复档案。S9 也明确承认没有私有权重的读者不能复现该策略。结论仍称提供了 reproducible interface，但读者获得何种可执行交付物、通过何种渠道取得、哪些组成部分受限，没有形成可独立使用的完整说明。

**Impact.** 这是整项实证结果所依赖的植物模型和策略对象，不是无关致谢。当前可以审计这一次执行结果，却不能据此确认继承部分的学术归属及一个合规、稳定、可运行的复现路径。我不将来源未知等同于抄袭或实验造假，也不声称 CCDC 强制所有权重公开；问题是作者尚未提供完成判断所需的证据。

**Minimum actual remedy.** 由负责的人类作者确认并记录源代码/权重的实际提供者或所属项目、应有引用/致谢以及能否提供给审稿人或读者。无公开论文的内部资产可以如实归属，不必编造与 [8] 的等价关系，也不要求重做不可追溯的训练。给出一份确实可访问的统一依赖清单和恢复入口，覆盖运行器、监督器、动力学、Actor/normalizer、环境版本、冻结 manifest、原始日志及命令；在允许的范围内提供完整归档。用一个新的恢复目录证明依赖能解析、权重哈希一致、至少一个保存结果/汇总可复核；不要求新增研究实验。若资产确实不能提供，精确改写可复现声明并给出明确限制与已获授权的替代核查方式。再次重复“尚未确认”不等于解决本项。

### C2 — 主实验场景的物理定义未在可读论文中充分交代

**Classification:** prose-layout (necessary scope specification; underlying evidence already exists). **Location:** pp.3–4 §IV-A，p.5 Fig.2 和 §V-B；Supplement S5/S6。

**Evidence.** 主文给出五个 family 名称和数量，但没有定义 pressure crossing 相对于普通 crossing 具体改变了什么，也没有给出目标速度范围。prepare_r12_confirmation.py 显示，pressure 同时采用 115–135° 基础风向、(850,300) m 的 45 m 实体静态圆障碍，以及 x∈[620,710] m、名义过线时刻 185–230 s 的横穿目标；其余 family 基础风向采样为 45–80°，没有这一静态障碍。目标通常为 0.65–0.95 m/s，endpoint 为 0.8–1.0 m/s。24 个主实验都是 1 km。这些资料目前需要读代码/JSON 才能理解；正文仅称 low-speed 和 designed strata。

**Impact.** 全部五个 R 失败和唯一 L 失败集中在 pressure 组。读者必须知道该组是风向、静态约束和会遇几何的组合，才能判断收益适用于什么工况。当前描述没有作错误因果归因，但不足以让应用领域读者解释结果；family 名称不能替代实验条件。

**Minimum actual remedy.** 在正文或可读 supplement 增加一个紧凑的场景定义表，列出任务长度、目标位置/速度生成范围、基础风向、静态障碍和 family 目的，引用冻结 manifest。明确 pressure 是组合工况，本实验没有隔离其中各因素的独立作用。只需整理已有证据，不需要重新采样、重新训练或追加扰动实验。

### C3 — PDF 数学排版与符号说明需要最后一次实质校对

**Classification:** prose-layout. **Location:** p.3 Eq.(3)/(4) 及 §III-C；p.5 Fig.2；p.8 参考文献末页。

**Evidence.** Markdown 中 Eq.(3) 有嵌套 min 的下标域，PDF 中这些域被压为与运算符挤在一起的行内字符串；Eq.(4) 的逻辑指示项也拥挤，影响区分 20、10 和其条件。p.5 Fig.2 的非均匀纵轴只称 expanded near zero，没有说明具体刻度变换。p.8 仅有少量参考文献尾部，存在可利用的版面空间。本轮查看的 8 页没有发现图表被裁切；此项不是笼统“重画所有图”。

**Impact.** 选择规则是主要技术对象，应当在 PDF 上无需反推 Markdown 就能读准。非线性纵轴需要使读者清楚点间距离不代表同等米数。末页空白本身不构成技术错误，我也没有独立核实当前会议页限，故不据此宣称违规。

**Minimum actual remedy.** 校正 Eq.(3)/(4) 的 Word/Office Math 运算符、上下标和指示函数，逐项对照科学公式；图注明确实际采用的刻度变换及线性区间。调整浮动、参考文献和段距，使新增场景说明无需靠压缩字号容纳。重新导出后逐页检查即可，无需科学代码修改。

## Related work and accepted limits

GVO 已将预测对象从瞬时可达速度推广至控制诱导运动，并讨论采样和有限时域；因此不能把“预测真实可执行运动”本身当作本文原创。[GVO 一手全文](https://gamma.cs.unc.edu/NHRVO/WilkieIROS09.pdf)。BC-MPC 已规划动态可行的多段海事机动并执行第一段；feedback motion prediction 已比较控制器相关预测及其受约束导航作用。[BC-MPC](https://arxiv.org/html/1907.00039)，[Feedback Motion Prediction](https://arxiv.org/html/2209.12648v3)。当前稿件基本尊重这些先例，没有把它们的保证迁移到递归帆船策略。进一步增加一两句说明本文特殊接口是“冻结递归策略的参考/保持/恢复与因果记忆重建”即可；不要求为本稿实现整套 BC-MPC 或 unicycle governor。

接受理想计算、单目标、匀速目标、相同继承动力学和有限场景的研究边界。多船、目标机动、物理船、完整 COLREGs、实时交付和更强的低阶模型是 optional future，不是本轮接受门槛。对一个仅增加 1/24 完成的比较，不应强行宣称总体优势，也不应仅因样本小就否定这一有限存在性/诊断结果。当前正文已经采用了合适的描述性边界。

## Unresolved items and persistent reviewer memory

- **C1 open, controls verdict:** 资产归属与可运行交付链仍需实际证据。原训练身份未知不是单独的否决理由；无法归属和无法说明受限复现入口的组合不能仅靠限制段落解决。
- **C2 open:** 将现有场景生成条件转成可读说明，尤其解释 pressure 组合工况；不接受把它写成已隔离的因果因素。
- **C3 open:** 校验最终 PDF 的数学层级和非线性坐标刻度说明。
- **Retain as resolved/accepted:** 主表 19/23/24 与 CSV 一致；L 唯一 incursion 是 t=402 s 端点已入缓冲区；t=260 s 的同输入不同决策已有证据；共同安全时间、窗口聚类、历史任务重叠、106 m 反例和 308 s 成本不能在下轮被删去或重新包装。
- **Do not re-open without new evidence:** 不为同一负端点再次要求整批 substep 实验；不把 H=60 s 预测的后续重规划实航当作固定协议真值；不要求不相干的新网络或实船实验来解决 C1–C3。
- **Remaining unknown:** 正式作者/归属、继承训练记录、许可/访问方案；全部轨迹的独立从零重算结果；本轮会议当前官方页限（官方网站请求超时，未据旧笔记作新判断）。

当前证据有保留价值，技术结论总体克制；但本轮版本仍需要实际完成 C1，并修复 C2/C3，才支持按声明范围发表。没有推断其他评审人的意见或投票。

**Final verdict: Major Revision**
