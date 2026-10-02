# 接力入口

项目上下文已合并到根目录四文件，不在本页独立维护状态：

1. [AGENTS.md](../AGENTS.md)：操作边界与跨设备协议。
2. [PROJECT_STATE.md](../PROJECT_STATE.md)：当前事实、证据和恢复材料。
3. [CURRENT_PLAN.md](../CURRENT_PLAN.md)：当前目标与下一步。
4. [PROJECT_MEMORY.md](../PROJECT_MEMORY.md)：按需检索的长期经验。

运行与同步命令见[README](../README.md)。服务器工作区为开发入口，本地镜像需先核对版本及服务器未提交工作。

## V0.1 诊断完成（2026-10-02）

已完成同状态评分与已有日志统计，详见 [V0_1_DIAGNOSIS.md](ep_result/V0_1_DIAGNOSIS.md)。仅一次估计风补日志且完整复现；新产物在 `runs/v0_1_diagnosis_20261002/`。本轮到此停止，未实施下一轮建议。

## V0.2 计划冻结

产物 runs/v0_2_margin_20261002T142441Z/；总预算2小时、实验30分钟、正式24/总启动26、review一次。先核验及6回合，通过门槛才18回归。计时起点和当前版本见plan.json；当前尚未启动实验。

V0.2主实验6回合完成；继续门槛=False，详见runs/v0_2_margin_20261002T142441Z/main_gate.json；本轮进程累计约60.5秒。

V0.2交付完成：57测试、同状态核验、6正式回合、一次同家族review（provisional）；运行进程54.76秒，含核验/分析账本62.27秒，截至review总历时11.40分钟。25m三方法均无候选失败，18回归按门槛跳过；完整报告 [V0_2_RESULTS.md](V0_2_RESULTS.md)。唯一下一步建议是离线检查t=165候选覆盖，不在本轮实施。
