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

## 独立有符号执行器（2026-11-07）
config_signed.json启用signed，帆舵规定角度均限速10°/s；native默认入口保留。真实伺服力矩未建模，船体参数未改。报告与新对照：signed_20261107/REPORT_ZH.md。响应./run-signed.sh response，通过后./run-signed.sh policy。固定结果目录signed_20261107，重复运行前先保留该目录。本轮完整结果与图形已生成，不需要为查看报告重跑。原ARTIFACT_INDEX.json仍对应首次交付版本。

## 原4DOF方程迁移（2026-11-08）

服务器连接：`ssh zhoushan`，工作目录`/home/ot/Students/hs/yara-env/migration18`。本机为交付/查看副本。最新模式对应表见MAPPING_ZH.md末节，结果见legacy4dof_20261108/REPORT_ZH.md。

- native：config.json，Yara原船体/帆缆。
- signed：config_signed.json，Yara原船体/理想有符号执行器。
- legacy4dof：config_legacy4dof.json，在Gazebo时钟内积分原4DOF方程；船体mesh是视觉代理，不启用原生接触动力学。
- 原Dryden风：config_legacy_dryden.json，复用原风场与步边界更新，不增加策略输入。

在已有已安装平台上，以新的输出名运行（旧目录存在时拒绝覆盖）：

```bash
cd /home/ot/Students/hs/yara-env/migration18
MIGRATION18_RUN=legacy4dof_demo_$(date +%Y%m%d_%H%M%S) ./run-legacy.sh capture
MIGRATION18_RUN=legacy4dof_verify_$(date +%Y%m%d_%H%M%S) ./run-legacy.sh verify
```

第一条运行60步实际策略演示并截图；第二条为有界CPU核验，包含原4DOF方程、响应、跨模式reset、短随机风、原三任务配对及图像。使用既有依赖与冻结权重，不训练。需要原有frozen模型和已安装Docker镜像；新源码包不是全新Yara安装包。

原生插件的独立数值对照使用新输出名执行`./run-legacy.sh control`；已有检查未通过逐位一致门，同seed旧插件自身也不逐位复现，详见本轮报告。该限制不计为通过，也不与原4DOF模式核验混合。
