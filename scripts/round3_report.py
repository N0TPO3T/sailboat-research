"""Generate both seeds and all pairwise tables; conclusions are evidence-written."""
import json,csv,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];run=ROOT/'runs/round3_20261011_2308';confirm=run/'confirmation50'
summary=json.loads((confirm/'summary.json').read_text());freeze=json.loads((run/'freeze.json').read_text())
assert summary['physical_rollouts']==600 and summary['independent_scenarios']==50
methods=('normal','w0','old_avoid','old_range','guard_old_range','final_avoid','final_range')
names=dict(normal='正常策略',w0='W0窗口初始化',old_avoid='第二轮专家',old_range='第二轮range',
           guard_old_range='旧权重+约束+range',final_avoid='新训练专家',final_range='新训练+range')
def fmt(x):return '—' if x is None else f'{x:.2f}'
def csvwrite(path,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)));writer.writeheader()
        writer.writerows({k:json.dumps(v) if isinstance(v,(list,dict)) else v for k,v in r.items()} for r in rows)
conclusions=run/'CONCLUSIONS_ZH.md'
assert conclusions.exists(),'Write factual conclusions after frozen confirmation; never guess performance.'
lines=['# 双策略动态避障第三轮实测报告','',conclusions.read_text(encoding='utf-8'),'',
'## 证据范围与比较对象','',
'两次独立训练、同一份50个未见实例，实际600个新完整闭环回合：normal与W0各50次共享，另有每训练种子5×50次。两个组合表各350行，包含共享控制的副本，不能称700次执行或100个独立场景。none/away/late/edge_static各8，cross/headon各9。配置和检查点先固定，再生成930000—930049；确认结果没有用于改方法、调参数或重新选点。', '',
'W0保留完整18D障碍输入，其动态新增列未训练且为零；使用与专家一致的26D统计、mask、10步真实历史和执行接口。normal是原流式记忆策略。W0−normal隔离的是历史/接口组合，不能进一步将差异全归于某个历史长度；训练专家−W0才比较学习适配。旧权重+约束+range使用第二轮原selected，仅改变输入处理，检验不重训的低成本方案。新专家与新range共用同一份权重和normalizer。','',
'| 表中简称 | 实际方法 |\n|---|---|\n| normal | 原正常策略始终运行 |\n| w0 | 未训练初始化窗口专家始终运行 |\n| old_avoid | 第二轮对应selected专家始终运行 |\n| old_range | 第二轮对应selected专家＋原range |\n| guard_old_range | 同一第二轮权重＋新输入约束＋原range，不重训 |\n| final_avoid | 第三轮独立训练selected专家始终运行 |\n| final_range | 同一第三轮专家＋原range |','',
'## 已见归因与有限探索','',
'完整证据见[DIAGNOSIS_ZH.md](runs/round3_20261011_2308/diagnosis/DIAGNOSIS_ZH.md)。旧50场W0为38/50，normal为30/50，第二轮专家38/36。两专家相对W0分别救12失12、救11失13；cross/edge_static收益伴随headon/late损失。此前相对normal的净成绩不能全部归于RL。','',
'四个预先固定的真实range接管源状态，完整恢复真实前缀、两策略各自历史、执行器、缓存和路由；每源比较normal继续、W0接管、训练专家接管，共12条完整分支，没有扫描时刻。920033、920038、920046中训练专家失败而W0安全；920040中只有训练专家接管安全。W0在920040从初态成功却从normal接管状态失败，说明不能用整回合结果代替接管能力。分支后策略锁定到结局，与在线交还分开。','',
'筛选仅用已见旧50：统一缩小新增输入至0.5使range为22/37，拒绝；条件输入约束使两份原权重range为43/41（原40/38），但丢失已有有利组合。range+W0仅34/50，弱于W0始终38/50，未作为新确认主要对照。所有筛选失败保留。筛选结果不是新确认结果。','',
'已有轨迹逐项比较进一步表明：两份固定权重加约束后，旧9场headon的raw/action/active均与range+W0完全相同，其余41场与各自原range完全相同。因此这部分开发收益是条件恢复初始化行为，不是新学会的能力。新确认仍保留不重训对照来检验重训增益。','',
'## 唯一算法改动及机制边界','',
'headon_guard在合法观测/短时缓存有效且目标世界速度与固定任务轴余弦<−0.7时，将归一化后的新增8维置零。原18D障碍槽、10步历史、5s缓存、过期mask与所有路由条件保持。每个历史观测按其当时可用信息独立处理。没有使用kind/seed/视域外真值，没有取消mask或改变安全阈值。','',
'```mermaid\nflowchart LR\n  O[当前或历史合法观测26D] --> N[原归一化与过期mask]\n  O --> V[自身状态恢复目标世界速度]\n  V --> C{有效且反任务方向余弦小于-0.7}\n  N --> C\n  C -->|是| Z[仅新增8维置零 原18D保留]\n  C -->|否| D[保持原归一化结果]\n  Z --> P[同一窗口专家Actor]\n  D --> P\n  P --> A[range选择实际命令并推进原执行器]\n```','',
'这是对反任务方向来船的学习适配约束，不是COLREGs分类器或未知目标安全判定。当前所有任务起点为世界原点，固定goal定义任务轴；移到非零起点必须显式保存任务轴。该生成器将反向目标和横穿速度较明显分开，其他方向、加速/转弯、多船、感知噪声和真实部署均未验证。历史内未受抑制的旧输入仍可影响动作，因此抑制当前列不等于完全切换成W0。','',
'训练从第0步采用约束；normalizer同时用于Actor、Q与target-Q。4096个新增输入列仍是唯一可训练Actor参数；继承参数冻结。奖励、SAC实现、更新比例、训练分布与开发选点保持第二轮。独立重训与仅旧权重套约束的对照将输入规则收益与重训收益分开；本轮没有证明某个单步动作或mask是唯一根因。','',
'## 两次最终独立训练与恢复','',
'两个种子均从同一继承Actor开始，Q/优化器/replay新建，resume_source=null、初始步数和replay为0；初始Actor哈希相同、Q哈希不同。训练种子和场景基址与第二轮匹配，以减少比较中的随机性混杂。预算统一40000环境步，完整回合边界略超；每5000步及最后边界用旧12场always-avoid开发结果，先安全数，再失败计700s的总航时，最后较早步。没有只挑较好的训练种子。','',
'| 种子 | 实际步数 | Q更新 | Actor更新 | 回合 | 墙钟min | selected步 | 开发安全/12 |','|---|---:|---:|---:|---:|---:|---:|---:|']
for e in freeze['experts']:
    seed=e['train_seed'];td=run/f'train_{seed}';c=json.loads((td/'complete.json').read_text())
    lines.append(f'| {seed} | {c["steps"]} | {c["updates"]} | {c["actor_updates"]} | {c["episodes"]} | {c["wall_seconds"]/60:.2f} | {e["steps"]} | {e["score"][0]} |')
    learn=[json.loads(x) for x in (td/'learning.jsonl').read_text().splitlines()]
    coverage={m:[r['takeover_time'] for r in learn if r['start_mode']==m and r['takeover_time'] is not None] for m in ('avoid','range','risk')}
    (td/'takeover_coverage.json').write_text(json.dumps(coverage,indent=2))
    check=json.loads((ROOT/f'checkpoints/round3/{seed}/checkpoint_verification.json').read_text());assert check['restored_four_updates_identical']
    assert (confirm/f'seed_{seed}/trajectory_checks.json').exists()
