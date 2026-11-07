# 恢复说明

两个既有原始包按字节复制，未重写代码或检查点：

- R13_REPRODUCTION_internal.zip：183个哈希索引成员，含实际源代码、Actor、normalizer、冻结配置、72条主轨迹及verify_recovery.py。
- R12_raw_results.tar.gz：R12补证完整归档及必要历史输入；与其既有索引一起查阅。

将内部包解压到一个新目录，使用已有兼容环境运行`python verify_recovery.py`。该命令校验/加载/汇总，不重新运行全部仿真。不要把现有已完成runs目录用作新实验输出。原包内的历史“内部使用/未公开”描述保留；最新来源与获准研究/评审提供范围见../09_sources/SOURCE_FOLLOWUP.md。

此资料包服务于当前用户的项目阅读、修改与复现；没有自动公开发布，也没有给继承代码或权重添加许可证。完整冻结身份见包内CONTENTS_SHA256.json。本次不安装新环境，不启动训练或实验。
