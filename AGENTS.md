# Persistent Context Protocol

本文件定义本仓库的长期 Agent 上下文协议。项目事实、当前工作和长期经验分别由下列三个文件维护；聊天仅作为临时工作区。

## Context Recovery

开始任何 meaningful work 时，默认静默执行：

1. 阅读 `PROJECT_STATE.md`，恢复当前 canonical truth。
2. 阅读 `CURRENT_PLAN.md`，恢复唯一 active thread。
3. 检查本任务直接涉及的代码、配置、测试和 artifacts；不要只信文档。
4. 判断任务是否可能命中长期经验；必要时按 dataset、model、loss、metric、experiment family、bug type、numerical issue 或 evaluation protocol 等关键词搜索 `PROJECT_MEMORY.md`。
5. 不默认通读 `PROJECT_MEMORY.md`，也不向用户逐项汇报恢复过程；发现重大冲突或关键未知时才说明。

证据冲突时依次检查：可执行当前代码、当前配置、可复现实验证据、测试、dataset/artifact、`PROJECT_STATE.md`、`PROJECT_MEMORY.md`、`CURRENT_PLAN.md` 中的 hypothesis、旧 prose 文档、未验证聊天假设。Markdown 不是权威，现实改变后应修正文档。

## Four Context Layers

- `PROJECT_STATE.md` = what is true now；当前事实快照，不是 changelog。
- `CURRENT_PLAN.md` = what we are doing now；唯一 active research/engineering thread，不是 backlog 或 session log。
- `PROJECT_MEMORY.md` = what we should not forget；稀疏、证据充分、会影响未来决策的经验。
- Conversation = temporary scratch space；brainstorm、猜测、debug 候选原因和临时参数默认随会话消失。

信息分类：

- Verified：由当前代码、配置、测试、数据或 artifact 支持，可进入 `PROJECT_STATE.md`。
- Hypothesis：正在验证但未建立，只进入 `CURRENT_PLAN.md`。
- Speculation：通常只留在 conversation。
- Durable Lesson：证据充分且遗忘会导致重大重复试错或错误决策，才进入 `PROJECT_MEMORY.md`。

## Autonomous Maintenance

用户无需提醒 context management。正常 coding、debugging、experimentation、analysis 或 brainstorming 期间不要即时记录所有想法。

每次 meaningful work 结束时，静默执行一次 lightweight reconciliation：

- current truth changed → 修改或替换 `PROJECT_STATE.md` 的相关内容；不要追加历史。
- active thread changed → 更新并删减 `CURRENT_PLAN.md`；删除已完成步骤、无效假设和已解决 blocker。
- durable lesson discovered → 经过写入门槛后，压缩追加或合并到 `PROJECT_MEMORY.md`。
- nothing meaningful changed → 不修改持久化文档。

线程完成或放弃时，把最终现实归入 state，把真正长期经验归入 memory，把原始输出留给实验 artifacts，删除中间猜测；没有新目标时把 plan 设为 `No active research thread.`

只有项目长期 Agent 协议本身变化时才修改本文件。

## Shared Server / Network Safety

这是多人共用实验室服务器。只操作当前用户和本项目明确范围内的文件与进程：不碰其他用户文件，不删除未知或已有文件/目录，不 kill、stop 或 renice 其他用户进程；删除任何已有内容必须先获得用户明确授权。

不得为项目任务使用 `sudo`、修改 `/etc`、NVIDIA driver/CUDA、系统 DNS/路由、防火墙（iptables/nftables）、systemd 或系统级代理，也不得重启服务器。禁止启用 TUN、TProxy、redir-port、auto-route 或任何透明代理；不要使用或修改已有的 7890/9090 监听服务。

确需外网时，优先使用现有 localhost-only Mihomo。先检查监听：

```bash
ss -lntp 2>/dev/null | grep -E ':(17890|19090)\b' || true
```

安全预期仅为 `127.0.0.1:17890`（mixed proxy）和 `127.0.0.1:19090`（controller）。若监听为 `0.0.0.0`、`*`、`::`、局域网 IP，或端口被未知进程占用，停止网络操作并报告用户，不自行修复系统网络。

17890 正常时只对当前命令显式 opt in：

```bash
HTTP_PROXY=http://127.0.0.1:17890 HTTPS_PROXY=http://127.0.0.1:17890 NO_PROXY=localhost,127.0.0.1 <command>
```

连续联网命令可仅在专用当前 shell 临时 export，并在结束后 unset。不得写入 `~/.bashrc`、`~/.profile`、`~/.zshrc`，不得设置永久/系统代理，也不得执行 `git config --global http.proxy ...` 或 `https.proxy ...`，除非用户明确要求。

若 Mihomo 未运行，不安装新的 Clash/Mihomo/sing-box，不创建 systemd service。只可检查 `PROJECT_STATE.md` 记录的现有用户态安装和 PID file；确需启动时，先确认无 17890 listener、无重复实例、不会覆盖未知 PID file，再以当前普通用户使用现有 binary/config 启动，且不修改 config；启动后必须复核两个端口仅监听 localhost。

禁止 `pkill mihomo` 和 `killall mihomo`。确需停止时，只能从 PID file 取得精确 PID，并确认进程属于当前用户且 executable 是既有 Mihomo binary；任何一项无法确认就不终止。

代理订阅和节点信息是敏感运行时凭据。不得读取、打印、总结、复制或提交 subscription URL、node address、UUID、password、token、secret；不得把它们写入聊天、日志、Git 或持久化项目文档。代理/provider 异常、连接失败或任何需要 sudo、TUN、DNS、路由、防火墙、覆盖代理文件的情况，都应停止并向用户报告问题、当前状态、可能原因、可选方案和推荐方案。

## Anti-Entropy Rules

- 不把 `PROJECT_STATE.md` 写成 changelog。
- 不把 `CURRENT_PLAN.md` 写成 session log、完成清单或长期 backlog。
- 不把 `PROJECT_MEMORY.md` 写成 experiment log、参数搜索表或研究日记。
- 不复制聊天原文或 Agent reasoning transcript。
- 不因普通代码修改机械更新文档；更新由 knowledge change 触发。
- 同一事实只维护一个 canonical location，不在多个文件重复。
- 默认不创建额外 TODO、notes、plan、progress、handoff、scratch 或 memory 文档。
- 项目历史交给 Git、commits、实验目录、configs、checkpoints、tracking service 和正式文档。
- Memory 是可被新证据推翻的 evidence，不是不可挑战的规则；失效内容应删除或明确标记 `Superseded`。
- 持久化目标是 curated current state 与 distilled knowledge，而不是 accumulated history。
