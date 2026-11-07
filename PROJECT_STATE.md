# Project State

## 项目目标与事实边界
- 基于师兄的无人帆船强化学习工作完成有独立增量的小论文，仅纯仿真；优先可实现、可复现与投稿可行性。
- 候选 CCDC / ICAUS / ICCA / DDCLS，期望约 2027-09-14 前录用，不保证录用；具体届次、学校认定、ICCA 全称和训练预算仍需确认。
- 静态避障与注意力属于继承基础，不得标成新增贡献。当前研究主线是第五章静态基线恢复与失败诊断，CPA/动态任务暂停。
- 两端开发文件已同步，并在服务器完成有界 CPU 冒烟；未启动训练、续训或正式评估。历史文档中的运行状态、PID、资源占用与启动许可不是当前状态。

## 唯一开发入口与来源
- Windows Git 同步仓库：`C:\Users\74095\hs\SailBoat\sailboat-research`；GitHub：私有仓库 `N0TPO3T/sailboat-research`。实际开发、调试、测试和实验均在服务器完成，本地不承担开发或运行职责。
- 唯一日常开发分支为 `main`；原研究基点 `ce83544e8dfd6a6833da03d626025b4e0a2ba000` 和后续整合提交保留在历史中，不再要求使用临时整合分支。
- `sailboat_RL/` 是主仓库直接跟踪的普通参考目录，677 个文件及文件模式来自 `19422525cb337831ca68f53a45661d34f3683ee1`，内容逐字节保留。已移除子模块依赖；旧 `N0TPO3T/sailboat_RL` 只归档留证，不作为开发入口。
- 海南工程提交：`143a508c422f746adb7af3577818060053f2620b`，比师兄基点多 8 个提交。它没有改动原 PART4/PART5、Gymnasium 参考目录和 requirements，而是增加独立工程包、回归测试及工程上下文。
- 海南下载工作区不完整，原 pack/index 不匹配；123 个有效 loose objects 经 SHA1 校验后与 GitHub 基础历史合并，完整 Git 对象校验通过。原下载保持不动，不能用其零字节工作文件覆盖有效源码。
- 海南完整原始历史保存于 `archive/hainan-learner-sync-v2`；另一个可恢复历史提交 `8837440c9eec84fd68cd757845b89f3981103279` 保存于 `archive/hainan-recovered-extra`，不是当前工程版本。
- `engineering/sailboat_rl/` 和 `engineering/tests/` 保存海南工程实现；仅测试参考路径按整合目录适配。独立源码根避免 Windows 上 `sailboat_rl` 与 `sailboat_RL` 的大小写冲突。
- `research/`、`configs/`、`docs/` 导入自主服务器 `/home/ot/Students/hs/sailboat-research`，包含原 GitHub 没有的后续研究工作。服务器目录已由旧部署副本接入同一主仓库 Git 历史，保留原环境和实验产物。
- 主服务器源快照中 489 个参考文件与原版提交 blob 哈希一致；完整原版的 677 个文件已纳入本仓库，不依赖旧仓库补齐。
- 原始主服务器上下文、部署前/后 TAR 与运行产物保存在来源归档中；根目录只维护协调后的当前事实。来源清单见 `research/validation/consolidation_20261001.json`。

