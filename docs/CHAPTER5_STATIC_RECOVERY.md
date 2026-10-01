# Chapter-5 Static Baseline Recovery

`STATIC_BASELINE_STATUS = IN_PROGRESS`

CPA保持暂停，`CURRENT_HYPOTHESIS = INCONCLUSIVE`不变。本轮没有动态环境/风险reward/A-B/Top-K实现，没有启动正式训练，也没有生成PASSED基线目录。

## 1. 协议和资产

Legacy与Aligned的逐项差异见[DYNAMIC_OBSTACLE_CODE_AUDIT.md](DYNAMIC_OBSTACLE_CODE_AUDIT.md)的同名章节。
Legacy保留旧权重的streaming hidden、K=5及原推理dropout设置；Aligned使用正确配对、10步零hidden窗口和显式episode reset。两者复用同一Actor/Critic，没有两套网络实现。

系统搜索发现三组结构匹配的旧权重，详见[CHAPTER5_ARTIFACT_SEARCH.md](CHAPTER5_ARTIFACT_SEARCH.md)。
主要测试对象为：

`research/supplements/yc_attention_121x/saclstm_s14obst_1213_{actor,q_critic,normalizer}15600.pth`

源路径：`/home/ot/Students/yc/SAC/model/`，副本和18项来源hash在同目录`provenance.json`。
三组均通过strict=True、18D normalizer、Actor/双Critic合成前向和hidden reset检查。
原训练seed、真实步数及环境版本绑定仍为unknown；文件编号不换算为训练收据，不能称论文最终checkpoint。

## 2. 旧checkpoint的Legacy行为

旧源码邻近评估入口为obst-v2/K5，先做Legacy/V2代理测试，再做当前V3迁移；从未先用Aligned评价旧权重。

| Checkpoint | Legacy/V2，无障碍 | Legacy/V2，静态安全到达 | Legacy/V3，无障碍 | Legacy/V3，静态安全到达 |
|---|---:|---:|---:|---:|
| 1211/3600 | 3/3 | 0/6 | 未扩展 | 未扩展 |
| 1213/15600 | 3/3 | 5/6 | 2/3 | 1/6 |
| 1216/12600 | 3/3 | 5/6 | 3/3 | 1/6 |

这是固定0°/90°/180°、初始艏向0、无外加噪声的9场景sanity，静态包含固定与随机布局。V2均风5m/s，V3为8m/s。不能估计总体性能或将差异单因果归于动力学/风/执行器其中之一。
1213与1216静态安全数打平，1213在这组静态样本平均最小间距略大，因此先用1213检查主bank；这是开发选择，不是无偏最终测试。

## 3. STATIC_EVAL_BANK

唯一主bank：`research/validation/static_eval_bank.json`，200个预生成场景：

- 无障碍100；原固定7障碍50；随机5–8静态障碍50。
- 风向0°/90°/135°/180°；初始艏向、完整初态、障碍坐标、wind/sensor/actuator/policy seed均逐场景保存。
- 目标(500,0)、起点(0,0)；主环境V3，均风8m/s，原Dryden更新。
- 随机布局最小间距140m，生成失败显式报错，不悄悄减少障碍个数。
- 风场RNG与replay、探索、噪声RNG隔离；noise wrapper种子每回合重置。
- bank用于开发和checkpoint选择，不是论文最终未触碰测试集。
- bank SHA256：`0719885cc70a25d0a943380726880805e36c2a1bbf8337b2ab0db724798897fc`。

### 200场景结果：1213 / Legacy / 当前V3

| 指标 | 结果 | 分母/条件 |
|---|---:|---|
| No-obstacle Success | **96% (96/100)** | 工程门95%，点估计通过 |
| Static Safe Success | **26% (26/100)** | 工程门85%，未通过 |
| 固定静态布局Safe Success | 24% (12/50) | 固定场景子组 |
| 随机静态布局Safe Success | 28% (14/50) | 随机场景子组 |
| Static Safety Violation | **74% (74/100)** | 40m，积分节点线段近似最小距离 |
| Timeout | 2% (4/200) | 4个均在无障碍180°风况；静态0/100 |
| Out of bounds | 0/200 | 与超时、侵犯分开记录 |
| Minimum Separation mean / median | 42.931 / 39.473 m | 仅100个静态场景，无障碍为NA |
| Navigation time | 310.361 s | 122个安全到达回合条件均值 |
| Trajectory length | 679.372 m | 同上，积分节点折线近似 |
| Sail variation rate | 0.036921 rad/s | 200回合各自TV/time的均值 |
| Rudder variation rate | 0.017412 rad/s | 同上 |

