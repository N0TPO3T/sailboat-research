# 独立环境见证

2026-11-05，按 ARIS run-experiment 的 agent-follows-doc 要求，由新建子 agent `/root/a_fair_environment_witness` 读取技能、服务器环境说明和本轮 environment.json，原样执行其中 smoke_command。

退出码 0，见证位于 `smoke/1793868936358568097/witness.json`。12 个控制步、13 个状态与旧参考轨迹逐值一致，控制动作逐值一致。CPU 随机核见证 seed=20261105，kernel_sum=-4.789722919464111。Python 3.13.11、Torch 2.13.0+cpu、NumPy 2.4.6、SciPy 1.18.1 符合声明版本；SciPy 由独立只读版本命令核查。

见证的 complete=false、success=false 对应预期 bounded_smoke，而非完整任务失败。Gymnasium 的 Box 精度转换警告为继承实现警告，未修改或隐藏。

子 agent 指出旧 provider ledger 缺少规范化 spec hash。本轮另建 `.aris/compute/a_fair_ssh.md` 记录环境规范哈希 17e51db5，并保留旧 ledger。未安装或更改依赖、共享环境、权重。

此独立检查仅覆盖环境与规定的前缀见证，不是论文科学评审。正式结果的全量轨迹复算由主 agent 编写的 audit_results.py 完成，属于自检，不冒充独立外审。
