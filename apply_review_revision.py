from pathlib import Path
import json,shutil,hashlib,datetime
p=Path(r'C:/Users/74095/hs/SailBoat/sailboat-track-b')
old=p/'reviews/submitted_v1';old.mkdir(parents=True,exist_ok=True)
for name in ['B_METHOD_NOTE.md','B_RESEARCH_REPORT.md','REVIEW_INPUT_MANIFEST.json']:
 shutil.copy2(p/'docs'/name,old/name)
f=p/'docs/B_METHOD_NOTE.md';s=f.read_text(encoding='utf-8').replace('零取+1','零取−1')
s=s.replace('或持续120s上限；退出后低速计数清零、冷却10s。','或恢复age达到120；触发点age先置0后立即加1，退出检查先于本步动作，因此最多执行119个1s恢复动作区间。退出后低速计数清零、冷却10s；冷却期间仍累计低速计数，冷却结束可立即重触发。')
s=s.replace('原模型直接控制带符号帆角并限制速率。','原模型直接控制带符号帆角并限制速率。同侧90°是理想帆角定位接口的命令，不自动等于被动松帆或卸载；本实现没有继承Viel2018式(12)随视风变化的帆角可达约束，可能仍需要主动保持帆面。')
s=s.replace('**背景。**','区内时间只作为可用观测时间的几何代理；采样质量、横倾/速度对观测的影响及任务达标阈值均未验证。release和匹配luff均保留为可用候选，不宣称应用最优权衡。\n\n**背景。**',1)
s=s.replace('t=25s退出恢复。','t=25s退出恢复时纵速仍为负；退出只表示朝向已进入横风/下风半平面，之后才恢复正向运动，不等于该时刻已恢复正向推进或直接测得操纵性。')
f.write_text(s,encoding='utf-8')
f=p/'docs/B_RESEARCH_REPORT.md';s=f.read_text(encoding='utf-8').replace('# B研究报告：先恢复操纵能力，再继续区域观测','# B研究报告：低速迎风恢复与区域观测的有限验证')
s=s.replace('3胜/8平/1负。因此','3胜/8平/1负。8个区内起始任务均为100%且配对相同；四个区外接入任务区内时间差依次为−19、+28、+32、+30s，合计小优势来自接入过程，不证明持续驻留稳定性普遍提升。因此')
s=s.replace('**定位。**','**观测效用边界。** 区内时间是可用观测时间的几何代理，尚未验证采样质量、空间采样偏差、允许中断或船速/横倾容忍条件。最长离区包含首次接入前时段。release和匹配luff均有保留价值，当前没有应用效用模型支持唯一最优选择。\n\n**定位。**',1)
s=s.replace('帆恢复模式而非','帆恢复模式而非')
s=s.replace('首要指标是1200个1Hz位置采样的区内比例；','各表SD为不同条件任务间的离散度，不是重复训练误差。首要指标是1200个1Hz位置采样的区内比例；')
s=s.replace('恢复从t=9到25s，显示','恢复从t=9到25s；t25退出时仍倒航，退出是朝向条件，随后才恢复正向运动。图显示')
s=s.replace('## 8. 复现、资源和材料','固定±90°只是当前理想定位接口的最大角命令；即使与简化视风同侧，也未满足Viel2018式(12)随视风变化的帆角可达约束，不能称为真实柔性帆被动松帆/卸载验证。\n\n## 8. 复现、资源和材料')
s=s.replace('scripts/station_recovery.py与configs/recovery_confirmation.json、recovery_scale.json可运行，','冻结scripts/station_recovery.py含2026-10-08 15:13:40 UTC绝对预算截止；截止后用scripts/station_reproduce.py及已授权的B_RESEARCH_DEADLINE环境变量，精确单行差异见docs/REPRODUCTION_SOURCE_DIFF.json，科学控制/动力学/指标不变。对应configs/recovery_confirmation.json、recovery_scale.json，')
f.write_text(s,encoding='utf-8')
f=p/'RESULTS_INDEX.json';d=json.loads(f.read_text(encoding='utf-8'))
for x in d:
 if x['batch']=='confirmation':x['interpretation']='v1 originally frozen new-instance validation; subsequently used as development; never pool with v2 as unseen confirmation'