完整结果：`research/validation/legacy_1213_static_bank_20260915/summary.json`与`episodes.jsonl`。
这不是原论文95.3%的复现，也不是对旧权重在历史环境中表现的否定。主bank包含当前V3、8m/s及3%噪声配置；Legacy噪声开启时保留原normalized-action噪声调用语义，Aligned使用明确物理弧度调用。两者的实际配置/协议必须同时引用。

## 4. 五条预先选择的trajectory和hidden验证

选择规则在评估前固定：`no_obstacle_0000/0001/0002`、`fixed_static_0000`、`random_static_0049`，不按结果挑成功图。

![五条静态轨迹](../research/validation/legacy_1213_static_bank_20260915/five_trajectories.png)

![帆舵角与LSTM hidden](../research/validation/legacy_1213_static_bank_20260915/actuators_hidden.png)

- 三条无障碍轨迹均到达；固定与随机静态例子进入40m安全域，说明不能只凭正常航行判定具备避障能力。
- 图上帆舵有启动饱和和部分持续调整；这里只作诊断，不给予“所有场景无高频振荡”验收。
- 200回合的`hidden_after_reset`全部0；非零reset前范数与清零后范数分别记录。
- `representative_trajectories.json`逐步保留hidden norm、LSTM输出h norm、attention weights、history索引、命令/实际动作和轨迹；Legacy dropout后的attention权重不保证和为1，未将它误标为eval-softmax概率。
- 五条轨迹再次按相同seed运行，全部逐点完全一致；除依赖上一场景的reset前hidden norm，metrics也完全相同。证据：`legacy_1213_repeatability_20260915/repeatability.json`。
- 首轮200场景保存了bank/config/权重身份，但启动时尚未保存独立driver provenance文件；不补造旧运行hash。其5场景复跑含当前provenance，后续入口已在评估开始保存source/Git/config/bank指纹。

图片已实际渲染检查。绘图在专用本机cache中使用兼容Matplotlib；没有修改共享Conda base或训练环境依赖。

## 5. Aligned训练准备与恢复

训练前新增语义门已完成：`V3_STATIC_ENV_STATUS=CORRECTED_BUT_INTENTIONAL`，权威依据见[V2/V3静态审计](V2_V3_STATIC_PARITY_AUDIT.md)。旧V2权重/normalizer与V3观测语义不匹配；本轮不训练。下述READY与服务器部署是审计前快照，本次V2噪声保护及审计尚未同步服务器，启动前须按清单同步并重查资源。

`READY_FOR_GPU_TRAINING = YES`：表示代码、配置、bank已准备并同步、CPU验证通过；不表示当前有空闲卡或已验证CUDA梯度吞吐。

唯一配置：`configs/chapter5_static_aligned.json`，配置规范化SHA256：
`ba2ce9842ca69b31d86375ef482976df96d8b414181a05e3b605f14de48c288d`。

本轮Aligned正式恢复训练 **0步**。CPU单元测试中的短更新只验证实现；此前300/50k预算均不能作为静态学习成败判据，没有可报告的正式学习曲线。

训练定义为 **Reimplemented Chapter-5 baseline under aligned temporal protocol**，不是exact reproduction。
继承原V3 reward、SAC、双Critic、attention、PER与normalizer；训练用30%无障碍/70%随机静态布局、4类固定均风、原3%噪声类。物理弧度执行器调用、历史对齐、独立随机流和安全检查属于明确工程修复，不作为研究贡献。

分阶段100k→500k→1M→1.5M→2M；每次只运行指定stage，保存后停在review点。100k关注finite/reward趋势/是否脱离随机，不要求已经达到最终Gate。后续是否延长依据曲线和固定bank，不因结果差自动加步数。
定期checkpoint自动执行主bank；best只用明确数值排序作指针，不等于PASSED。

保存内容包含Actor/Critic/target、全部optimizer、alpha、normalizer、完整replay与priorities、历史窗口、环境/噪声/RNG状态、config、bank/source/Git指纹。恢复拒绝配置、可执行源码、bank或runtime漂移；不同Python/Torch版本不声称精确恢复。
一个run目录使用进程文件锁；已有目录没有`--resume`时拒绝启动，防重复实验。服务器非Git快照使用`static_deployment_manifest.json`绑定本机revision/diff及实际源码hash。

### 唯一建议启动命令

服务器项目目录已同步入口、配置和bank。先进入该目录，使用以下唯一入口；它自己检查空闲GPU，没有空闲卡则在启动训练前拒绝。

