"""Development evidence only: attribution, fixed branches and two probes."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from dynamic import *
from round2_metrics import paired
run=ROOT/'runs/round3_20261011_2308';d=run/'diagnosis'
rows=[json.loads(x) for x in (d/'old50_episodes.jsonl').read_text().splitlines()]
pairs=json.loads((d/'old50_pairs.json').read_text());summary=json.loads((d/'old50_summary.json').read_text())
branches=[json.loads(x) for x in (d/'branches/results.jsonl').read_text().splitlines()]
old_events={}
for ts,scene in ((20261011,920033),(20261011,920038),(20261012,920046),(20261011,920040)):
    source=json.loads((ROOT/f'runs/round2_20261011/confirmation50/seed_{ts}/case_events.json').read_text())
    old_events[f'{ts}/{scene}']=source[str(scene)]['range']
(d/'key_case_timelines.json').write_text(json.dumps(old_events,indent=2))
lines=['# 第三轮开发归因与有限探索','',
'这些都是已见任务，不是第三轮新确认。原350回合未重跑；仅新增W0始终运行50场、4个源状态的12条完整分支、两个候选跨两权重的200场range与range+W0的50场。','',
'## 历史接口与学习适配','',
'W0与第二轮专家使用同一26D统计、mask、10步真实历史和动作执行接口，原18D障碍槽保留。两处新增输入列均为初始化零值，其余Actor参数与两份训练专家完全一致。W0不具有新训练Q/优化器，不冒充训练恢复状态。','',
'| 方法 | 安全/50 | none | away | late | cross | headon | edge_static |','|---|---:|---:|---:|---:|---:|---:|---:|']
for m,s in summary.items():lines.append(f'| {m} | {s["safe"]} | '+' | '.join(str(s['by_kind'][k]) for k in KINDS)+' |')
lines+=['','| 后−前 | 救回ID | 损失ID | 共同安全n | 平均航时差s | 平均航程差m |','|---|---|---|---:|---:|---:|']
for key in ('w0-minus-normal','avoid_20261011-minus-w0','avoid_20261012-minus-w0'):
    p=pairs[key];lines.append(f'| {key} | {p["rescued"]} | {p["lost"]} | {len(p["common_safe"])} | {p["time"]["delta_mean"]:.2f} | {p["path_length"]["delta_mean"]:.2f} |')
lines+=['','W0相对normal净增8场，足以解释此前相对normal的净成绩幅度，但不是完全相同的成功集合。训练相对W0救12失12、救11失13：cross和edge_static收益伴随headon/late损失，不能说训练没有改变能力，也不能把历史接口收益全算作RL。','',
'## 同一真实接管状态的完整分支','',
'每个源状态重放原range实际前缀，逐步核对原始状态、风、帆舵设定值与执行命令；缓存、静态记忆、normal记忆和专家窗口都由真实历史重建。相同源状态三分支指纹相同。分支后锁定某策略直到到达/违规/时限，**没有路由交还**；这与完整在线range比较分开。','',
'| 训练种子/场景 | 分支时刻 | 继续策略 | 安全 | 结局时刻s | 最小间距m |','|---|---:|---|---|---:|---:|']
for r in branches:lines.append(f'| {r["train_seed"]}/{r["seed"]} | {r["cut"]} | {r["continuation"]} | {r["safe_complete"]} | {r["time"]} | {r["min_distance"]:.2f} |')
lines+=['','三个失败源均由W0安全完成，其中920038的normal也失败，说明这些具体状态至少存在本项目策略可执行的安全轨迹。W0在920038仅42.43m最小间距，不能推成大裕度保证。正例920040在同一43s接管状态只有训练专家安全；W0整回合成功不能替代这一状态比较。','',
'### 接管时的可用状态与实际动作响应','']
for r in branches:
    if r['continuation']!='trained':continue
    b=r['branch_input'];lines.append(f'- {r["seed"]}@{r["cut"]}s：目标距离{b["distance"]:.2f}m，位置{b["position"]}，航向{b["heading_deg"]:.2f}°，世界速度{b["own_velocity"]}m/s，18D障碍槽{b["original_slots"]}。normal/W0/训练专家命令分别为{b["normal_action"]}/{b["w0_action"]}/{b["trained_action"]}。')
    for method in ('initial','trained'):
        q=next(x for x in branches if x['seed']==r['seed'] and x['continuation']==method)
        z=np.load(d/'branches'/f'{q["file"]}.npz');t=r['cut'];end=min(t+5,len(z['t'])-1)
        delta=np.degrees(z['setpoints'][t+1]-z['setpoints'][t]);heading=np.degrees(wrap(float(z['raw'][end,3]-z['raw'][t,3])))
        lines.append(f'  - {method}第一步帆/舵设定值实际增量{delta.round(3).tolist()}°；随后{end-t}s航向变化{heading:.2f}°。这反映量化执行器响应，不把单步动作独立当成整个失败的唯一原因。')
lines+=['','### 原range的事件时间线（复用已有日志）','']
for name,c in old_events.items():
    events='；'.join(str(e['t'])+'s:'+','.join(e['changes'])+f'(age={e["age"]:.0f})' for e in c['events'])
    lines.append(f'- {name}：{events}；接管{c["result"]["takeover_times"]}，交还{c["result"]["handback_times"]}，全窗口缺失仍接管{c["blind_active_steps"]}步。')
lines+=['','visible表示当步视域内，valid表示当前动态缓存有效；danger是原CPA条件在有效输入下的计算结果。缓存失效造成danger−不等于物理风险解除，range仍保持接管。920033/038失联后重见再违规；920046在103s对不可见目标违规，但前10步历史还未全部清空。三失败首次可见/风险条件/接管同刻，没有提前交还；不能单靠这些时间线将失联mask判作唯一根因。','',
'目标发现距离约146—147m，距40m域仍约106m；仅几何余量不足以判定可避性，以上闭环分支才是具体可行证据。三个源失败均无此前交还；不同完整策略各自到同一秒并不是同状态。','',
'## 两个固定候选及取舍','',
'shrink：归一化后新增8维统一乘0.5；headon_guard：合法缓存目标速度与固定任务轴余弦<−0.7时新增8维置零，原18D槽不变。没有改路由阈值、场景或安全标准。guard不是海事规则分类器，也不是未知目标安全判断；本生成器将反任务方向与横穿速度明显分开，跨方向分布泛化尚未检验。','',
'| 训练种子 | 原range | shrink | headon_guard | range+W0 |','|---|---:|---:|---:|---:|']
screen=json.loads((run/'screen/summary.json').read_text())
screen_observations=[]
for ts in (20261011,20261012):
    rr=[dict(r,mode='old_range') for r in rows if r['mode']==f'range_{ts}']
    for key,method in [(f'{ts}_shrink','shrink'),(f'{ts}_headon_guard','headon_guard'),('w0_range','w0_range')]:
        rr.extend(dict(json.loads(x),mode=method) for x in (run/f'screen/{key}/episodes.jsonl').read_text().splitlines())
    pp=paired(rr,('old_range','shrink','headon_guard','w0_range'));(run/f'screen/pairs_{ts}.json').write_text(json.dumps(pp,indent=2))
    lines.append(f'| {ts} | {summary[f"range_{ts}"]["safe"]} | {screen[f"{ts}_shrink"]["safe"]} | {screen[f"{ts}_headon_guard"]["safe"]} | {screen["w0_range"]["safe"]} |')
    p=pp['headon_guard-minus-old_range'];screen_observations += ['',f'{ts} guard相对旧range：救回{p["rescued"]}，损失{p["lost"]}；共同安全{len(p["common_safe"])}场平均航时差{p["time"]["delta_mean"]:.2f}s、最大退化{p["time"]["max_degradation"]:.2f}s。','']
lines+=screen_observations
effects={}
for ts in (20261011,20261012):
    counts={k:dict(n=0,same_as_w0_range=0,same_as_old_range=0) for k in KINDS}
    for r in [r for r in rows if r['mode']==f'range_{ts}']:
        scene=r['seed'];kind=r['kind'];counts[kind]['n']+=1
        guard=np.load(run/f'screen/{ts}_headon_guard/trajectories/{scene}_range.npz')
        for name,path in [('w0_range',run/f'screen/w0_range/trajectories/{scene}_range.npz'),
                          ('old_range',ROOT/f'runs/round2_20261011/confirmation50/seed_{ts}/trajectories/{scene}_range.npz')]:
            other=np.load(path)
            counts[kind][f'same_as_{name}']+=int(all(np.array_equal(guard[k],other[k]) for k in ('raw','action','active')))
    effects[str(ts)]=counts
(run/'screen/equivalence.json').write_text(json.dumps(effects,indent=2))
lines+=['','### 固定权重输入约束的轨迹归因','',
'以下只读取已有轨迹，不新增实验。完全相同要求整回合raw/action/active数组逐项一致，而不是只比较成功率。','',
'| 种子/类别 | n | guard与range+W0完全相同 | guard与原range完全相同 |','|---|---:|---:|---:|']
for ts,counts in effects.items():
    for kind,c in counts.items():lines.append(f'| {ts}/{kind} | {c["n"]} | {c["same_as_w0_range"]} | {c["same_as_old_range"]} |')
lines+=['','在这份旧50场中，两权重的9个headon均与range+W0逐步完全相同，其余41场均与各自原range完全相同。因此该固定权重开发收益来自有条件恢复W0行为，不能称为重新学习的能力。原range在920040的独有救回随之消失。该结论限定这份恒速方向分离的场景集，不外推任意运动目标。','',
'统一缩半在一个种子严重退化，拒绝该候选。guard在两份固定专家中均净救3场，支持对特定运动方向保留初始化能力；它丢失920040的有利组合，绝非无代价支配。range+W0仅34/50，低于W0始终38/50，也不能解释guard的全部效果。','',
'保留guard进入从零初始化的两次最终训练，并把“不重训、旧权重加同一guard”保留为新确认强对照。只改变输入适配约束，不同时更改奖励、mask、窗口或选点。开发选点不足的H3没有在本轮另加修复，不声称已排除。','']
(d/'DIAGNOSIS_ZH.md').write_text('\n'.join(lines),encoding='utf-8');print(d/'DIAGNOSIS_ZH.md')
