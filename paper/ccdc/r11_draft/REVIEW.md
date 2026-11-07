# R11 分离会话模拟写作评审

日期：2026-10-05。范围：完整英文正文、三张实际生成的 PNG、关键冻结实现、现有结果行及正文引用。此为内部模拟同行评审，不具有真实 CCDC 审稿身份，不评分，不作录用判断，也不重开 R10 方法选型。

**稿件已有的价值。** 本稿已把“位置参考如何经继承的循环策略与执行器产生运动”写成可检查的研究对象。动作先生成、参考下一秒交付、真实历史重编码、候选独立预测、保持后恢复反馈等细节共同构成明确的接口贡献。证据叙事也基本可信：历史救回指向缓冲侵入而非实体碰撞；13 个机制实例与历史组重叠；12 个新实例没有反应式安全完成优势；271 s 代价和 S60 的竞争力均未隐藏。这些内容支持当前有限的应用／接口研究定位。下面的修改用于使稿件更清楚、更可核查，不要求追加实验来维持这个定位。

本轮直接核查了 r8_planner.py、r8_model.py、run_r8.py、run_r10.py、wind_fields.py、prepare_r10_confirmation.py，并从实际 rows.json／analysis_rows.json 重聚合主表计数和 S15−R 条件航时。历史短组 30/28、长组 4/3、新组 12/12、机制组 13/11/13/9，以及 +15.29、+8.67、+38.91、+27.08 s 均与正文一致。原稿对应 SHA256：84c62cbb84663592a11a72093bdbc79136993b947eec7cef2f521d6892a3ebf2。作者可能在评审期间进行已沟通的符号和排版编辑，本报告不是最终文件哈希认证。

## 1. 让伪代码和 NH 定义精确对应实际计时与可行性判定

**证据。** Algorithm 1 第 8 步把 hold/review timer 放在 non-nominal 分支，容易被读成普通预测通过后不推进复评时刻。但 src/sailboat_routing/r8_planner.py:47 在任何一次预测开始时都设置 next_plan=t+period；仅 held/until 在第 69 行取决于是否选择非普通参考。正文 IV-A 把 NH 写成“prediction falls below the guard”，而 scripts/run_r10.py:48-50 对无效预测或积分失败也视为不满足可行性条件；只有存在当前参考时才保持。

**影响。** 按现有伪代码实现，读者可能每秒重算普通预测，改变 CPU、风拟合历史及未来选择。将 NH 写成纯数值阈值比较，也会漏掉其失败分支。这与本文强调执行协议精确性的贡献直接相关。

**本轮可修。** 明确初始化 next_plan=10，每次实际预测都令 next_plan=t+P；仅非普通选择设置 held 与 until=t+P，普通选择释放保持。NH 复用完整的 nominal 可行性谓词，而不只是 margin<30。无需改源码或重跑；正文已有 t→t+1→t+2 的物理时序可保留。

## 2. 补足真实实验条件，尤其明确主实验没有目标转弯

**证据。** II-A 与 V 说实际环境可偏离目标恒速外推，却没有交代本次主结果是否真的包含这种偏离。实际历史短组、历史长组和新确认的所有目标均没有 turns。短组目标速度范围为 0.574866–1.230519 m/s；长组为 0.9 或 1.0 m/s；新组为 0.657165–0.913105 m/s。短组风配置为 stable/slow/fast = 18/6/6，新组为 stable/fast = 6/6；wind_fields.py 定义基准风速 8 m/s 和具体空间／时间调制。上述信息来自实际 manifest，而不是用抽象“low-speed”补猜。正文的可复现表述也尚未对应到明确的冻结场景、代码和资产恢复入口。

**影响。** 所有主实验的目标恒速模型与被观察目标运动结构匹配。读者若误以为结果已覆盖目标机动失配，会高估方法边界。反过来，缺少风和任务生成条件会妨碍读者判断真实的模型误差来自哪里。继承资产的内部可恢复与外部可获得也不能等同。

**本轮可修。** 在 IV-A 加一个紧凑设置段或表，保留单目标、恒速／无转弯、风配置计数和数值范围；指向现有冻结配置、场景 manifest、源码与资产身份索引。把摘要的“establishes a reproducible ... interface”限定为明确指定并在冻结资产条件下可恢复的接口；没有作者许可时不承诺公开发布。正式作者和资产署名继续占位。无需新实验。目标机动、噪声或自然交通分布的验证属于未来研究，不能通过改写补成已验证结果。

可直接入稿的简短版本：

> All main tasks contain one non-reacting target with constant world-frame velocity and no scheduled turn. Target speeds range from 0.575 to 1.231 m/s in the historical short group, are 0.9 or 1.0 m/s in the long group, and range from 0.657 to 0.913 m/s in new confirmation. Thus constant-velocity extrapolation is matched to the observed targets in these tests; the results do not evaluate robustness to target maneuvers. The environment uses a private synthetic wind field with base speed 8 m/s. Historical short tasks comprise 18 stable, six slow and six fast profiles; new confirmation comprises six stable and six fast profiles. Stable wind is fixed. Slow/fast profiles add bounded spatial and temporal direction waves with amplitudes 25/45 degrees, directional perturbations up to 3/6 degrees and speed modulation of 12/20 percent.

配置证据：runs/r8_closedloop_20261005T062543Z/confirmation.json、long.json；runs/r10_decision_20261005/confirmation.json、freeze.json、REPRODUCE.md、SOURCE_HASHES.json、ASSET_HASHES.json；src/sailboat_routing/wind_fields.py:18-99；scripts/prepare_r10_confirmation.py。引用范围和计数不能与旧 R9 时延协议混合。

