import json,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];run=ROOT/'runs/round4_20261025';out=run/'diagnosis'
old=ROOT/'runs/round3_20261011_2308/diagnosis/branches';new=out/'final_branches'
read=lambda p:[json.loads(x) for x in p.read_text(encoding='utf-8-sig').splitlines()]
previous=read(old/'results.jsonl');added=read(new/'results.jsonl');rows=[]
for r in added:
 baseline=[x for x in previous if x['train_seed']==r['train_seed'] and x['seed']==r['seed']]
 assert len(baseline)==3 and all(x['fingerprint']==r['fingerprint'] for x in baseline)
 for label,z,folder in [('selected' if x['continuation']=='trained' else x['continuation'],x,old) for x in baseline]+[('terminal_checkpoint',r,new)]:
  d=np.load(folder/f'{z["file"]}.npz');cut=z['cut'];t=d['t'];vis=d['visible'];valid=d['valid'];end=int(t[-1]);changes=lambda arr:[int(t[i]) for i in range(1,len(arr)) if arr[i]!=arr[i-1]]
  rr=dict(z,continuation=label,source=str((folder/f'{z["file"]}.npz').relative_to(ROOT)),visibility_changes=changes(vis),validity_changes=changes(valid),violation_time=end if z['violated'] else None,terminal_age=float(d['age'][-1]),first_post_takeover_action=d['action'][cut].tolist())
  rows.append(rr)
(out/'paired_branches.json').write_text(json.dumps(rows,indent=2))
coverage=[]
for source in (20261011,20261012):
 logs=read(ROOT/f'runs/round2_20261011/train_{source}/learning.jsonl')
 for kind in sorted({r['kind'] for r in logs}):
  for mode in ('avoid','range','risk'):
   subset=[r for r in logs if r['kind']==kind and r['start_mode']==mode];taken=[r for r in subset if r['takeover_time'] is not None]
   coverage.append(dict(source=source,kind=kind,start_mode=mode,episodes=len(subset),taken=len(taken),early10_transitions=sum(min(10,r['time']-r['takeover_time']) for r in taken) if mode!='avoid' else 0,physical_steps=sum(r['time'] for r in subset),expert_steps=sum(r['expert_steps'] for r in subset)))
(out/'coverage.json').write_text(json.dumps(coverage,indent=2))
lines=['# 第四轮小分支诊断','', '复用12条既有真实同状态分支，新增4条末点分支；所有分支状态指纹与对应历史状态完全相同。仅固定首次实际接管，无切换时刻扫描。','', '| 源专家 | 场景 | 分支 | 安全完成 | 最小距离 m | 结束 s |','|---|---|---|---:|---:|---:|']
for r in rows:lines.append(f"| {r['train_seed']} | {r['seed']} | {r['continuation']} | {int(r['safe_complete'])} | {r['min_distance']:.3f} | {r['time']} |")
lines+=['','事实：三个失败在末点仍失败，正例仍成功但裕度降低。因此此次有限检查不支持以末点替换selected作为修复。它没有排除其他选点规则的价值。','', '事实：三个失败状态W0均成功，但正例W0失败；相同物理/历史条件下策略动作改变结果，不能用状态必然不可解来解释。分支固定接管到终点，排除了提前交还作为这些分支失败的必要原因；并未隔离某一个动作或失联机制。','', '覆盖统计仅表示暴露次数与最初10步转移数，不能证明几何状态覆盖。干预对这些实际转移增加replay副本，检验优化权重；不称新增了独立状态。PER及容量造成的有效多样性变化属于机制限制。','', '| 源专家 | 实际range/risk接管回合 | 最初10步转移 | 全物理转移 | 比例 |','|---|---:|---:|---:|---:|']
for source in (20261011,20261012):
 rr=[r for r in coverage if r['source']==source];early=sum(r['early10_transitions'] for r in rr);total=sum(r['physical_steps'] for r in rr);takes=sum(r['taken'] for r in rr if r['start_mode']!='avoid')
 lines.append(f'| {source} | {takes} | {early} | {total} | {early/total:.3%} |')
lines+=['','完整逐分支事件见paired_branches.json，分类型训练计数见coverage.json。新训练/确认结论须等待真实运行，不由这些诊断预先决定。']
(out/'DIAGNOSIS_ZH.md').write_text('\n'.join(lines),encoding='utf-8');print('\n'.join(lines))
