# B2 完整结果索引

最终决策：idea-stage/IDEA_REPORT.md；独立复核：notes/critical_review.md。

|目录|用途与有效性|
|---|---|
|candidates/front_sampling/runs/main_v2|最终18场、轨迹NPZ、逐次横断、独立评分、收据；运动学代理|
|candidates/front_sampling/runs/*v1|首腿计分问题版本；历史保留，不用于最终结论|
|candidates/return_sampling/results|最终72方法任务行=24成对任务×3方法；配置、路径、真值、计时、验证|
|candidates/return_sampling/archive_no_planning_latency|原遗漏搜索时间的版本，不沿用其全按时结论|
|candidates/acoustic_update/stable_results|最终探索性修复；逐组预测、全部掩码、开发选择、历史状态、198评分、辅助指数、核验及图|
|candidates/acoustic_update/results|完整输入的失稳趋势原型；用于失败诊断，不据此否定应用|
|服务器 candidates/acoustic_update/invalid_transfer_race|部分输入传输竞态，无效；远端保留，不计科学结果|
|notes/needs_sources/xdat.Full.csv；candidates/acoustic_update/input/xdat.Full.csv|同一CC0公开数据；SHA256 b3936d9d7507679d3b98ed6f4e0db34a4f6011e43c346e59491a7ff267006b7b|
|notes/；.aris/|独立意见、来源深度、预算、设备与工作流回执|

## 复现

服务器根目录 /home/ot/Students/hs/sailboat-track-b/discovery_b2。Python：/home/ot/Students/hs/sailboat-routing-v0/.venv/bin/python。无训练权重或新依赖。统一单线程、GPU隐藏；所有输出与cache必须位于hs。

F：在 candidates/front_sampling 下，用上述 Python 执行 `pilot.py --phase main --out runs/reproduce_v2`。实际冻结源码见对应run内快照；不可将v1计分与v2混用。

I：pilot.py写固定results路径。请先将 candidates/return_sampling 整个目录复制到B2内新的复现目录，随后按该目录 RESULTS.md 的单线程命令运行 pilot.py 与 verify.py，不覆盖归档结果。

U：在 candidates/acoustic_update 下执行 `bash RUN.sh`，输出stable_results_reproduce；用相同Python执行 `verify.py stable_results` 可只核验归档。原始与稳定版本分别是pilot.py/pilot_stable.py，协议分别为PROTOCOL_initial.md/PROTOCOL.md。

## 打包范围

预览包包含报告、HTML、代码、配置、必要数据、全结果与独立意见。未用于pilot的EK80大raw、缓存、字节码不纳入；原件仍保留在磁盘/服务器。不得将已有资产或第三方代码改授开源许可。文件级SHA256见PACKAGE_MANIFEST.json，zip完整性见PACKAGE_CHECK.json（包外）。
