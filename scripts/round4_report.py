"""Report actual frozen confirmation, paired outcomes, costs, and handovers."""
import sys,json,csv,hashlib,zipfile
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];run=ROOT/'runs/round4_20261025';conf=run/'confirmation50';fig=run/'figures';fig.mkdir(exist_ok=True)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation,PillowWriter
frozen=json.loads((run/'freeze.json').read_text());summary=json.loads((conf/'summary.json').read_text())
read=lambda p:[json.loads(x) for x in p.read_text(encoding='utf-8-sig').splitlines()]
methods=['normal','w0','old_avoid','old_range','control_avoid','control_range','weighted_avoid','weighted_range']
final_prefix='weighted' if frozen['final_arm']=='takeover4' else 'control'
final_avoid=final_prefix+'_avoid';final_range=final_prefix+'_range'
rows_by={s:read(conf/f'seed_{s}/episodes.jsonl') for s in (20261011,20261012)}
pairs={s:json.loads((conf/f'seed_{s}/pairs.json').read_text()) for s in rows_by}
for s,rows in rows_by.items():
 with (conf/f'seed_{s}/episodes.csv').open('w',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
# Offline timeline reconstruction from saved observations; terminal active is a placeholder.
for source,rr in rows_by.items():
 events=[]
 for r in rr:
  d=np.load(conf/f'seed_{source}/trajectories/{r["seed"]}_{r["mode"]}.npz');t=d['t'];v=d['visible'];valid=d['valid'];visible_ids=np.flatnonzero(v)
  event=dict(seed=r['seed'],method=r['mode'],safe_complete=r['safe_complete'],first_visible=None if len(visible_ids)==0 else int(t[visible_ids[0]]),lost_visibility=[int(t[i]) for i in range(1,len(t)) if v[i-1] and not v[i]],reseen=[int(t[i]) for i in range(1,len(t)) if v[i] and not v[i-1]],expired=[int(t[i]) for i in range(1,len(t)) if valid[i-1] and not valid[i]],takeover_times=r['takeover_times'],handback_times=r['handback_times'],violation_time=r['time'] if r['violated'] else None,terminal_age=float(d['age'][-1]),valid_before_terminal=bool(valid[-2]),handback_before_violation=bool(r['violated'] and r['handback_times']))
  if event['first_visible'] is not None:
   j=event['first_visible'];event['first_visible_distance']=float(np.linalg.norm(d['target'][j]-d['raw'][j,:2]))
  events.append(event)
 (conf/f'seed_{source}/events.json').write_text(json.dumps(events,indent=2))

# Paired summary uses each pair's own common-safe set only.
lines=['# 双策略第四轮研究报告','',f"本轮最终协议在新确认前选择 `{frozen['final_arm']}`。两份第二轮专家各做普通适配和接管转移加权适配，共四次真实训练；这是两个历史专家上的配对适配，不是同一继承Actor起点的独立训练复现。",'', '## 已执行的诊断和干预','', '12条既有同状态分支已核验复用，新增4条固定末点分支。三个失败仍失败，有利案例仍成功但安全裕度降低；简单换末点不解决这些失败。W0在三条失败状态成功而在有利状态失败，说明专家行为存在局部收益与退化；不证明某个单步动作或失联mask是唯一根因。','', '第二轮真实range/risk接管后最初10步仅占全部物理转移的2.423%/2.450%。本轮唯一训练干预是在replay插入这些转移4份，普通对照1份；未新增独立几何状态。PER会改变实际采样权重，有限容量也使独立转移减少，因此不能将结果解释成纯粹增加数据覆盖。', '', '保持原18D障碍信息、26D窗口、5秒缓存/mask、4096可训练参数、奖励、运动学、执行器和range交还规则。无第三轮headon_guard、无额外路由网络。', '', '## 训练与选择', '', '每臂从对应第二轮selected Actor/normalizer热启动，重新初始化Q、优化器和replay。两臂同训练随机种子、场景序列生成规则和20000物理步预算；按完整回合结束，实际步数略超。开发用固定旧12场，avoid/range各跑一次。先最大化两模式较小安全数，再总安全数，再失败记700秒的航时之和，再最早步数；含step0以允许拒绝退化。', '', '| 源专家 | 训练臂 | 实际步数 | 选中步数 | 开发avoid/range | 训练秒 |','|---|---|---:|---:|---|---:|']
for r in frozen['selections']:lines.append(f"| {r['source']} | {r['arm']} | {r['complete']['steps']} | {r['selected_steps']} | {r['counts']['avoid']}/12，{r['counts']['range']}/12 | {r['complete']['wall_seconds']:.1f} |")
lines+=['', '加权方案只有在两个源的开发avoid均不低于普通适配、且range安全数合计增加时才被采用。两种训练臂均进入最终确认，禁止确认后重新挑选。初始试运行因回放复制提前触发更新门槛被终止并保留；v2四臂统一256真实步开始更新。', '', '开发评估会消耗全局Torch RNG；这是所有臂共同使用的现有协议，快照在开发前保存。恢复状态可重现加载后的SAC更新，但不据此声称恢复整段训练与原不中断运行逐位一致。', '', '## 新50场同场景确认', '', '940000—940049在冻结权重/方案后生成；与历史训练、开发及前三轮确认实例核对去重。none/away/late/edge_static各8，cross/headon各9；同一50场被两个源专家共享，不是100个独立场景。normal/W0各50次共享，其余6方法×2源×50构成逻辑比较；逐字节相同Actor/normalizer且相同控制模式的组按冻结身份复用，唯一实际回合数见下。所有失败保留，视域外目标仍计入安全。','', '| 方法 | 源20261011 | 源20261012 |','|---|---:|---:|']
ss=summary['training_seeds']
for m in methods:lines.append(f"| {m} | {ss['20261011'][m]['safe_complete']}/50 | {ss['20261012'][m]['safe_complete']}/50 |")
lines+=['', '| 源专家 | 方法 | none | away | late | cross | headon | edge_static |','|---|---|---:|---:|---:|---:|---:|---:|']
for s in rows_by:
 for m in methods:lines.append('| '+str(s)+' | '+m+' | '+' | '.join(str(ss[str(s)][m]['by_kind'][k]) for k in ('none','away','late','cross','headon','edge_static'))+' |')
lines+=['', '## 配对安全和代价','', '下表B−A；救回/损失为安全完成的配对变化。航时和航程仅在该对共同安全场景计算，失败早停不算加速。完整全部28对及逐场差值见各seed目录pairs.json。','', '| 源 | B−A | 救回/损失 | 共同安全n | 平均Δ航时s | 最坏Δ航时s | 平均Δ航程m | 最坏Δ航程m |','|---|---|---|---:|---:|---:|---:|---:|']
keys=['w0-minus-normal','old_avoid-minus-w0','control_avoid-minus-old_avoid','weighted_avoid-minus-control_avoid','weighted_range-minus-control_range',final_range+'-minus-'+final_avoid,final_range+'-minus-old_range']
for s in rows_by:
 for key in dict.fromkeys(keys):
  p=pairs[s][key];n=lambda v:'NA' if v is None else f'{v:.2f}'
  lines.append(f"| {s} | {key} | {len(p['rescued'])}/{len(p['lost'])} | {len(p['common_safe'])} | {n(p['time']['delta_mean'])} | {n(p['time']['max_degradation'])} | {n(p['path_length']['delta_mean'])} | {n(p['path_length']['max_degradation'])} |")
lines+=['', '## 交接与计算成本','', '| 源 | 方法 | 到达 | 违规 | 超时 | 最小距离m | 切换总数 | 平均专家秒 | 接管/交还回合 | 交还后安全到达 | 决策ms/步 |','|---|---|---:|---:|---:|---:|---:|---:|---|---:|---:|']
for s in rows_by:
 for m in methods:
  r=ss[str(s)][m];lines.append(f"| {s} | {m} | {r['arrived']} | {r['violations']} | {r['timeouts']} | {r['min_distance']:.2f} | {r['switches']} | {r['takeover_seconds_mean']:.1f} | {r['takeover_episodes']}/{r['handback_episodes']} | {r['finished_normal_after_handback']} | {r['decision_ms_per_step']:.3f} |")
lines+=['',f"唯一实际确认{summary['physical_rollouts']}回合，耗时{summary['wall_seconds']:.1f}秒，最多4个单线程CPU worker。非normal每步仍计算两个Actor；接管减少不是计算节省。安全裕度和最坏退化比均值更能暴露风险；本实验不是实船安全保证。",'', '## 结果归因边界','', 'W0对normal隔离的是窗口/历史接口整体差异，不能单独归因某一种历史语义。old_avoid对W0衡量旧学习适配。weighted对control衡量本轮接管回放加权加上其训练轨迹反馈的净作用；共同选点规则相同。每个range对自身avoid衡量同一权重的路由作用。跨新旧训练同时改变初始化Q/replay和选点方式，不能把其全部变化归于回放加权。','', '该小分支组可排除“只需更换末点”作为本组失败的充分修复，并表明行为可行性具有策略依赖。它不能证明广泛状态覆盖不足、不能隔离失联的独立因果作用。新确认不再用于调参；负结果同样保留。','', '## 证据与复现','', '实际命令见runs/round4_20261025/COMMANDS.md；协议PROTOCOL.md；完整分支diagnosis/；训练来源、选择规则及冻结身份freeze.json；原始逐回合和轨迹confirmation50/parts/；全部配对和轨迹核验confirmation50/seed_*/。选中检查点与恢复状态checkpoints/round4/<源>/<臂>/；终末恢复状态和所有中间点保存在远端train_v2_*目录。','', '仅一次ARIS针对新增实现的检查，same-family/provisional；未执行全仓审计或论文评审。审查发现与处理详见implementation_check.json及PROTOCOL.md，不将检查称为方法有效性证明。']
(ROOT/'REPORT_ROUND4_ZH.md').write_text('\n'.join(lines),encoding='utf-8')
# Three evidence figures.
fig1,axes=plt.subplots(1,2,figsize=(12,4))
for ax,s in zip(axes,rows_by):
 for arm,color in [('control','C0'),('takeover4','C1')]:
  ds=read(run/f'train_v2_{s}_{arm}/development.jsonl')
  for mode,style in [('avoid','-'),('range','--')]:
   ax.plot([d['steps'] for d in ds],[sum(r['safe_complete'] for r in d['results'] if r['mode']==mode) for d in ds],style,color=color,label=arm+'/'+mode)
 ax.set(title=f'Source {s}',xlabel='Physical training steps',ylabel='Safe completions / 12',ylim=(0,12.5));ax.legend(fontsize=8);ax.grid(alpha=.2)
fig1.tight_layout();fig1.savefig(fig/'01_development.png',dpi=160);plt.close(fig1)
fig2,ax=plt.subplots(figsize=(11,4));x=np.arange(len(methods));width=.36
for i,s in enumerate(rows_by):ax.bar(x+(i-.5)*width,[ss[str(s)][m]['safe_complete'] for m in methods],width,label=str(s))
ax.set_xticks(x,methods,rotation=25,ha='right');ax.set(ylabel='Safe completions / same 50 scenes',ylim=(0,52));ax.legend();fig2.tight_layout();fig2.savefig(fig/'02_confirmation.png',dpi=160);plt.close(fig2)
fig3,axes=plt.subplots(1,2,figsize=(11,4))
for ax,key in zip(axes,['weighted_range-minus-control_range',final_range+'-minus-'+final_avoid]):
 for s in rows_by:
  p=pairs[s][key];ax.scatter([r['delta'] for r in p['time']['per_scene']],[r['delta'] for r in p['path_length']['per_scene']],alpha=.7,label=str(s))
 ax.axhline(0,color='grey',lw=.7);ax.axvline(0,color='grey',lw=.7);ax.set(title=key,xlabel='Time delta (s), common safe only',ylabel='Path delta (m)');ax.legend()
fig3.tight_layout();fig3.savefig(fig/'03_paired_cost.png',dpi=160);plt.close(fig3)
# Deterministic descriptive selection; preserve a loss, a rescue, a handback if available.
cases=[]
# One rescue, one loss relative to the same expert, and worst common-safe time cost.
for s in rows_by:
 ids=pairs[s][final_range+'-minus-old_range']['rescued']
 if ids:cases.append((s,ids[0],'rescue','old_range'));break
for s in rows_by:
 ids=pairs[s][final_range+'-minus-'+final_avoid]['lost']
 if ids:cases.append((s,ids[0],'routing loss',final_avoid));break
costs=[(r['delta'],s,r['seed']) for s in rows_by for r in pairs[s][final_range+'-minus-'+final_avoid]['time']['per_scene']]
if costs:
 delta,s,seed=max(costs);cases.append((s,seed,f'cost +{delta:.0f}s',final_avoid))
if not cases:cases=[(20261011,940024,'first cross','old_range')]
cases=cases[:3];fig4,axes=plt.subplots(1,len(cases),figsize=(5*len(cases),4),squeeze=False);loaded=[];artists=[]
for ax,(s,seed,label,baseline) in zip(axes[0],cases):
 ds=[np.load(conf/f'seed_{s}/trajectories/{seed}_{mode}.npz') for mode in (baseline,final_range)];loaded.append(ds)
 spec=json.loads(str(ds[0]['spec']));ax.plot(500,0,'g*',ms=10)
 for pos in spec['statics']:ax.add_patch(plt.Circle(pos,40,fill=False,color='grey'))
 a=[]
 for mode,color in [(baseline,'C0'),(final_range,'C1')]:
  line,=ax.plot([],[],color=color,label=mode);dot,=ax.plot([],[],'o',color=color);a.append((line,dot))
 target,=ax.plot([],[],'rx');circle=plt.Circle((0,0),40,fill=False,color='r',alpha=.3);ax.add_patch(circle);text=ax.text(.01,.98,'',transform=ax.transAxes,va='top',fontsize=8)
 ax.set(xlim=(-40,550),ylim=(-230,230),aspect='equal',title=f'{s} / {seed} / {label}');ax.legend(fontsize=7,loc='lower right');artists.append((a,target,circle,text))
max_t=max(len(d['t']) for ds in loaded for d in ds)
def animate(t):
 for ds,(a,target,circle,text) in zip(loaded,artists):
  labels=[]
  for d,(line,dot) in zip(ds,a):
   j=min(t,len(d['t'])-1);line.set_data(d['raw'][:j+1,0],d['raw'][:j+1,1]);dot.set_data([d['raw'][j,0]],[d['raw'][j,1]]);k=min(j,len(d['t'])-2);labels.append(('A' if d['active'][k] else 'N')+(' ended' if t>=len(d['t'])-1 else ''))
  d=max(ds,key=lambda trace:len(trace['t']));j=min(t,len(d['t'])-1);spec=json.loads(str(d['spec']))
  if spec['target_position'] is not None:target.set_data([d['target'][j,0]],[d['target'][j,1]]);circle.center=d['target'][j]
  else:target.set_data([],[]);circle.set_visible(False)
  text.set_text(f't={t}s base/range: {labels}\nTarget shown for evaluation, not policy input')
 return []
fig4.tight_layout();ani=FuncAnimation(fig4,animate,frames=range(0,max_t+4,4),interval=150,blit=False);ani.save(fig/'04_cases.gif',writer=PillowWriter(fps=7));plt.close(fig4)
(fig/'manifest.json').write_text(json.dumps(dict(cases=cases,selection='first final-vs-old range rescue; first same-expert routing loss; largest common-safe routing time cost (tie by source,scene); descriptive only',frame_stride_seconds=4),indent=2))
print(json.dumps(dict(report='REPORT_ROUND4_ZH.md',figures=4,final_arm=frozen['final_arm'],cases=cases)))