```bash
cd /home/ot/Students/hs/sailboat-research
TMPDIR=/home/ot/Students/hs/tmp XDG_CACHE_HOME=/home/ot/Students/hs/cache MPLCONFIGDIR=/home/ot/Students/hs/cache/matplotlib \
  .venv/bin/python -B research/chapter5_static.py train \
  --config configs/chapter5_static_aligned.json --history-protocol aligned \
  --through-stage 100000 \
  --output research/outputs/chapter5_static_aligned_seed101
```

现有checkpoint续跑使用同一入口、同一run目录和`--resume <确切step文件>`；先核对原进程是否仍运行。不要启动第二个seed或并行Reactive/Predictive。
服务器入口在导入Torch前将TMP、XDG、CUDA、Torch/extension、Triton/Inductor缓存全部绑定到hs，并检查真实路径；不修改共享账户HOME。

## 6. 测试、资源与实际限制

本机9项测试通过（11.13s）；hs最终缓存边界版9项测试通过（22.68s）。覆盖：

1. Legacy/Aligned配对与索引；2. bank确定性/200条/布局约束；3. 风与noise不受replay RNG干扰；4. 40m段内侵犯与中止；5. Legacy hidden reset；6. 记录hook不改变Legacy原动力学；7. Gate未过禁止freeze；8. 完整运行与中断恢复逐参数/replay完全相同；9. 插入checkpoint评估不改变后续训练参数。

证据：`chapter5_static_tests_final_20260915.txt`、`chapter5_static_tests_server_cacheguard_20260915.txt`（均在research/validation）。源配置、bank和代码同步后已在hs核对hash并测试，不是仅import通过。

2026-09-15 **12:51:30 +08:00** preflight：

| GPU | 显存MiB | 利用率 | 原计算PID |
|---|---:|---:|---:|
| 0 | 5261 / 49140 | 27% | 2884993 |
| 1 | 32893 / 49140 | 87% | 2919829 |

启动器实际返回`REFUSED_OCCUPIED_GPUS`；没有分配GPU、启动训练或停止他人任务。快照不代表未来状态。
服务器Python3.13.11、Torch2.13.0+cu130、NumPy2.4.6、SciPy1.18.1、Gymnasium1.3.0；仍是借用部分共享包的hs环境，未宣称全隔离锁定。CUDA梯度及长程收敛待空闲卡后的Stage A验证。

## 7. 冻结规则及修改范围

当前未创建 `checkpoints/chapter5_static_recovered/`。未来必须主bank达到95%/85%、重跑一致、hidden/safety检查及轨迹/帆舵审核通过，才能用`freeze`导出不可覆盖的目录。
导出包括权重/normalizer或完整bundle、配置、seed（旧seed未知明确标记）、评估、bank、revision/diff/source哈希和审核记录。缺少证据或目录已存在时拒绝覆盖。

本轮修改/新增：

- `research/chapter5_baseline.py`：显式protocol兼容开关，保留旧工程诊断。
- `research/chapter5_static.py`：静态bank/两协议/评估/训练/恢复/冻结；无动态实现。
- `research/chapter5_artifacts.py`：只读候选检查；`research/test_chapter5_static.py`：回归测试。
- `configs/chapter5_static_aligned.json`；主bank、搜索CSV/JSON、测试与评估收据、图片。
- `research/supplements/yc_attention_121x/`：18项原样参考资产副本及hash，不是复制开发两套网络。
- 两份审计/恢复文档及本报告；CURRENT_PLAN/PROJECT_STATE/PROJECT_MEMORY同步当前事实。

参考子模块未修改；原有`.gitignore`及未提交研究产物保留；未commit/push。`git diff --stat`不显示untracked新增文件，不能只拿其行数代表本轮全部修改。
当前tracked diff为4文件、95行新增/50行删除，包含接手前修改；本轮新增Python职责文件为static运行器645行、artifact检查器136行、测试135行，既有baseline入口465行（本轮增加显式协议选项）。详细产物清单以本节和research/validation为准。


## Stage 1.5 正式冻结定义（2026-09-15）

正式基线为“a reimplemented Chapter-5-style baseline under the corrected observation and aligned temporal protocol”，不称exact reproduction。seed101，从头初始化Actor/Critic/normalizer；Legacy只保留历史调试。

Aligned train/eval统一构造最近10个(s[k],a[k])，k<t；当前s[t]单独输入。窗口不足时左侧重复本episode初始观测、动作零，索引-1；无mask，全部10 token参与attention。LSTM每次完整窗口前向，未传入h/c，PyTorch默认零初值；不使用episode streaming hidden。训练时dropout按原网络启用，评估关闭；这不改变历史配对规则。normalizer沿用原4批replay更新，评估冻结。

