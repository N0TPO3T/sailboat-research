from pathlib import Path
import zipfile,hashlib,json,datetime
root=Path('/home/ot/Students/hs/sailboat-routing-v0').resolve()
assert root.is_relative_to(Path('/home/ot/Students/hs').resolve())
p=root/'paper/ccdc/r13_revision'
with zipfile.ZipFile(p/'R13_CCDC_REVIEW_preview.zip') as z:
 for n in z.namelist():assert (p/n).resolve().is_relative_to(p.resolve())
 z.extractall(p)
v=json.loads((p/'review_round_03_input/VERSION.json').read_text(encoding='utf-8-sig'))
assert all(hashlib.sha256((p/k).read_bytes()).hexdigest()==h for k,h in v.items())
state=root/'PROJECT_STATE.md';s=state.read_text()
entry='- R13 正文与三审循环交付：paper/ccdc/r13_revision/（实际8页Word PDF、可编辑Word/LaTeX、补充材料、9份原始意见）。两轮完整审查＋一轮最终校样，A/B/C均Major Revision；人工来源归属及访问确认未解决，未三审通过。当前结论与入口仅在FINAL_REVIEW_STATUS.md和AUTHOR_NOTES_ZH.md维护。无新增独立任务；3次同指令子步核验，科学冻结资产未改，无运行中实验/GPU/push。\n'
if entry not in s:state.write_text(s.replace('## 项目与唯一入口\n','## 项目与唯一入口\n'+entry,1))
(root/'CURRENT_PLAN.md').write_text('''# Current Plan

R13 自主修订及评审工作已停止，等待人工来源/归属/访问证据；不是继续方法研究。

- 最终稿及状态：paper/ccdc/r13_revision/FINAL_REVIEW_STATUS.md、AUTHOR_NOTES_ZH.md。
- 两轮完整独立审查及一轮最终校样已结束，A/B/C 均 Major Revision。已关闭的技术事项不无故重开。
- 必要下一步：作者/资产提供者确认 Python 移植、18D Actor、normalizer 的正式来源、引用/署名及允许提供方式；收到后定向更新和复核。
- 未获该信息不追加仿真、训练或重复审查以换取接收。无运行中作业、GPU、自动 push 或投稿。
- 保留 R12 与全部历史资产；LaTeX 源已交付但编译因平台目录缺失未验证，实际 PDF 来自 Word。
''')
h=root/'docs/HANDOFF.md'
mark='## R13 正文修订与模拟三审交付 — 2026-10-07'
if mark not in h.read_text():
 with h.open('a') as f:f.write('\n'+mark+'\n- 首读paper/ccdc/r13_revision/AUTHOR_NOTES_ZH.md与FINAL_REVIEW_STATUS.md；完整8页Word PDF、可编辑Word和LaTeX、补充材料及真实图表已交付。\n- 两轮完整独立审查＋一轮最终校样，9份原始意见；A/B/C最终均Major Revision，未三审通过。剩余人工来源归属及访问确认，技术问题已关闭；无新证据不重复审查。\n- 原24场比较保持R19/L23/S15 24安全；相对L多1场、共同安全平均+7秒/最坏+308秒，不支持普遍优势。仅增加3次原任务同指令子步核验（42.956秒、1CPU、0GPU），无新独立任务。\n- R13_CCDC_REVIEW_preview.zip与独立R13_REPRODUCTION_internal.zip含交付/内部恢复证据；183文件身份和72轨迹恢复已验证，不代表公开发布授权。科学旧资产不改，无训练/push/在跑实验。\n')
snap=p/'server_state';snap.mkdir(exist_ok=True)
for n in ['PROJECT_STATE.md','CURRENT_PLAN.md','docs/HANDOFF.md']:(snap/Path(n).name).write_bytes((root/n).read_bytes())
with zipfile.ZipFile(p/'R13_CCDC_REVIEW_preview.zip','a',zipfile.ZIP_DEFLATED) as z:
 for f in snap.iterdir():z.write(f,'server_state/'+f.name)
receipt={'time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewed_files':v,'rounds':3,'full_rounds':2,'final_copyedit_rounds':1,'verdicts':dict.fromkeys('ABC','Major Revision'),'new_independent_tasks':0,'numerical_replays':3,'gpu':0,'artifacts':{}}
for n in ['R13_CCDC_REVIEW_preview.zip','R13_REPRODUCTION_internal.zip']:
 f=p/n;receipt['artifacts'][n]={'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size}
(p/'DELIVERY.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt,indent=2))
