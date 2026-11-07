# B3资产与复现入口

先读 [中文选题报告](idea-stage/IDEA_REPORT.md)。本包是有限选题筛选，不是新论文或实船系统交付。A、旧B、B2未被替换；服务器满盘，本轮仅本地运行。

| 内容 | 入口 | 实际范围 |
|---|---|---|
| T测线交接 | candidates/turn_handover/RESULTS.md | 8任务×3方法；旧诊断批、共同修复、最终原始NPZ均保留 |
| N位置缺失传播 | candidates/position_outage/RESULTS.md | 1条真实记录9固定窗口×4方法；并非9次独立海试 |
| R已知执行器降额 | candidates/derated_return/RESULTS.md | 10任务×3方法；原始轨迹、预定半步检查及失败均保留 |
| 原始候选和来源 | notes/operations.md、control_opportunities.md、reliability.md | 三路独立提出，不是三个审稿人接收 |
| 选题审查 | notes/selection_review.md | gpt-6-astra xhigh，同家族provisional |
| 原始证据审查 | notes/evidence_review.md | gpt-6-astra ultra，同家族provisional |
| 水质方向资产筛查 | notes/water_sampling_screen.md | 原文核验；未取得可判别原始记录，没有虚构pilot |
| 环境、资源、执行边界 | RESEARCH_BRIEF.md、SHARED_BUDGET.json、notes/venue_and_execution.md | 本地既有Anaconda，单数值线程，GPU0 |
| 文件身份 | FILE_MANIFEST.csv、DELIVERY.json | 完整包逐文件哈希；包外交付收据保存ZIP哈希 |

## 可运行入口

以下使用本轮验证过的Python，不要求安装依赖。换设备时需已有numpy/scipy/matplotlib；不能从“代码存在”推断另一环境已验证。环境变量和依赖来源见各候选报告。新输出目录必须不存在，不覆盖旧结果。

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$env:CUDA_VISIBLE_DEVICES=''
Set-Location 'C:/Users/74095/hs/SailBoat/sailboat-track-b/discovery_b3/candidates/turn_handover'
& 'C:/Users/74095/anaconda3/python.exe' -B -X utf8 preflight.py
& 'C:/Users/74095/anaconda3/python.exe' -B -X utf8 pilot.py --mode main --out runs/reproduction_1

Set-Location '../derated_return'
& 'C:/Users/74095/anaconda3/python.exe' -B -X utf8 preflight_R.py
& 'C:/Users/74095/anaconda3/python.exe' -B -X utf8 pilot.py --mode main --out runs/reproduction_1
```

N的`pilot.py`默认写入results，复现前请复制整个position_outage目录到新的本地位置，再运行该副本；原脚本内根目录跟随文件位置，禁止直接覆盖本包原始评分。`check_fixed_normal.py`只复算已有traces。T/R的verify_and_plot也写检查产物，若重跑同样使用副本。

## 读取数据时的关键区别

- T/R动力学日志中，t为积分区间起点，记录位置/速度/轴速为t+dt；actual_X/N为本步起点轴速计算的反馈力，command作用于这一积分区间。不能把同一行所有字段假定为同一时刻。
- T有效格：每1m格至少一次达到阈值，不是连续合格声纳数据。R不以T速度采样门判断成功。
- N是离线预测与后处理参考的比较，不是控制器实际闭环轨迹；初始状态和过去校准参考含特权信息。原随动法向、补算固定法向与船离原直线的距离分开保存。
- 力绝对值积分和桨速总变化是操纵代理，不是已标定电能或磨损。

## 来源与许可

Otter固定上游commit、逐文件哈希及原MIT文本在turn_handover/upstream_commit.txt、preflight_receipt.json及vendor/LICENSE。R依赖T的最小源码，不能单独遗漏这些文件。

CANOE片段来自作者官方数据集，CC BY 4.0；源URL、字节范围、外参、下载收据与哈希保存在position_outage目录。详见[作者数据说明](https://raw.githubusercontent.com/utiasASRL/pycanoe/main/DATA_REFERENCE.md)及[AWS数据登记](https://registry.opendata.aws/canoe/)。没有给旧帆船资产新增许可，也未将复现能力写成公开发布。

## 本轮没有完成的事

没有实船或任务质量验收，没有在线GNSS初态验证，没有故障检测/中止决策，没有新训练，没有将任何新方案合入A。三个有限pilot结束，不承诺后台继续。