配置在正式训练开始前补充上述padding定义和阶段[100k,500k,1M,2M]；bank坐标/hash未修改，bank生成时配置hash为旧版本是预期记录。每个run保存config、provenance、源文件快照、bank副本和含optimizer/replay/RNG的完整checkpoint；resume强制核对config/bank/source/runtime。开始后任何学习配置变更必须INVALIDATED_FOR_CONFIG_CHANGE并建新run。

训练前入口：`research/pretrain_static_sanity.py --output NEW_DIRECTORY`，包含前12步历史/padding/零hidden/attention/Actor/Critic/reward finite检查以及完整静态回归（严格加载、精确resume、eval不污染训练、safety、bank不变）。测试是CPU工程运行，不计正式steps。

新增Q幅度、sample entropy、动作饱和度、损失/alpha日志及1000步GPU/进度记录。0步和checkpoint评估使用同一200场景bank，deterministic action、dropout关闭；健康判定入口`research/static_training_report.py RUN_DIRECTORY`，数值HEALTHY不是最终行为通过，100k后还需轨迹审查。

分层固定为no/static；static按nominal直线距离d的几何代理分hard(d<40)、medium(40<=d<80)、easy(d>=80)，由已有parity几何定义派生，不更改bank、不根据学习结果重选。记录四类失败标签，可重叠。

best_static_safe_success.pt按静态safe success、较低violation、较低timeout、较短成功navigation time排序。best_reward.pt仅在保存点比较最近20个训练episode平均return，不能代替正式选择。曲线脚本只画实际已完成节点，无未来伪造值。

仅启动seed101到100k，完成后evaluation+health+轨迹报告，不自动继续500k/2M。满足95%/85%/<=15%及行为/重现门后，最终冻结目录为`research/outputs/chapter5_static_aligned_seed101/frozen_baseline/`。未过门保持IN_PROGRESS。


### Stage1.5 启动回执

本机和服务器PRETRAIN_SANITY均PASSED（15项/10回归）；服务器证据`research/validation/pretrain_sanity_stage15_server/PRETRAIN_SANITY.json`，GPU合成梯度证据`stage15_cuda_witness.json`。首轮新增小bank汇总测试失败已修复并重跑通过，未进入正式run。

正式配置hash：`1e26c257e1ab31da26f82fad8acb402b28361684d5e4da0d0e44b9c60e6cac3f`；主bank hash保持`0719885cc70a25d0a943380726880805e36c2a1bbf8337b2ab0db724798897fc`。部署前旧代码已在hs内打包保留；source/config hashes现场通过。

seed101 run已启动：监督PID2939239，训练PID2939240；日志`research/validation/stage15_launch.log`，运行目录`research/outputs/chapter5_static_aligned_seed101`。GPU0在启动前空闲（15MiB/无计算进程），GPU1不动。先0步评估再100k；尚无100k结论。监督器在训练退出后保存stage15_exit.json并生成training_health.json，不自动运行下一阶段。

本任务心跳`chapter-5-seed101-100k`每10分钟仅跟进并在完成时验收/汇报，之后暂停。所有状态以当前运行收据为准。

### 资源等待（2026-09-15 17:27）

eval_0已完成，no/static safe success均0；这是未训练初始网络。最后完整训练进度10,000环境步（预热，尚无梯度更新）。GPU0后来加入他人任务，按用户无空闲卡暂停约定，对已核对cmd/cwd/start_ticks的本任务PID2939240发送SIGSTOP。没有修改配置/源码或停止他人任务。原进程保留RAM状态及约560MiB显存，尚未新增持久训练checkpoint。心跳在GPU0无其他计算任务且身份仍匹配时仅SIGCONT原进程，不重启。暂停收据：research/validation/stage15_resource_pause.json。

资源恢复：2026-09-15 21:42核对GPU0无其他计算PID，原进程start_ticks/cmd/cwd及T状态匹配后SIGCONT同一PID2939240。暂停15251.6秒，未重启、未重跑eval_0、未改配置。stage15_resource_resume.json保存恢复证据；wall_seconds含暂停时间，后续报告需分别给总耗时与有效耗时。

