# Project State

## GitHub 分支管理（2026-11-07）
- 本方向版本分支：`idea/yara`；同仓库的其他思路使用独立分支，入口为 `main`。`main` 保留原历史基点。
- 模型与原始结果的位置由 `migration/ASSETS.json` 维护；原服务器工作区和原有产物未修改。此次仅整理并发布版本，未重新运行实验。


- 独立18D→Yara迁移环境与有限配对验证已完成；没有训练、GPU或自动push。当前无本任务容器。
- 实际加载链、模型及继承源码身份见actual_loading_chain.json、source_identity.json、ASSET_HASHES.json；所有继承文件与原工作区哈希一致。
- 共享18D观测/归一化、奖励、安全判分、因果历史；精确1秒控制/0.01秒积分。原Yara入口保留。
- 原生帆缆无法完整实现原有符号帆角。物理差异与未知项见REPORT_ZH.md、MAPPING_ZH.md；不称动力学等效迁移。
- 三个固定任务结果仅在output/summary.json及REPORT_ZH.md维护；原环境的安全违规与Yara超时均保留。
- 初始Yara奖励浮点路径差已修复；原日志不改写，精确复算另存。所有计分策略输入逐位一致，安全与结局复算通过。
- 相机为计分后的真实继续运行，不是终止瞬间。旧静态冻结标记未生效；详见output/capture_audit.json。最新水下检查仅隐藏水面视觉。
- 入口README_ZH.md；完整验证verify.sh；原始日志、异常与图片保存在output/、logs/。启动验证均不训练。

## 原4DOF模式（2026-11-08）
- 新增config_legacy4dof.json及可选config_legacy_dryden.json；Gazebo回调中积分原4DOF方程，native/signed小船入口保留。
- 方程、49步响应、10次reset、30步随机风及原三任务配对已完成，详见legacy4dof_20261108/REPORT_ZH.md。无障碍123秒、单障碍139秒到达但缓冲违规、换点147秒，对应原模型行为；不是成功率/泛化验证。
- 场景使用kinematic模型和原4DOF状态，Yara mesh仅显示代理；不宣称原船3D几何、原生6DOF受力或接触动力学等价。完整物理边界见报告及MAPPING末节。
- 旧插件同seed自重复也不逐位相同；原生数值重复性门未通过，native_control_gate.json保留false。两种控制律文本未改；不要把此项报告为通过。
- 未训练、未改策略/安全标准、未使用GPU、未push。本机应使用本轮同步源码和该报告，旧signed交付及所有旧结果保留。
