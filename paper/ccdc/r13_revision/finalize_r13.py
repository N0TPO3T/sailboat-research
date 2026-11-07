from pathlib import Path
import json,hashlib,zipfile
p=Path(r'C:/Users/74095/hs/SailBoat/sailboat-routing-v0/paper/ccdc/r13_revision')
def put(n,s):
 (p/n).parent.mkdir(parents=True,exist_ok=True);(p/n).write_text(s,encoding='utf-8')
put('FINAL_REVIEW_STATUS.md','''# R13 最终模拟审查状态

最终状态：**未达到三位 Accept；A、B、C 均为 Major Revision。**

实际完成 3 轮：第 1、2 轮为完整独立审查，第 3 轮为同一最终版本的短校样复核。三位始终为独立、持久的子 agent，原始意见共 9 份，保存在 review/round_01—03。没有替换审稿人、多数票替代或把 Minor Revision 计为接收。模拟审查不是 CCDC 正式审稿或录用。

| 轮次 | A 方法/控制 | B 实验/归因 | C 应用/表达 |
| --- | --- | --- | --- |
| 1 完整初审 | Major Revision | Major Revision | Major Revision |
| 2 修改后完整复审 | Major Revision | Major Revision | Major Revision |
| 3 最终校样核对 | Major Revision | Major Revision | Major Revision |

最终审查身份由 review_round_03_input/VERSION.json 的正文、DOCX、PDF、补充材料四项 SHA256 确定。交付文件已逐项匹配。全部 8 页实际 Word 导出 PDF 已由作者及三位审稿人查看。LaTeX 内容已核对，但内置编译器缺少平台目录，未获得 LaTeX 编译 PDF。

三位已关闭自主可处理的公式、执行协议说明、场景定义、图表与内部恢复问题。**唯一仍控制审查结论的是人工来源、归属及资产访问/使用确认**：需要负责作者或资产提供者确认继承的 Python 动力学、18D Actor 和 normalizer 的准确来源、应有引用/致谢/署名，以及允许提供给审稿人/读者的对象与方式。公开发布不是唯一可接受方式。原 MATLAB 发行的许可不自动覆盖 Python 移植和权重。

本地论文草稿、文件哈希和实际内部恢复只能证明部分来源链与字节身份，不能替代该确认。完整训练记录缺失继续披露，不自动要求重训。不得将此状态写成已通过科学审查或发表就绪。

已向用户集中询问，尚无新确认。本轮停止自主扩展；更多仿真或重复改写不能解决人工事实缺口。下一次复核由真实来源/访问证据触发，只核对新增证据及相应表述，无依据不重开已关闭技术问题。

独立性和已知限制见 REVIEW_PROCESS.md；所有原始意见未改写。
''')
put('AUTHOR_NOTES_ZH.md','''# R13 作者说明

## 问题—假设—方法—效果

问题是未知风场中，固定学习型帆舵控制器能否借助候选位置参考的执行预测，避免部分单船动态缓冲区侵入。假设是完整静态地图、因果观测历史、单个目标船及理想计算交付；不等价于实时系统、完整 COLREGs 或实船验证。

方法保留冻结实现：局部风拟合、候选参考条件化闭环预测、同时刻最小余量评价、nominal 优先与保持/恢复机制。本轮修改数学解释和证据呈现，没有修改算法、模型、权重或判分。

主比较仍是 R12 冻结的 24 个匹配任务：R 19/24、L 23/24、S15 24/24 安全完成。S15 相对 L 多救回 1 场，在 23 个共同安全任务中平均多 7 秒、最坏多 308 秒。有限收益伴随航行和计算代价，不支持普遍优势、30 m 安全保证或实时可部署结论。

## 已落实的主要修订

- 主表与全任务图以当前 24 场为中心；历史评估分开，失败与不利结果保留。没有合并重复场景或不同协议的成功率。
- 明确预测最小余量的时间/障碍域、有效预测时域、空集/失败处理、nominal 优先、20 m 项的条件性抵消及全不满足 guard 时的排序；区分同域预测误差不等式与全任务安全。
- 明确旧指令先执行、下一步参考生效及实际反馈时序；L 的转向/速度含义按实现说明。
- 新确认唯一 L 侵入而 S15 安全的 pressure1 实际航迹及 260 秒同状态候选数字进入正文/补充材料；保留 endpoint3 的 +308 秒代价。
- 预测质量按 6 个源状态及其协议分支分组，保留 106 m 误差反例；窗口不作为独立任务。
- 使用用户 Word 模板生成实际 8 页 PDF；修正可编辑公式的帽号与最小值下标，逐页检查。LaTeX 同步源及图已打包，编译未验证，原因见下文。

## 新增证据及其边界

只新增 3 次现有任务的同指令积分子步核验，未增加独立任务或改变行为。端点状态最大误差为 0。R/L/S15 的子步最小动态余量分别为 -0.162187、-1.117383、42.094165 m；与原端点记录的分类一致。该核验耗时 42.956 秒，1 个 CPU 进程、GPU 0。原始记录见 evidence/new_case_substeps.json；它不是新的泛化评估。

内部恢复包 R13_REPRODUCTION_internal.zip 包含实际运行依赖代码、精确 Actor/normalizer、配置和 72 条主比较轨迹。183 个索引成员哈希核验通过，在现有环境中的新目录恢复已实际加载模型并复算 19/23/24 与 +7/+308。未声称全新机器从零安装通过。来源、命令、哈希和限制见 EVIDENCE_INDEX.md。

科学冻结文件及受保护旧稿未改变，证据见 evidence/r13_preservation_check.json。无训练、GPU 使用、自动 push 或投稿。

## 审查结果与剩余事项

完成两轮完整独立审查和一轮最终校样复核，三位最终均 Major Revision，未实现三审通过。逐项回应和原始意见见 review/；停止原因与最终身份见 FINAL_REVIEW_STATUS.md。

需要作者/资产提供者集中确认：
1. sailboat_s14.py Python 移植、18D Actor 和 normalizer 的创作者/提供者、准确来源及应有引用、致谢或署名。
2. 上述资产允许向哪些人以何种方式提供；可为获准的受限访问，不预设必须公开。
3. 作者、单位、资助和其他投稿元数据。未知项不猜填。

已找到的杨潮本地论文草稿和 MathWorks 原发行不能证明精确 checkpoint 的训练关联，也不能自动授权 Python 移植或权重。具体已证实/未知边界见 SOURCE_FOLLOWUP.md 与补充材料 S9、S11—S12。未知完整训练细节不自动构成重训要求，但不得宣称新场景已认证为低层训练 holdout。

下一步是取得上述人工记录并定向复核，不是自动增加实验或再开方法搜索。当前材料不是投稿就绪状态。

## 阅读与修改入口

manuscript.md 是科学正文；manuscript.docx 保留模板及原生可编辑公式；manuscript.pdf 是实际成功生成的 Word PDF。latex/main.tex 与 R13_LaTeX.zip 提供一致的可编辑 LaTeX。内置 LaTeX 编译器报平台标准目录缺失，因此没有 LaTeX 生成的 PDF；不以 Word PDF 冒充。

优先看 figures/figure5_rescue.png、figure6_adverse.png、figure2_confirmation.png、figure4_prediction.png。图均来自真实日志。原始证据及复现命令在 EVIDENCE_INDEX.md，当前 24 场与历史数据保持分开。
''')
put('review/round_03/AUTHOR_RESPONSE.md','''# 最终校样逐项回应

回应对象为同一最终 VERSION.json 下的三份原始意见，未修改评审原文。

- A1：接受其仍缺人工来源、归属与实际访问记录的判断。内部身份/恢复已补齐，但没有新的人类确认，故不标为关闭。A2/A3 和元数据校正已按最终 PDF 核验；无进一步实验要求。
- B1：交叉引用已修复，183 文件及 72 轨迹恢复证据成立；创作者/提供者及授权访问的人工确认仍开放。B2 的有限结论保留，B3 已关闭。没有用重复实验替代来源确认。
- C1：内部恢复部分关闭；Python 移植、Actor、normalizer 的归属及允许访问方式仍开放。C2/C3 与可选元数据修正关闭。

作者不请求无证据改票。最终三位 Major Revision 如实保留。后续收到人工证据后，才更新归属/访问表述并请求定向复核；不新增算法或试验来换取接收。
''')
with (p/'REVIEW_PROCESS.md').open('a',encoding='utf-8') as f:f.write('\nTwo full review rounds and one final copyedit round completed. All nine actual reports remain Major Revision. Round03 verified the same final four-file hash identity and all eight PDF pages; no new scientific evidence was implied by that short check. Final author response records the unresolved human attribution/access evidence without asking for a vote change.\n')
# Verify reviewed identity before delivery.
v=json.loads((p/'review_round_03_input/VERSION.json').read_text(encoding='utf-8-sig'))
assert all(hashlib.sha256((p/k).read_bytes()).hexdigest()==h for k,h in v.items())
assert all((p/f'review/round_{r:02}/{a}.md').exists() for r in (1,2,3) for a in 'ABC')
print('Final documents and nine raw reviews verified')
