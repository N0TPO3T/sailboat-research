from pathlib import Path
import json,hashlib,datetime,zipfile,re
p=Path(r'C:/Users/74095/hs/SailBoat/sailboat-routing-v0/paper/ccdc/r13_revision')
v=json.loads((p/'review_round_04_input/VERSION.json').read_text())
assert all(hashlib.sha256((p/n).read_bytes()).hexdigest()==h for n,h in v.items())
for role in 'ABC':
 s=(p/f'review/round_04/{role}.md').read_text(encoding='utf-8');assert re.search(r'(?:verdict:|Verdict:)\s*\*?\*?Accept',s),role
(p/'FINAL_REVIEW_STATUS.md').write_text('''# R13 最终复核状态

**第四轮原 A、B、C 三位对同一最终版本均给出 Accept。** 这是实际独立模拟意见，不是 CCDC 正式录用或已经投稿。

|轮次|性质|A 方法/控制|B 实验/归因|C 应用/表达|
|---|---|---|---|---|
|1|完整初审|Major Revision|Major Revision|Major Revision|
|2|修改后完整复审|Major Revision|Major Revision|Major Revision|
|3|最终校样检查|Major Revision|Major Revision|Major Revision|
|4|用户提供新来源/许可证据后的定向复核|Accept|Accept|Accept|

累计4轮、12份原始意见。原三位持久身份未替换，原意见未改写。第四轮每人阅读全文、补充材料和全部8页PDF，核对来源论文相关页与最终文件身份。判定变化依据是新增用户确认及实际落地修订，不是重复采样意见。

最终版本由 review_round_04_input/VERSION.json 四项哈希标识：正文、DOCX、PDF与Supplement。三位均已核对一致。原始意见在 review/round_04/A.md、B.md、C.md；集中回应在 AUTHOR_RESPONSE.md。正文II-A、新增材料可用性、第9条文献及S9/S11/S12已解决A1/B1/C1；旧公式、场景和恢复问题保持关闭。

## 已确认与仍保留的边界

用户明确转述 Chao Yang 同意继承动力学、18D Actor及normalizer用于本研究，并能提供完整源代码、权重和配套材料给编辑/审稿人。这是当前来源与提供权限依据；不要求同范围重复授权，也不伪造许可证。

Yang et al.期刊报告14D；实际评估18D注意力变体有独立代码/检查点/归一化身份。不得宣称两者是相同基准checkpoint、转移期刊成绩或把能提供写成已公开。原训练run关联未知及模型等价性边界继续披露。

科学范围仍是理想计算、单低速匀速目标船闭环仿真。24场R/L/S15为19/23/24，S15对L多1场而共同安全均值+7秒/最坏+308秒；106m误差和计算代价保留。没有普遍优势、实时安全或完整COLREGs保证。

当前无未关闭的实质模拟审稿项。真实投稿前仍须作者填写本稿署名、单位、通讯信息和资助，不从来源论文复制。可编辑LaTeX内容同步，但内置编译失败；实际8页PDF为Word导出且已逐页检查。

本续办新增实验0、训练0、方法/权重变更0、图表重画0。已有183文件/72轨迹归档重新核对，字节不变。模拟审查在此结束，不自动扩大研究或投稿。

独立性披露见REVIEW_PROCESS.md；A/B在共享回应中看到C提出的支持文档指针校正，但未读其他审稿意见或票数，该非阻塞校正不改变最终四项稿件身份。
''',encoding='utf-8')
f=p/'AUTHOR_NOTES_ZH.md';s=f.read_text(encoding='utf-8').replace('原三位持久审稿人正在第四轮复核同一实际修改版；结果以FINAL_REVIEW_STATUS.md及原始review/round_04意见为准。','原三位持久审稿人已在第四轮对同一实际修改版均给出Accept，A1/B1/C1关闭；原始意见见review/round_04，最终状态见FINAL_REVIEW_STATUS.md。这是内部模拟接收，不是CCDC正式录用。');f.write_text(s,encoding='utf-8')
with (p/'REVIEW_PROCESS.md').open('a',encoding='utf-8') as f:f.write('\nRound04 resumed the same three identities after explicit user confirmation and the supplied formal Yang et al. paper. All three returned actual Accept for the same four-file identity in review_round_04_input/VERSION.json. Twelve total raw reviews are preserved. No new experiments or scientific changes. A/B disclose narrow exposure through the shared author response to C\'s nonblocking support-pointer correction, not C\'s report or vote. That support pointer was corrected outside the four reviewed manuscripts. This is same-family provisional simulation, not actual conference acceptance.\n')
with (p/'review/round_04/AUTHOR_RESPONSE.md').open('a',encoding='utf-8') as f:f.write('\n## 实际复核收尾\n原A/B/C均已返回Accept；A1/B1/C1关闭，其他既有关闭项保留。没有待实施的科学修订或补实验。保留有限范围和负结果，作者元数据另行填写；不将模拟意见改写成真实录用。\n')
# Final evidence receipt, not a new experiment.
(p/'evidence/round04_final_identity.json').write_text(json.dumps({'reviewed_files':v,'verdicts':dict.fromkeys('ABC','Accept'),'review_independence':'same-family','acceptance_status':'provisional internal simulation','new_experiments':0,'new_training':0,'source_paper_sha256':'9bc5165d59141e64c32cea5f4fbc2f4464c6fe0f88b40334de85703b92d356b9'},indent=2))
print('All three actual reviews verified; final status updated')