- 2026-09-15 21:54第二次资源暂停：GPU0新他人PID3135486占43888MiB，已SIGSTOP原PID2939240；最后完整进度22,000步、808次critic更新，末次q_loss3.2062/a_loss3.9935/alpha0.199596均有限。RAM保留、没有新磁盘checkpoint，当前显存约758MiB。证据stage15_resource_pause_2.json；未来恢复必须用独立resume_2回执，耗时扣除两次暂停。不是训练BROKEN。

- 2026-09-15用户澄清共享GPU规则后，已恢复原PID2939240（第二次暂停773.0秒，resume_2收据）。仅因其他任务后来加入同卡暂停的旧处理已被AGENTS新规则取代；配置/源码/学习状态未改，继续100k审核节点。


## Stage A 100k 完整验收（2026-09-16）

**TRAIN_HEALTH=SUSPICIOUS；STATIC_BASELINE_STATUS=IN_PROGRESS。** 数值检查通过，但导航行为未建立；建议先诊断，不直接推进500k。未启动后续训练或CPA。

权威收据：`research/outputs/chapter5_static_aligned_seed101/stage100k_review.json`；原始数值自动报告`training_health.json`中的HEALTHY仅代表有限值/阈值检查，保留原件，与本次综合行为判断区分。

1. **实际steps**：100,000，122个训练回合；原进程正常退出，`research/validation/stage15_exit.json` returncode=0。完整checkpoint留在服务器原run，SHA256=20fa658b77667a12907cba90f75aebd45629944bf789d7adfaa3a7eaa72ebbfa；本次未取回权重副本。
2. **耗时**：从9月15日13:39:25至9月16日03:44:16，总14小时4分50秒；扣两次暂停4小时27分5秒后为9小时37分46秒（含初始/最终评估）；训练循环扣暂停、不含评估为2小时35分38秒。最终200场景评估约3小时23分。
3. **GPU**：GPU0合法空闲启动。100k末次整卡利用率100%、总显存44275MiB；包含后来加入的他人任务，不能作为本任务专属利用率。无OOM/异常退出证据，不因共享GPU推断失败原因。
4. **Actor/Critic/alpha**：8,002次Actor、32,008次Critic更新。最后1000次更新均值Q loss=10.5473、Actor loss=12.4110、alpha=0.184851、Q绝对最大值的均值131.6983、sample entropy=0.163645、动作饱和比例0.00008594。最后alpha=0.18462；没有非有限值或预设数值发散阈值触发。损失正负不单独证明学习正确。
5. **训练reward**：首20回合均值−725.45，末20回合−572.19；曲线波动大，混合场景与探索策略下的回报提升未转化为可靠确定性导航。
6. **无障碍**：1/100成功，97/100超时，2/100出界；唯一成功718步、航迹1421.38m。未满足95%门。
7. **静态**：0/100安全成功；5个easy、20个medium、75个hard均0成功。分层为直线几何距离代理，不等于帆船可达性。未满足85%门。
8. **安全违规**：34/100；easy 2/5、medium 5/20、hard 27/75。平均最小距离84.59m、中位数74.57m；采用40m积分节点线性扫掠近似。
9. **超时**：总体158/200=79%，静态61/100；静态另外5/100出界。相对step0，静态违规21%→34%，总体超时89.5%→79%，不能把超时下降解释为导航改善。
10. **轨迹与帆舵**：已生成并查看`learning_curves.png`、`eval_100000/five_trajectories.png`及`actuators_hidden.png`。三个预定无障碍案例均超时且明显偏离目标，最终目标距离832.27/675.59/1129.80m；fixed_static_0000在107步违规；random_static_0049曾接近目标119.79m后远离，536步结束。部分帆舵长时间保持常数，随机静态示例帆角达到−π/2；低平均变化率不能视为有效稳定控制。五条预定轨迹中未观察到可靠绕障证据。
11. **综合健康**：SUSPICIOUS，非已确认BROKEN。100k是早期工程检查，低性能本身不证明实现错误；控制长平台和基础导航缺失值得廉价诊断。重复运行的行为稳定性本轮未重新验证。
12. **500k建议**：暂不直接追加。下一步建议固定少量无障碍状态/轨迹，核对deterministic动作、物理增量、量化死区、帆舵限幅与实际更新，区分动作落在死区、策略尚未学会导航与训练/评估不一致。均为待验证假设，不能写成根因；未改配置/网络、未启动该诊断实验。

学习曲线仅有0和100k两个完整评估点，连线不代表中间测量；固定200场景属于开发/选择bank，单seed结果不支持泛化。日志、两次评估和来源快照已取回；关键日志/评估SHA与服务器逐项一致（见review收据）。正式参数、bank、原始summary保持原样；没有冻结合格baseline。
