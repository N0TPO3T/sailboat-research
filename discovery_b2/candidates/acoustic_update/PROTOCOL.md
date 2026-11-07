# 冻结预结果协议：声学历史模型的少量当年观测更新

保存时间：2026-10-08；尚未运行拟合/查看方法胜负。候选编号3，独立于原占空比问题。

## 任务与观测单位
主任务：当年未用于更新的已观测空间组的线性NASC重构。辅助：测试支持集平均预测偏差；另列完整观测支持集的HT/GREG均值估计，不将均值与重构混为一项。
输入只用既有xdat.Full.csv。每行先exp(log_NASC)，在Year/Month/floor(X/2)/floor(Y/2)内取算术平均，形成2km月空间组；特征取组内平均（Hour先sin/cos），权重主任务每组相等。保留n_segments，每组不是一次现场测量。研究目标是该观测设计下的组均值，不是整月均匀时刻或整个海域总量。
月份固定4–6。X/Y以km计算。缺失字段直接报错，不补目标。所有聚合真值用于评分，训练侧仅可见所选组。后验CMSI仅离线可用。

## 拆分、设计和预算
开发：2019历史训练，2020当前少样本校正/空间测试。确认性探索：2021、2022、2023逐年仅用所有更早年训练，绝不利用较晚年份。
当年以8km空间块（floor(X/8),floor(Y/8)）作简单随机不放回整块抽样，比例15%和35%，K=ceil(fraction*B)，每块纳入概率pi=K/B。种子3101、3102、3103。每块所有月/格标签同时可见，所有方法共享同一mask。记录可见组数及实际原始7分钟段数，不称节电或航程收益。
测试组须来自未见块且距所有已见格中心至少2km；相同坐标多月份均同可见/不可见状态。空间缓冲只定义共同测试集，不改变完整有限总体/HT/GREG设计。保存每次mask、pi、缓冲剔除组、索引。主任务允许历史同地观测，含义是已监测区域新年更新，不声称新空间外推。
超参数只用2019/2020开发任务；模型特征标准化、smearing均仅历史训练标签。2021–2023不得用于方法选择。目标坐标及采样框在离线掩蔽中已知，这是回放有限总体设计，不是真实在线站点调度。

## 方法与强简单选择
历史模型：NumPy/SciPy的正则化加性三次样条特征（深度、月、小时周期、环境、空间坐标/有限RBF），拟合log组均值，再以历史训练残差smearing回到线性尺度。ridge候选1、10、100；不称完整复现GAM/sdmTMB。
当前均值/水深-月份分层均值、当前IDW、当前普通克里金；历史预测原样、加当前全局线性残差、加按月/深度分层收缩残差。分层不足时回退全局（收缩n/(n+5)）。所有线性重构预测截断到非负。
原型：历史预测+当前残差普通克里金（成熟regression kriging）。只预设长度尺度2、5、10、20km和nugget比0.1、1、5，开发集选择，不穷扫。
最强可部署简单法按开发六任务的平均主指标选一个固定方法；不在测试年各挑赢家冒充部署对照。额外报告每个简单法，test-oracle仅作诊断。
辅助完整均值：HT=sum_visible(y/pi)/N；GREG=mean_all(hist_prediction)+sum_visible((y-hist_prediction)/pi)/N。pi按抽样块，非按组数猜测；簇大小不等时HT不等于样本均值。

## 首先实现诊断，再冻结开发选择
常数重构、核矩阵对称/稳定、普通克里金常数再现、线性↔log转换、同mask/标签预算、年度断言、缓冲距离、GREG残差零一致性。诊断失败先修复，不把缺陷计作收益。

## 指标与意义门（胜负前固定）
主指标：每组等权linear MAE / 测试支持集真实mean NASC；附linear RMSE、log RMSE、测试均值相对偏差与高值组误差。分母仅评分端使用。
先按每个目标年×预算汇总3个mask（共6个year-budget单元）。有继续信号需：至少4/6单元的主指标下降>=0.05（平均组误差至少降低相当于测试支持集平均NASC的5%）；全部6单元不退步；且每个单元绝对相对均值偏差不比固定简单法增加>0.02。这个5%是本任务探索门，不是通用发表门/领域管理标准。
均值HT/GREG单独评价完整支持集相对误差。即使GREG优秀也不替代主命题；若主任务门失败则STOP原型，不追加模块/换seed。只有3个目标年份，mask不是独立海洋样本，不做夸张显著性或广泛泛化声明。

## 资源与产物
1个CPU worker，每库1线程，GPU0。首轮<=1CPU小时，硬超时3h；cache/tmp放候选目录。仅写本候选及服务器镜像。脚本、协议哈希、输入哈希、开发选择、全部组/拆分/预测/评分、两幅真实图、RESULTS.md与运行收据交付。没有训练不足的RL对比，没有造海域真值。


## Pre-run amendment (before any fits or target results)
Add current global median, month/depth-stratum median (fallback global), and history plus median residual to strong-simple methods because primary MAE is heavy-tail sensitive. All use identical visible labels. Freeze best_current_only among all current methods and best_history_enabled among all history methods including RK using 2020 mean NMAE only. Apply the same six-cell threshold and bias gate to historical updating versus current-only. This application gate is separate from RK incremental gate: failure of RK alone cannot eliminate mature history updating. Each target year receives full prior-year data: independent annual sparse-update hypotheticals, not a sequence of sparse-acquisition years. Models, training indices and development predictions are saved.

## Diagnosed repair after first valid target run
Original polynomial/hinge historical trend failed already on development: history NMAE 59.50; 33.66% of 2020 predictions hit log clipping. This warrants repairing trend extrapolation, not rejecting historical information. Preserve original output and code. Stable version replaces nonlinear features with train-range-clipped standardized linear ridge using original three penalties; add historical month/depth median and historical IDW (distance squared plus 25 times month difference squared plus 1) as candidate trends. Choose trend on 2020 alone, apply same chosen historical trend to all residual corrections; all label masks, evaluation metrics, selection/gate rules and kernel grid unchanged. This is a disclosed post-initial-result implementation repair, not new independent confirmation. No more repair/search after stable run absent correctness fault.
