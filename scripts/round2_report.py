"""Build round2 report and CSV tables from both seeds, without selecting a winner."""
import json,csv,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];run=ROOT/'runs/round2_20261011';confirm=run/'confirmation50'
summary=json.loads((confirm/'summary.json').read_text());freeze=json.loads((run/'freeze.json').read_text())
names={'normal':'正常策略','avoid':'专家始终运行','range':'范围路由','risk':'风险路由'}
def fmt(x):return '—' if x is None else f'{x:.2f}'
def csvwrite(path,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)));writer.writeheader()
        writer.writerows({k:json.dumps(v) if isinstance(v,(list,dict)) else v for k,v in r.items()} for r in rows)
lines=['# 双策略动态避障第二轮实测报告','',
'## 本轮回答什么','',
'检验专家能力与路由收益在两个从继承Actor独立初始化的训练中能否重复，并解释首轮路由损失。首轮权重/失败/确认和A线保留。没有视觉、第三路由网络、S15搜索或新仿真器。','',
'两训练种子共用同一份50个新场景：none/away/late/edge_static各8，cross/headon各9。实际完整新回合350个：normal50个复用，加两个专家各150个。不是100个独立场景；全部50场均在分母内。','']
improvements=[];routing=[]
for seed,ss in summary['training_seeds'].items():
    improvements.append(ss['avoid']['safe_complete']-ss['normal']['safe_complete'])
    routing.append(ss['risk']['safe_complete']-ss['avoid']['safe_complete'])
