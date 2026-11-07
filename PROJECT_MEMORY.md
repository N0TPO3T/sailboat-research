# 长期经验

## 回放加权必须保持真实交互时钟
Tags: replay, SAC, warmup, paired-training
Conclusion: 通过重复插入加权转移时，用buffer.size触发更新会提前开启Q预热，混入优化预算差异。应同时用真实控制步数约束更新门槛，按物理步核对Q更新数。
Evidence: runs/round4_20261025/implementation_check.json、PROTOCOL.md；旧试运行同源control479步56次Q更新、加权483步64次（同物理门槛应为57次），v2统一steps>=256后逐回合通过updates=max(0,floor(steps/4)-63)。
Implication: 以后改变replay权重/副本/容量时，先核查更新、预热、保存和开发评估分别依赖哪个时钟；不能仅看总步数相同就认定预算一致。

