"""Generate R9 human-readable reports from audited retained data."""
import json,sys,csv
from pathlib import Path
R=Path(sys.argv[1]).resolve();P=Path(__file__).resolve().parents[1]
S=json.loads((R/'analysis.json').read_text());T=json.loads((R/'timing_analysis.json').read_text());rows=list(csv.DictReader((R/'all_rows.csv').open()));cfg=json.loads((R/'frozen_configs.json').read_text())
def fmt(x):return '—' if x is None else f'{x:.2f}' if isinstance(x,float) else str(x)
def table(batch):
 out='| 方法 | 安全/总数 | 动态侵入 | 静态侵入 | 实体碰撞 | 相对reactive新增/损失 | 共同安全航时差均值/中位/P95/最大(s) |\n|---|---:|---:|---:|---:|---:|---|\n'
 for v,a in S[batch]['methods'].items():
  c=S[batch]['comparisons'].get(v);pair='—' if c is None or not c['n'] else f"{c['gains']}/{c['losses']}";dt='—' if c is None else '/'.join(fmt(c[k]) for k in ['dt_mean','dt_median','dt_p95','dt_max'])+f" (n={c['common_safe']})"
  out+=f"|{v}|{a['safe']}/{a['n']}|{a['dynamic']}|{a['static']}|{a['collision']}|{pair}|{dt}|\n"
 return out
def timing_table():
 out='| 批次/方法 | 重规划n | 墙钟P50/P95/max(s) | 观测到应用P50/P95/max(s) | 控制tick n/max/超过1s | 结果状态 |\n|---|---:|---|---|---|---|\n'
 for k,g in T.items():
  if k.split('/')[0] not in ['confirmation','long_confirmation','sensitivity','static_regression']:continue
  w=g['walls'];a=g['ages'];c=g['ticks'];ff=lambda d:'/'.join(fmt(d.get(x)) for x in ['p50','p95','maximum'])
  out+=f"|{k}|{w['n']}|{ff(w)}|{ff(a)}|{c['n']}/{fmt(c.get('maximum'))}/{c.get('over1',0)}|{g['statuses']}|\n"
 return out
