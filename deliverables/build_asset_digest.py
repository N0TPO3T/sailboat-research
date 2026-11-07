from pathlib import Path
import shutil,json,zipfile,tarfile,hashlib,re,html,base64
r=Path(r'C:/Users/74095/hs/SailBoat/sailboat-routing-v0');p=r/'paper/ccdc/r13_revision';o=r/'deliverables/SailBoatRL_asset_digest_20261007'
def copy(src,dst):
 dst=o/dst;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
def put(n,s):(o/n).write_text(s,encoding='utf-8')
for n in ['manuscript_zh.md','manuscript.md','manuscript.docx','manuscript.pdf','SUPPLEMENT.md','AUTHOR_NOTES_ZH.md','SOURCE_FOLLOWUP.md','AUTHOR_ASSET_CHECKLIST_ZH.md','R13_LaTeX.zip']:
 copy(p/n,'03_paper/'+n)
# Preserve manuscript relative image links inside its own folder.
for f in (p/'figures').glob('*'):
 if f.is_file() and f.suffix in ['.png','.pdf','.svg'] and f.stem!='figure5_encounters':
  copy(f,'04_figures/'+f.name)
  if f.suffix=='.png':copy(f,'03_paper/figures/'+f.name)
for f in (p/'evidence').glob('*'):
 if f.suffix in ['.json','.csv','.log'] and f.name not in ['job_pid.json','pipeline_pid.json','final_delivery_check.json']:
  copy(f,'05_evidence/'+f.name)
copy(p/'R13_REPRODUCTION_internal.zip','06_reproduction/R13_REPRODUCTION_internal.zip')
copy(p.parent/'r12_revision/R12_raw_results.tar.gz','06_reproduction/R12_raw_results.tar.gz')
copy(p/'EVIDENCE_INDEX.md','06_reproduction/ORIGINAL_EVIDENCE_INDEX.md')
for n in ['plot_r13.py','check_case_substeps.py','package_reproduction.py','CODE_FORMULA_AUDIT.md']:
 copy(p/n,'06_reproduction/'+n)
for f in (r/'docs').glob('R*.md'):
 if any(k in f.name for k in ['RESEARCH_REPORT','METHOD_NOTE','REVISION_REPORT','METHOD_DECISION']):copy(f,'07_history/'+f.name)
