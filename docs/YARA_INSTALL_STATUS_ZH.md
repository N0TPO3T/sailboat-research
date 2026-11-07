# Yara 独立运行环境

状态（2026-11-06）：**安装及无 GUI 短步进验证通过**。全部 catkin 插件编译通过；`Eboat53-v0` 完成 8 步，仿真时钟从 4.05 s 推进到 18.06 s，末位姿约 `(14.907, 2.928, -0.094) m`。观测 float32、5 维，动作 3 维，观测/奖励/位置有限。测试进程和临时容器已退出。该结果仅证明安装接口可运行。

本轮按用户明确要求删除 `hs/pi05_runtime` 和 `hs/act-dp-playground`，合计约 55.68 GiB；删除前核对真实路径、进程与容器挂载。安装及临时文件清理后根盘约剩 57 GiB，项目目录约 2.8 GiB，另有授权 Docker 镜像存储。

服务器路径：`/home/ot/Students/hs/yara-env`。用户于本轮明确允许现有 Docker 存储写入；Docker 镜像保存在 `/var/lib/docker`，项目源码、Python 包、日志和运行数据均通过 `/work` 挂载在本目录内。未更改 Docker daemon 配置、共享 Conda 或其他项目。

## 来源与环境

- Yara 官方源：<https://github.com/medialab-fboat/Yara_OVE>，固定提交 `e708703e7367993f56ff2187a06e05b09d19e696`。使用官方源码归档，不是 Git 工作树。
- 镜像：官方 `osrf/ros:noetic-desktop-full`，本地专用标签 `hs-yara:noetic-base`；精确摘要、实际镜像标识、配置和 rootfs 校验见 `docker/IMAGE_RECEIPT.json`。
- Ubuntu 20.04、ROS Noetic、Gazebo 11.15.1、Python 3.8.10。
- CPU PyTorch 1.13.1+cpu、Gymnasium 0.29.1、Stable-Baselines3 2.3.2。所有离线 wheel 在 `docker/wheels/`。
- 这是可执行的 CPU 兼容环境，不声称逐项复现原文 Python 3.7 / CUDA 训练环境。未训练、未使用 GPU、未迁移师兄模型。
- 系统旧 Matplotlib 的 namespace 与独立 Python 包冲突，通过 `python/sitecustomize.py` 修正加载顺序；不改系统包，也不修改 Yara 算法。
- 隔离网络内显式配置 `ROS_HOSTNAME=127.0.0.1`、`ROS_MASTER_URI=http://127.0.0.1:11311`，避免容器主机名回连失败；首次失败日志保留。

## 使用

```bash
cd /home/ot/Students/hs/yara-env
# 编译（已编译后通常无需重跑）
./run-yara.sh catkin_make -j4 -l4 -DCMAKE_BUILD_TYPE=Release
# 无 GUI 安装验证：启动 Gazebo，创建 Eboat53-v0，执行短步进
./run-yara.sh bash /work/docker/smoke.sh
# 自己运行脚本，文件放在本目录下
./run-yara.sh python3 /work/your_script.py
```

容器限制为 4 CPU / 12 GiB，无 GPU，无外部网络，ROS/Gazebo 在容器内部通信。每次退出删除本任务临时容器，保留挂载目录。没有配置 GUI 转发；不能据此声称可远程显示 Gazebo。

`smoke.py` 使用未训练 SAC 的推理输出检查接口，电机动作固定为 0；不会调用 learn，不产生模型性能结论。验证结果以 `logs/SMOKE_RESULT.json` 为准；没有 PASS 文件就不能称步进通过。

## 证据

- `SOURCE_COMMIT`：源码提交。
- `docker/registry_manifest.json`、`docker/IMAGE_RECEIPT.json`：镜像来源与核验。
- `logs/versions.log`：实际软件版本。
- `logs/catkin-build.log`：编译日志。
- `logs/python-install.log`：安装原始日志，保留首次 namespace 冲突；后续修正见 sitecustomize 与导入复核。
- `logs/gazebo-smoke.log`、`logs/smoke-console.log`、`logs/SMOKE_RESULT.json`：实际仿真证据。

旧 `INSTALL_PREFLIGHT_ZH.md` 是授权前的预检历史；其中 Docker 写入禁止和 13 GiB 余量已由本轮用户授权及目录删除取代。未修改旧研究资产、权重、结果或论文。
