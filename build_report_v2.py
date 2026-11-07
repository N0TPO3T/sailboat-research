import json,math
from pathlib import Path
R=Path(__file__).resolve().parents[1];D=R/'docs';O=R/'analysis_v2';g=json.loads((O/'group_summary.json').read_text());pairs=json.loads((O/'paired_summary.json').read_text());cases=json.loads((O/'selected_cases.json').read_text())
def group(v,cond,b='recovery_confirmation',st='all'):return next(x for x in g if x['batch']==b and x['variant']==v and x['condition']==cond and x['stratum']==st)
def pair(v,cond,b='recovery_confirmation'):return next(x for x in pairs if x['batch']==b and x['against']==v and x['condition']==cond)
def tab(batch,split=False):
 s='|条件|起始|方案|n|区内比例均值±SD|最长离区最大(s)|帆舵变化均值(rad)|最大横倾(°)|完整仿真|\n|---|---|---|---:|---:|---:|---:|---:|---:|\n'
 for x in g:
  if x['batch']!=batch or x['condition']=='all' or (x['stratum']=='all')==split:continue
  s+=f"|{x['condition']}|{x['stratum']}|{x['variant']}|{x['n']}|{100*x['inside_fraction_mean']:.2f}±{100*x['inside_fraction_std']:.2f}%|{x['max_outside_s_max']:.0f}|{x['actuator_variation_rad_mean']:.1f}|{x['max_heel_deg_max']:.1f}|{x['complete']}/{x['n']}|\n"
 return s
