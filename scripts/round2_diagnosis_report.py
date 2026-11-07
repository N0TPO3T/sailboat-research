"""Readable record of the fixed diagnostic evidence, including negative controls."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from dynamic import *
run=ROOT/'runs/round2_20261011';d=run/'diagnosis'
cases=json.loads((d/'key_cases.json').read_text());pairs=json.loads((d/'round1_pairs.json').read_text())
branches=[json.loads(l) for l in (d/'branches/results.jsonl').read_text().splitlines()]
lines=['# 首轮五场交接诊断（第二轮开发材料）','',
'结论：两场range损失与不必要进入一致；共同cross损失发生在首次可见即接管后，没有交还，且正常/初始窗口专家在同状态可成功。先补训练实际接管分布，不同时改mask、奖励、网络和路由。单例分支支持策略/状态相互作用，不证明训练覆盖是唯一根因。','',
'![相同真实前缀的完整分支](910009_same_state_branches.png)','',
'![cross同步时间线](910009_timeline.png)','',
'## 时间线','',
'标记：visible为可见，valid为5秒缓存有效，danger为已有CPA/任务方向风险条件，active为实际专家接管；+进入，−退出。terminal只表示终止状态，没有新动作或交还。时间单位秒。','']
for c in cases['cases']:
    lines += [f'### {c["seed"]} / {c["kind"]}','', '| 方法 | 安全完成 | 事件时间线 | 全窗口缺动态信息的步数 |','|---|---:|---|---:|']
    for m,x in c['methods'].items():
        events='；'.join(str(e['t'])+':'+','.join(e['changes']) for e in x['events'])
        lines.append(f'| {m} | {x["result"]["safe_complete"]} | {events} | {x["completely_missing_steps"]} |')
    lines.append('')
lines += ['## 七个预先固定的完整分支','',
'全部从reset重放实际命令前缀，每步核对原物理状态、风与帆舵设定值。normal自己的循环记忆、专家窗口和路由计时都由该前缀维护；同一分支点的完整状态指纹一致。没有拿同时间的不同轨迹冒充同状态。续接协议为指定策略一直执行到终止，未扫描切换时刻。','',
'| 场景 | 分支时刻 | 后续策略 | 安全完成 | 结束/s | 最小间距/m |','|---|---:|---|---:|---:|---:|']
for b in branches:lines.append(f'| {b["seed"]} | {b["cut"]} | {b["continuation"]} | {b["safe_complete"]} | {b["time"]} | {b["min_distance"]:.2f} |')
lines += ['', '同状态动作例（归一化增量命令顺序为帆、舵；不是帆舵绝对角）：','']
for seed,cut in [(910009,86),(910009,102),(910010,90)]:
    z=np.load(d/f'branches/{seed}_{cut}_trained.npz');i=cut
    def array_text(values,digits):return '['+', '.join(f'{v:.{digits}f}' for v in values)+']'
    lines.append(f'- {seed}@{cut}s：船位{array_text(z["raw"][i,:2],2)}，航向{np.degrees(z["raw"][i,3]):.2f}°，体纵速{z["raw"][i,4]:.2f}m/s；normal={array_text(z["normal_action"][i],4)}，trained={array_text(z["trained_action"][i],4)}，initial={array_text(z["initial_action"][i],4)}。')
lines += ['', '分支旧NPZ末行的setpoints及影子策略输出沿用了上一动作边界，属于一次检查发现的日志问题；该末行这些字段不得用于终止状态恢复。真实raw/time/target、分支点指纹、全部已执行动作和结局不受影响。未来生成代码已修正；现有原始文件保留且明确标注，不伪造新的执行数据。', '',
'## 证据支持的判断','',
'- 910002、910014：risk未接管并分别176/174s安全到达；range在97/75s没有danger时接管，随后104/80s出现danger并最终违规。完整前缀相同，支持无谓接管可把安全航行变坏。已有risk避免这两次进入，无需再为此堆新阈值。',
'- 910009：range/risk首次可见86s即接管，133s违规，均无交还。86s同状态trained失败，normal170s和initial167s完成。该专家在这个状态的适配动作不合适，不能把失败称为普通控制必然无解或单纯风险路由延迟。',
'- 910009：97s失去视域、102s缓存失效，110s再见；此段不足以让10步窗口完全清空目标信息。127s再失效、131s再见。102s改normal可204s到达，但该分支同时改变整套策略，不能单独证明mask是原因，也不能据此制定“失联就交还”。',
'- 910010：专家从初态始终运行失败，但normal真实前缀90s后trained和initial都安全。相同专家从不同实际状态结果不同，整回合成功集合不能代表接管可达能力。trained比initial此分支慢53s，不应只展示其安全。',
'- 910008：normal和路由全程未见目标而安全；专家在不同初始控制轨迹上75s见目标、98s违规。normal streaming与专家窗口不同，不能把这一整回合差异全部归因于新增动态列。',
'- 因此本轮只干预训练接管分布，保持三种实际使用起点。未进行同随机种子的完整分布消融；两次新训练结果可回答重复性，不能单独把收益因果归于分布修改。','',
'## 首轮两两共同安全效率','',
'差值为后者−前者；失败停止时间全部排除。更快/同/更慢均在该对自己的共同安全集合上计数。','',
'| 对照（后−前） | 共同安全 | 救回/丢失 | 时间均值前→后/s | 时间差均值/中位/最大/s | 更快/同/慢 | 航程均值前→后/m | 航程差均值/中位/最大/m | 短/同/长 |',
'|---|---:|---:|---|---|---|---|---|---|']
for name,p in pairs.items():
    t=p['time'];l=p['path_length']
    lines.append(f'| {name} | {len(p["common_safe"])} | {len(p["rescued"])}/{len(p["lost"])} | {t["a_mean"]:.2f}→{t["b_mean"]:.2f} | {t["delta_mean"]:.2f}/{t["delta_median"]:.2f}/{t["max_degradation"]:.2f} | {t["faster"]}/{t["equal"]}/{t["slower"]} | {l["a_mean"]:.2f}→{l["b_mean"]:.2f} | {l["delta_mean"]:.2f}/{l["delta_median"]:.2f}/{l["max_degradation"]:.2f} | {l["faster"]}/{l["equal"]}/{l["slower"]} |')
lines += ['', 'risk−avoid直接共同安全21场平均−6.67s、−11.38m；四组共同12场的+8.17s属于不同子集。不能只选较有利的分母。逐场差值及ID在round1_pairs.json。','']
(d/'DIAGNOSIS_ZH.md').write_text('\n'.join(lines),encoding='utf-8')
print(d/'DIAGNOSIS_ZH.md')