lines+=['','训练前缀仍按回合轮换：初态专家、真实range首次接管、真实risk首次接管；前缀实际执行normal且维护双方历史，接管后专家锁存至完整结局。没有触发则正常结束并如实进入回放。这不是本轮新增路由算法。选点仍只测always-avoid，是保留的局限，不能声称已优化路由选点。','',
'最终完整恢复状态在checkpoints/round3/<seed>/resume.pt，含Actor/Q/target-Q、优化器、replay、RNG、normalizer和训练协议；另存actor.pth/normalizer.pth。两次独立装载后连续4次更新完全一致，只证明本实现恢复自洽，不冒充上游历史精确续训。W0和旧权重加约束控制只有Actor与normalizer，不冒充SAC训练恢复状态。','']
for seed,ss in summary['training_seeds'].items():
    folder=confirm/f'seed_{seed}';rows=[json.loads(l) for l in (folder/'episodes.jsonl').read_text().splitlines()]
    pairs=json.loads((folder/'pairs.json').read_text());csvwrite(folder/'episodes.csv',rows)
    lines += [f'## 种子 {seed}：新50场','',
      '| 方法 | 安全完成 | 到达 | 违规 | 超时 | 其他失败 | 最小距离m | 切换总数 | 平均专家执行s | 接管/交还/交还且安全/最终normal完成 | 决策ms/步 |',
      '|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|']
    for mode in methods:
        r=ss[mode];safe_handback=sum(x['handback_and_safe_complete'] for x in rows if x['mode']==mode)
        lines.append(f'| {mode} | {r["safe_complete"]}/50 | {r["arrived"]} | {r["violations"]} | {r["timeouts"]} | {r["other_failures"]} | {fmt(r["min_distance"])} | {r["switches"]} | {r["takeover_seconds_mean"]:.2f} | {r["takeover_episodes"]}/{r["handback_episodes"]}/{safe_handback}/{r["finished_normal_after_handback"]} | {r["decision_ms_per_step"]:.2f} |')
    lines+=['','接管/交还为发生事件的回合数；always-avoid没有路由接管事件。“交还且安全”允许之后再次接管，“最终normal完成”还要求最后已执行策略为normal。所有实体都参与最小距离与违规评价，不可见目标不删除，无实体的null不当零距离。','',
            '| 类别/总数 | '+' | '.join(methods)+' |','|---|'+'---:|'*len(methods)]
    for kind,n in [('none',8),('away',8),('late',8),('cross',9),('headon',9),('edge_static',8)]:
        lines.append(f'| {kind}/{n} | '+' | '.join(str(ss[m]['by_kind'][kind]) for m in methods)+' |')
    equivalence=json.loads((folder/'functional_equivalence.json').read_text())
    lines+=['','逐步状态/动作身份核对（读取现有轨迹，不是新增实验）：']
    for key,eq in equivalence.items():
        lines.append(f'- {key}：headon完全一致{eq["headon"]["identical"]}/{eq["headon"]["n"]}；各类全量结果见functional_equivalence.json。')
    lines+=['','### 学习、输入处理和路由的配对安全得失','',
            '| 后者−前者 | 救回ID | 损失ID | 共同安全 | 共同失败 |','|---|---|---|---:|---:|']
    for key,p in pairs.items():
        lines.append(f'| {key} | {p["rescued"]} | {p["lost"]} | {len(p["common_safe"])} | {len(p["both_failed"])} |')
    compact=[];long_rows=[]
    for metric,label in [('time','所有两两共同安全航时/s'),('path_length','所有两两共同安全航程/m')]:
        lines+=['',f'### {label}','', '| 后者−前者 | n | 前均值/中位 | 后均值/中位 | 差均值/中位 | 最大退化 | 更小/相同/更大 |','|---|---:|---|---|---|---:|---|']
        for key,p in pairs.items():
            q=p[metric];lines.append(f'| {key} | {len(p["common_safe"])} | {fmt(q["a_mean"])}/{fmt(q["a_median"])} | {fmt(q["b_mean"])}/{fmt(q["b_median"])} | {fmt(q["delta_mean"])}/{fmt(q["delta_median"])} | {fmt(q["max_degradation"])} | {q["faster"]}/{q["equal"]}/{q["slower"]} |')
            compact.append(dict(pair=key,metric=metric,common_safe_n=len(p['common_safe']),rescued=p['rescued'],lost=p['lost'],**{k:v for k,v in q.items() if k!='per_scene'}))
            long_rows.extend(dict(pair=key,metric=metric,**item) for item in q['per_scene'])
    csvwrite(folder/'pairs.csv',compact);csvwrite(folder/'paired_scenes.csv',long_rows)
    lines+=['','每一对使用自己的共同安全集合，失败早停不进入效率比较。最大退化为后−前最大值；若为负则该子集没有正退化。逐场ID和差值保留在paired_scenes.csv，不能混用不同共同安全分母。','',
            '### 新range相对新专家的事件证据','']
    cases=json.loads((folder/'case_events.json').read_text())
    p=pairs['final_range-minus-final_avoid']
    for label in ('rescued','lost'):
        for scene in p[label]:
            c=cases[str(scene)]['final_range'];r=c['result'];events='；'.join(str(e['t'])+':'+','.join(e['changes']) for e in c['events'])
            lines.append(f'- {label} {scene}/{r["kind"]}：接管{r["takeover_times"]}，交还{r["handback_times"]}，终止{r["time"]}s/{r["termination_reason"]}，最小距离{fmt(r["min_distance"])}m；全窗口失联仍运行专家{c["blind_active_steps"]}步。时间线：{events}。')
    lines+=['','事件先后不是单因素因果证明；没有交还的失败不归因于过早交还。新确认只做离线事件分析，没有新增分支、扫描切换点或修改策略。','']
