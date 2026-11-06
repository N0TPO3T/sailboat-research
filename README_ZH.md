# 独立18D迁移运行包

运行端：/home/ot/Students/hs/yara-env/migration18。依赖已安装的父目录Yara容器镜像与原项目.venv，不安装系统包，不使用GPU。原版Yara的run-yara.sh及原任务保持不变。

启动（真实Gazebo、4个控制步）：
    cd /home/ot/Students/hs/yara-env/migration18 && ./run.sh --stage smoke

完整验证（固定清单，先归档已有output再重跑；不训练）：
    cd /home/ot/Students/hs/yara-env/migration18 && ./verify.sh

程序接口：
    from environment import MigrationEnv, Transport, ObstacleController
    transport = Transport()
    env = MigrationEnv("yara", transport)
    policy = ObstacleController(mode="eval")
    obs, info = env.reset()
    policy.reset(obs)
    obs, reward, terminated, truncated, info = env.step(policy.act(obs).action)
    policy.close()
    env.close()
    transport.close()

切换原物理：MigrationEnv("original")，策略加载器相同。完整循环例见validate.py。每次env.reset后必须policy.reset；连续改目标调用env.set_goal(goal, policy)，该接口用真实历史重编码并保持物理连续。

动作空间是归一化[-1,1]^2，非Yara绝对角。18D原信息边界、归一化及加载路径不变。此包默认采用Yara原生帆缆执行；它不等价于可主动控制正负帆侧的原执行器。报告及MAPPING_ZH.md明确列出差异。

文件：
- REPORT_ZH.md / index.html：结论与图集。
- config.json：固定初态、任务清单、风及时间/安全门。
- environment.py / step.cc / bridge.py：共享语义、同步Gazebo步进、ROS桥接。
- frozen/：按哈希复制的实际低层源码与模型；不修改继承原件。
- output/：逐步真实日志、核验、相机图、响应图、配对航迹及奖励复算。
- source_identity.json / actual_loading_chain.json / ASSET_HASHES.json：源身份。
- PHYSICS_PARAMETERS.json / NORMALIZATION.md：参数和18D归一化统计。

计分日志与终止后的实际继续运行取图分开。旧冻结标记未生效，当前相机跟随实际船体；看水下结构时仅隐藏水面视觉。黄色航迹标记来自日志实际位置；不是构造轨迹。首次Yara计分日志中的reward存在微小进展浮点路径偏差，原件保留，reward_recomputed_*.json是原源码精确复算；audit.json验证所有策略输入逐位相同、安全结果一致。当前代码已修复。

所有完整验证固定最多3个任务×2后端、每任务900秒仿真上限，另加有限响应检查。异常不启动训练、不更换场景。用户决定后续执行器协议、微调或重训。
