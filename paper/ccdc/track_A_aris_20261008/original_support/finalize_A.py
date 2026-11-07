from pathlib import Path
import json,zipfile,hashlib,statistics,re,csv
P=Path(__file__).resolve().parent;R=P.parent/'r13_revision';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
z=zipfile.ZipFile(R/'R13_REPRODUCTION_internal.zip');rows=[json.loads(z.read(n))['row'] for n in z.namelist() if n.endswith('trace.json')];assert len(rows)==72
variants=['reactive','simple','sampled'];safe={v:sum(r['success'] for r in rows if r['variant']==v) for v in variants};assert list(safe.values())==[19,23,24]
families={f:{v:sum(r['success'] for r in rows if r['family']==f and r['variant']==v) for v in variants} for f in sorted({r['family'] for r in rows})};assert list(families['mixed_pressure'].values())==[3,7,8]
for f in families:
 if f!='mixed_pressure':assert list(families[f].values())==[4,4,4]
a={(r['scene_id'],r['variant']):r for r in rows};d=[a[(k,'sampled')]['time_s']-a[(k,'simple')]['time_s'] for k in {r['scene_id'] for r in rows} if a[(k,'sampled')]['success'] and a[(k,'simple')]['success']];assert len(d)==23 and statistics.mean(d)==7 and max(d)==308
cpu={v:sum(r['cpu_seconds'] for r in rows if r['variant']==v) for v in variants}
old=(R/'manuscript.md').read_text(encoding='utf8');s=(P/'manuscript.md').read_text(encoding='utf8');assert re.findall(r'\$\$(.*?)\$\$',old,re.S)==re.findall(r'\$\$(.*?)\$\$',s,re.S)
assert all(sha(f)==sha(R/'figures'/f.name) for f in (P/'figures').glob('*') if f.is_file())
with zipfile.ZipFile(P/'manuscript.docx') as doc,zipfile.ZipFile(P/'official_template.docx') as template:
 from lxml import etree as E
 assert E.tostring(E.fromstring(doc.read('word/styles.xml')),method='c14n')==E.tostring(E.fromstring(template.read('word/styles.xml')),method='c14n')
 # Text, equations, table count and native editable math checked in actual OOXML.
 xml=doc.read('word/document.xml').decode();assert xml.count('<w:tbl>')==3;assert '<m:acc>' in xml and '<m:limLow>' in xml
