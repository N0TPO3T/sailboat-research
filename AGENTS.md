# 项目上下文运行协议

## 职责与边界
- `PROJECT_STATE.md` = what is true now；当前事实的紧凑快照。
- `CURRENT_PLAN.md` = what we are doing now；唯一主要活跃线程。
- `PROJECT_MEMORY.md` = what we should not forget；稀疏、可检索的长期经验。
- Conversation = temporary scratch space；猜想、讨论和调试过程默认不持久化。
- 历史由 Git、实验目录、配置、结果、检查点、实验平台及正式文档保存。
- 持久上下文维护不增加执行、付费、发布、外发或共享资源操作权限。

## 组内服务器硬边界
- 在 `ot@172.16.2.249` 上，所有项目写入仅允许落在 `/home/ot/Students/hs/` 内；操作前核对真实路径，禁止通过符号链接越界。
- `/home/ot/Students/yc/` 及其他学生目录只读。可按需将yc文件复制到hs，记录来源与哈希；不得修改、覆盖、移动或删除原件。
- 环境、依赖安装、缓存、临时文件、日志和结果均放hs；禁止修改共享Conda base、他人环境、系统配置或共享缓存。
- 同用ot账号不等于拥有全部进程；只操作由本任务启动且有明确归属的作业，不停止他人任务、不擅自独占资源。
- GPU空闲检查用于新任务启动。任务在空闲卡合法启动后，其他任务后来加入同卡不构成暂停理由，不要求持续独占GPU；不得仅因其他PID出现、总显存升高或利用率高而暂停本任务。仅按实际故障/资源不足或用户明确指令处理，不操作他人任务。
- yc是历史补充，未经版本/配置/权重核验不能作为论文最终基线。SSH断线后先查原任务状态，不盲目重启。

## 自动恢复
每次 meaningful work 开始时，默认静默完成：
1. 阅读 `PROJECT_STATE.md`。
2. 阅读 `CURRENT_PLAN.md`。
3. 核查本任务涉及的实际代码、配置、测试和 artifacts。
4. 判断是否涉及已有长期经验。
5. 必要时按数据集、组件、loss、metric、实验族、故障或协议关键词搜索
   `PROJECT_MEMORY.md`，只展开相关条目，不默认通读。
- 不依赖历史聊天才能正确理解项目。
- 只有重大矛盾、影响决策的不确定性或必要授权缺口才需要专门告知用户。

## 证据与分类
- Verified：由当前代码、配置、测试、数据检查或可复现实验支持，可进入 STATE。
- Hypothesis：正在验证的解释，只进入 PLAN，并说明区分性检查。
- Speculation：尚未成为活跃假设的想法，留在 conversation。
- Durable Lesson：有证据且遗忘会导致昂贵重复或错误决策，才进入 MEMORY。
- 未核实的信息明确写 `Unknown / not verified`，不得补猜项目历史。
- 冲突时依次检查：可执行当前代码、当前配置、可复现实验证据、测试、
  数据/artifacts、STATE、MEMORY、PLAN 假设、旧文档、未验证聊天假设。
- 代码存在不等于运行通过；离线结果不等于闭环能力或泛化结论。
- 文档服从实际证据；发现过时事实应核查并修正。

## 自动维护与轻量 reconciliation
维护是 Agent 默认职责，不需要用户重复提醒或确认。
工作过程中正常实现、调试和实验，不因讨论量大就持久化。
每次 meaningful work 结束并完成必要验证后，静默判断：
- 当前现实改变 → 修改或替换 STATE 的相关事实及必要证据指针。
- 活跃线程理解或下一步改变 → 增量修改 PLAN，并删除无效内容。
- 发现有长期决策价值的经验 → 压缩写入 MEMORY。
- 无 meaningful knowledge change → 不修改持久文档。
- 只有长期操作协议改变才修改本文件。

## 活跃线程生命周期
- PLAN 不是 backlog，也不是一条用户消息对应一个新计划。
- 同一线程中的调试、参数调整、ablation 应增量维护。
- 仅在目标完成、明确放弃、切换独立目标或计划失去价值时整体重写。
- 保留 objective、已验证事实、活跃假设、少量下一步、阻碍和完成标准。
- 删除完成步骤、废弃假设、已解决 blocker 和无决策价值的中间过程。
- 线程结束时：当前事实归 STATE，长期经验归 MEMORY，原始输出留 artifacts。
- 清除中间猜想和完成清单；无已确认新目标时写 `No active research thread.`。
- 多项长期待办使用项目已有 tracker，不膨胀 PLAN。

## 长期记忆门槛
- 写入前问：遗忘是否现实地可能导致昂贵重复、再次踩坑或错误研究决策？
- 只有答案为 YES 且证据充分才写；没有经验时保持基本为空。
- 每条包含简短标题、Tags、Conclusion、Evidence、Implication；必要时加 Context。
- 失败实验压缩为尝试动机、实际观察、结论边界和重试条件，不保存流水。
- 不把普通修改、琐碎修复、单次参数结果或未验证解释写成长期经验。
- MEMORY 是证据而非权威；数据、实现、协议或假设改变后允许重新检验。
- 旧经验无价值则删除；仍有解释价值则标记 Superseded 并指向新结论。
- 随相关任务合并、去重和清理，不机械追加。

## 防止上下文熵增
- STATE 不是 changelog，PLAN 不是 session log，MEMORY 不是 experiment log。
- 不复制完整聊天、不保存 Agent reasoning transcript、不写会话总结存档。
- 每条事实只在一个 canonical location 维护；其他文件必要时引用。
- 文档变化由知识变化触发，而非每次代码修改机械触发。
- 不默认创建额外 TODO、NOTES、HANDOFF、PROGRESS、SESSION、SCRATCH 或计划文件。
- 现有正式文档若有独立职责则保留；冗余上下文先核实迁移，再安全清理。
- 保留用户数据、实验收据和用途不明的文件，不以文档整理为由删除。
- AGENTS 约 50–100 行，PLAN 尽量不超过 100 行，STATE 通常约 100–200 行；
  简单项目应更短，不为凑结构填充未知内容，复杂项目先压缩再扩展。
- 完成前自检证据、事实/假设边界、唯一信息位置、可恢复性和上下文预算。
- 优化目标：minimal context, maximum recoverability；保存 curated state 而非历史堆积。
