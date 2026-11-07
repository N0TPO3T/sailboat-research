# 文献与适配证据

| 来源 | 实际访问等级 | 本轮使用 | 没有复现/不能转移 |
|---|---|---|---|
| Viel, Vautier, Wan, Jaulin, Position keeping control of an autonomous sailboat, IFAC PapersOnLine51(29),14–19,2018,10.1016/j.ifacol.2018.09.462 | 6页全文；方法、阶段、仿真及p17图像核对。https://webperso.ensta.fr/jaulin/paper_position_keeping.pdf | 接近/绕行/驻留；正向去推力与倒航恢复推进；可航角处理 | 300kg模型、原加速度自适应控制、原文空间条件与稳定性结果没有原样转移到25.9t4DOF。 |
| Morge, Pelle, Wan, Jaulin, Experimental Studies of Autonomous Sailing With a Radio Controlled Sailboat, IEEE Access10,2022,10.1109/ACCESS.2022.3232462 | 8页全文及Table2/3图像。https://publications.aston.ac.uk/id/eprint/44523/1/Experimental_Studies_of_Autonomous_Sailing_With_a_Radio_Controlled_Sailboat.pdf | 传统航向/帆角与阶段引导的成熟来源 | 1m实船短时结果不横比；Table3区间排版歧义不直接照搬。 |
| Kai Liu,Jiancheng Yu,Wentao Zhao,Zhaoyang Sun, Position-Keeping Method for Unmanned Sailboats Based on NMPC Maximum Speed and Heading Control, JMSE13,668,2025,10.3390/jmse13040668 | 26页全文；Section3中心/圆/方形策略与NMPC构造。https://mdpi-res.com/d_attachment/jmse/jmse-13-00668/article_deploy/jmse-13-00668.pdf | 保持运动/避免失速的动机；直接指向中心的強简单引导 | 本轮没有实现其NMPC，不能称复现完整方法或推断优于其论文结果。 |
| K.J.A.Bink,B.Düz,G.D.Weymouth, Autonomous sailing with sim-to-real reinforcement learning, EAAI182,115804,2026,10.1016/j.engappai.2026.115804 | 16页机构全文；训练400k步、传统SRCS对照、水池结果与恢复。https://repository.tudelft.nl/file/File_31b73099-04ae-4da9-a746-2ec2e2179636 | 候选2的强基线和样本成本依据 | 没有移植或训练该RL；其最佳RL12/12与SRCS15/16不能视为显著普遍胜出。 |
| Phase-based station-keeping strategy for unmanned sailboats: Disturbance estimation and navigation mode switching, Ocean Engineering2026,10.1016/j.oceaneng.2026.126031 | 仅出版商摘要/入口，未取得全文 | 提醒驻留已有阶段估计/模式工作 | 未复现公式；不声称其方法失败、具体作者或本文算法首次。 |

本轮横风双点接力是成熟路线接力思想的简单几何实例，并非声称上述任一论文逐式提出完全相同的两个点参数。所用0.5R/0.2R和共同PD参数是当前实现选择，不能伪称文献最优值。可航角来自传统帆船控制结构，50°是本轮共同配置。

继承动力学来源引用Yang等AOR2026（10.1016/j.apor.2026.105246）相关研究资产；用户已确认使用与评审提供许可。本轮未加载14D或18D检查点、未训练，不能称RL方案。旧源代码版权和第三方说明保持，不新增开源许可证。来源快照与每批runner哈希保存在INITIAL_SNAPSHOT和结果目录。
