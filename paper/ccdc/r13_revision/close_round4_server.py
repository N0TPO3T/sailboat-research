from pathlib import Path
import json,base64
r=Path('/home/ot/Students/hs/sailboat-routing-v0').resolve();assert r.is_relative_to(Path('/home/ot/Students/hs').resolve());p=r/'paper/ccdc/r13_revision'
f=r/'PROJECT_STATE.md';s=f.read_text();lines=s.splitlines();lines=[('- R13完成4轮模拟审查（12份原始意见）；原A/B/C对round04同版均Accept，非CCDC正式录用。用户确认Chao Yang来源及研究使用/评审提供同意已落实；14D期刊与18D资产区别保留。当前入口paper/ccdc/r13_revision/FINAL_REVIEW_STATUS.md及AUTHOR_NOTES_ZH.md；无新增实验/训练/图表重画，无在跑任务。' if x.startswith('- R13 正文与三审循环交付：') else x) for x in lines];f.write_text('\n'.join(lines)+'\n')
(r/'CURRENT_PLAN.md').write_text('''# Current Plan

No active research thread.

R13资产确认续办和原三位复核完成：round04 A/B/C均Accept，属内部模拟意见，不是正式录用。来源及研究/评审提供权限已确认，不重复询问。

当前交付入口：paper/ccdc/r13_revision/FINAL_REVIEW_STATUS.md、AUTHOR_NOTES_ZH.md、manuscript.pdf及可编辑Word/LaTeX。

后续仅待作者填写本稿署名、单位、通讯信息、资助并决定真实投稿。未授权自动投稿、push或扩大研究。LaTeX内置编译失败；实际PDF为8页Word导出。
''')
f=r/'docs/HANDOFF.md';s=f.read_text();heading='## R13 资产确认续办与第四轮复核完成 — 2026-10-07'
if heading not in s:
 s+='\n'+heading+'\n- 用户明确确认Chao Yang提供的继承动力学、18D Actor及normalizer可用于本研究并可完整提供给编辑/审稿人；此前来源/许可待确认状态已过期，不重复要求授权。\n- 正式引用Yang et al., Applied Ocean Research 175 (2026)105246，DOI10.1016/j.apor.2026.105246；期刊14D与实际18D注意力资产独立说明，代码/检查点/归一化身份保持，不转移期刊成绩，不称已公开发布。\n- 原A/B/C在第4轮对同一稿件均实际Accept；累计12份意见，FINAL_REVIEW_STATUS.md及review/round_04记录身份、集中回应和真实判定。内部模拟不等于CCDC录用。\n- 更新后的8页PDF、Word、LaTeX、Supplement及预览包位于paper/ccdc/r13_revision。183成员/72轨迹原包重新核验；本续办无新实验、训练、模型/方法改动或图表重画。\n- 本稿作者/单位/通讯/资助仍需人工填写；不照抄来源论文。无活动研究线程、后台实验、push或投稿。\n';f.write_text(s)
snap=p/'server_state';snap.mkdir(exist_ok=True)
for name in ['PROJECT_STATE.md','CURRENT_PLAN.md','docs/HANDOFF.md']:(snap/Path(name).name).write_bytes((r/name).read_bytes())
print(json.dumps({f.name:base64.b64encode(f.read_bytes()).decode() for f in snap.iterdir() if f.is_file()}))