## 目录与运行职责
- `research/chapter5_static.py`：第五章静态 bank/evaluate/plot/train/freeze 工具，明确区分 Legacy 与 Aligned 协议；配套 `chapter5_baseline.py`、`chapter5_artifacts.py`、`pretrain_static_sanity.py`、`static_training_report.py`、`v2_v3_static_parity.py` 和 `test_chapter5_static.py`。
- `configs/chapter5_static_aligned.json`：当前 corrected-V3、Aligned、seed101 配置；固定开发 bank 位于 `research/validation/static_eval_bank.json`。
- `engineering/sailboat_rl/`：第四章 14/16 维环境、SAC-FC/SAC-LSTM、优先回放、续训状态与评估实现。它不是第五章 18 维注意力研究入口，不能自动替代后者。
- `research/smoke_baseline.py`：使用同仓库内未改动的原版参考文件与根目录 `model/` 的第四章 CPU 闭环验证；不代表海南工程代码已验证。
- `model/`：原 Git 已跟踪的三套第四章检查点，共 12 个文件；`师兄大论文.pdf`、`yara.pdf` 是原研究资料。
- 安装、克隆和有界 CPU 命令见根 `README.md`。工程命令须设置 `PYTHONPATH` 指向 `engineering/`。
- `.venv`、缓存、凭据不迁移；部分第五章工具依赖 Linux、fcntl 和 hs 路径约束。Windows 仅作 Git 同步，服务器承担开发与实际运行。

## 当前研究结果：尚无合格冻结基线
- 主服务器历史收据记录 seed101 corrected V3 + Aligned run 完成 100,000 环境步及 200 场景评估，2026-09-16 正常退出（returncode=0）。没有据此启动 500k 或 CPA。
- `TRAIN_HEALTH=SUSPICIOUS`，`STATIC_BASELINE_STATUS=IN_PROGRESS`。自动数值检查为 HEALTHY，但行为检查 `COMPLETED_NOT_PASSED`；不能把数值有限等同于策略有效。
- 无障碍：1/100 到达、97 超时、2 出界。静态：0/100 安全到达、34 违规、61 超时、5 出界。证据是 run 内 `stage100k_review.json`、训练健康与逐场景结果，不是本次重新训练得到的结果。
- 五条预定轨迹显示偏航与长时间恒定帆舵。2026-10-02 隔离探针确认 Aligned 执行器噪声调用存在单位契约错误，且相关源码与 100k source_snapshot 一致；该错误对失败的贡献仍未量化，不能据此排除学习不足等原因。具体证据与开发约束见下方审查节。
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
- 主服务器入口：`ssh donghai`（`ot@172.16.2.249`），工作范围 `~/Students/hs`。已只读连接确认用户为 `ot`、工作根真实路径为 `/home/ot/Students/hs`，且 `/home/ot/miniconda3/condabin/conda` 可执行；本次未创建环境。环境与缓存隔离规则见 `AGENTS.md`，不改共享 base、系统环境、其他学生目录或进程。
- 海南 `hainan`（`user@172.16.1.59`）只是历史工程来源，后续不是默认运行端。连接曾中断；源码通过已校验 Git 对象恢复，不依赖连接恢复来猜测代码。
- 主服务器既有 `.venv` 借用共享 Python/PyTorch；已观察版本 Python 3.13.11、PyTorch 2.13.0、Gymnasium 1.3.0。它不是完全锁定的跨平台复现环境。
- 同步必须先核对服务器和本地改动，不能把服务器项目当作可删除的镜像。以服务器实际开发版本为准，经差异核对后同步源码、配置与必要收据回本地 Git；不以本地旧版本覆盖服务器新工作，不覆盖运行中的实验目录。
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