expert_answer='两个种子均出现安全完成净改善，构成有限重复证据。' if all(x>0 for x in improvements) else '专家安全完成净改善没有在两个种子中一致重复。'
route_answer='两个种子的风险路由净收益方向一致为正，但两次训练仍不足以证明稳定优势。' if all(x>0 for x in routing) else '风险路由相对始终使用专家的收益没有在两个种子中一致为正，不应默认采用较复杂的风险路由；范围路由须按其自己的配对结果判断。'
lines += [f'**专家能力：** {expert_answer} 两个净变化为{improvements}场。', '',f'**路由价值：** {route_answer} 两个净变化为{routing}场。','',
'**范围路由：** 两种子相对avoid均净增2场，但各自仍损失2场和1场。risk相对range没有救回任何场，分别额外损失2场和1场。复杂风险门在本确认上不值得默认采用。','',
'## 四个问题的结论','',
'1. **改善是否重复？** 相对normal的30/50，两个专家为38/50和36/50，净改善重复；但专家分别救回14/13场、又损失6/7场，不是全面替代。首轮旧cross的接管修复仅一个种子成功，不能声称本轮训练修改已稳定解决接管问题。','',
'2. **路由救回、损失什么？** range相对avoid分别救4失2、救3失1；risk分别救2失2、救3失2。两种子共同救回的late 920018完全未接管，是保留normal避免专家自行引入冲突。另有normal和avoid均失败、切换后成功的真实组合收益，例如种子20261011的headon 920040、种子20261012的late 920020及headon 920035。逐场ID在下面配对表保留。','',
'3. **与接管、失联还是交还有关？** risk在cross 920025于32s接管，比range的25s晚7s，两种子均因此组比较损失该场；两种路由在失败发生前都尚未交还，进入规则是受控比较中的关键差异。种子20261011的late 920019也是risk延至68s才接管、range为53s。两种子其余路由损失920033/920038/920046都在首次可见时接管，仍会失败，不能只靠更早阈值解决。','',
'失联确实出现在这些轨迹：920033/920038在缓存失效后重新看见目标，随后仍违规；920046在97s缓存失效、103s对不可见动态目标违规，但此前10步历史尚未全部清空。920025的第二个种子直到终止帧才首次形成“当前输入和全部10步历史都无动态槽”，最后已执行动作尚有历史。因此失联是相关状态，不足以单独定罪mask；当前路由全部损失均无此前交还。','',
'4. **下一步？** 优先诊断并改善专家在真实接管及失联/重见状态下的动作稳定性，保留range作简单候选，暂不采用当前risk作为默认方案。不增加路由网络、不取消mask、不按新确认调阈值。下一轮先用少量预登记同状态分支区分适配动作与失联表示，再决定是否最小改输入或训练。若再做新训练/路由修改，必须使用另一份未见确认集。','',
'range的有限收益也有成本：其与avoid共同安全场景平均分别多用7.89s、4.77s；risk分别多用13.50s、3.38s。路由当前仍计算两个Actor，没有计算节省证据。这里建议保留range作研究候选，不宣称已获得稳定安全保证或部署优势。','',
'## 首轮诊断与唯一算法修改','',
'关键案例为910008/910010（专家损失）、910002/910014（range额外损失）、910009（两路由共同cross损失）。完整时间线、原动作/航向/航速、七个固定分支及全部两两效率见 [DIAGNOSIS_ZH.md](runs/round2_20261011/diagnosis/DIAGNOSIS_ZH.md)。', '',
'910009在首次可见86s即由两种路由接管，133s违规，没有交还。相同86s状态交给首轮训练专家失败，保持normal或用未训练新增列的初始窗口专家则分别170/167s到达。102s缓存首次失效后改normal可204s完成，但同时改变了整套策略，不能单独证明mask致错。违规路径没有出现连续超过10步无效槽后才失败的证据。因此不撤销曾修复超时的mask。', '',
'910002/910014的range在尚无danger时接管，随后才出现danger并违规；risk不进入且安全。已有风险门避免这两次无谓接管，没有再加阈值。910010从normal前缀90s接管时，训练/初始专家均安全，说明整回合失败不能代替接管能力判断。', '',
'首轮risk与avoid直接共同安全21场，risk平均快6.67s、航程短11.38m；四组共同12场risk慢8.17s属于另一子集。两者同时保留，不挑有利分母。','',
'唯一算法修改是训练接管分布：按回合轮换三种起点（各约1/3）：从初态专家、原range实际首次接管、原risk实际首次接管。前缀始终真实执行normal并维护双方各自历史；第一次接管后专家锁存到任务结束学习完整推进。未触发回合继续normal并如实进入回放。没有改输入、mask、奖励、4096参数适配范围或路由阈值。另补了终止原因日志，不改变终止条件。','',
'```mermaid\nflowchart LR\n  I[随机任务初态] --> A[初态专家]\n  I --> N[真实正常策略前缀]\n  N --> R[原range或risk首次接管]\n  R --> E[同一专家执行至完整结局]\n  A --> E\n  N --> U[未触发则正常完成或失败]\n  E --> B[SAC真实回放与更新]\n  U --> B\n```','',
'该干预针对已见状态差异，但本轮没有同随机种子的训练分布消融；新训练与首轮中途改协议的训练也不同。不能把全部变化因果归于接管分布。','',
'## 独立训练与选点','',
'两运行均无resume，Q/目标Q、优化器和replay新建；初始Actor哈希相同、Q哈希不同、replay=0。从第0步使用最终mask、横摇投影、归一化、10步窗口、奖励和更新比例。保留normal streaming与专家窗口的已知差异。统一预算40000环境步（按完整回合略超），每5000步及最终边界用固定12场810000—810011的avoid表现选点；先安全完成，再失败计700s的总航时，再较早步数。没有按种子表现单独延长，也未将新确认纳入选点。','',
'| 训练种子 | 实际环境步 | Q更新 | Actor更新 | 回合 | 墙钟/分 | 选定步 | 选定开发安全 |','|---|---:|---:|---:|---:|---:|---:|---:|']
for e in freeze['experts']:
    seed=e['train_seed'];train=run/f'train_{seed}';c=json.loads((train/'complete.json').read_text())
    lines.append(f'| {seed} | {c["steps"]} | {c["updates"]} | {c["actor_updates"]} | {c["episodes"]} | {c["wall_seconds"]/60:.2f} | {e["steps"]} | {e["score"][0]}/12 |')
    learn=[json.loads(x) for x in (train/'learning.jsonl').read_text().splitlines()]
    coverage={m:[r['takeover_time'] for r in learn if r['start_mode']==m and r['takeover_time'] is not None] for m in ('avoid','range','risk')}
    (train/'takeover_coverage.json').write_text(json.dumps(coverage,indent=2))
