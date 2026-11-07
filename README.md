# B：区域观测中的低速迎风恢复

本方向 GitHub 分支：`idea/B`。其他思路见 `main`；资产恢复见 `migration/ASSETS.json`。本次发布保留原研究结论与限制，不代表重新运行验证。


先读 docs/B_METHOD_NOTE.md 和 docs/B_RESEARCH_REPORT.md。B使用理想当前局部风，不与A动态避碰结果混合。没有加载RL权重，没有训练或GPU。

## 主要材料

- docs/FREEZE_V2.json、FROZEN_V2_INSTANCES.json：结果前冻结的24主任务与8尺度任务。
- configs/recovery_confirmation.json、recovery_scale.json：原始主比较；recovery_luff_control.json、recovery_luff_scale.json：同实例结构匹配对照。
- analysis_v2/all_results.csv、group_summary.json、paired_summary.json：完整任务级结果。
- analysis_v2/gallery.html：离线真实日志图集；figures/06到10为当前主要图。
- runs/、RESULTS_INDEX.json：全部原始证据，含原型错误、失败与第一版负确认。不能把V1当当前未见测试。
- docs/ASSET_AND_SENSOR_SCOPE.md：资产、传感与物理适用范围。
- reviews/：实际独立审查及回应（审查完成后交付）。

## 复现

服务器根目录 /home/ot/Students/hs/sailboat-track-b。使用已有只读环境 /home/ot/Students/hs/sailboat-routing-v0/.venv/bin/python。设置 PYTHONDONTWRITEBYTECODE=1、OPENBLAS_NUM_THREADS=1、OMP_NUM_THREADS=1、MKL_NUM_THREADS=1。归档主源码为 scripts/station_recovery.py；匹配补充源码为 scripts/station_luff_control.py。两者具有原研究截止时间，禁止修改归档版。

便捷重跑使用 scripts/station_reproduce.py，仅将墙钟截止参数化，科学代码不变；差异和哈希见 docs/REPRODUCTION_SOURCE_DIFF.json。复制对应配置，只将batch改为新名称，避免覆盖原结果；由使用者设置已授权的新 B_RESEARCH_DEADLINE（UTC Unix秒）。执行：

```sh
B_RESEARCH_DEADLINE=<authorized_unix_deadline> /home/ot/Students/hs/sailboat-routing-v0/.venv/bin/python scripts/station_reproduce.py configs/<fresh_config>.json
/home/ot/Students/hs/sailboat-routing-v0/.venv/bin/python scripts/analyze_recovery.py
```

分析脚本读取既有batch，不推进物理环境。新batch需另存分析入口/路径。运行前核对导入只来自B副本。任何记录存在时runner拒绝覆盖。

全时区内比例分母固定1200个1Hz时刻，积分失败缺失尾部不给区内信用。终态另存并纳入最大半径。数值完成不等于任务成功，无连续安全保证。

## 资源披露

目标上限为4个单数值线程实验worker。一次调度未等旧批明确退出便启动下一批；结果时间反推未发现活跃回合重叠，但不能排除进程启动/清理短暂重叠。详见 docs/RESOURCE_SCHEDULING_INCIDENT.json。两批最终exit_code=0，全部实验已结束。不得把配置的4worker写为经过完整进程审计的全局峰值。GPU=0；CPU回合计时不包含全部导入/分析耗时。

不新增许可证，不声称公开发布。无需安装服务或修改共享环境。
