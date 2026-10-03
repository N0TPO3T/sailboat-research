# Current Plan — R2 frozen evaluation

目标：完成R2固定低层的安全/效率与简化研究，交付真实航迹图和可复现报告。

四轮开发648回合已完成，另3场原R1逐值复现。完整72开发实例中：前向/窄候选/纯路线成本65安全到达，R1为63，100m有效持有门64，去改点代价62，无预测几何接力61，趋势接力62。选择forward500主方案；分支去留详见run/method_freeze.json。短径向与角度消融限于开发证据，不宣称普遍等价。

主方法、参数、分析和选图规则已固定。下一步仅生成并运行seed1271的72新平衡实例×4方法（R1、Forward、RouteCost、几何Relay），共288回合，全部新跑。不能根据最终结果换主方法或调参。完成后做原始指标复算、PNG/SVG实际航迹图、离线HTML、研究报告、result-to-claim审查与本地预览包。

冻结原低层、归一化、动力学、因果历史、t→t+1协议与真实安全/到达判据。预算仍为原12小时、最多8轮、4个单数值线程CPU实验进程、GPU0；未重置计时。保护旧产物和本地未提交改动，不push。

恢复：runs/r2_autoresearch_20261003T063153Z/plan.json、method_freeze.json；最终运行完成以final/completion.json为准。