for f in (r/'docs/ep_result').glob('*.md'):copy(f,'07_history/'+f.name)
copy(r/'paper/ccdc/METHOD_SCOPE.md','07_history/R10_METHOD_SCOPE_historical.md')
for f in (p/'review').rglob('*.md'):copy(f,'08_review/'+str(f.relative_to(p/'review')))
copy(p/'FINAL_REVIEW_STATUS.md','08_review/FINAL_REVIEW_STATUS.md')
copy(p/'REVIEW_PROCESS.md','08_review/REVIEW_PROCESS.md')
copy(p/'review_round_04_input/VERSION.json','08_review/FINAL_VERSION.json')
copy(r/'main.pdf','09_sources/Yang_et_al_2026.pdf')
copy(p/'SOURCE_FOLLOWUP.md','09_sources/SOURCE_FOLLOWUP.md')
put('01_METHOD_MAP.md','''# 方法与实现地图

本文主线：固定低层的候选位置参考执行预测。术语nominal=常规参考，continue=继续当前参考，side=四个侧向参考，S15=详细预测且保持/复查周期15秒，L=同接口低阶预测对照。

## 输入—处理—输出

输入是截至当前的船舶状态、真实观测/指令历史、现用参考与管理器、静态地图、目标船当前及历史观测。输出是位置参考，不是瞬时可实现的航向或速度。

1. 从真实历史恢复策略记忆、参考坐标系、累积帆舵设定和已算出的当前动作。
2. 用过去三个运动转移拟合局部风，不读取环境真风或未来。
3. 先预测常规参考；有效且预测最小余量≥30米则直接采用。
4. 否则对继续当前参考及四个350米侧向目标，分别预测保持15秒后恢复反馈的轨迹，最多60秒。
5. 在可行集中选终端代价最低者；全不满足时，在有效候选中先最大化余量再比代价。无有效候选时按实现回退；基础规划失败仍可能退出。
6. 旧动作先推进一个控制步，再应用新参考。真实控制器仍持续反馈，新参考最早影响下一段物理运动。

代价为预测终点到任务终点的距离＋20米×非nominal指示＋10米×侧向指示。nominal被拒后20米对全部可行备选相同，并非一般干预成本；它在包含nominal的同余量退化排序中仍可能有作用。不能改写成一个未经实现的新评分公式。

真实动态排除距离85米，与预测额外30米门槛不同。前者用于判分，后者用于决策。实体代理合计25米再加60米缓冲；缓冲侵入不是实体碰撞同义词。静态判据为实体半径＋60米。

## 源码入口（解压06_reproduction/R13_REPRODUCTION_internal.zip后的相对路径）

| 功能 | 实际入口 | 继承/本篇角色 |
| --- | --- | --- |
| 候选协议、触发、保持与选择 | src/sailboat_routing/r8_planner.py | 冻结的详细监督逻辑 |
| 详细预测、局部风与闭环展开 | src/sailboat_routing/r8_model.py | 继承控制器的候选执行预测 |
| 匹配的低阶预测器L | src/sailboat_routing/r12_model.py | 简单且有竞争力的预测对照 |
| 真实闭环任务执行 | scripts/run_r8.py、scripts/run_r12.py | 真实状态、动作与评价记录 |
| 继承动力学 | third_party/senior/sailboat_s14.py | Chao Yang相关研究代码库提供 |
| 18D策略与归一化 | checkpoints/obstacle_candidate/下actor10800及normalizer10800 | 固定资产，本篇不训练 |
| 确认配置与原始轨迹 | runs/r12_revision_20261006/confirmation/ | 24场×3方法，72条trace.json |

具体身份见05_evidence/asset_resume_check.json与08_review/FINAL_VERSION.json。内部预测与真实执行使用分离实例；这防止串改状态，不构成模型失配鲁棒性证据。

## 与师兄研究的区别

Yang等期刊研究提供无直接风输入的低层帆舵控制背景，期刊公式描述14D输入。我们使用相关代码库提供的18D注意力变体，但不声称与期刊基准checkpoint相同，也不继承其99%等成绩。本篇不重训底层，研究其上面的参考选择与执行预测接口。

GVO、参考调节器、BC-MPC和反馈运动预测是既有思想来源；本文不宣称发明预测避碰。保留原动力学理论文献及第三方说明，材料获准供研究/编辑/审稿人复现，不等于已公开发布或附加新许可证。
''')
put('02_EVIDENCE_MAP.md','''# 结论—证据—原始资产

## 以哪组结果为主

主结果为R12冻结24项1km任务：R19、L23、S15 24安全完成；在R12时冻结后评估，R13只复核和修订，不能说是R13重新独立测试。72条完整轨迹在内部恢复包；配置、全部失败、动作及预测保留。

| 要回答的问题 | 关键数值/观察 | 本包入口 |
| --- | --- | --- |
| 有无安全收益与代价？ | 19/23/24；S15对L多1场，共同安全23场均值+7秒/最大+308秒 | 05_evidence/analysis.json、episodes.csv；06_reproduction内72条轨迹 |
| 同一状态为什么换点？ | 260秒常规预测11.893米与59.832米不同；S15选择+90度 | decision_260.csv、case_analysis.json、figure5_rescue |
| 是否存在过度干预？ | endpoint3：R/L279秒，S15 587秒 | case_analysis.json、figure6_adverse及完整原轨迹 |
| 详细预测是否更准？ | 6快照×2协议；中位分支最大误差1.104对53.818米，106.064米反例 | matched_prediction_quality.json/.csv、fixed_branches.json |
| 门槛是否最优？ | 0/15/30/60米均12/12，没有确定最优值 | analysis.json的guard部分、guard.json |
| 是否只是数值伪影？ | 新差异案例子步余量−0.162/−1.117/42.094米，端点误差0 | new_case_substeps.json；历史substep_safety.json |
| 计算有多贵？ | 核心调用中位17.009对0.067秒；不是相同候选数的等工作量比较 | planning_profile.json、analysis.json |
| 是否可复现已报告主表？ | 已加载实际模型、导入worker、恢复19/23/24及+7/+308 | recovery_check.json/.log、asset_resume_check.json |

上述文件名无目录前缀时位于05_evidence；图位于04_figures。

## 历史组必须分开

| 历史证据 | 角色 | 不能做的合并 |
| --- | --- | --- |
| R8短30/长4 | 主方法早期条件性安全证据；含1/3/5km范围 | 不能与新24场拼成新的独立确认成功率 |
| R10已见13 | 同状态机理与简单保持对照；与R8重叠 | 不能作为额外13个独立样本 |
| R10新12 | 当时新冻结；R、S15均12/12，S15有+271秒代价 | 不能只保留有利历史场景 |
| R9时间协议 | 计算等待进入运动闭环的独立边界研究 | 不能用R9时序加R12成绩声称实时24/24 |
| 1083预测窗 | 来自46个源任务的聚类窗口 | 不能当成1083次独立任务 |

## 复现包范围与已知限制

06_reproduction/R13_REPRODUCTION_internal.zip：精确代码/运行依赖、18D Actor及normalizer、冻结配置和全部72条主比较轨迹。解压后在已有兼容项目环境运行`python verify_recovery.py`，核对成员、加载模型并复算主表，不重跑物理任务。此前确已执行成功，但不是全新机器从零安装通过的证明。

06_reproduction/R12_raw_results.tar.gz：完整R12补证原始归档及其所需历史输入。它补充了内部恢复包主要聚焦主比较的范围。两包原样保留，具体大小/来源/哈希见ASSET_MANIFEST.json。

本包附V0至R12现有方法/报告，供历史追溯；不声称包含所有V0—R10全量原始运行。报告中的服务器runs路径仍是相应旧证据入口。本包不是整个Git历史和全部环境的系统镜像。

本轮仅整理解释与打包，没有运行新实验，没有修改正式稿/算法/权重。模拟三审Accept是内部质检，不替代真实实验，更不代表正式会议录用。
''')
put('06_reproduction/READ_ME_FIRST.md','''# 恢复说明

两个既有原始包按字节复制，未重写代码或检查点：

- R13_REPRODUCTION_internal.zip：183个哈希索引成员，含实际源代码、Actor、normalizer、冻结配置、72条主轨迹及verify_recovery.py。
- R12_raw_results.tar.gz：R12补证完整归档及必要历史输入；与其既有索引一起查阅。

将内部包解压到一个新目录，使用已有兼容环境运行`python verify_recovery.py`。该命令校验/加载/汇总，不重新运行全部仿真。不要把现有已完成runs目录用作新实验输出。原包内的历史“内部使用/未公开”描述保留；最新来源与获准研究/评审提供范围见../09_sources/SOURCE_FOLLOWUP.md。

此资料包服务于当前用户的项目阅读、修改与复现；没有自动公开发布，也没有给继承代码或权重添加许可证。完整冻结身份见包内CONTENTS_SHA256.json。本次不安装新环境，不启动训练或实验。
''')
# Render the reading guide as a fully offline HTML with embedded existing figures.
s=(o/'00_START_HERE.md').read_text(encoding='utf-8-sig')
def inline(t):
 t=html.escape(t);t=re.sub(r'\*\*(.*?)\*\*',r'<strong>\1</strong>',t);t=re.sub(r'`([^`]+)`',r'<code>\1</code>',t);return t