lines += ['', '完整恢复状态、Actor、normalizer、选点记录分别位于`checkpoints/round2/20261011/`和`checkpoints/round2/20261012/`。恢复状态含Q目标、优化器、replay、RNG与训练协议。首轮selected只作历史诊断，不算第三次独立训练。','']
lines += ['| 训练种子/前缀 | 回合数 | 实际进入专家 | 首次接管中位/最大s | 超过45s接管数 |','|---|---:|---:|---|---:|']
for e in freeze['experts']:
    seed=e['train_seed'];learn=[json.loads(x) for x in (run/f'train_{seed}/learning.jsonl').read_text().splitlines()]
    for mode in ('avoid','range','risk'):
        subset=[r for r in learn if r['start_mode']==mode];times=[r['takeover_time'] for r in subset if r['takeover_time'] is not None]
        lines.append(f'| {seed}/{mode} | {len(subset)} | {len(times)} | {fmt(statistics.median(times) if times else None)}/{fmt(max(times) if times else None)} | {sum(t>45 for t in times)} |')
lines += ['', '此表覆盖整个训练预算；被选检查点只包含截至其步数的经验。avoid的0s是从初态运行，不是路由事件。覆盖更晚的首次接管不代表已覆盖所有状态或重复交还后的接管。','']
for seed,ss in summary['training_seeds'].items():
    folder=confirm/f'seed_{seed}';rows=[json.loads(l) for l in (folder/'episodes.jsonl').read_text().splitlines()]
    pairs=json.loads((folder/'pairs.json').read_text());csvwrite(folder/'episodes.csv',rows)
    lines += [f'## 训练种子 {seed}：50场确认','',
        '| 方法 | 安全完成 | 到达 | 违规 | 超时 | 其他失败 | 最小间距/m | 切换总数 | 平均接管/s | 接管/交还/交还且安全/最终normal完成 | 决策ms/步 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|']
    for mode,r in ss.items():
        lines.append(f'| {names[mode]} | {r["safe_complete"]}/50 | {r["arrived"]} | {r["violations"]} | {r["timeouts"]} | {r["other_failures"]} | {fmt(r["min_distance"])} | {r["switches"]} | {r["takeover_seconds_mean"]:.2f} | {r["takeover_episodes"]}/{r["handback_episodes"]}/{r["handback_safe_episodes"]}/{r["finished_normal_after_handback"]} | {r["decision_ms_per_step"]:.2f} |')
    lines += ['', '接管/交还计数为发生该事件的回合数；“交还且安全”允许之后再接管，“最终normal完成”还要求最后实际控制者是normal。always-avoid不是一次路由接管。最小间距纳入全部实体，包括不可见目标；无实体的null不混入间距均值。终止原因与原环境terminated/truncated单独保存在逐回合表。','',
        '| 类别（总数） | normal | avoid | range | risk |','|---|---:|---:|---:|---:|']
    for kind,n in [('none',8),('away',8),('late',8),('cross',9),('headon',9),('edge_static',8)]:
        lines.append(f'| {kind}（{n}） | '+' | '.join(str(ss[m]['by_kind'][kind]) for m in names)+' |')
    p=pairs['avoid-minus-normal']
    lines += ['',f'normal/avoid四格：共同安全{len(p["common_safe"])}；仅normal安全{len(p["lost"])}；仅avoid安全{len(p["rescued"])}；共同失败{len(p["both_failed"])}。这是实际整回合成功集合，不是在线事后赢家路由。','']
    conflict=[r['seed'] for r in rows if r['mode']=='normal' and r['violated']]
    rescued_in_conflict={m:sum(r['safe_complete'] for r in rows if r['mode']==m and r['seed'] in conflict) for m in names}
    lines += [f'原正常轨迹真实违反安全域的集合为{len(conflict)}场{conflict}；各方法在该集合安全完成数为{rescued_in_conflict}。这是按正常闭环轨迹定义的动/静态实际冲突集合，不把名义cross/late标签当成必然冲突，也不用于训练或筛选最终场景。','']
    for key in ('avoid-minus-normal','range-minus-avoid','risk-minus-avoid','risk-minus-range'):
        p=pairs[key];lines.append(f'- {key}：救回{len(p["rescued"])}场 {p["rescued"]}；损失{len(p["lost"])}场 {p["lost"]}。')
    compact=[];long_rows=[]
    for metric,label in [('time','共同安全航时/s'),('path_length','共同安全航程/m')]:
        lines += ['',f'### {label}','', '| 后者−前者 | 共同安全n | 前均值/中位 | 后均值/中位 | 差均值/中位 | 最大退化 | 更小/相同/更大 |',
            '|---|---:|---|---|---|---:|---|']
        for key,p in pairs.items():
            q=p[metric]
            lines.append(f'| {key} | {len(p["common_safe"])} | {fmt(q["a_mean"])}/{fmt(q["a_median"])} | {fmt(q["b_mean"])}/{fmt(q["b_median"])} | {fmt(q["delta_mean"])}/{fmt(q["delta_median"])} | {fmt(q["max_degradation"])} | {q["faster"]}/{q["equal"]}/{q["slower"]} |')
            compact.append(dict(pair=key,metric=metric,common_safe_n=len(p['common_safe']),rescued=p['rescued'],lost=p['lost'],**{k:v for k,v in q.items() if k!='per_scene'}))
            long_rows.extend(dict(pair=key,metric=metric,**item) for item in q['per_scene'])
    csvwrite(folder/'pairs.csv',compact);csvwrite(folder/'paired_scenes.csv',long_rows)
    lines += ['', '每行使用该对各自的共同安全集合，失败提前停止不进入效率比较；逐场差值与对应ID见paired_scenes.csv。最大退化为后−前最大值，负值表示该集合没有正退化。','',
        '### 路由得失的事件证据','']
    cases=json.loads((folder/'case_events.json').read_text())
    for category in ('rescued','lost'):
        for scene in pairs['risk-minus-avoid'][category]:
            c=cases[str(scene)]['risk'];r=c['result'];events='；'.join(str(e['t'])+':'+','.join(e['changes']) for e in c['events'])
            lines.append(f'- risk相对avoid {category} {scene}（{r["kind"]}）：接管{r["takeover_times"]}，交还{r["handback_times"]}，结束{r["time"]}s/{r["termination_reason"]}，末步策略{r["last_executed_policy"]}；全窗口动态缺失且仍接管{c["blind_active_steps"]}步。事件：{events}。')
    lines += ['', '上述是同步事件顺序，不是单因素因果证明。没有交还的失败不能归因于过早交还；交还后失败仅提示检查退出/接回，不能自动证明退出是唯一原因。最终确认没有新增同状态分支或事后调参。','']
