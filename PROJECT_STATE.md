# Project State

## 项目与唯一入口
- 目标：已知完整静态海图、无外部天气预报，以冻结局部SAC-LSTM完成连续多航迹点，再验证当前局部风向旁路对高层选点的价值。纯仿真、小规模V0，不保证优于基线。
- 连接：ssh donghai，ot@172.16.2.249；开发根目录 /home/ot/Students/hs/sailboat-routing-v0（NEW_ROOT），独立Git仓库main。
- 只读上游：/home/ot/Students/hs/sailboat-research（SOURCE_ROOT）；不得覆盖其代码、模型、环境和既有改动。
- Windows同步目录约定：C:/Users/74095/hs/SailBoat/sailboat-routing-v0；其他设备可选自己的本地路径，均通过SSH开发。
- 同步方向：服务器开发/验证/提交 → 本机SSH拉取 → 本机获准后push到托管远端。服务器不承担外网推送或保存托管凭据。
- 本机origin用于从服务器拉取，向服务器push已禁用；V0托管远端尚未配置，地址未确定。源码镜像不等于完整实验备份。
- 研发基点4e86b74；完整运行实现已提交为857ff57。源码镜像与大产物分开恢复，资产回执见docs/DELIVERY.json。
- 专用解释器 .venv/bin/python，Python 3.13.11；独立依赖见requirements.lock，共享Miniconda仅作为只读解释器来源。安装及命令见README。

## 实现与协议
- 当前连续低层：14D saclstm_s14nowind_buf1e6_seed100@7200，Actor/normalizer冻结；不是官方final@9000或论文最终身份的证明。
- 新集成协议：configs/navigation_contract.json；无额外sensor/actuator噪声，关闭dropout；原A/B用Dryden，新navigation改用私有SyntheticWindField，须单独验证。
- third_party/senior保存原样最小继承快照；runtime.py加载资产，continuous.py维护物理连续，frames.py负责刚性坐标与因果记忆重编码。
- navigation.py已写真实运行链：每控制步一次Actor决策，同前向旁路270维特征，高层t选点在t+1应用。已由真实闭环与旁路非干扰准入验证。
- wind_readout.py/fit_wind_readout.py实现sin/cos岭回归、整episode/scenario划分、train-only标准化、validation选alpha、test一次评估。
- planner.py提供静态地图A*和有限候选；wind_fields.py/metrics.py提供私有时空风场与安全/换舷/配对统计。正式planner输入无环境或风场查询器。
- 三方法geometry_only/oracle_local/estimated_local共享低层与选点参数；oracle只提供当前本船局部真风方向，是诊断参照，不是全局最优上界。
- 18D 0204@10800为独立避障候选；原尺度通过，不具备已验证连续多目标接口，未替换14D。

## 已验证能力与证据
- A/B原协议：迁移及新旧解释器比较误差0，500m为12/12，约1km为5/6；失败前1000步与原500m一致。证据：runs/stage_a、stage_b、stage_b_failure_diagnostic及audit/cross_environment_parity.json。
- 18D独立候选原协议8/8，尚未连续适配，不替换14D；证据runs/obstacle_capability_legacy及docs/OBSTACLE_PROTOCOL.md。
- 新导航准入54项测试通过，完整274步旁路开/关轨迹及动作一致，2次目标切换连续；140步变风标签检查通过。证据runs/v0_admission_final_20261002、runs/navigation_admission.json。
- 20个完整采集episode按12/4/4划分，2个训练超时保留；已冻结读出器并完成一次test评估。离线误差、36次闭环结果及全部失败统一见docs/V0_RESULTS.md及其原始证据链接。
- 本轮上游1351文件与Git状态无变化：runs/audit/upstream_integrity_v0_final_20261002.json。
- V0规定的最小工程/开发诊断已完成；未证实估计风优于几何基线，不等于论文方法已成立。几何路径安全未保证真实闭环安全。

## 限制与恢复
- 模型在checkpoints、运行产物在runs，Git忽略；已提交来源清单见docs/UPSTREAM_MANIFEST.md、migration_identity.json。完整本地资产位置与校验见docs/DELIVERY.json。
- docs/validation_summary.json和旧B passed=false保留历史含义，不代表当前准入；本轮未篡改旧结果。
- 代码/协议/权重改变后重新验收；源码身份和特征schema不匹配时拒绝使用既有读出器。
- 单CPU数值线程、首轮累计计算预算3600秒，实际消费见runs/computation.jsonl；不启动低层/高层RL、长搜索或后台无人看管任务。
- 3/5km只有configs/distance_demos.json配置，未运行；动态/COLREGs、天气预报、完整风场重建不在本轮范围。
- 后续最小实验建议见结果报告；当前没有已启动的新研究线程。