## 3. 修复图文不一致和最终尺寸下的可读性

**证据。** 直接查看三张 PNG：Fig. 2 图注称 selected side reference 已单独标记，但该参考为 (238.784, −324.617) m，绘图区约为 x=420–530、y=−100–−30 m，因此目标点不可见。Fig. 1 中 “Restore policy memory” 和底部执行文字跨越节点边框；Fig. 3 的新 endpoint 面板中，目标船 250/300 s 标签互相重叠，部分本船时刻标注也靠得过近。Fig. 2 的 149 s 标注靠近标题，图例遮挡了部分局部运动。

**影响。** Fig. 2 是主要机制证据，缺失参考点会让“参考方向不等于执行轨迹”的核心关系难以阅读。同步时刻是避免把相交空间路径误判为碰撞的关键，重叠时间标注会削弱 Fig. 3 的解释力。

**本轮可修。** 保持局部运动放大图，并用指向框外的方向箭头／小插图标明已选参考坐标，或者删除与实际图不符的图注句子。给 Fig. 1 正确换行并调整框宽；给 Fig. 3 标签设置独立偏移和引线。最终按 Word/PDF 双栏的实际尺寸检查全部文字、图例和线型。图形编辑不得改动轨迹数据，也不需要新实验。

## 4. 给核心输入适配补上最小数学定义

**证据。** II-B 写“rigid local frame places the active reference at (500,0)”及“two progress differences”，但这不足以唯一确定旋转角、平移原点和两个差分的符号。冻结 frames.py:35-77 与 evidence_check.md 已提供具体定义：参考应用时从本船到参考的方位决定 frame angle；frame origin 为 g−500[cos(theta),sin(theta)]；两个进度量分别为前一状态距离减当前距离、前一状态的 |500−x_local| 减当前值。船体 u/v 不再次旋转；参考变化后所有真实历史按新框架重编码。

**影响。** 本文价值主要在控制器接口。省略这些定义比省略非关键实现参数更容易造成复现偏差，尤其是误把 body velocity 旋转到参考框架，或把差分符号颠倒。当前数值结果本身未因此被否定。

**本轮可修。** 用一至两句或一个紧凑输入表定义 frame angle／origin 和两个进度量，注明初始进度为零、u/v 保持船体坐标。可把详细 18 维顺序放在现有补充证据中，并在正文明确指向它。无需新增模块、试验或策略训练。

## 引用与结论核查

五条引用均在正文中实际使用。当前引用用途与可访问的一手来源相符：

- [1] 是全局帆船 Q-learning 路径规划的背景，不是本文动态参考预测的性能基线。核对依据为论文在 [PMC 的正文检索内容](https://pmc.ncbi.nlm.nih.gov/articles/PMC7146235/) 和 [MDPI 版本记录](https://www.mdpi.com/1424-8220/20/6/1550/notes)；直接 PMC 打开触发验证页，未把它记为本轮全文逐节核查。
- [2] 的 [GVO 原文 §IV](https://gamma.cs.unc.edu/NHRVO/WilkieIROS09.pdf) 确实以控制诱导的位置轨迹及同步最小距离定义障碍，并允许数值采样。稿件称接口适配、没有继承安全定理，符合来源。
- [3] 的 [作者机构公开稿](https://www.merl.com/publications/docs/TR2016-102.pdf) 支持监督器修改既有闭环参考的连接。稿件没有把经验 guard 写成 reference-governor 的约束证书。
- [4] 的 [Wiley 作者与摘要页](https://onlinelibrary.wiley.com/doi/abs/10.1002/rob.22512) 支持从帆船运动估计风这一背景，并与列出的作者、卷页信息一致。稿件明确未实现 MoWe，未借用其性能性质；本轮未把摘要访问冒充完整方法核查。
- [5] 的 [PMLR 官方记录](https://proceedings.mlr.press/v80/haarnoja18b.html) 对应 SAC 基础来源。该引用不能替代继承的 18D 循环／注意力资产本身的最终署名，正文目前已经承认这一点。

这不是穷尽查新，也不意味着所有可比较动态避碰方案都已覆盖。现有数据支持“候选搜索与指定 NH 保持规则可能不同，且存在收益与代价”；不支持普遍优于反应式、不支持各组件独立必要、不支持 15 s 最优。稿件当前结论保留了这些边界，建议保留。

本报告提出四项可由现有材料处理的修改。作者可逐项有据回应，采用等效表述或说明保留理由；不要求将所有建议照单执行。官方模板生成、实际 PDF 页数和最终字图排版由协调作者继续验证；本评审没有以尚未完成的 PDF 为科学阻断项，也没有推断匿名、AI 披露或超页规则。署名和发表许可仍须由人类作者确认，不能由内部审稿代替。

## 同轮修订核对

作者修订稿 ba89d561d0d80dd8d3768e7328425e0dba3592f1a4c034f2ad14e737246e092e 已直接核对：Algorithm 1 现在规定每次预测后更新复评时刻；IV-A 补充了无转弯目标、真实速度范围与风配置；摘要改为 auditable；Fig. 2 删除了不可见参考点已标记的错误图注。重新查看的三张 PNG 显示 Fig. 1 框内文字与 Fig. 3 重叠标签已作调整。上述修订解决了相应的主要表述问题。

该版本尚未把 NH 无效／积分失败分支和第 4 项输入定义写入正文，已交作者作最终说明或有据回应。此处记录的是同一轮修订核对，不启动第二轮评审。协调作者报告已生成并逐页检查 6 页 Word 模板 PDF；本评审只确认本地 PDF 文件存在，不把协调作者的页级验证冒充独立复核。

本轮审稿结束。无新增实验、科学源码变更、调参、训练或发布操作。