tex=(P/'latex/main.tex').read_text(encoding='utf8');assert tex.count('\\begin{equation}')==6 and tex.count('\\begin{table}')==3
assert not (set(re.findall(r'\\ref\{([^}]+)\}',tex))-set(re.findall(r'\\label\{([^}]+)\}',tex)))
check={'raw_trace_rows':72,'safe':safe,'families':families,'S15_minus_L_common_safe':{'n':23,'mean':7,'median':statistics.median(d),'max':308},'episode_cpu_seconds':cpu,'equations_byte_identical_to_R13':True,'figures_byte_identical_to_R13':True,'template_styles_unchanged':True,'PDF_pages':8,'all_8_pages_visually_inspected':True,'new_navigation_runs':0,'training':False,'review_type':'one bounded author claim/evidence/layout check, not simulated acceptance','latex_compile':{'success':False,'error':'Unable to find standard directories for platform'},'source_R13_hashes':{n:sha(R/n) for n in ['manuscript.md','manuscript.docx','manuscript.pdf','SUPPLEMENT.md']}}
(P/'CLAIM_LAYOUT_CHECK.json').write_text(json.dumps(check,indent=2),encoding='utf8')
(P/'CLAIM_LAYOUT_CHECK.md').write_text('''# Bounded claim and layout check

One author-side check, no acceptance vote. Read 72 original trace.row records from the preserved R13 recovery archive: R/L/S15 =19/23/24, pressure=3/7/8, remaining four families each4/4/4. Common-safe S15−L: n23, mean7 s, median0, maximum308 s. Episode CPU totals reconstructed. This reads original task summaries; it is not a new integration or a fresh raw-coordinate safety audit. The prior raw-coordinate check remains in R13 EDITORIAL_REVIEW_20261007.md.

All six mathematical display expressions remain byte-identical to R13; nominal-first, conditional20m cancellation, fallback and next-step reference timing remain in the main manuscript. Main table numbering and figure order checked. Native Word math remains editable. Source styles.xml has identical canonical XML to the supplied template (only XML declaration serialization differs). Six plotted figures retain original bytes. Actual Word2019 PDF has8A4 pages; every final rendered page was inspected. No clipping, overlap, split figure/caption or unreadable math observed. Last page contains references and whitespace; no font shrink or unsupported6page requirement applied.

Claim boundaries retained: gain concentrated in the jointly changed pressure family; no single-factor attribution; one additional completion over this particular L;15s unchanged-reference calibration does not validate every60s maneuver;106m adverse prediction;308s detour; ideal computation not real-time deployment. No universal necessity of detailed dynamics, static encoding novelty, certified guard, training novelty, or checkpoint identity with the14D journal baseline claimed.

Residual author work: author list/order, affiliation, corresponding details and funding; actual venue submission/declarations. LaTeX source conversion is complete and statically checked, but the native compiler returns a platform-directory error. Delivered PDF is actual Word output, not a claimed LaTeX build.
''',encoding='utf8')
(P/'VENUE_CHECK.md').write_text('''# Official submission check

Checked2026-10-07 via live web search of official pages after direct fetch timed out.

- https://www.ccdc.neu.edu.cn/firstSubmit/list.htm : CCDC2027 permits8pages at first submission including figures; full paper PDF required. It mentions6pages at final submission and excess-page charges; recheck final rules when applicable.
- https://www.ccdc.neu.edu.cn/001/ and https://www.ccdc.neu.edu.cn/ : full-paper deadline31October2026; conference14–16May2027 inChangsha.
- https://www.ccdc.neu.edu.cn/finalSubmit/list.htm currently labelsCCDC2026; its past instructions are not silently applied as2027final policy.

Anonymous/AI-specific policy was not established by these pages. No guessed rule is applied. Current8page PDF meets the observed initial length. Human authors still complete identities, funding, metadata and required declarations before actual submission. No submission has been made.
''',encoding='utf8')
(P/'AUTHOR_NOTES_ZH.md').write_text('''# A线作者说明

本稿研究：在一个既有循环式帆舵控制器上，如何预测“位置目标＋保持与恢复规则”实际会产生的航迹，并据此调整目标。它完成的是理想计算条件下的有限仿真应用研究。没有证明实时部署、详细模型普遍必要或整体效率优越，也没有新训练网络。A现已独立交付，不等待B；B的新方法和新结果未进入本稿。

## 论文着力点

一个点并不足以定义控制器未来动作。控制器记忆、目标坐标系、已经算好的旧动作、保持多久和怎样恢复普通路线，共同决定执行航迹。本文把这些执行语义接入成熟的控制诱导预测思想，并用匹配对照检验价值。正确恢复状态是接口正确性，不包装成新控制理论；动力学、18D策略和风拟合来源各自说明。

## 效果与代价放在一起看

24场全部保留：R/L/S15安全19/23/24。8场联合压力任务为3/7/8；其余16场三法全安全。压力任务同时改变几何、风与静态障碍，不能归因于单个因素。S15相对具体低阶L只多完成1场；23场共同安全任务平均多7秒，最坏多308秒，累计回合CPU为2133.23对378.44秒。普通条件中简单方案已经很有竞争力。真实救回和多308秒的反例同时留主文；106米预测误差也没有删去。

## 这次实际改了什么

- 引言集中区分已有思想、继承资产、执行接口与实证发现。
- 新增主文分工况表；把单例收益、航时尾部和CPU成本放到同一论证中。
- 保留nominal优先、20m项条件性抵消、无guard可行候选排序及指令交付时序。
- 将低层输入细节、求解器设置、冗长核验记录和版本身份移到补充；未改变六条公式、模型、配置或任何成绩。
- 明确保留L的15秒不换目标标定范围，不能由此否定所有低阶方法。
- 正文不再用旧R编号推动叙事；历史集合单独索引。

## 阅读和恢复

先读manuscript.pdf（实际Word导出8页），修改用manuscript.docx或manuscript.md。SUPPLEMENT.md包含完整补充说明。latex/main.tex及A_LaTeX.zip与当前正文同步，但本机内置编译器报平台目录错误，未宣称生成LaTeX PDF。

A_SUBMISSION_READY_preview.zip中的ready表示内容与当前模板交付完成，不表示已经投稿或保证录用。一次有限主张—证据—版面检查见CLAIM_LAYOUT_CHECK.md/json；从原复现包72条trace.row重算主表、按族结果和时间成本，全匹配。没有新增导航实验或训练，也没有新一轮模拟Accept。

既有复现包仍为../r13_revision/R13_REPRODUCTION_internal.zip，保留原哈希。当前使用及向编辑/审稿人提供资产的许可已获用户确认；历史归档README过期措辞由CURRENT_ASSET_STATUS.md明确更正，不改旧包，不添加新许可证，不宣称已经公开。

人工待填仅包括本稿作者顺序、单位、通讯信息和资助，以及正式投稿所需声明。官方当前初投允许8页、截止2026-10-31；最终规则和专项声明由作者提交前复核。A没有自动投稿。B成熟后是否替换或升级本篇由人类决定。
''',encoding='utf8')
(P/'EVIDENCE_INDEX.md').write_text('''# Evidence and reproduction index

A adds no navigation or training results. `evidence/` is a byte-copy of R13 supporting data plus no new scientific rows. `CLAIM_LAYOUT_CHECK.json` records this author check of all72confirmation trace.row entries from the original archive. `figures/` preserves six cited actual figures and inherited optional files; the manuscript references the correct six.

Canonical complete recovery archive: `../r13_revision/R13_REPRODUCTION_internal.zip`. Contains source dependencies, Actor, normalizer, original manifests and72primary traces. Run its existing `python verify_recovery.py` in the documented environment; this A check does not claim a new environment installation or navigation rerun. Current permission note: CURRENT_ASSET_STATUS.md.

Full raw R12 supplementation: `../r12_revision/R12_raw_results.tar.gz`. Original source and formula audit: `../r13_revision/CODE_FORMULA_AUDIT.md`. Raw authority: `/home/ot/Students/hs/sailboat-routing-v0/runs/r12_revision_20261006/`. Archive identities are in DELIVERY.json. Historical reports and results remain outside the preview and are not pooled.

Build current editable Word with `python build_docx.py`; Windows Word export with `powershell -File export_pdf.ps1`. Source manuscript is manuscript.md. Generate matching TeX with `python convert_to_latex.py` on the original workstation containing the user template ZIP; no installed TeX runtime is needed to edit it. Native LaTeX compilation remains unavailable.
''',encoding='utf8')
(P/'latex/README_ZH.md').write_text('主文件main.tex。使用用户提供IEEEtran.cls；与A正文、三表、六图、六条公式及九项引用同步。内置编译器报Unable to find standard directories for platform，未验证编译。实际PDF见上一级manuscript.pdf，为Word2019导出。\n',encoding='utf8')
(P/'latex/compile.log').write_text('Unable to find standard directories for platform\n',encoding='utf8')
with zipfile.ZipFile(P/'A_LaTeX.zip','w',zipfile.ZIP_DEFLATED) as out:
 for f in (P/'latex').rglob('*'):
  if f.is_file():out.write(f,f.relative_to(P/'latex'))
