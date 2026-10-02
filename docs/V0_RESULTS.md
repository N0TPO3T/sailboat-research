# V0 结果与验收（2026-10-02）

## 结论
A→B→C→D 最小工程与开发诊断链路已完成；没有证明估计风优于几何基线。冻结控制器保持不变，未进行低层/高层 RL 或追加调参。负结果保留，不视为论文方法已成立。

## 隔离与验收
- 独立服务器仓库：`/home/ot/Students/hs/sailboat-routing-v0`；运行实现提交 `857ff57`，协议及资产身份见 `runs/navigation_admission.json`。
- 本轮重新核对只读上游1351文件，无新增/修改/删除，Git状态一致：`runs/audit/upstream_integrity_v0_final_20261002.json`。继承清单与哈希见 `docs/UPSTREAM_MANIFEST.md`。
- A：固定输入及两组短闭环误差0；原500m四风况×3seed为12/12。B：约1km为5/6，目标切换连续性通过；失败在首次切换前，同条件原500m也失败。旧失败未抹除。
- 新协议准入：54项测试通过；真实274步完整约1km旁路开/关轨迹与动作逐值一致，两次目标切换连续。另有140步变风检查，标签时刻/位置与场查询误差0。证据：`runs/v0_admission_final_20261002/`。
- 修复短程capture误标完整、NumPy标量JSON保存及风场坐标精度一致性；初始无路保留为失败行。两次开发准入失败日志完整保留。

## C：当前局部风读出
20个完整episode按场景分12/4/4；18到达、2训练episode超时，失败仍保留。冻结14D观测+256D历史特征，train-only标准化；validation从0.1/1/10中选alpha=0.1，test只评估一次。

| 测试范围 | 有效帧 | MAE (°) | P90 (°) |
|---|---:|---:|---:|
| 整体 | 1940 | 17.01 | 48.26 |
| 目标切换窗口 | 79 | 10.04 | 20.60 |
| 风变化响应窗口 | 20 | 41.51 | 82.51 |

窗口为10步；1976测试帧中1940有效，初始化不足标为无效。向量模长只判退化，不是置信概率。响应窗口只有20帧，不支持强泛化结论。模型与数据：`runs/v0_fit_20261002/model.npz`、同目录result.json、`runs/v0_capture_20261002/`。

## D：固定12场景×三方法
稳定/慢变/快变风各4场，包含开阔、单障碍、宽通道与偏转终点。open_turn只是偏转终点，不等于强制访问中间转角；适度转折连续性另见B。全部36次均完整执行，失败纳入分母；效率只统计三方法共同成功场景。

| 方法 | 安全到达 | 共同成功样本 | 平均航时(s) | 平均航程(m) |
|---|---:|---:|---:|---:|
| geometry_only | 9/12 | 8 | 540.00 | 1308.32 |
| oracle_local | 8/12 | 8 | 540.00 | 1308.32 |
| estimated_local | 9/12 | 8 | 540.00 | 1308.32 |

逐场结果（✓=安全到达；其余为失败原因）：

| 场景 | geometry_only | oracle_local | estimated_local |
|---|---|---|---|
| stable_open | ✓ | ✓ | ✓ |
| stable_single_obstacle | ✓ | ✓ | ✓ |
| stable_wide_channel | NoRouteError | NoRouteError | NoRouteError |
| stable_open_turn | ✓ | ✓ | ✓ |
| slow_open | ✓ | ✓ | ✓ |
| slow_single_obstacle | NoRouteError | NoRouteError | NoRouteError |
| slow_wide_channel | NoRouteError | NoRouteError | NoRouteError |
| slow_open_turn | ✓ | ✓ | ✓ |
| fast_open | ✓ | ✓ | ✓ |
| fast_single_obstacle | ✓ | NoRouteError | ✓ |
| fast_wide_channel | ✓ | ✓ | ✓ |
| fast_open_turn | ✓ | ✓ | ✓ |

失败均进入了障碍安全缓冲区，随后NoRouteError；没有实体碰撞。逐例最小安全余量：
- stable_wide_channel / geometry_only: -1.579982 m（实体余量58.420018 m）。
- stable_wide_channel / oracle_local: -1.579982 m（实体余量58.420018 m）。
- stable_wide_channel / estimated_local: -1.579982 m（实体余量58.420018 m）。
- slow_single_obstacle / geometry_only: -0.369491 m（实体余量69.630509 m）。
- slow_single_obstacle / oracle_local: -0.369491 m（实体余量69.630509 m）。
- slow_single_obstacle / estimated_local: -0.369491 m（实体余量69.630509 m）。
- slow_wide_channel / geometry_only: -2.403597 m（实体余量57.596403 m）。
- slow_wide_channel / oracle_local: -2.403597 m（实体余量57.596403 m）。
- slow_wide_channel / estimated_local: -2.403597 m（实体余量57.596403 m）。
- fast_single_obstacle / oracle_local: -0.096094 m（实体余量69.903906 m）。

完整记录逐值比较：estimated_local与geometry_only在12/12场轨迹/动作完全相同；oracle_local为11/12。风信息实际进入评分且存在非零风代价，见diagnostic.json。快速变风单障碍中oracle改变决策并失败，不能称oracle为全局最优上界。

本轮不支持继续以“读出更准就能提升导航”为既定结论。其余指标（帆舵变化、换舷、风驱动换边、改点、计算与记忆重编码耗时）完整保存在episodes.csv/jsonl。开阔场安全余量是无穷大，汇总JSON以null表示；不能把该列混合平均解释成障碍裕量。

## 交付与限制
- 配对原始轨迹、逐步动作/可见输入/候选评分：`runs/v0_comparison_20261002/*.json`；总表 `episodes.csv`、`episodes.jsonl`、`result.json`；图 `trajectories.png`、`success_counts.png`。
- 源码/配置进Git；模型、原始输出另做带逐文件SHA256的本地归档。运行/恢复命令见README；跨设备资产回执见 `docs/DELIVERY.json`（备份完成后生成）。
- 累计实验账本约1212.38秒（20.21分钟），低于首轮3600秒预算；不含安装、编辑、文档与绘图。
- 这是固定开发小样本，非论文最终测试；14D@7200不代表final@9000论文身份；18D原尺度8/8不等于连续18D已可用。
- 安全由离散控制步间线段近似统计，不证明精确积分曲线/船体安全。风场为私有合成场，无外部预报。3/5km只留配置，未运行。

## 下一项最小实验（建议，尚未启动）
先对保存的选点状态做离线评分分解与安全约束诊断，定位风代价、改点阈值及真实跟踪偏离之间的作用；随后预注册少量新场景验证一个明确的选点/安全改进。不要先扩大读出器或启动RL；本轮场景不能再当未见测试集。
