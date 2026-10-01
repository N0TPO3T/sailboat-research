# Project State

## 项目目标与事实边界
- 基于师兄的无人帆船强化学习工作完成有独立增量的小论文，仅纯仿真；优先可实现、可复现与投稿可行性。
- 候选 CCDC / ICAUS / ICCA / DDCLS，期望约 2027-09-14 前录用，不保证录用；具体届次、学校认定、ICCA 全称和训练预算仍需确认。
- 静态避障与注意力属于继承基础，不得标成新增贡献。当前研究主线是第五章静态基线恢复与失败诊断，CPA/动态任务暂停。
- 本次任务是跨设备版本整理，不授权重新启动训练、续训或正式评估。历史文档中的运行状态、PID、资源占用与启动许可不是当前状态。

## 唯一开发入口与来源
- Windows 正式目录：`C:\Users\74095\hs\SailBoat\sailboat-research`；GitHub：私有仓库 `N0TPO3T/sailboat-research`。
- 唯一日常开发分支为 `main`；原研究基点 `ce83544e8dfd6a6833da03d626025b4e0a2ba000` 和后续整合提交保留在历史中，不再要求使用临时整合分支。
- `sailboat_RL/` 是主仓库直接跟踪的普通参考目录，677 个文件及文件模式来自 `19422525cb337831ca68f53a45661d34f3683ee1`，内容逐字节保留。已移除子模块依赖；旧 `N0TPO3T/sailboat_RL` 只归档留证，不作为开发入口。
- 海南工程提交：`143a508c422f746adb7af3577818060053f2620b`，比师兄基点多 8 个提交。它没有改动原 PART4/PART5、Gymnasium 参考目录和 requirements，而是增加独立工程包、回归测试及工程上下文。
- 海南下载工作区不完整，原 pack/index 不匹配；123 个有效 loose objects 经 SHA1 校验后与 GitHub 基础历史合并，完整 Git 对象校验通过。原下载保持不动，不能用其零字节工作文件覆盖有效源码。
- 海南完整原始历史保存于 `archive/hainan-learner-sync-v2`；另一个可恢复历史提交 `8837440c9eec84fd68cd757845b89f3981103279` 保存于 `archive/hainan-recovered-extra`，不是当前工程版本。
- `engineering/sailboat_rl/` 和 `engineering/tests/` 保存海南工程实现；仅测试参考路径按整合目录适配。独立源码根避免 Windows 上 `sailboat_rl` 与 `sailboat_RL` 的大小写冲突。
- `research/`、`configs/`、`docs/` 导入自主服务器 `/home/ot/Students/hs/sailboat-research`，该目录是部署副本而非 Git 仓库。它包含原 GitHub 没有的后续研究工作。
- 主服务器源快照中 489 个参考文件与原版提交 blob 哈希一致；完整原版的 677 个文件已纳入本仓库，不依赖旧仓库补齐。
- 原始主服务器上下文、部署前/后 TAR 与运行产物保存在来源归档中；根目录只维护协调后的当前事实。来源清单见 `research/validation/consolidation_20261001.json`。

## 目录与运行职责
- `research/chapter5_static.py`：第五章静态 bank/evaluate/plot/train/freeze 工具，明确区分 Legacy 与 Aligned 协议；配套 `chapter5_baseline.py`、`chapter5_artifacts.py`、`pretrain_static_sanity.py`、`static_training_report.py`、`v2_v3_static_parity.py` 和 `test_chapter5_static.py`。
- `configs/chapter5_static_aligned.json`：当前 corrected-V3、Aligned、seed101 配置；固定开发 bank 位于 `research/validation/static_eval_bank.json`。
- `engineering/sailboat_rl/`：第四章 14/16 维环境、SAC-FC/SAC-LSTM、优先回放、续训状态与评估实现。它不是第五章 18 维注意力研究入口，不能自动替代后者。
- `research/smoke_baseline.py`：使用同仓库内未改动的原版参考文件与根目录 `model/` 的第四章 CPU 闭环验证；不代表海南工程代码已验证。
- `model/`：原 Git 已跟踪的三套第四章检查点，共 12 个文件；`师兄大论文.pdf`、`yara.pdf` 是原研究资料。
- 安装、克隆和有界 CPU 命令见根 `README.md`。工程命令须设置 `PYTHONPATH` 指向 `engineering/`。
- `.venv`、缓存、凭据不迁移；部分第五章工具依赖 Linux、fcntl 和 hs 路径约束。Windows 负责编辑/Git，主服务器负责实际运行。

