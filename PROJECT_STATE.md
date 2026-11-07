# Project State

- 独立18D→Yara迁移环境与有限配对验证已完成；没有训练、GPU或自动push。当前无本任务容器。
- 实际加载链、模型及继承源码身份见actual_loading_chain.json、source_identity.json、ASSET_HASHES.json；所有继承文件与原工作区哈希一致。
- 共享18D观测/归一化、奖励、安全判分、因果历史；精确1秒控制/0.01秒积分。原Yara入口保留。
- 原生帆缆无法完整实现原有符号帆角。物理差异与未知项见REPORT_ZH.md、MAPPING_ZH.md；不称动力学等效迁移。
- 三个固定任务结果仅在output/summary.json及REPORT_ZH.md维护；原环境的安全违规与Yara超时均保留。
- 初始Yara奖励浮点路径差已修复；原日志不改写，精确复算另存。所有计分策略输入逐位一致，安全与结局复算通过。
- 相机为计分后的真实继续运行，不是终止瞬间。旧静态冻结标记未生效；详见output/capture_audit.json。最新水下检查仅隐藏水面视觉。
- 入口README_ZH.md；完整验证verify.sh；原始日志、异常与图片保存在output/、logs/。启动验证均不训练。
