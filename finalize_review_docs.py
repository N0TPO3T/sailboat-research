from pathlib import Path
p=Path(r'C:/Users/74095/hs/SailBoat/sailboat-track-b')
r=p/'docs/B_RESEARCH_REPORT.md'
s=r.read_text(encoding='utf-8')
s=s.replace('最多4个单数值线程实验worker，共享截止不重置。','资源限制目标为全任务最多4个单数值线程实验worker，共享截止不重置。曾在上一批尚未收到明确退出码时启动下一批，属于调度疏漏。事后各回合结束写入时间与wall_s反推的活跃计算峰值为4，新批最早计算比旧批最后结果写入晚1.85s；这些代理不能排除进程启动/清理短暂重叠，因此不声称全程进程并发上限已被证明遵守。两批均已收到exit_code=0，协调者独立检查无剩余B作业；GPU使用为0。详情见docs/RESOURCE_SCHEDULING_INCIDENT.json。')
s=s.replace('研究全文/图表、离线HTML、源码/配置、原始结果、独立三审及作者回应打包在B_RESEARCH_preview.zip。','研究全文/图表、离线HTML、源码/配置及原始结果已形成，正在提交独立三审；实际审查和回应完成后生成B_RESEARCH_preview.zip，当前不预写审查结论。')
s=s.replace('## 8. 复现、资源和材料','匹配简单对照必须单独解释：release相对luff_no_build在12风险任务仅+0.4931个百分点（每1200s平均多5.92s区内），同时帆舵累计变化+3.9823rad；3胜8平1负，最差少19s区内，最长离区最大值98s对85s。证据支持需要帆恢复模式，不支持90°精确规则具有普遍独占价值。\n\n## 8. 复现、资源和材料')
r.write_text(s,encoding='utf-8')
r=p/'docs/B_METHOD_NOTE.md';s=r.read_text(encoding='utf-8').replace('相对luff为+0.49个百分点','相对匹配的luff_no_build为+0.49个百分点（3胜8平1负）').replace('**代价。** 恢复时','**代价。** 相对匹配luff_no_build，12风险任务平均仅多5.92s区内，但帆舵累计变化多3.98rad；最差任务少19s区内，最长离区最大值98s对85s。主要证据支持帆恢复模式，不支持最大90°规则的普遍优势。恢复时');r.write_text(s,encoding='utf-8')
(p/'STATUS.md').write_text('B实验已完成：V1负确认保留并转为开发；V2为24个50m任务×6方案及8个100m任务×4方案，共176回合、32独立实例。核心证据是低速迎风帆恢复；最大放帆对匹配luff增益小且有代价。当前：同版本独立三审与最终打包。无运行实验、无GPU、无训练。资源调度疏漏及无法排除的短暂进程重叠见docs/RESOURCE_SCHEDULING_INCIDENT.json。\n',encoding='utf-8')
(p/'README.md').write_text('''# B：区域观测中的低速迎风恢复

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
''',encoding='utf-8')
