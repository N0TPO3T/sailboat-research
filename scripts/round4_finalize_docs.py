import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];run=ROOT/'runs/round4_20261025'
conclusion=(run/'CONCLUSIONS_ZH.md').read_text(encoding='utf-8-sig').replace('抽帧每4秒，结束后','A表示专家、N表示normal。抽帧每4秒，结束后')
report=ROOT/'REPORT_ROUND4_ZH.md';base=report.read_text(encoding='utf-8-sig')
start='<!-- ROUND4_CONCLUSIONS -->';end='<!-- END_ROUND4_CONCLUSIONS -->'
if start in base:base=base.split(start)[0]+base.split(end,1)[1]
title,body=base.split('\n',1)
report.write_text(title+'\n\n'+start+'\n'+conclusion+'\n'+end+'\n'+body,encoding='utf-8')
f=json.loads((run/'freeze.json').read_text())
header='''# 当前交接：第四轮已完成

先读REPORT_ROUND4_ZH.md；运行目录runs/round4_20261025。前三轮报告、权重、失败与原始结果保留；未修改A线。

## 结果与限制

在第二轮两份selected上各做control/takeover4配对适配，共4次约20000步真实训练。Q/优化器/replay重新初始化；不是同一继承Actor起点的独立训练复现。只提高实际range/risk首次接管后10步的回放副本数（1→4）；输入、历史、mask、奖励、可训练参数与路由未改。

固定joint avoid/range开发选点：20261011/takeover4选5070，其余三臂step0。旧avoid-only会选四臂step0。故本轮没有两份源专家上重复的学习改善；三份step0不是新学习权重。四份真实训练末状态仍保存，未隐藏退化。

新50场940000—940049：normal35、W038；两份旧always-avoid均40，旧range41/40；最终always-avoid41/40，最终range44/40。第一份final range相对旧range救回3场无损失；相对自身always-avoid救回5损失2，共同安全平均+7.74s。第二份路由救回2损失2。原三个同状态失败最终仍未修复。结论、事件与限制以报告为准，不能只挑44/50宣布可重复改进。

## 位置与复现

服务器donghai:/home/ot/Students/hs/sailboat-dynamic-routing-v0；本地C:/Users/74095/hs/SailBoat/sailboat-dynamic-routing-v0。只读Python=/home/ot/Students/hs/sailboat-routing-v0/.venv/bin/python。无GPU，最多4个单线程CPU实验worker。

- 实际命令：runs/round4_20261025/COMMANDS.md；协议PROTOCOL.md；冻结身份freeze.json；配对选择及旧规则反事实包含在各selection.json。
- 最终协议模型：checkpoints/round4/<20261011或20261012>/takeover4/resume.pt、actor.pth、normalizer.pth；20261012为拒绝更新后的原Actor和fresh step0训练状态。
- 两源×两臂均有terminal_resume.pt，是真实训练后完整Q/optimizer/replay/RNG状态；terminal_verification.json记录加载后4次SAC更新一致。selected0为空replay；用终末状态检查真实恢复，不冒称整段不中断训练逐位一致。
- 中间快照在远端train_v2_*/*.pt.gz；解压字节SHA核验见compression.jsonl。终末状态的硬链接仅指向已完成、不会再改写的本轮恢复文件。
- 复用12条旧分支、新增4条末点分支和4条最终分支；diagnosis/final_attribution.json核验状态指纹及三个新救回场景的相同真实前缀。
- 新确认逻辑组去重后实际400回合；confirmation50/parts含400条唯一NPZ；按源组合800行含复用副本，只有50个独立场景。aliases.json记录复用，metadata_errata.json纠正freeze旧文字计数。
- 各seed目录有CSV/JSONL、全部28对共同安全航时/航程、逐场救回/损失、events.json和trajectory_checks.json。全结果保留，不以失败早停提速。
- figures包含3PNG与1GIF（三个真实案例：救回/路由损失/无目标代价）；预览DualPolicy_Round4_preview.zip，完整证据Round4_evidence.tar.gz，模型Round4_models.tar.gz（本地打包避免远端占盘）。

## 恢复注意

最初train_<source>_<arm>为因replay副本提前触发预热而中止的实现试运行，不用于结论。正式结果是train_v2_*，更新门槛使用256真实步。一次针对性检查same-family/provisional；剩余RNG/选点接口限制见报告，不追加审查或宣称clean。

--resume必须使用新输出目录并保持seed/scene-base/actor-start/takeover-copies/冻结参数协议。当前选择入口只接纳本次fresh固定四臂目录，不自动接纳中断续训目录；不要盲目覆盖输出或重启旧PID。

本轮全部作业已结束。940000—940049现为已见确认资料，后续改进必须换新确认集。No active research thread.
'''
(ROOT/'HANDOFF.md').write_text(header,encoding='utf-8')
(ROOT/'PROJECT_STATE.md').write_text('''# 当前事实
第四轮已完成：REPORT_ROUND4_ZH.md为结果与结论的canonical来源，HANDOFF.md为恢复入口，runs/round4_20261025为证据。
四个真实训练运行完成，两源各两臂；一份选中新适配Actor，其余三臂拒绝更新。不能声称两个源重复学习改善。
400个唯一评估回合已完成；相同新50场940000—940049供两源共享，800组合行含复用。该集合现为已见，不能重新称新确认。
四个终末检查点恢复更新核验与800组合轨迹指标核验已通过。原三个同状态失败仍未修复；改进归因边界见报告。
第三轮以及更早权重/失败均保留，src/dynamic.py与scripts/train.py未改，A线未改。
最终文件位置、训练续行限制、存储压缩及计数勘误见HANDOFF.md。
''',encoding='utf-8')
(ROOT/'CURRENT_PLAN.md').write_text('No active research thread.\n\n第四轮已完成，结果与后续研究判断见REPORT_ROUND4_ZH.md；恢复入口HANDOFF.md。未承诺自动启动下一轮。\n',encoding='utf-8')
(ROOT/'PROJECT_MEMORY.md').write_text('''# 长期经验

## 回放加权必须保持真实交互时钟
Tags: replay, SAC, warmup, paired-training
Conclusion: 通过重复插入加权转移时，用buffer.size触发更新会提前开启Q预热，混入优化预算差异。应同时用真实控制步数约束更新门槛，按物理步核对Q更新数。
Evidence: runs/round4_20261025/implementation_check.json、PROTOCOL.md；旧试运行同源约480步control56次Q更新、加权64次，v2统一steps>=256后逐回合通过updates=max(0,floor(steps/4)-63)。
Implication: 以后改变replay权重/副本/容量时，先核查更新、预热、保存和开发评估分别依赖哪个时钟；不能仅看总步数相同就认定预算一致。
''',encoding='utf-8')
readme=ROOT/'README.md';text=readme.read_text(encoding='utf-8-sig');parts=text.split('\n',3)
if len(parts)>3:
 text=parts[0]+'\n\n第四轮已完成4次真实适配训练、固定状态诊断和新50场400个唯一回合确认。见[第四轮报告](REPORT_ROUND4_ZH.md)、[实际命令](runs/round4_20261025/COMMANDS.md)及[交接](HANDOFF.md)。前三轮全部结果保留；不能把单源局部改善称为重复成功。\n'+parts[3]
readme.write_text(text,encoding='utf-8')
print('report and handoff finalized')