prof=json.loads((R/'profile_summary.json').read_text());pt='| 历史长度 | 候选数 | 原实现s | 优化s | 最大航迹差m |\n|---:|---:|---:|---:|---:|\n'
for z in sorted(prof,key=lambda x:x['history']):pt+=f"|{z['history']}|{z['candidates']}|{z['old']:.3f}|{z['optimized']:.3f}|{z['difference']}|\n"
case=json.loads((R/'development2/confirm_mixed_7__slot_feedback60/trace.json').read_text());ev=next(x for x in case['timeline'] if x['observation_time']==150);pred=next(x for x in case['predictions'] if x['time']==150)
ct='| 候选 | 目标坐标m | 预测最小余量m | 代价m | 可行 |\n|---|---|---:|---:|---|\n'
for c in pred['candidates']:ct+=f"|{c['name']}|({c['target'][0]:.2f},{c['target'][1]:.2f})|{c['prediction']['min_margin']:.3f}|{c['cost']:.3f}|{c['feasible']}|\n"
method=fr"""# R9 方法说明：与计算等待一致的航迹点预测和交付

本轮改高层的时间协议和历史重编码实现，没有训练或更换SAC-LSTM。目标是检验R8候选执行预测在计算期间仍航行时是否有用。R6障碍输入适配的条件性证据、R8理想交付收益仍保留；旧结果不能替代本轮时间验证。

## 采用什么、为什么改

沿用[Wilkie、van den Berg、Manocha的GVO（IROS2009）](https://gamma.cs.unc.edu/NHRVO/WilkieIROS09.pdf) §IV式(2)(3)的控制条件轨迹与同时刻最小距离思想。位置参考及其保持/恢复协议替代车辆控制变量；通过固定学习控制器和独立已知动力学产生预测运动。不是完整BC-MPC，不继承安全定理。

六个真实状态的profile显示动力学积分、路线搜索和历史Actor重放均有开销。首先只删除重放中不用的历史动作输出头，保留归一化、全部真实历史、逐步FC/LSTM、h/c及注意力窗口。六状态所有已评估候选航迹逐点一致；四个完整理想交付回合的实际状态和动作也与R8逐值一致（full_replay_equivalence.json）。这不代表任意环境的形式等价证明。旧状态最长单决策从43.64降至30.77秒，仍不能当瞬时计算。

{pt}

初次新模型构造另计，插桩与非插桩分开。cProfile有明显额外开销，嵌套累计时间不能相加成比例。计算器使用AMD EPYC7V12主机，4个单线程回合进程、无GPU。热点原表见profile.json。

## 输入和可用信息

正式输入仅有当前本船状态、实际已执行命令、真实带时间/身份的目标观测、当前参考、静态地图和管理状态。未知风由近期已发生运动拟合，预测时固定局部风；目标按当前地速外推。预测器不接收真实未来风、目标转向表、真实环境副本或未来轨迹。历史重编码使用每个过去时刻当时的目标观测，不用当前位置回填。

## 明确的闭环时间协议

```mermaid
flowchart LR
 O[时刻t真实观测与历史] --> C[计算候选及等待阶段预测]
 O --> W[保持旧位置参考]
 W --> A[每秒新观测重新计算帆舵动作]
 A --> M[本船 目标船 风时钟推进]
 M --> A
 C --> Q{{墙钟不超过25秒 且结果未过期}}
 Q -->|是| D[t+26应用参考]
 Q -->|否| X[丢弃结果 继续反馈]
 D --> F[避让参考保持60秒 普通参考恢复接力]
 F --> O
```

一次只允许一个待决计划。离线事件模拟假设规划执行器和反馈执行器独立；没有在每个实验进程另开并行求解线程。真实测得规划墙钟决定ready时间；主方案固定B=25秒交付时隙，ready前不能使用结果。快于25秒也等到时隙结束。超过时隙则等计算真正结束后丢弃；超过60秒参考年龄也丢弃。任务结束取消待决结果。ready、可交付、实际应用、同参考交付分别记录。

时刻t先算实际动作a_t，再开始快照计算。等待t至t+25期间，每秒依据真实新状态和旧位置参考重算动作，绝不重复旧帆舵增量。t+25释放结果，旧参考下已算的动作仍执行到t+26，然后才应用新参考。保持钟从t+26开始；下一次高层请求最早t+86。低层始终按原实际帆船动力学执行，位置参考不等于瞬时航向。

若选普通候选，应用后立即继续每秒AvailabilityRelay反馈；若选避让候选，则保持该参考60秒。预测H=86秒覆盖同样的26秒首次生效延迟和后续60秒。观察范围1000m、预测触发范围600m、侧向参考350m、guard30m沿用开发起点。B=25是初始工程时隙；首轮全参考保持开发最大19.15秒，等待一致版开发最大16.77秒，随后冻结；没有根据新集反调。不称最优值或硬实时界。

## 评价公式及退出

候选为普通接力、继续当前参考、相对普通目标方向±45°/±90°参考。每个候选在同一观测历史上运行同一低层；等待阶段都保持旧参考。令p_c(k)为候选预测本船位置，q_j(k)为当前地速外推位置，动态余量为同一秒相对线段的最小距离减85m，同时检查静态实体边界外60m。m(c)取整个预测有效区间最小值。

可行要求完整有效预测且m(c)≥30m。普通候选可行则直接采用，否则选可行候选中：

J(c)=终端距原任务目标距离+20·1[非普通]+10·1[新侧向参考]

最小者。全候选不满足guard时，选完整有效预测中余量最大者；无完整预测则继续当前参考。这是尽力退化规则，不是安全保证。实际判分仍要求动态余量>0、静态余量>0和原10m目标到达，未放宽安全标准。临时终点处理公平复用AvailabilityRelay，并单独报告其代价。

## 一个真实决策及机制边界

旧开发mixed7，t=150，本船(481.063,7.829)m，主方案和忽略等待消融直到176秒状态一致。实测计算{ev['measured_wall']:.3f}秒，ready={ev['plan_ready']:.3f}；25秒时隙结束后，于176秒真正应用+90°参考，首个不同实际状态出现在177秒。

{ct}

同状态消融把未来预测当作立即交付，普通候选余量88.689m，因此不干预；等待一致的预测为−1.032m，改选+90°，预测余量43.541m。完整任务主方案524秒、安全余量{case['row']['min_dynamic_margin']:.3f}m；消融219秒NoRoute并侵入−2.032m。原表mechanism_case.json保存精确值。这个对照支持该状态下等待建模影响了实际选择，不能证明所有场景都需要该模块。

mixed3中两组全轨迹相同、全为普通候选，收益来自等待期间冻结参考更新的协议效应；不将它归为预测避让。endpoint_5主方案777秒对reactive317秒，增加460秒，仍是显著误干预/任务交互代价。冻结短集中主方案与reactive均安全、没有新增安全例；仍有5次全候选低于guard的尽力选择（最低5.953m）。更重要的是slot30下mixed3的101秒预测余量82.692m、实际共同窗口却侵入−0.949m，最大位置误差140.048m。因此等待协议一致并不保证预测准确或安全，不能把30m当作误差上界。新长程和转向验证见研究报告。

## 运行与边界

配置：{R.relative_to(P)}/frozen_configs.json。实际代码r9_timing.py、r9_planner.py、r9_model.py、r9_replay.py与scripts/run_r9.py；公共动力学、安全判分、R8源文件均保留。独立规划资源是声明部署条件，4回合吞吐不等于部署实时保证；控制tick包括重编码/编码、当前Actor和普通规划，超1秒情况见报告。

恒速目标、短期风拟合、有限候选、60秒避让保持和25秒等待均有边界。没有多船规则系统、真实感知噪声或硬实时/安全理论证明。观察到更快的计算可能改变交付时刻及轨迹，不能以同状态数值等价推出闭环安全改善。
"""
(P/'docs/R9_METHOD_NOTE.md').write_text(method)
report=fr"""# R9 研究报告：计算等待进入真实闭环后的动态避碰

运行根：`{R.relative_to(P)}`。冻结来源：`freeze.json`；原始代码基点f75130d，R9源文件内容哈希另存。未训练、GPU0；使用已有环境，最多4单线程CPU回合。未修改历史结论、上游资产、真实判据或R3英文底稿。

冻结短实例中，主方案和reactive均为{S['confirmation']['methods']['main']['safe']}/{S['confirmation']['methods']['main']['n']}安全完成；主方案没有新增安全案例，共同安全航时平均增加{S['confirmation']['comparisons']['main']['dt_mean']:.2f}秒、最大增加{S['confirmation']['comparisons']['main']['dt_max']}秒。这一结果不支持普遍优于reactive。\n\n新3km实例中reactive485秒侵入后NoRoute，主方案909秒安全完成，最小动态余量51.706m；新5km共同安全，主方案增加32秒。等待从25增至30秒时，旧mixed3却在184秒侵入−0.949m。这些结果支持条件性收益，不支持普遍延迟鲁棒性。\n\n本轮得到的是**时间协议影响避让选择与安全结果的条件性证据**。不是“加速即可安全”，也不是动态避碰已完成。方法、公式、时序和真实数值例见R9_METHOD_NOTE.md。模型采用GVO控制条件预测思想，增加与交付等待一致的预测；主方案计算时隙25秒，参考在观测后26秒生效。

## 研究过程和淘汰理由

1. 六个真实短/长历史状态定位开销。只省略历史重放的旧动作头，候选航迹最大差0；积分与路线搜索仍重要，不能声称瓶颈只有历史重编码。
2. 原R8理想15秒方案、实测延迟15/60秒与全参考固定保持对照。全参考保持在mixed3用了838秒；没有采用它。
3. 普通航行恢复接力、只保持避让参考。旧开发四例安全399/524/298/777秒；fast60在mixed6到达但缓冲侵入约−42.18m，fast15在mixed3侵入约−27.35m。更快交付改变闭环分支，不自动带来收益。
4. ignore_wait消融保留实际slot25与H86，但预测忽略等待。mixed7从相同150秒输入产生不同选择并失败；mixed3/mixed6/endpoint5与主方案无差别，机制结论局限明确。
5. 冻结方法、配置及新实例生成条件后才开始确认；未按胜负筛种或修改参数。12个短实例加3/5km各一个，另保留旧静态和激活后转向/额外延迟验证。源场景是比较单位，决策窗/候选不是独立样本。

初版development的reactive漏Availability配置、控制tick及应用日志口径不完整。旧产物保留，公平reactive在development2补跑；最终时序统计使用修正批次。所有正式确认配置显式共享终点处理。审查仅same-family/provisional，不评分，不替代结果。

## 对照的准确含义

reactive为共享终点处理的普通接力，正常参考下一秒生效。ideal15沿用R8理想计算及选择时刻保持钟，只作理想参照。delayed15沿用R8的H60候选预测，却用一个pending槽、实测墙钟向上取整后再下一秒应用；等待旧参考，保持及下一次请求钟从应用时刻起算。fast60在此协议中使用优化重放和60秒周期。两者预测仍按理想首次交付计算，属于未补偿延迟对照。它们不只是给R8总航时加秒数，也不是“只改一个时延”的纯消融。

主方案同时改为固定25秒时隙、H86和等待一致预测，因此机制隔离依赖同H86/同实际slot25的ignore_wait对照，不能把与ideal15的所有差别都归因于等待预测。所有实际控制器共享数值核验后的历史重放优化；原R8预测器对照仍保留其原计算成本。

## 冻结短实例

{table('confirmation')}

预定义类别为途中混合压力4、普通横穿2、非冲突2、终点2、错时2；全部保留，不按模块激活筛选。逐类结果family_analysis.json；新增/损失场景名paired_identities.json。每行安全完成需要到达且全过程安全；失败提前停止不当作更快。全样本失败惩罚航时另按原1.8s/m上限统计。

## 3/5km与静态回归

{table('long_confirmation')}

{table('static_regression')}

两条长程是预定义横穿实例，不能外推所有3/5km路线或长程泛化；实际本船和目标同步航迹见图01。无动态目标的静态回归用于检查通用实现影响，不作为避碰收益。

## 已激活后的转向和交付变化

{table('sensitivity')}

已知mixed7在参考应用176秒后7秒，即183秒，目标转向+15°；该未来转向表只由真实环境读取。不能用未激活但成功替代该验证。slot30在旧mixed3/7同时把声明等待及预测等待增加5秒，H91；不是新参数搜索。主方案确在176秒激活，转向试验530秒安全完成，余量45.158m。slot30的mixed7也在186秒实际应用turn−45并463秒安全完成；mixed3没有非普通选择且184秒侵入，属于普通协议的时延敏感性，不能冒充激活后避让失败。slot30的mixed3在101秒所选普通预测为正余量82.692m，但83秒实际共同窗口侵入−0.949m、最大位置误差140.048m。这是等待一致模型的“预测安全、实际侵入”反例，同时限制预测可靠性；当前证据不能把根因单独归为风拟合。精确记录见timeline与trace。

## 计算与交付

{timing_table()}

冻结短集总CPU时间：主方案410.718s、R8实测延迟15秒765.601s、reactive124.754s；主方案减少总预测次数，但单次P95更长，固定26秒参考年龄也更大。不能将总CPU下降写成每次响应更快。\n\n墙钟为非插桩高层预测服务；ideal15也有真实预测计算，其交付年龄留空表示未按实测计算延迟执行，而非没有计算；年龄从观测到实际参考/协议生效，包含整数边界。普通规划、历史编码/重放、当前Actor纳入控制tick。低层超1秒只按实测样本报告；即使样本全通过，也不构成最坏执行时间保证。ideal15的零计算延迟是参照，不能用它证明部署可行。

修正后的99回合日志通过实际同步距离复算、无提前应用、等待期参考保持和控制tick覆盖检查（final_audit.json）；其中观测到的控制tick最大0.645秒。初版20回合保留但不混入此统计。\n\n事件模拟声明规划与反馈执行器独立，计算期间本船、目标、风时钟照常按物理时间推进；等待期每秒重算帆舵动作。不是在最终航时加计算秒数。固定时隙不使用过早结果，超预算/过期结果丢弃；实际丢弃数在上表。正式闭环没有触发deadline/age超期丢弃，超期仅在确定性队列逻辑测试中覆盖，不能据此证明超预算时的航行安全。硬件负载会改变实测延迟方案的轨迹，复跑必须报告新测量条件，不能承诺逐位重复。

## 机制、代价和不支持的结论

最强开发机制对照为mixed7同状态150秒：普通方案预测余量从忽略等待的88.689m变为等待一致的−1.032m，选择+90°后完整安全；两组首个实际状态差异177秒。具体候选表与ready/apply见方法说明及图02。

mixed3仅普通候选也受等待冻结参考的影响，不能把其改善全部归于预测。endpoint5仍额外460秒；图03保留该不利航迹及fast60的真实侵入，图05单独展示主方法slot30的预测安全/实际侵入反例。新实例共同安全航时和所有失败在图04同时呈现；不将成功率或总回合数当作研究结论。

预测误差只在真实执行共同区间比较，预测不是实际航迹；新短主方案48个接受窗口中8个不足86秒，不能当完整H86验证；普通大间距案例也有63.246m最大共同窗位置误差。原始timing_analysis.json保留每窗长度和误差。恒速预测无法预知转向，拟合风并非真风；每个候选不保证实际可达。新短主方案实际有5次全候选不满足30m guard，仍走尽力退化分支，最低选中预测余量5.953m；不能说规划始终满足guard。30m为规划guard，真实安全标准仍为0m；任何guard退化或实际负余量均保留。

额外5秒等待的反例还表明：预测匹配控制协议仍不足以保证长窗口预测准确，不能将guard30m解释为误差上界。当前证据不支持硬实时、一般安全保证、完整COLREGs、真实传感部署或训练改进。还存在事件计数的轻量记账边界（例如丢弃后last_selected）；执行收益统计使用实际轨迹和接受timeline，不能只依赖enter计数。

## 论文定位及复现

建议将动态部分作为**有明确计算/交付假设的扩展验证**，不作为本篇CCDC投稿不可缺少的主安全结论。可写贡献是接口和时间协议的实证适配，以及同状态消融揭示的预测/执行不一致；不宣称提出新的GVO理论或已达到录用条件。另存paper/ccdc/R9_POSITIONING.md，R3底稿不改。

可复现命令（在已核实的服务器环境）：

```bash
.venv/bin/python scripts/reproduce_r9.py --manifest {R.relative_to(P)}/confirmation.json --out runs/r9_reproduction_new --variant main
.venv/bin/python scripts/analyze_r9.py {R.relative_to(P)}
.venv/bin/python scripts/plot_r9.py {R.relative_to(P)}
.venv/bin/python scripts/test_r9_timing.py
```

reproduce使用新的输出目录并保留旧日志，默认最多4CPU、4小时，绝不覆盖原运行根。原manifest/配置、trace/row、源码快照、freeze哈希、profile及审查证据均在运行根。all_rows.csv、family_analysis.json、paired_identities.json、timing_analysis.json和mechanism_case.json是原始表索引；每个回合trace包含真实目标历史、实际动作、参考变更和预测。离线gallery.html及PNG/SVG在同根；交付包R9_TIMING_preview.zip另含报告和索引，原始日志另归档。
"""
(P/'docs/R9_RESEARCH_REPORT.md').write_text(report.replace(chr(92)+'n',chr(10)))
(P/'paper/ccdc/R9_POSITIONING.md').write_text("""# R9 positioning update (R3 draft preserved)

Position the dynamic component as a bounded extension study of executable waypoint supervision under computation and delivery delay. The core empirical question is whether candidate-conditioned predictions retain avoidance benefits when the vessel keeps moving while planning.

Use Generalized Velocity Obstacles (Wilkie, van den Berg and Manocha, IROS2009, DOI10.1109/IROS.2009.5354175) as the source of control-conditioned trajectory evaluation. Our reference/hold/feedback and fixed delivery slot are adaptations to a learned sailboat controller, not a new safety theorem or a reproduction of full BC-MPC.

Report ideal and delayed R8 separately. A recurrence-only replay optimization preserves the saved-state candidate trajectories but can still change closed-loop outcomes through delivery timing. The strongest developmental contrast uses identical observed history at150s in mixed7: accounting for waiting changes the nominal prediction from88.689m to−1.032m and selects a different maneuver. Mixed3 is instead a scheduling effect with no nonnominal selection. Do not combine these into one unsupported causal claim.

State the independent planner/feedback executor assumption,25s slot,26s reference age,60s avoidance hold,86s horizon, deadline drops, controller-tick measurements, and the remaining endpoint777vs317s cost. Include every frozen win and loss from docs/R9_RESEARCH_REPORT.md, the two long instances, and activated turn/delay checks. Do not claim hard real time, broad generalization, COLREGs completeness or deployment readiness.

The frozen12short instances add no safety gain over reactive and incur57.42s mean extra time. One new3km case retains an avoidance gain, while the5km case costs32s. A30s-slot sensitivity has a false-safe prediction (82.692m predicted versus−0.949m actual common-window margin); report it explicitly, together with5guard fallback selections on the short set.

Recommendation: retain this as extension evidence and a failure-aware discussion, not a necessary condition for the current CCDC submission. No claim about acceptance follows from this round. R3 draft.md is unchanged.
""")
print('R9 reports generated; require raw-data/claim review before delivery')
