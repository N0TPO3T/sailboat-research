"""Publish compact verified handoff after confirmation and evidence-written report."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];run=ROOT/'runs/round3_20261011_2308';confirm=run/'confirmation50'
freeze=json.loads((run/'freeze.json').read_text());summary=json.loads((confirm/'summary.json').read_text())
assert (ROOT/'REPORT_ROUND3_ZH.md').exists()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(ROOT/'src/dynamic.py')==sha(run/'source_before/dynamic.py')
assert sha(ROOT/'scripts/train.py')==sha(run/'source_before/train.py')
assert sha(ROOT/'checkpoints/selected/resume.pt')=='057773e12565567290a0174cc73551ab442db79d506d4717047a461cc5df4b48'
for e in freeze['experts']:
    assert sha(ROOT/e['old_checkpoint'])==e['old_sha256']
    assert sha(ROOT/e['checkpoint'])==e['sha256']
    assert json.loads((confirm/f'seed_{e["train_seed"]}/trajectory_checks.json').read_text())['all_metric_checks_passed']
unique=list((confirm/'parts').glob('*/trajectories/*.npz'));assert len(unique)==600
for method in ('normal','w0'):
    for scene in range(930000,930050):
        assert sha(confirm/f'seed_20261011/trajectories/{scene}_{method}.npz')==sha(confirm/f'seed_20261012/trajectories/{scene}_{method}.npz')
checks=dict(unique_new_trajectories=len(unique),combined_rows=700,independent_scenarios=50,
            old_w0_trajectories=len(list((run/'diagnosis/w0_old50/trajectories').glob('*.npz'))),
            same_state_branches=len(list((run/'diagnosis/branches').glob('*.npz'))),
            screening_trajectories=len(list((run/'screen').glob('*/trajectories/*.npz'))),
            old_dynamic_and_train_preserved=True,round1_and_round2_selected_preserved=True,
            shared_normal_w0_raw_identical=True,selected_hashes_match_freeze=True)
assert checks['old_w0_trajectories']==50 and checks['same_state_branches']==12 and checks['screening_trajectories']==250
(run/'delivery_checks.json').write_text(json.dumps(checks,indent=2))
methods=('normal','w0','old_avoid','old_range','guard_old_range','final_avoid','final_range')
lines=['# 当前交接：第三轮已完成','',
'先读REPORT_ROUND3_ZH.md；第三轮证据位于runs/round3_20261011_2308。首轮REPORT_ZH.md、第二轮REPORT_ROUND2_ZH.md及全部旧权重/失败仍保留。新50场现为已见证据，不得继续调参后称新确认。','',
'服务器donghai:/home/ot/Students/hs/sailboat-dynamic-routing-v0；本地C:/Users/74095/hs/SailBoat/sailboat-dynamic-routing-v0。只读Python为/home/ot/Students/hs/sailboat-routing-v0/.venv/bin/python。服务器所有写入限定hs真实路径。本轮无GPU，最多4个单线程CPU实验进程。','',
'## 当前已验证结果','',
'| 训练种子 | '+' | '.join(methods)+' |','|---|'+'---:|'*len(methods)]
for seed,ss in summary['training_seeds'].items():lines.append(f'| {seed} | '+' | '.join(str(ss[m]['safe_complete'])+'/50' for m in methods)+' |')
lines+=['','两训练种子共用同一份930000—930049，只有50个独立场景。normal/W0各50次共享，另外5方法×2种子×50，实际600回合，组合表700行包括复用副本。所有失败保留，物理/视域/执行器指标重算通过。','',
'W0使用相同窗口/normalizer/mask且保留18D障碍信息，新增动态列为零。旧50场W0=38、normal=30、旧专家=38/36；12条固定同状态分支证明学习既有接管救回也有损失。统一减半候选22/37被拒绝；反任务方向输入约束进入最终训练。','',
'本轮唯一算法改动：合法目标世界速度与固定任务轴余弦<−0.7且缓存有效时，归一化新增8维置零，18D保留。每个历史观测独立处理；原5s缓存/mask、10步窗口、4096参数范围、奖励及range进入/交还未改。它不是COLREGs分类器；方向分布泛化未知。','',
'最终两训练均从相同继承Actor独立初始化，新Q/优化器/replay，40000步预算（完整回合略超），同旧12场avoid开发规则选点。第二轮selected不是新训练的resume源。强对照guard_old_range是不重训的旧权重加同约束。研究结论及是否值得代价见报告开头，不将输入处理收益全算作重训或路由收益。','',
'## 权重、原始证据与复现','']
for e in freeze['experts']:
    c=json.loads((run/f'train_{e["train_seed"]}/complete.json').read_text())
    lines.append(f'- {e["train_seed"]}：实际{c["steps"]}步，selected {e["steps"]}；完整状态`{e["checkpoint"]}`，SHA256 `{e["sha256"]}`。')
lines+=['- 同目录actor.pth、normalizer.pth、selection.json、checkpoint_verification.json；两次加载后4次更新一致。完整中间训练检查点留服务器train_<seed>目录。',
'- 新方法务必使用src/round3_policy.py的AdaptNormalizer和scripts/train_round3.py、round3_evaluate.py、verify_round3_checkpoint.py；旧FixedNormalizer会漏掉约束。W0/guard旧权重控制只有Actor，不称SAC恢复状态。',
'- 实际命令：runs/round3_20261011_2308/COMMANDS.md；冻结与身份：freeze.json、w0_identity.json；恢复训练需新输出目录并保留seed/scene-base/actual_routes/headon_guard及mask/冻结参数模式。',
'- 旧50配对与真实源分支：diagnosis/DIAGNOSIS_ZH.md、old50_pairs.json、branches/；开发候选和失败：screen/。',
'- 新确认：confirmation50/seed_<seed>/含逐回合CSV/JSONL、全部21对航时航程、事件及轨迹核验；parts/*/trajectories/是600条唯一原始轨迹。',
'- figures/共3张关键PNG和1段三案例真实GIF，manifest.json记录实际来源、抽帧及描述性选例规则；预览包DualPolicy_Round3_preview.zip不含大权重或全量轨迹。',
'- 只做一次新增实现检查，same-family/provisional，无阻塞发现；不等于方法有效性或部署安全证明。delivery_checks.json记录旧资产保留、600条唯一轨迹与共享控制身份。','',
'## 边界与后续','',
'500m/700s/40m/1Hz/120°150m不变，视域外实体仍参与安全评价。路由保留失联风险不等于专家仍知道目标；终止行active=False仅占位，不能当作交还。共同安全航时/航程按各对各自子集，不能用失败早停声称提效。当前非normal组每步两个Actor前向，少接管不是计算节省。','',
'本轮训练、确认与报告流程完成；不要重启旧PID或覆盖输出。No active research thread. 若继续改方法，需新的研究请求及另一份未见确认集。','']
(ROOT/'HANDOFF.md').write_text('\n'.join(lines),encoding='utf-8')
readme=(ROOT/'README.md').read_text(encoding='utf-8');first=readme.index('\n\n');second=readme.index('\n\n',first+2)
readme=readme[:first+2]+'第三轮已完成W0归因、12条真实同状态分支、有限探索、两次独立训练与新50场600回合确认。见[REPORT_ROUND3_ZH.md](REPORT_ROUND3_ZH.md)、[实际命令](runs/round3_20261011_2308/COMMANDS.md)及[HANDOFF.md](HANDOFF.md)。第二轮报告和全部旧结果保留；下文规格与24场结果属于首轮背景。'+readme[second:]
if '## 第三轮入口' not in readme:
    readme+='\n\n## 第三轮入口\n\n新输入约束由src/round3_policy.py中的AdaptNormalizer实现，旧核心dynamic.py与train.py保持不变。新训练入口scripts/train_round3.py，评估round3_evaluate.py，恢复验证verify_round3_checkpoint.py。所有实际命令、最终矩阵及边界见第三轮COMMANDS.md和报告。不要将旧FixedNormalizer用于加载带guard的新权重。新确认930000—930049现已见，不能用于再次选点。\n'
(ROOT/'README.md').write_text(readme,encoding='utf-8');print(json.dumps(checks,indent=2))
