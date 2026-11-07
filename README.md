# Sailboat 项目分支入口

项目按独立思路保存在同一私有仓库的不同分支。各分支有独立根目录与上下文，不能直接混合研究结论。main 保留原历史；此次没有合并到 main，也没有重新训练或评估。

| 分支 | 内容 |
| --- | --- |
| [`codex/static-baseline`](https://github.com/N0TPO3T/sailboat-research/tree/codex/static-baseline) | 继承静态基线与诊断 |
| [`codex/idea-a-routing`](https://github.com/N0TPO3T/sailboat-research/tree/codex/idea-a-routing) | A 线导航路由；含服务器科学提交与本机资料 |
| [`codex/idea-dual-policy`](https://github.com/N0TPO3T/sailboat-research/tree/codex/idea-dual-policy) | 双策略动态避障原型及四轮交付 |
| [`codex/idea-b-recovery`](https://github.com/N0TPO3T/sailboat-research/tree/codex/idea-b-recovery) | B 线区域观测与低速迎风恢复 |
| [`codex/yara-migration18`](https://github.com/N0TPO3T/sailboat-research/tree/codex/yara-migration18) | 18D→Yara 迁移与平台支持材料 |
| [`codex/idea-discovery-worktree`](https://github.com/N0TPO3T/sailboat-research/tree/codex/idea-discovery-worktree) | 探索 worktree 的未提交交接修改 |

每个方向用独立克隆或 Git worktree。运行仍遵守各项目服务器边界，避免两台设备同时改写同一个服务器现场。服务器现有分支和未提交工作未被本次整理改写。

## 取回项目

```bash
git clone --branch codex/idea-a-routing https://github.com/N0TPO3T/sailboat-research.git sailboat-routing-v0
```

模型、训练状态、原始轨迹和结果由各分支 `migration/ASSETS.json` 索引。新增归档：[project-assets-20261107](https://github.com/N0TPO3T/sailboat-research/releases/tag/project-assets-20261107)。继承静态资产复用 [consolidated-20261001](https://github.com/N0TPO3T/sailboat-research/releases/tag/consolidated-20261001)。新 Release 的各 tar.gz 单独解压到对应项目根目录，不串接；旧 Release 按原 parts 清单重组。

A 线本机旧源码与服务器新版不同的 12 个文件保存在 `migration/windows-overlay/`，清单见 SOURCE.json。默认科学源码来自服务器已提交版本。Yara 用服务器最新已提交版本。B/双策略为本机完整交付快照，没有虚构之前不存在的 Git 历史。

## 恢复边界

虚拟环境、依赖缓存、Docker 镜像层、下载半成品、设备凭据和浏览器临时 profile 不进入仓库或本次 Release。环境安装脚本与规格仍保留。来源备份的重复本机展开副本不另行上传，原始静态归档仍在已有 Release。需要 Mac 恢复旧 Codex 聊天时使用用户另行转移的私有 Codex 包，不上传会话或登录信息到 GitHub。

此次只验证版本迁移与文件存储，不改变任何方法是否有效、论文是否可投稿的结论。开始下一项研究前阅读选定分支的 AGENTS、PROJECT_STATE 和 CURRENT_PLAN，并核查实际代码/结果。
