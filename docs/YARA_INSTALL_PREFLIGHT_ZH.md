# Yara服务器安装预检（2026-11-05）

> 历史预检，已被2026-11-06安装结果取代：见 YARA_INSTALL_STATUS_ZH.md。用户已允许Docker写入并删除指定旧目录；以下保留当时事实，不代表当前阻塞状态。

状态：BLOCKED；仅创建本目录和预检记录，尚未安装或启动Yara。

目标：ot@172.16.2.249，真实目录/home/ot/Students/hs/yara-env。
官方要求：ROS Noetic、Gazebo11、catkin及独立Python环境。Noetic的目标Ubuntu为20.04，Python3.8；Yara esailor.yml固定Python3.7/PyTorch1.13.1/CUDA11.7并含未固定版本的RL依赖，不能直接保证现代求解成功。

实际检查：
- Ubuntu24.04.3；roscore/gazebo/gzserver均不在PATH，/opt/ros无安装。
- 根盘1.8T，剩余约13G，df显示100%；hs就在此盘。内存251Gi，可用约232Gi。不能把GPU空闲或docker组资格当扩大权限授权。
- Docker可读，数据根/var/lib/docker，现有镜像没有ROS/Noetic环境；拉镜像或建容器会写出hs范围，故未执行。
- 无podman/apptainer/proot命令；有bwrap/unshare。unshare -Ur true实际失败：写/proc/self/uid_map不允许。因此未假定rootless容器可用。
- 未运行sudo、apt、docker pull/run/build、环境安装或训练；未修改系统、共享Conda、shell启动文件或旧研究资产。

结论：不是服务器算力不足，也不是证明Yara不能运行；当前官方原生安装与宿主版本不匹配，现有容器路径超出项目写入边界，用户命名空间路径未通过准入。没有把只下载源码算安装完成。

推荐恢复条件：提供已配置的Ubuntu20.04/ROS Noetic/Gazebo11隔离环境，或由管理员准备数据、缓存和日志全部落在hs内的可用容器执行方式，同时给该环境留出独立磁盘余量。再进行源码固定、catkin编译、无界面场景加载和ROS观测/动作冒烟测试。13G不是已测安装需求，不能声称必然装不下，但不宜未经容量核算占满共享根盘。

其他路线（例如PRoot用户态根文件系统或Ubuntu24.04全源码移植）未验证；不声称不可行，也未把本次安装任务扩展为平台移植工程。

来源：
https://github.com/medialab-fboat/Yara_OVE
https://raw.githubusercontent.com/medialab-fboat/Yara_OVE/main/README.md
https://raw.githubusercontent.com/medialab-fboat/Yara_OVE/main/esailor.yml
https://raw.githubusercontent.com/ros-infrastructure/rep/master/rep-0003.rst

注意：README旧示例含eboat命名路径，实际当前目录为yara；其中重定向写.bashrc的示例不应执行。setup.py会遍历home甚至根目录寻找环境，后续应使用显式路径适配，不照抄运行。