## 当前研究结果：尚无合格冻结基线
- 主服务器历史收据记录 seed101 corrected V3 + Aligned run 完成 100,000 环境步及 200 场景评估，2026-09-16 正常退出（returncode=0）。没有据此启动 500k 或 CPA。
- `TRAIN_HEALTH=SUSPICIOUS`，`STATIC_BASELINE_STATUS=IN_PROGRESS`。自动数值检查为 HEALTHY，但行为检查 `COMPLETED_NOT_PASSED`；不能把数值有限等同于策略有效。
- 无障碍：1/100 到达、97 超时、2 出界。静态：0/100 安全到达、34 违规、61 超时、5 出界。证据是 run 内 `stage100k_review.json`、训练健康与逐场景结果，不是本次重新训练得到的结果。
- 五条预定轨迹显示偏航与长时间恒定帆舵；学习不足、执行器死区、训练/评估不一致等仍是待区分假设，根因未确定。
- 冻结门：至少 95% 无障碍成功、85% 静态安全成功，并通过轨迹/执行器/安全/重复性检查。当前 200 场景 bank 是开发与选择集合，不是未触碰的论文最终测试集。
- 现有 run 路径 `research/outputs/chapter5_static_aligned_seed101/`；原始 checkpoint、source_snapshot、配置、bank、评估、日志、暂停/退出回执须整体保存，不改写历史收据中的当时本地复制状态。
- `docs/CHAPTER5_STATIC_RECOVERY.md` 的末尾 Stage A 100k 节是该报告最新阶段；前部零步/准备启动段落是历史记录，不能用于判断当前阶段。

## 环境与旧模型的语义边界
- 第四章根模型是 14 维无风观测 FC、16 维显式风 FC、14 维 LSTM。已保存的 2026-09-14 收据证明严格加载与有界 CPU 闭环，不证明总体成功率，也没有完整 optimizer/replay/RNG 续训状态。
- 第五章参考 V3 观测 18 维、动作 2 维；每动作约 1 秒，Dormand–Prince 自适应积分，0.05 秒是初始步长而非固定 20 步。
- V2 障碍槽是全局坐标，V3 是距离/相对角；当前 Aligned 层另有积分步长上限、线段近似安全检查、时序配对与噪声约束。它不是 V2 等价复现，安全检查也不是精确连续曲线证明。
- 原论文表 5.1 的 95.3%/93.3%/80.8% 是论文报告，不是本项目复现结果。固定风向、障碍布局、窗口 5/10、streaming/sequence、normalizer 和旧配置绑定均需区分。
- yc 的 selfatt 0113 与当前第五章注意力实现不同；历史日志异常、代理环境下少量失败都不足以确认师兄最终模型身份或唯一失败原因。
- `research/supplements/` 保存历史源码与兼容性证据；`research/weights_library/20260928_import/` 保存 9 月模型目录、来源清单及 source_evidence。
- 9 月目录文档记录 416 个 yc 权重/统计文件、109 组模型及 81 个来源代码文件；此处是来源目录说明，不把文件名编号自动解释为真实训练步数或 seed。
- 新增 `user_0204_10800` 三件套的来源检查记录严格加载与有限合成前向；原始训练协议、V2/V3 语义和实际性能仍未知，不能称合格障碍策略。

