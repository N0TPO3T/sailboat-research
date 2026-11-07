# N3 声学数据可用性核验（2026-10-08）

结论：**当前暂缓 N3 的因果占空比重放 pilot**。已获得并实际解析真正的公开声学预处理数据，但它没有足够时间标识，无法核实连续开启区间或重建12分钟测量组。不能按CSV行号制造等间隔时间，也不把空间抽样实验当占空比实验。此结论是当前数据契约不满足，不是证明占空比研究无效。

## 已下载并检查：Sailbuoy 声学积分

- 数据：Carlsen 等，USV Sailbuoy hydroacoustic integrations from 2019–2023。
- [永久来源 DOI](https://doi.org/10.5878/9m27-vg06)，[大学资料页](https://research.slu.se/en/datasets/usv-sailbuoy-hydroacoustic-integrations-from-20192023-pre-process/)。
- [实际 CSV 下载](https://api.researchdata.se/dataset/2024-517/1/file/data/xdat.Full.csv)，[ReadMe](https://api.researchdata.se/dataset/2024-517/1/file/documentation/ReadMe_datastatement.txt)。无需账户；实际请求成功。
- 数据集页面的 link rel=license 与 JSON-LD 都标 [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/)。不把大学整个网页页脚版权当成该开放数据许可。
- 本地：`notes/needs_sources/xdat.Full.csv`，8,234,802 bytes；`notes/needs_sources/ReadMe_datastatement.txt`，4,282 bytes。合计实际数据文件下载 **8,239,084 bytes**，未下载其他CSV、原始回声或代码压缩包。网页/API小型响应只用于读取，没有保存为数据文件。
- CSV SHA256：`b3936d9d7507679d3b98ed6f4e0db34a4f6011e43c346e59491a7ff267006b7b`；实际 Get-FileHash 与数据集 JSON-LD 的 SHA256 一致。
- Python标准库csv实际读到41,292数据行；14个命名变量，另有1个无名行号列。
- 命名变量：`X, Y, log_NASC, Week, Hour, Depth, Year, Month, Mean_thetao_SST, Chl_surf, Mean_NS_vo_Wclm, Mean_EW_uo_Wclm, SO_surf, Mean_current_speed`。
- 年份行数：2019=5,570；2020=10,342；2021=7,847；2022=10,919；2023=6,614。
- `log_NASC` 没有空值/NA/NaN，读取范围 -2.32165578821787 至 9.62739907647249。这是对数变量，不直接当线性NASC，也未假定对数底或零值处理。
- ReadMe明确NASC来自USV的Simrad WBT mini，单位 m² nmi⁻²；该数据是真正声学积分，不是名称相似的光学背散射或ADCP流速。

### 为什么不能据此直接做原N3

1. CSV没有日期、分钟、秒、UTC时间戳、单元起止时刻、ping编号或开关状态。Year/Month/Week/Hour只形成1,510个唯一键，另有39,782行共享这些粗时间键；一周内相同小时无法区分日期。
2. ReadMe将NASC描述为hourly mean，但同Hour有很多记录；它同时称Full为最高可用分辨率。缺少更细空间/时间积分单元定义，不能自行假定“一行=一小时”。
3. 文档没有在当前核验材料中给出连续100%开启区间、停机/故障/质量筛除掩码或开关能耗。无缺失log_NASC不等于无缺测。
4. 环境变量来自Copernicus事后产品，其中有月均量。即使以后取得时间戳，也不能默认它们在在线决策当时可用。
5. 固定轨迹的分层空间抽样或年度统计建模可能可以使用这个表，但那是另一明确任务；不在本核验中偷换成占空比pilot。

## NOAA 2015/2016目录：访问成功，文件变量仍未验证

- [0187987目录](https://www.ncei.noaa.gov/data/oceans/archive/arc0137/0187987/1.1/data/0-data/)实际列出：
  - `saildrone_PMEL_Arctic_2015_126.nc`，目录约56M；
  - `saildrone_PMEL_Arctic_2015_128.nc`，约65M；
  - `saildrone_PMEL_Arctic_2016_126.nc`，约89M；
  - `saildrone_PMEL_Arctic_2016_128.nc`，约89M。
- 全包页面标约318.4MB。单个文件都超过本次50MB下载上限，因此没有下载。未读取NetCDF变量，**不据目录“fish biomass”描述断言文件有可用声学序列**。
- 浏览器工具访问部分NCEI入口失败，但PowerShell只读HTTP请求能列出官方目录。这是工具访问差异，不是数据不可获得的证据。

## NOAA 2020原始EK80：确认目录，尚无小型处理序列

- [2021原论文Data availability](https://pmc.ncbi.nlm.nih.gov/articles/PMC8499815/)指向三个2020声学航次DOI。
- [NOAA SD1049 EK80元数据](https://www.ncei.noaa.gov/access/metadata/landing-page/bin/iso?id=gov.noaa.ncei%3ASD1049-2020-01_EK80)与[官方开放桶索引](https://registry.opendata.aws/ncei-wcsd-archive/)提供公开入口。
- 实际匿名S3目录请求列出 `data/raw/Saildrone/SD1043-2020-01/`、`SD1046-2020-01/`、`SD1049-2020-01/`，另有2018航次。仅验证目录存在，未核验单个EK文件尺寸、连续性或变量，未下载。
- 实际 `data/processed/` 一级目录列出AMLR、Pisces、SH1305、SH1707、冷泉数据库，未列出Saildrone。这只能说明这一已查前缀没有Saildrone处理目录，不能推出全网不存在处理数据。

## 建议与停止点

目前无满足原N3时间决策契约的小型声学序列。按协调者指令在此结束检索，不继续为凑可用数据无限寻找。恢复N3的最低条件是取得带真实时间、采样/质量掩码、连续开启依据的声学积分序列，再明确转换、传感预算与开关限制。另一条路是为原始EK处理单独分配数据/处理预算，但本次没有执行，也不承诺它一定能低成本完成。

本次只有文件下载、哈希、CSV结构与基础值检查；没有训练、仿真、策略比较或数值实验worker。未安装软件或服务，未联系数据作者。

## 协调者追加核验：SD1049小型原始文件实际读取

此节更新上文“未下载2020原始文件”的阶段状态。收到独立评审提供的同一源后，按协调者要求补做一次有界实际核验，未扩大处理。

- 实际检查EK80前1000条对象清单，最小已见文件2,031,760 bytes；这只是已查首批中的最小值，不声称全航次最小。许多常规文件约87,633,696 bytes，超本次单次剩余预算。
- 实际下载[SD1049_2020-01_EK80_D20200705-T175454.raw](https://noaa-wcsd-pds.s3.amazonaws.com/data/raw/Saildrone/SD1049-2020-01/EK80/SD1049_2020-01_EK80_D20200705-T175454.raw)，22,245,560 bytes，SHA256 `919e3bb876170dd8ce67b0003cec80ccfb1078f8b6e14f5784dc4148af6185f7`。
- 实际下载[SD1049_EBS_2020_calibration_512us.ecs](https://noaa-wcsd-pds.s3.amazonaws.com/data/raw/Saildrone/SD1049-2020-01/EK80_calibration/calibration/SD1049_EBS_2020_calibration_512us.ecs)，6,686 bytes。两者均存 `notes/needs_sources/`。**累计落盘下载30,491,330 bytes**（约30.49MB），仍在50MB上限内。
- 用Python标准库struct仅读取二进制datagram边界、类型与FILETIME时间，前后长度字段全部匹配，解析到文件末尾。读到XML0=442、FIL1=4、RAW3=440。RAW3共有220个唯一时间，2020-07-05T17:54:57.368479Z至18:05:59.122099Z，跨度661.754秒，最大相邻时间差3.034秒。当前小文件只有约11.03分钟，不足一个完整12分钟组；不把文件名时间当实际ping时间。
- 实际XML包含EKauto配置、Environment及Parameter；已见38,000Hz、PulseDuration=0.000512s、SampleInterval=0.0001200048s、TransmitPower=500。仅证明该文件确含可解析的声学datagram及配置，**没有把RAW3值转换成校准Sv/NASC**。
- 本机Python依赖核验：xarray/numpy/scipy已安装；echopype/echolab2/netCDF4不存在。未安装任何包。普通xarray不能直接把专有EK80 raw解释成可用定量背散射。
- ECS文件名为SD1049，但其内部说明有“SD1043 calibration”及与官方航次说明不完全一致的日期文字。这可能是注释复制问题，当前不能下定论；正式定量处理要对校准源记录/通道确认，不能不加核验地套用文件。

**最终边界：** NOAA原始数据确实匿名可获取，已有小型实际样本；不是“没有公开声学数据”。但当前没有完成可靠校准、质量控制、底部/近表层排除、完整连续采样组和功耗契约，因此N3仍为“数据处理契约未满足，暂缓/未判定”。12分钟占空比pilot不能靠本次11分钟样本或粗时间CSV伪造。本核验到此结束并释放代理工作槽。