(P/'README.md').write_text('# Track A completed manuscript\n\nRead AUTHOR_NOTES_ZH.md then manuscript.pdf. Edit manuscript.docx or manuscript.md; optional matching LaTeX in A_LaTeX.zip. Current source/permission clarification in CURRENT_ASSET_STATUS.md supersedes historical pending language. Evidence index and supplementary methods are included. Scientific results remain R13/R12 frozen assets. B is independent and contributes no result to A. Final human authorship/affiliation/funding and submission checks remain. No automatic submission.\n',encoding='utf8')
(P/'STATUS.md').write_text('# A status\n\nComplete: independent editorial consolidation of R13, actual8pageWordPDF fully inspected, editableWord/Markdown/LaTeX source, supplement, original figures, one bounded raw-row/equation/layout check. No navigation/training experiments, noGPU, nochanges to original assets, noBresults. Await only human authorship/funding/submission decisions; not waitingB. NativeLaTeXcompile unavailable; actualWordPDF delivered.\n',encoding='utf8')
meta={'files':{n:sha(P/n) for n in ['manuscript.md','manuscript.docx','manuscript.pdf','SUPPLEMENT.md','AUTHOR_NOTES_ZH.md','CLAIM_LAYOUT_CHECK.json']},'preserved_recovery_archive_sha256':sha(R/'R13_REPRODUCTION_internal.zip'),'source_R13':check['source_R13_hashes'],'new_experiments':0,'physics_changed':False,'A_independent_of_B':True}
(P/'DELIVERY.json').write_text(json.dumps(meta,indent=2),encoding='utf8')
with zipfile.ZipFile(P/'A_SUBMISSION_READY_preview.zip','w',zipfile.ZIP_DEFLATED) as out:
 for f in P.rglob('*'):
  if f.is_file() and f.name!='A_SUBMISSION_READY_preview.zip' and '__pycache__' not in f.parts and 'rendered' not in f.parts:out.write(f,f.relative_to(P))
with zipfile.ZipFile(P/'A_SUBMISSION_READY_preview.zip') as q:assert q.testzip() is None
print(json.dumps(check,indent=2));print('Preview bytes', (P/'A_SUBMISSION_READY_preview.zip').stat().st_size)