blocks=s.strip().split('\n\n');out=[]
for b in blocks:
 if b.startswith('```'):out.append('<pre>'+html.escape('\n'.join(b.splitlines()[1:-1]))+'</pre>')
 elif b.startswith('# '):out.append('<h1>'+inline(b[2:])+'</h1>')
 elif b.startswith('## '):out.append('<h2>'+inline(b[3:])+'</h2>')
 elif b.startswith('### '):out.append('<h3>'+inline(b[4:])+'</h3>')
 elif b.startswith('!['):
  m=re.fullmatch(r'!\[(.*?)\]\((.*?)\)',b);data=base64.b64encode((o/m[2]).read_bytes()).decode();out.append('<figure><img src="data:image/png;base64,'+data+'" alt="'+html.escape(m[1])+'"><figcaption>'+inline(m[1])+'</figcaption></figure>')
 elif b.startswith('|'):
  rows=[[c.strip() for c in l.strip('|').split('|')] for l in b.splitlines() if not re.fullmatch(r'[| :\-]+',l)]
  out.append('<div class="table"><table>'+''.join('<tr>'+''.join(('<th>' if i==0 else '<td>')+inline(c)+('</th>' if i==0 else '</td>') for c in row)+'</tr>' for i,row in enumerate(rows))+'</table></div>')
 elif b.startswith('> '):out.append('<blockquote>'+inline(b[2:])+'</blockquote>')
 elif b.startswith('- '):out.append('<ul>'+''.join('<li>'+inline(l[2:])+'</li>' for l in b.splitlines())+'</ul>')
 elif re.match(r'^\d+\. ',b):out.append('<ol>'+''.join('<li>'+inline(re.sub(r'^\d+\. ','',l))+'</li>' for l in b.splitlines())+'</ol>')
 else:out.append('<p>'+inline(b)+'</p>')