risk=group('release','low_speed_upwind');normal=group('release','ordinary');pc=pair('center','low_speed_upwind');pl=pair('luff_no_build','low_speed_upwind');pn=pair('center','ordinary');pb=pair('release_build','low_speed_upwind')
report=f'''# B研究报告：先恢复操纵能力，再继续区域观测

## 第一页：做了什么，得到什么

**问题。** 在当前风可测、固定帆船动力学与原执行器限制下，如何在有限区域持续观测，避免低速迎风状态造成长时间横漂？这是真正更换了任务，不是继续修改A的动态避碰guard。

**方法。** 最后采用传统中心引导，增加一个小型帆舵恢复模式：连续10个1Hz观测低速迎风后，向视风同侧最大放帆并转向下风；转入横风/下风半平面即恢复中心引导。没有训练、预测网络或新安全理论。开发发现主动背风帆和额外增速等待都不是必要部分，已删去。具体公式与执行时序见B_METHOD_NOTE.md。

**新证据。** 第二版预定义的12个低速迎风任务中，最终release全1200s区内占比平均 **{100*risk['inside_fraction_mean']:.2f}%**；相对普通center增加 **{100*pc['delta_occupancy_mean']:.2f}个百分点**（每任务平均增加{1200*pc['delta_occupancy_mean']:.1f}s区内采样时间），配对{pc['wins']}胜/{pc['ties']}平/{pc['losses']}负。相对结构匹配、同样立即返回的随视风放帆luff_no_build增加 **{100*pl['delta_occupancy_mean']:+.2f}个百分点**，{pl['wins']}胜/{pl['ties']}平/{pl['losses']}负。因此不能只引用弱center对照来说明方法价值。

**普通航行与代价。** 12普通任务release平均区内比例 **{100*normal['inside_fraction_mean']:.2f}%**，相对center **{100*pn['delta_occupancy_mean']:+.2f}个百分点**；风险/普通任务帆舵总角变化相对center分别 **{pc['delta_actuator_mean']:+.1f}/{pn['delta_actuator_mean']:+.1f}rad**。恢复可能先离开观测区；最长离区和最大横倾见主表。操纵角变化不是能耗。积分跑满也不等于全时驻留成功。

**定位。** 这是成熟引导与帆力管理在当前接口上的应用验证，最有证据的价值是解除一个可重复的低速工作域问题，而不是普遍击败已有驻留算法。保留A，B先作为独立证据与方法原型；是否独立组织或升级投稿由人类作者决定，不能把不同信息/任务的A和B数字拼成同一系统性能。

## 1. 选题和第一版负结果

最初保留持续驻留、失速恢复、按需高成本预测三个候选，原文与成本见PROBLEM_SELECTION.md。100m简单开发任务已有简单解，不能宣称驻留空白。50m四场开发中横风接力/中心追踪均100%，但第一版24场冻结确认暴露长期低速横漂：relay相对center平均−0.69个百分点（2胜13平9负），虽少6.8rad操纵，不能算能力问题已经解决。

第一版144回合（24×5+8×3）完整保留于runs/confirmation、runs/scale_check，报告/图表见docs/v1_validation。其后这些实例用于开发，不再称未见测试，也不与第二版合并报告“成功率”。舵符号、倒航帆分支、接力leg/q共用状态等更早原型错误单独记录并作废受影响成绩，不作为研究收益。

## 2. 区分性诊断和最小适配

稳定风confirmation_12在t100时u=0.138m/s、v=0.467m/s，之后趋向u≈0.125、v≈0.459，饱和舵仍无法获得所需偏航。重放100s历史逐项一致，无干预400s分支原始状态与原日志逐项一致。保持反馈、中立舵、反向舵均27.5%区内；改变帆加载可恢复，且同侧最大放帆不需要主动推到视风另一侧。原始分支与核对见recovery_diagnosis、recovery_sail_check、BRANCH_REPLAY_CHECK.json。

随后在4个真实失败和4个按ID固定的普通对照中比较仅下风参考、随视风放帆、同侧最大放帆、主动背风帆及阶段删除。最终release在失败4场达到100/100/100/95.67%，普通4场均100%；删除增速阶段后占比不降且操纵略少。该过程是机制检验与必要简化，没有扫描新测试阈值。

方法来源为Viel2018、Morge2022的传统模式/帆舵控制，Liu2025的保持运动/中心引导，以及Bink2026真实迎风停滞恢复的行为证据。没有复现其全部NMPC、RL、船型或理论。当前触发和退出状态机是本地适配，不能挂名为某篇论文的完整算法。

## 3. 冻结协议与比较口径

主源码SHA见FREEZE_V2.json；结构公平补证LUFF_MATCHED_EXTENSION.json在查看第二版结果前登记，另存源码/批次，只增加luff_no_build，不改主方法、实例或判分；实例先于方法最终评估写入FROZEN_V2_INSTANCES.json。24场由12风险/12普通组成，各8区内起始（半径0–10m）和4区外接入（75m）。风险只由初始物理状态定义：迎风±35°、纵速0/.25/.5m/s；普通为相对下风±110°、纵速.5/2/4m/s。基风向和位置角随机，stable/slow/fast循环，基风速8m/s。不是按这些新任务的输赢挑选。stable为恒定风；slow/fast的方向主波幅分别25°/45°，另有3°/6°平滑扰动，风速幅度为基值的12%/20%，主时间尺度1800/480s；t100后分别用60/30s平滑启用。它们是公开实现的合成场，不是真实天气预报。

全部6方案从同一真实状态开始，使用同一当前风/姿态/速度观测、4DOF动力学、量化与限速执行器。新方法不读取未来风或事后最优分支。源路径、初态、有限值、源码哈希、1200s终态和失败计数核验全部有机器记录（CONFIRMATION_INTEGRITY_V2.json）。

首要指标是1200个1Hz位置采样的区内比例；缺失尾部无信用。最长离区同为离散采样时长，最大半径包含t1200。任务才是样本单位，1200个时间点或多次触发不当独立任务；不为p值追加样本。低速风险分布是条件化验证，不等于真实海况发生率。

## 4. 第二版全部确认结果

{tab('recovery_confirmation')}

所有6种方案均保留。downwind只更改参考，不能因实现较简单就删除；luff是随视风放帆并随后增速的替代，luff_no_build给予它与最终方案同样的立即返回简化；release_build在最大放帆后保留1.5m/s增速等待，用来检验最终方案删除的阶段。release相对release_build在风险组占比差{100*pb['delta_occupancy_mean']:+.2f}个百分点、操纵差{pb['delta_actuator_mean']:+.1f}rad；这限定了“更简单”的实际代价，而不是只比较代码量。

风险组实际触发任务{risk['activated_tasks']}/{risk['n']}，普通组{normal['activated_tasks']}/{normal['n']}。激活并恢复的证据来自真实模式和执行轨迹，不能用模块没激活的普通成功来证明恢复机制。

## 5. 图中的有利与不利证据

- 图06保留全部24场区内比例和操纵量，区分风险/普通；完整数值见analysis_v2/all_results.csv。
- 图07按事前说明选相对center最大收益场景 **{cases['best_vs_center']}**，同时画全局与局部实际航迹，不把参考线当实际运动。
- 图08使用首个实际激活场景 **{cases['mechanism']}**，恢复从t={cases['recovery_start']}到{cases['recovery_end']}s，显示帆参考与实际限速响应、纵横速度和相对风角。
- 图09保留相对匹配luff_no_build最不利场景 **{cases['worst_vs_matched_luff']}**（占比同分时按操纵增加排序），不隐藏退化/代价。
- 图10是冻结100m尺度检查。

这些图是解释性的事后选例，全部任务仍纳入统计。相关曲线不能证明唯一因果；同历史控制分支提供的是所测试状态的局部因果区分。

## 6. 一项有限推广：区域尺度

{tab('recovery_scale')}

8个100m新任务各4风险/4普通，组内2内/2外；区外初距150m。比较center、luff、luff_no_build、release，控制公式、触发/退出阈值、风型和时长均未改变。支持范围仅为这个尺度变化，不外推海流、波浪、传感误差、其他船型或实船。

## 7. 代价和未解决边界

首先，恢复会放弃一段指向中心的运动，不能承诺全时留区；保护指标与最差案例已给出。其次，继续观测需实际航行，较停滞失败通常增加操纵量，不能把它换算为电能。第三，当前模型直接定位带符号帆角；同侧放帆较主动背风帆弱，但没有建立帆索、帆布或真实执行器的可实现性。第四，使用理想当前风与完整本船状态，不是无风输入方法。第五，未进行实际计算/传感延迟闭环研究，不称实时安全系统。

最大放帆是原执行器限制内的命令，没有放宽物理或评价边界。所用简化反馈、触发参数和初始条件族均有范围限制，不能泛称“传统方法无法恢复”或“所有帆船驻留已解决”。更完整的NMPC/学习控制是未来外部比较，当前不能声称优于它们。

## 8. 复现、资源和材料

所有旧失败、开发、分支和两版确认保留。RESULTS_INDEX.json标注有效性；RESOURCE_LEDGER.json记录实际CPU、墙钟和0GPU/无训练事实。最多4个单数值线程实验worker，共享截止不重置。scripts/station_recovery.py与configs/recovery_confirmation.json、recovery_scale.json可运行，重跑须使用新batch，不能覆盖原输出。分析脚本analyze_recovery.py不推进物理环境。

研究全文/图表、离线HTML、源码/配置、原始结果、独立三审及作者回应打包在B_RESEARCH_preview.zip。文献原文仅作阅读依据，下载源URL集中列出；不新增开源许可证或假称模型公开发布。旧A不改变，最终稿件选择由人类作者完成。

## 附：风险/普通内的起始条件细分

{tab('recovery_confirmation',True)}
'''
(D/'B_RESEARCH_REPORT.md').write_text(report,encoding='utf-8')
# Put actual final result near start of method note; retain development figures explicitly labelled.
p=D/'B_METHOD_NOTE.md';s=p.read_text();needle='**效果。**';a=s.index(needle);b=s.index('\n\n',a)
s=s[:a]+f"**效果。** 第二版冻结12风险任务平均区内{100*risk['inside_fraction_mean']:.2f}%，相对center增加{100*pc['delta_occupancy_mean']:.2f}个百分点，相对luff为{100*pl['delta_occupancy_mean']:+.2f}个百分点；12普通任务平均{100*normal['inside_fraction_mean']:.2f}%，相对center为{100*pn['delta_occupancy_mean']:+.2f}个百分点。所有任务与不利例均保留。开发中的100/100/100/95.67%仅解释方案选择，不冒充新确认。"+s[b:]
a=cases['activation_record'];raw=a['raw'];s+=f"\n## 一个新确认中的真实决策\n\n{cases['mechanism']}在t={cases['recovery_start']}s：纵速{raw[4]:.3f}m/s、横速{raw[5]:.3f}m/s，船首{math.degrees(raw[3]):.2f}°、当前风吹向{math.degrees(a['wind']):.2f}°，低速迎风计数{a['low_count']}。控制器进入{a['mode']}，帆参考{math.degrees(a['sail_ref_rad']):.1f}°，当时实际帆角仅{math.degrees(raw[8]):.1f}°；图08显示原限速接口如何逐步执行。t={cases['recovery_end']}s退出恢复。记录来源为analysis_v2/selected_cases.json及对应原始轨迹；不是人工挑选未来最优动作。\n"
p.write_text(s,encoding='utf-8');print(report[:1800])