## 服务器与资产管理
- 主服务器：`ot@172.16.2.249`；所有写入限定真实路径 `/home/ot/Students/hs/`。不改共享 base、系统环境、其他学生目录或进程。详细边界见 `AGENTS.md`。
- 海南 `hainan`（`user@172.16.1.59`）只是历史工程来源，后续不是默认运行端。连接曾中断；源码通过已校验 Git 对象恢复，不依赖连接恢复来猜测代码。
- 主服务器既有 `.venv` 借用共享 Python/PyTorch；已观察版本 Python 3.13.11、PyTorch 2.13.0、Gymnasium 1.3.0。它不是完全锁定的跨平台复现环境。
- 同步必须先核对远程改动，不能把原部署目录当作可删除的镜像。默认本地修改提交，再部署到独立版本目录验证，不覆盖正在使用的实验工作区。
- 模型库、完整运行 checkpoint 与大体积输出不加入普通 Git；小型源码、配置、清单及必要收据进 Git，完整归档放私有 GitHub Release。恢复时按清单校验 SHA256。
- 原始两个 hs TAR 的成员已检查，包含静态恢复代码/配置/部署收据，没有补齐此前文档提及的动态研究文件。
- 完整主服务器归档已下载并核对整体 SHA256，大小 1,020,662,564 字节、包含 1,115 个文件；原始归档与解压快照保存在 `C:\Users\74095\hs\SailBoat\source-backups\20261001`。
- 正式本地项目已补齐 439 个此前未复制的资产，没有覆盖冲突。`step_100000.pt` 与历史收据的 SHA256 `20fa658b77667a12907cba90f75aebd45629944bf789d7adfaa3a7eaa72ebbfa` 一致，五项关联运行证据哈希也一致；不改写旧收据当时的 `checkpoint_local_copy=false`。

## 尚未恢复的资料
- 主服务器/本次 TAR 中未发现 `research/idea-stage/IDEA_REPORT.md`、`research/navigation_trace.py`、`research/dynamic_observation.py`、`docs/DYNAMIC_OBSTACLE_CODE_AUDIT.md`、`docs/CHAPTER5_ARTIFACT_SEARCH.md` 等旧文档引用目标。
- 这些引用可能来自原 Mac 工作区；不创建空文件冒充恢复，不据文字声明动态代码已整合。保留来源原文供后续核对。
- 第五章最终论文模型身份、原训练环境与实际统计仍未完全绑定；本次归档与代码整理不解决这些研究未知。

## 当前验证边界
- 已从 GitHub 进行不带递归子模块的全新普通克隆：零 gitlink、零嵌套仓库，677 个参考文件逐字节及目录树哈希与原提交一致。证据见 `research/validation/single_repository_20261001.json`。
- 将这份克隆中的运行源码部署到主服务器独立临时目录验证，禁用 CUDA，CPU 线程为 1；缺失依赖只安装在临时 deps，验证后已清理。原服务器项目、`.venv` 与共享 base 未修改。
- 海南工程回归：31 项运行，30 项通过、1 项跳过；第五章静态回归：10 项全部通过。
- 原版三套第四章模型分别完成 50 步有限 CPU 闭环，障碍环境额外完成至多 5 步零动作检查；最新证据见 `research/validation/single_repo_reference_smoke_20261001.json`。
- 海南工程 CLI 使用三套 seed100 模型各完成 1 个场景、5 步评估，生成 3 行 episodes 与汇总；最新证据见 `research/validation/single_repo_engine_smoke_20261001/`。
- 本机六个 Actor/normalizer 文件与实际 CPU 冒烟使用的服务器文件 SHA256 一致；9 卷源码归档的本地重组与整体 SHA256 验证通过。
- 本次验证不证明策略成功率、GPU 性能或论文复现；未启动正式训练、续训、500k 或 CPA。源代码自带历史空白/格式问题保持原样，不借整理任务批量格式化。