lines += ['## 旧关键任务前后对比','',
    '两个已选专家在首轮五场上按同样四模式另跑小组对照；这是已见开发材料，不算50场新确认。每个专家的normal仍可复用。逐回合及配对记录在runs/round2_20261011/retrained_key_cases。','',
    '| 新训练种子 | 场景 | 历史normal/avoid/range/risk | 新normal/avoid/range/risk |','|---|---:|---|---|']
oldrows=[json.loads(l) for l in (ROOT/'runs/confirmation/episodes.jsonl').read_text().splitlines()]
for seed in summary['training_seeds']:
    new=[json.loads(l) for l in (run/f'retrained_key_cases/seed_{seed}/episodes.jsonl').read_text().splitlines()]
    for scene in sorted({r['seed'] for r in new}):
        flag=lambda rr:'/'.join('✓' if next(r for r in rr if r['seed']==scene and r['mode']==m)['safe_complete'] else '×' for m in names)
        lines.append(f'| {seed} | {scene} | {flag(oldrows)} | {flag(new)} |')
lines += ['', '旧cross 910009的路由失败只在20261011修复：86s接管、293s交还、318s安全到达；normal为170s，安全修复伴随148s航时代价。20261012仍在121s违规，且没有交还。两份新专家从初态运行在该场均失败，不能将首轮专家成功视为已保留的能力。910010两份新路由也均失败，而首轮路由成功。接管覆盖干预尚未稳定修复旧问题，部分能力发生退化。','',
'## 实际成本、验证与适用边界','',
f'- 新确认实际350回合，最多4个单线程CPU worker，墙钟{summary["wall_seconds"]:.2f}s。normal50回合只运行一次。两个训练按各自墙钟报告，并行时间不能相加冒充总墙钟。',
'- 决策计时包含路由和Actor前向，不含观测构造/环境推进/初始化。normal一次Actor；avoid/range/risk当前实现都计算两个Actor。接管减少不等于计算节省。',
'- 500m任务、700s时限、40m中心安全域、1Hz、120°/150m理想几何观测、0—1艘低速恒速目标保持不变。出视域真值停止更新，5s缓存后mask保持；评价仍检查不可见实体。',
'- 失联交还仍依赖最后观测位置及1.6m/s上界的可达圆盘与向外运动条件。不是长期点位置真值，也不保证后续任意操舵安全。',
'- 40m判分采用1s端点相对线段近似，不是连续ODE/实体船体安全证明。保留所有超时、违规和其他失败，未缩小阈值。',
'- 两种子只提供有限重复性信息；50场同一清单不能算100个独立实例。选择集仅avoid表现，不保证选出的权重最适合路由。',
'- 本文“专家改善”指所选专家相对normal的安全完成净差。新50场没有增加零新增列的初始窗口专家对照，因此不能把该差全部因果归于RL训练；normal流式记忆与专家窗口的差异仍存在。',
'- 只做一次针对训练分布/信息边界/日志变更的实现检查，same-family/provisional。确定性前缀核验与恢复检查另有真实收据，不称论文审稿通过。','',
'## 真实动画与复现','']
for e in freeze['experts']:
    seed=e['train_seed'];verification=json.loads((ROOT/f'checkpoints/round2/{seed}/checkpoint_verification.json').read_text())
    assert verification['restored_four_updates_identical']
    check=json.loads((confirm/f'seed_{seed}/trajectory_checks.json').read_text())
    lines.insert(lines.index('## 真实动画与复现'),f'- 训练{seed}的所选恢复状态两次独立装载后连续4次更新完全一致；轨迹核验收据：`runs/round2_20261011/confirmation50/seed_{seed}/trajectory_checks.json`。')
lines.insert(lines.index('## 真实动画与复现'),'\n两份轨迹核验各含200条方法记录，其中normal50是复用副本；对应350条唯一真实新回合，不是400次独立执行。\n')
for seed in summary['training_seeds']:
    manifest=confirm/f'seed_{seed}/figures/animation_manifest.json'
    if manifest.exists():
        for a in json.loads(manifest.read_text()):
            if a['file'].endswith('.gif'):
                lines.append(f'- [训练{seed} / {a["label"]}](runs/round2_20261011/confirmation50/seed_{seed}/figures/{a["file"]})：scene {a["result"]["seed"]}，{a["result"]["mode"]}，safe={a["result"]["safe_complete"]}。')
lines += ['', '动画来自实际轨迹，显示同步目标、FOV、活动策略和间距；终止帧只显示最后已执行策略，未来轨迹仅离线展示。','',
'实际命令见[COMMANDS.md](runs/round2_20261011/COMMANDS.md)。预览包`DualPolicy_Round2_preview.zip`不含大权重和全量轨迹；完整产物保存在当前项目对应目录。','']
(ROOT/'REPORT_ROUND2_ZH.md').write_text('\n'.join(lines),encoding='utf-8');print(ROOT/'REPORT_ROUND2_ZH.md')