style='body{margin:0;background:#f4f6fa;color:#202936;font:17px/1.85 system-ui,"Microsoft YaHei",sans-serif}main{max-width:1040px;margin:30px auto;background:white;padding:44px;border-radius:12px}h1{font-size:32px}h2{margin-top:42px;border-bottom:2px solid #e4eaf1;padding-bottom:8px;color:#123a57}h3{color:#17546d}strong{color:#163f5c}table{border-collapse:collapse;width:100%;font-size:15px}th,td{padding:10px;border:1px solid #d5dce5;text-align:left;vertical-align:top}th{background:#edf3f8}.table{overflow:auto}figure{margin:26px 0}img{max-width:100%;height:auto;display:block;margin:auto}figcaption{font-size:14px;color:#536779}pre{white-space:pre;overflow:auto;background:#eef4f8;padding:22px;font:15px/1.8 Consolas,"Microsoft YaHei",monospace}blockquote{border-left:5px solid #2c8298;background:#f0f8fa;padding:14px 22px;margin:20px 0}code{background:#eef2f6;padding:2px 4px}@media(max-width:700px){main{margin:0;padding:20px}h1{font-size:26px}}@media print{body{background:white}main{padding:0}h2{break-after:avoid}figure,table{break-inside:avoid}}'
put('00_START_HERE.html','<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SailBoatRL 论文着力点与资产导读</title><style>'+style+'</style><main>'+''.join(out)+'</main></html>')
# Verify exact source identity, primary counts, raw archive integrity and member index.
a=json.loads((p/'evidence/analysis.json').read_text());assert [a['confirmation'][n]['safe'] for n in ['reactive','simple','sampled']]==[19,23,24];assert a['detailed_vs_simple']['common_safe_time_delta']['mean']==7
with zipfile.ZipFile(o/'06_reproduction/R13_REPRODUCTION_internal.zip') as z:
 assert z.testzip() is None;idx=json.loads(z.read('CONTENTS_SHA256.json'));assert len(idx)==183
 for name,h in idx.items():assert hashlib.sha256(z.read(name)).hexdigest()==h
 assert sum(n.endswith('trace.json') for n in z.namelist())==72
 for n in ['src/sailboat_routing/r8_planner.py','src/sailboat_routing/r8_model.py','src/sailboat_routing/r12_model.py','scripts/run_r8.py','scripts/run_r12.py']:assert n in z.namelist()
raw=o/'06_reproduction/R12_raw_results.tar.gz';assert hashlib.sha256(raw.read_bytes()).hexdigest()=='a0d1be6102bccf99a01c947f58d47e1721630dff47bd0e910bb2ab9d3c7ad618'
with tarfile.open(raw,'r:gz') as t:raw_members=len(t.getmembers())
manifest={'purpose':'Current-paper reading and reproducibility assets; not all historical project raw runs','new_experiments':0,'r12_raw_archive_members':raw_members,'inherited_bundle_indexed_members':183,'primary_traces':72,'files':[]}
for f in sorted(o.rglob('*')):
 if f.is_file() and f.name!='ASSET_MANIFEST.json':manifest['files'].append({'path':f.relative_to(o).as_posix(),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
put('ASSET_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2))
zpath=o.parent/'SailBoatRL_assets_and_paper_guide_20261007.zip'
with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as z:
 for f in sorted(o.rglob('*')):
  if f.is_file():z.write(f,(Path(o.name)/f.relative_to(o)).as_posix())
with zipfile.ZipFile(zpath) as z:assert z.testzip() is None
print(json.dumps({'archive':str(zpath),'bytes':zpath.stat().st_size,'sha256':hashlib.sha256(zpath.read_bytes()).hexdigest(),'files':len(manifest['files'])+1,'raw_members':raw_members},indent=2))
