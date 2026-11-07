from pathlib import Path
import shutil,json,hashlib,datetime
r=Path(r'C:/Users/74095/hs/SailBoat/sailboat-routing-v0');d=r/'docs/ab_20261007';snap=d/'reconciliation';snap.mkdir(exist_ok=True)
for n in ['PROJECT_STATE.md','CURRENT_PLAN.md','PROJECT_MEMORY.md','docs/HANDOFF.md']:
 f=r/n;target=snap/('local_'+f.name+'.before');assert not target.exists();shutil.copy2(f,target)
budget={'start_utc':'2026-10-07T15:13:40Z','deadline_utc':'2026-10-08T15:13:40Z','max_wall_hours':24,'max_experiment_processes':4,'numerical_threads_per_process':1,'allocation':{'A_experiment_workers':0,'B_experiment_workers':4},'gpu':{'maximum_devices':1,'maximum_gpu_hours':12,'device_authorization':'not yet verified; use only after actual authorization confirmed if training needed'},'A_directory':'paper/ccdc/track_A_submit','B_server_directory':'/home/ot/Students/hs/sailboat-track-b','old_assets_read_only':True,'push_or_submission':False}
(d/'SHARED_BUDGET.json').write_text(json.dumps(budget,ensure_ascii=False,indent=2),encoding='utf-8')
plan='''# Current Plan

AB并行工作包已授权，完整任务见docs/prompt/SailBoatRL_AB_Parallel_Paper_and_Problem_Discovery.md。

- A：在paper/ccdc/track_A_submit独立完成R13作者修订、分工况/收益代价表达及模板PDF，不等B，不启动新导航实验。
- B：独立/home/ot/Students/hs/sailboat-track-b，从最多3个问题候选的文献与合理基线开始，至少1项换任务，实际推进原型/开发/消融/确认与真实图表。
- 总共享预算与截止时间见docs/ab_20261007/SHARED_BUDGET.json：24h、最多4个单线程实验进程（分配B）；GPU实际授权未核实，不当作永久禁令，确需时集中确认。
- 协调者更新根交接；A/B只更新自己状态，不争写根文件。旧代码/权重/日志只读，本机和服务器未提交修改保留，不自动push/投稿。
- R13已有研究/评审提供许可保持有效；18D与期刊14D的区别必须保留。A不能使用B的新成绩替代当前证据。
- 原本机R6状态为滞后记录，原文完整保存在docs/ab_20261007/reconciliation；不再作为当前限制。
'''
(r/'CURRENT_PLAN.md').write_text(plan,encoding='utf-8');(d/'CURRENT_PLAN_SHARED.md').write_text(plan,encoding='utf-8')
f=r/'PROJECT_STATE.md';s=f.read_text(encoding='utf-8');intro='''## 当前已核对事实（AB续办，2026-10-07）
- 服务器实际稿件已到R13，round04原A/B/C均模拟Accept；这是内部意见，非正式录用。主证据19/23/24，联合压力3/7/8，其余16场均成功；范围为理想计算单船会遇仿真。
- 当前授权改为独立A稿件与B问题研究并行，入口CURRENT_PLAN.md和docs/ab_20261007/SHARED_BUDGET.json。B允许改变任务、信息、控制器和训练，不继承历史阶段禁令。
- A/B目录分离，旧科学资产及未提交代码不修改。Chao Yang继承资产的研究使用和评审材料提供权限已由用户确认。
- 本文件后续R1—R6段落为本机历史快照，最新论文事实见paper/ccdc/r13_revision。已保留本次同步前原文，未reset/clean/pull覆盖。

''';f.write_text(s.replace('# Project State\n','# Project State\n\n'+intro,1),encoding='utf-8')
f=r/'docs/HANDOFF.md';f.write_text(f.read_text(encoding='utf-8')+'\n## AB并行任务启动 — 2026-10-07\n- A独立稿件paper/ccdc/track_A_submit；B独立服务器/home/ot/Students/hs/sailboat-track-b。共享预算、截止与分工见ab_20261007/SHARED_BUDGET.json。\n- 本机滞后R6入口已纠正，原本机STATE/PLAN/MEMORY/HANDOFF保留在ab_20261007/reconciliation。未触碰现有未提交科学代码/日志。\n',encoding='utf-8')
print('Local stale state reconciled with preserved original context; shared deadline fixed')