## 2026-10-02 本地审查与开发起点
- 本地审查基点为 `main` 的 `b079399`；本次未拉取远程、部署或核查服务器实时进程。用户已有未跟踪的 `大论文-Final.pdf` 与 `research/validation/advisor_action_units_probe.json` 保持原样。
- **Verified：动作单位契约错误。** `research/chapter5_static.py:184-190` 的 Aligned 分支先把命令乘动作上限转为弧度，再传给 `noise_utils.py:264-294` 要求归一化输入、返回归一化输出的接口，随后直接将返回值当弧度。影响死区、量化和最终限幅；本次只审查，尚未修复。
- 在本地 Python 3.11.4 / NumPy 1.24.3 实际调用原噪声类，seed=0、noise_ratio=0.03、command=[0.2,0.2]：当前调用输出约 `[0,1.775406]` 度，契约一致调用约 `[2.025368,1.923399]` 度，与已有 `advisor_action_units_probe.json` 一致。探针不包含环境角度量化、动力学或策略闭环。
- 本次重新核对 checkpoint 和 Stage 100k review 列出的五项证据 SHA256，全部匹配；从 200 行 episodes 复算的成功、违规、超时与出界计数与上述历史结论一致。没有重跑历史评估，也没有改写旧收据。
- 本机缺少 PyTorch、Gymnasium、Pygame 和 stable-baselines3，未运行完整环境/策略闭环或回归套件；上一节的测试通过记录仍为历史服务器验证，不是本次结果。
- 本次有界诊断、源码身份、历史资产完整性与复算计数收据：`research/validation/code_review_20261002.json`。
- 研究链路另有三项静态审查问题，尚未运行触发场景：独立 `evaluate` CLI 仅加载三件套 `.pth`，不能直接加载训练保存的 `step_N.pt` 完整 bundle（`chapter5_static.py:265-280,584-592,693-700`）；`freeze_baseline` 重算当前源码 provenance 而非保留评估时来源（`:644-662`）；冻结入口未强制检查 Aligned/V3，数值门与人工 review 通过的 Legacy/V2 也可被标为 PASSED（`:638-642,658`）。这些问题需在独立重复评估与正式冻结前处理，不代表当前已有错误冻结产物。
- 第四章工程审查（不归因第五章失败）：`noise_utils_wind.py:157-163` 把环境的第14槽风速/第15槽风向反用；本地实际调用零比例噪声仍将 `[8 m/s,-1 rad]` 变为 `[1.716815,0]`，已复现。以下仅静态确认，未运行触发场景：`training/runtime.py:264-269` 在 checkpoint 步数重名时返回旧状态而不保存当前状态；`training/train_sac_lstm.py:331-338` 回放历史配成 `(s_next,a)`，与在线 `(s_current,a)` 契约错拍；同文件 `:314-342` 非有限 transition 仅计数仍入回放，可污染 `algorithms/sac_lstm.py:146-149` 的归一化统计；`evaluation/analyze_results.py:459-506` 含写死的零成功/最佳模型结论和复用150°成功率描述180°，新 CSV 下可产生不实报告。第四章不作为当前第五章基线替代入口。

## 2026-10-02 两端开发同步
- 服务器与 Windows 工作区使用同一 `main` 基点 `b079399bfeb659c228156f767962374f95f56614`；两端保留一致的未提交文档和新增资料，没有自动提交或推送 GitHub。不是后台自动双向同步。
- 同步前核对全部开发文件及服务器存量文件：无新增服务器源码冲突，467 个 Git 忽略的存量资产在本机也存在且哈希一致。服务器新增 239 个开发/资料文件，更新 5 个旧说明/配置文件，旧 `.gitmodules` 备份后移出开发目录；后续补充本节及同步收据。
- 原件与传输清单保存在服务器 `/home/ot/Students/hs/sync-backups/20261002_104555/`；原 `.venv`、模型、100k 运行目录和历史收据未覆盖。同步不修复上节记录的算法/接口问题。
- 使用服务器既有环境、禁用 GPU、单 CPU 线程：三套原版策略各运行 5 步，状态/动作/奖励有限；新同步的工程 CLI 运行三套模型各 1 场景、最多 5 步，生成 3 行结果。只证明入口可运行，不证明策略效果，未重跑回归套件。
- Git 核查额外发现 66 个历史文件相对提交基点仅有 CRLF/LF 差异；原始文件字节保留不变。本机旧索引统计曾漏报，确认无暂存改动后已刷新索引统计，两端现在显示相同的未提交状态，不将这些换行差异误认为新增算法改动。
- 同步与冒烟证据见 `research/validation/server_sync_20261002.json`；完整冒烟输出保存在上述服务器备份目录。后续在服务器开发；提交/推送后，本机在工作区干净时拉取。服务器 GitHub 凭据未复制，推送认证仍须单独确认。
