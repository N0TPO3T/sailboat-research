from pathlib import Path
import zipfile,json,hashlib
r=Path('/home/ot/Students/hs/sailboat-routing-v0').resolve();assert r.is_relative_to(Path('/home/ot/Students/hs').resolve());p=r/'paper/ccdc/r13_revision'
with zipfile.ZipFile(p/'R13_source_update_transfer.zip') as z:
 for n in z.namelist():assert (p/n).resolve().is_relative_to(p.resolve())
 z.extractall(p)
v=json.loads((p/'review_round_04_input/VERSION.json').read_text());assert all(hashlib.sha256((p/n).read_bytes()).hexdigest()==h for n,h in v.items())
f=r/'PROJECT_STATE.md';s=f.read_text();s=s.replace('人工来源归属及访问确认未解决，未三审通过。','历史前三轮未三审通过；2026-10-07用户已确认Chao Yang来源及研究使用/评审提供同意，已更新稿件并交原三位进行第四轮复核，结果待返回。');f.write_text(s)
(r/'CURRENT_PLAN.md').write_text('''# Current Plan

R13 资产确认续办：用户已明确确认来源及研究使用/编辑与审稿人材料提供同意，不再是许可阻塞。

- 正文/补充材料/引用/提供说明已实际更新；14D期刊与18D实际资产分开，原实验不改。
- 原A/B/C正在复核review_round_04_input的同一版本；实际结论待返回，不预写接收。
- 剩余操作：按真实意见收尾，更新状态/交接/预览包。未知本稿署名、单位、资助留给作者。
- 本续办无新实验、训练、GPU或图表重画；无自动push/投稿。
''')
print('Source update extracted; reviewed identity matches; current authorization status corrected')