f.write_text(json.dumps(d,indent=2),encoding='utf-8')
f=p/'docs/ASSET_AND_SENSOR_SCOPE.md';s=f.read_text(encoding='utf-8').replace('User confirmation on2026-10-07','Explicit user confirmation');f.write_text(s,encoding='utf-8')
(p/'reviews/AUTHOR_RESPONSE.md').write_text('''# B 三位独立首审：逐项作者回应

同一首审版本由docs/REVIEW_INPUT_MANIFEST.json绑定；被审正文另存reviews/submitted_v1。三位真实独立agent先提交后才统一修订；容量失败经同身份有限恢复，不算完成审查，不改变结果方向。所有本轮修改为文档/元数据，没有改算法、权重或成绩，没有新增航行实验。

## 方法审查

M1 接受复现表述问题。README在首审前已提供station_reproduce.py，但报告§8遗漏。现已在§8明确归档截止2026-10-08 15:13:40 UTC、B_RESEARCH_DEADLINE与新batch。REPRODUCTION_SOURCE_DIFF.json证明只替换墙钟守卫一行，默认截止保持、科学代码不变、未用于已报告实验；无需再造运行器。

M2 接受精确语义修订。方法说明将q零点改为−1；明确触发点age立即加1、age120先退出后执行，因此至多119个恢复动作区间。冷却期间继续累计低速计数，冷却结束可立即重触发。没有改代码迁就文字。

M3 接受边界。简化视风侧不等于完整气动力侧；同侧90°仍是可直接定位模型内参考，非真实帆索可执行性证明。

## 证据审查

E1 已将RESULTS_INDEX的confirmation标签改为“v1当时冻结，后来用于开发，不与v2混作未见确认”。完整根索引、ledger和原始日志在本地校验同步；保留原冻结收据。

E2 已在报告首页列出8区内全平与4接入−19/+28/+32/+30s；最长离区包含首次接入，SD是条件间离散度。这些是已有日志解释，无须追加样本。

E3 保持收窄：主要证据是恢复模式，精确90°规则独占价值未建立，100m四风险任务不外推广泛优势。

## 应用审查

A1 接受。明确未继承Viel式(12)随视风变化帆角可达约束。将90°解释为理想帆角定位命令，不因同侧就称为被动松帆或卸载；真实机构仍未验证。

A2 接受范围收窄。区内时间是几何观测可用代理；质量、容忍中断及任务效用未验证。release和luff_no_build均保留，不事后编造刚好通过的任务阈值。

A3 采用审查允许的图注修复而非重复重画：报告首页突出3/8/1及成本，图06配合逐任务分解；图08图注明确t25退出时仍倒航、退出仅朝向条件、其后才正向运动。研究报告改题为低速迎风恢复的有限验证，不把未测操纵性当直接结论。原图均来自真实日志并保留。

## 资源与交付

一次调度未等旧批明确退出便启动下一批。事后活跃回合时间代理未见重叠，但不能排除进程启动/清理重叠；不声称严格并发合规已证明。两批均exit_code=0，GPU为0，全部作业已结束。独立复核结论待三位实际提交，不预写Accept。
''',encoding='utf-8')
files=['docs/B_METHOD_NOTE.md','docs/B_RESEARCH_REPORT.md','RESULTS_INDEX.json','RESOURCE_LEDGER.json','README.md','reviews/AUTHOR_RESPONSE.md','docs/ASSET_AND_SENSOR_SCOPE.md','scripts/station_recovery.py','scripts/station_luff_control.py','scripts/station_reproduce.py','docs/REPRODUCTION_SOURCE_DIFF.json']
m={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'purpose':'targeted recheck; scientific code/results unchanged','files':{n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in files}}
(p/'docs/REVIEW_REVISION_MANIFEST.json').write_text(json.dumps(m,indent=2),encoding='utf-8')
print(json.dumps(m,indent=2))
