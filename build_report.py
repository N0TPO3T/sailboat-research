import json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[1];D=R/'docs';D.mkdir(exist_ok=True)
g=json.loads((R/'analysis/group_summary.json').read_text());p=json.loads((R/'analysis/paired_summary.json').read_text());cases=json.loads((R/'analysis/selected_cases.json').read_text())
def table(batch):
 s='|起始条件|方案|n|区内比例均值±样本SD|最长离区最大值(s)|帆舵变化均值(rad)|完整仿真|\n|---|---|---:|---:|---:|---:|---:|\n'
 for x in g:
  if x['batch']!=batch or x['stratum']=='all':continue
  s+=f"|{x['stratum']}|{x['variant']}|{x['n']}|{100*x['inside_fraction_mean']:.2f}±{100*x['inside_fraction_std']:.2f}%|{x['max_outside_s_max']:.0f}|{x['actuator_variation_rad_mean']:.1f}|{x['complete']}/{x['n']}|\n"
 return s
pair=next(x for x in p if x['batch']=='confirmation' and x['against']=='center' and x['stratum']=='all')
report=f'''# B 研究报告：有限区域观测的成熟控制选型

## 结论

本轮实际换了任务：由A线的连续航行/动态避碰，转为当前风可测条件下的区域持续观测。实现并冻结了无需训练的横风双点接力，保留中心追踪强基线、两个阶段适配及禁航区投影消融。不是新RL、NMPC或新安全理论。

24场新确认中，相对center，relay区内比例配对均值差为 **{100*pair['delta_occupancy_mean']:+.2f}个百分点**；逐任务 **{pair['wins']}胜/{pair['ties']}平/{pair['losses']}负**，帆舵累计角变化平均差 **{pair['delta_actuator_mean']:+.1f}rad**。不能据开发集全圆内结果称接力普遍更好。所有任务均保留，表中完整仿真仅代表跑满1200s，不代表全时驻留成功。

建议保留A独立完成作者确认；B作为成熟方法适配与边界的独立研究证据，是否另行组织由人类决定。本轮没有把不同任务成绩拼成同一系统性能，也没有自动替换A。

## 问题、版本和公平性

完整问题卡见PROBLEM_SELECTION.md，方法与来源见B_METHOD_NOTE.md、LITERATURE_AND_ADAPTATION.md。先后排除了舵符号、倒航帆分支、接力端点/换舷共用状态等原型错误；旧错误成绩不作为算法贡献。冻结文件FREEZE.json记录时间、源码SHA和全部新实例；确认期间未改算法或配置。

共同低层为常规PD航向反馈、视风帆角及实际速率受限执行器；所有方法使用同一继承4DOF动力学，当前风/位置/姿态/速度条件相同。旧A的SAC-LSTM没有加载。内部圈不同是被比较的引导机制差异，不能把phase_small叫原Viel全方法复现。较大内部圈也不构成原文假设在本船成立的证明。

50m主确认24任务，16从0–10m内开始，8从75m接入；初始航向和基风向均匀随机，速度0/0.5/2/4m/s循环，stable/slow/fast风型循环，基风速8m/s。生成器seed202610708，具体列表已在结果前冻结。每任务1200s、1Hz；主指标分母固定1200，提前失败剩余时间无区内信用。最长离区是1s采样时长，不是连续安全证明。最大半径包含1200s终态。实际角变化不是能耗。

## 完整确认结果

{table('confirmation')}

同任务配对原表见analysis/all_results.csv；所有差值见analysis/paired_summary.json。样本单位是独立任务而不是1200个时间点；没有以海量窗口做显著性检验。inside与entry分层展示，因为接入任务有不可避免的初始离区。合并均值不能替代分层事实。

## 真实案例和机制边界

图02展示relay相对center区内占比最不利场景 **{cases['worst_vs_center']}**；图03展示相对phase_small最有利场景 **{cases['best_vs_phase']}**。两者按提前公布的argmin/argmax规则从完成数据中选作解释，不作为筛选测试的依据，其余任务全部在图01与CSV。

无禁航投影消融只隔离可航航向约束：若直接指向逆风目标恶化，说明常规几何约束必要，不是新增机制或概率安全保证。低速比例与离区共现是诊断相关性，不能单凭曲线宣称低速是唯一原因。

## 有限推广检查

{table('scale_check')}

R100的8任务另用冻结新种子，4从区内/4从150m接入，仅relay、center和消融。除半径与对应初始距离外，信息、动力学、控制器比例和时长分布相同。只支持这一尺度变化，不外推到海流、波浪、感知噪声、实船或任意船型。

## 成本、失败与停止判断

没有训练或占用GPU。各回合CPU/墙钟与来源路径保存在原始JSON，累计资源见RESOURCE_LEDGER.json。最多4个单数值线程实验worker；计算延迟没有嵌入1s物理时钟，本轮不声称实时系统。未耗尽24h预算不是证据不足时追加场景的理由。

本轮不存在“必须超过基线”的结论。成熟简单方案解决开发问题后，完成了冻结的新实例和尺度检查；不再为追求新模块无界收缩半径或搜索参数。尚缺现实传感模型、外部平台与实船确认；若要形成独立投稿，先明确应用需求和相对成熟全系统的价值，不能直接把本报告包装成全面算法优越性。

## 交付与复现

- configs/confirmation.json、configs/scale_check.json：冻结配置。
- scripts/station.py：实际控制/执行/记录入口，源码哈希见FREEZE.json。
- runs/confirmation、runs/scale_check：完整原始轨迹，含失败和末态。
- analysis/all_results.csv、group_summary.json、paired_summary.json、selected_cases.json：完整数值。
- figures/01–05与analysis/gallery.html：真实日志图与离线图集。
- RESULTS_INDEX.json：历史开发有效性、批次源码/文件哈希和资源记录。
- reviews/：真实独立审查，单独交付，不用模拟评分替代结果。

运行命令见README.md。由于输出保护，复跑须复制配置并使用新的batch名。旧结果不覆盖，A资产不改变。
'''
(D/'B_RESEARCH_REPORT.md').write_text(report,encoding='utf-8')
# exact logged initial decision: no dynamics replay, reconstruct geometric endpoint only
import math
z=json.loads((R/'runs/confirmation/confirmation_00_relay__shuttle.json').read_text());t=z['trace'][0];j=z['result']['job'];w=t['wind'];pos=t['raw'][:2];b=[math.cos(w+math.pi/2),math.sin(w+math.pi/2)];target=[.5*j['radius']*x for x in b];dist=math.dist(pos,target)
if dist<.2*j['radius']:target=[-x for x in target]
example=f"\n## 一个真实决策\n\n冻结confirmation_00在t=0：位置({pos[0]:.2f},{pos[1]:.2f})m，当前风吹向{math.degrees(w):.2f}°，船首{math.degrees(t['raw'][3]):.2f}°，初速{t['raw'][4]:.2f}m/s。接力端点按当前横风计算为({target[0]:.2f},{target[1]:.2f})m，切点门限10m。记录的最终参考航向为{math.degrees(t['desired_heading']):.2f}°，归一化帆/舵增量命令为{t['command']}。该命令随后才进入实际动力学，不能把参考方向当作瞬时运动。原始证据：runs/confirmation/confirmation_00_relay__shuttle.json的trace[0]。\n"
pth=D/'B_METHOD_NOTE.md';s=pth.read_text();s=s.replace('**效果与代价。** 待冻结新任务的全量配对结果；开发4场接力与中心同为100%区内，实际帆舵累计变化均值122.6和131.6rad。该差异不能自动推广到新实例，也不能称能耗节省，帆舵角变化不是电能测量。',f"**效果与代价。** 新确认24场相对中心追踪，接力区内占比平均{100*pair['delta_occupancy_mean']:+.2f}个百分点，{pair['wins']}胜/{pair['ties']}平/{pair['losses']}负，实际帆舵累计变化平均{pair['delta_actuator_mean']:+.1f}rad。开发集的并列100%不能代替这一结果。帆舵角变化不是能耗测量；分工况完整数值见研究报告。")
s=s.replace('（冻结版本，结果待回填）','');pth.write_text(s+example,encoding='utf-8')
print(report[:1100])