lines+=['## 执行成本与限制','',
f'- 新确认600回合墙钟{summary["wall_seconds"]:.2f}s，最多4个单线程CPU worker，无GPU；各方法决策ms/步见上表。训练墙钟按两运行分别列出，不将并行时间相加当总墙钟。',
'- 决策计时包含路由和Actor前向，不含观测构造、物理推进或初始化。normal一个Actor，其他方法当前都计算两个Actor；专家接管时长减少不等于计算节省。',
'- 500m任务、700s时限、40m中心安全域、1Hz、前向120°/150m、0—1艘恒速低速目标。目标不可见后停止真值更新，缓存只外推5s，年龄显式可用；物理评价始终保留目标。',
'- 40m判分是1s端点相对线段近似，不是连续ODE或实体船体安全证明。无目标/远离/错时类别不自动等于真实无冲突，轨迹才决定安全。',
'- range保持既有进入/交还；丢失后仍用最后合法观测可达域判断风险，不能当作专家继续知道真值。切换不重置船体、帆舵设定值、时钟或各自真实历史；未执行输出不写成真实动作。',
'- 只有两个训练种子和一份50场，不能声称稳定泛化或部署安全。试探过的shrink失败、所有超时/违规/退化均保留。',
'- 只做一次新增实现检查（same-family/provisional），未做全仓复核、论文审查或新平台。物理轨迹检查与恢复一致性是实际收据，不替代方法有效性证据。','',
'## 产物与复现','',
'实际命令见[COMMANDS.md](runs/round3_20261011_2308/COMMANDS.md)。协议、冻结身份和来源分别为PROTOCOL.md、freeze.json、source_before；旧首轮/第二轮selected、失败轨迹和A线均保留。新检查点必须用AdaptNormalizer加载，旧FixedNormalizer会漏掉约束，不能用于复现本轮方法。','',
'逐回合、全部配对、事件和轨迹：runs/round3_20261011_2308/confirmation50/seed_<seed>/；唯一600条原始轨迹在parts/*/trajectories。旧50W0与12分支在diagnosis，筛选250回合在screen，全部失败均在对应文件。','',
'3张静态关键图及1段真实动画位于runs/round3_20261011_2308/figures；动画从实际轨迹抽帧，完整原始1Hz轨迹另存。终止帧不伪造交还。图是证据展示，不是机制证明。','']
manifest=run/'figures/manifest.json'
if manifest.exists():
    for item in json.loads(manifest.read_text()):
        lines.append(f'- [{item["label"]}](runs/round3_20261011_2308/figures/{item["file"]})：{item["description"]}')
        if item.get('cases'):
            lines.append('  '+ '；'.join(f'{c["label"]}：{c["train_seed"]}/{c["scene"]}，safe={c["safe_complete"]}，最小距离{fmt(c["min_distance"])}m' for c in item['cases'])+'。成功案例930034最小裕度仅约0.65m，不代表稳健安全保证。')
lines+=['','[DualPolicy_Round3_preview.zip](DualPolicy_Round3_preview.zip)含报告、代码、表格和关键图；大检查点、全量原始轨迹另存于项目目录，不声称预览包可脱离继承环境独立运行。','']
(ROOT/'REPORT_ROUND3_ZH.md').write_text('\n'.join(lines),encoding='utf-8');print(ROOT/'REPORT_ROUND3_ZH.md')
