# 权重目录：来源、用途与可用边界

2026-09-28整理。服务器权重库：
`/home/ot/Students/hs/sailboat-research/research/weights_library/20260928_import/`

## 先看这个表

| 类别 | 权重库内目录 | 内容 | 如何使用 |
|---|---|---|---|
| 本次师兄提供的避障版本 | `01_obstacle_18d/user_0204_10800/` | `saclstm_s14obst_noise_0204`，编号10800；actor、q_critic、normalizer三件套及原ZIP | 新的优先核验候选；18维注意力结构严格匹配，但原环境/窗口/噪声配置未绑定 |
| 历史第五章注意力候选 | `01_obstacle_18d/chapter5_attention/yc/SAC/model/` | 1211/3600、1213/15600、1216/12600，3组三件套，共9文件 | 保留Legacy协议；不要直接套用新Aligned训练协议 |
| 另一套避障self-attention | `01_obstacle_18d/other_attention/yc/SAC/sac-lstm-selfatt/model/` | 0113系列，16组、64文件 | 18维，但与当前第五章主网络不同，不能互换 |
| 其他避障网络 | `01_obstacle_18d/other_network/yc/SAC/model/` | 1021/1800，4文件 | 18维，当前第五章主网络严格加载不匹配 |
| 无显式障碍输入的导航系列 | `02_navigation_14d/yc/` | SAC-LSTM、PPO、TD3、seed400/500、xiaolunwen，共339文件 | 14维导航接口，不作为18维第五章避障基线 |

这里“避障相关”指用户提供的用途、观测结构和相邻源码的证据，不等于已验证安全避障性能。“导航系列”指无显式障碍输入的14维接口，不证明每个旧checkpoint历史训练环境都已绑定。文件编号仅作身份标签，不自动解释成实际训练步数、训练日期或最佳模型。

## 本次附件检查

- ZIP含完整三件套，原始文件名保留；本地副本在 `research/supplements/user_obstacle_0204_10800/`。
- `torch.load(weights_only=True, map_location='cpu')`读取；Actor与双Critic严格加载到当前第五章Attention-SAC-LSTM网络通过；未重命名参数或部分加载。
- Actor输入18维、动作2维；normalizer的mean/var为18维，统计量有限、方差非负、count>0；所有权重张量有限。
- Actor eval模式、合成零输入、10步sequence前向输出形状`[1,2]`且有限。该窗口只是接口检查，不代表已确认原训练窗口。
- 与1211、1213、1216三个既有Actor逐张量比较，均不相同；不是这三组Actor的简单改名副本。
- 尚未验证：V2/V3观测语义、原环境版本、历史窗口、hidden/dropout协议、噪声参数、成功率及论文最终模型身份。`noise`文件名不能替代训练配置。
- 本轮没有运行导航/避障评估或训练，未改动既有Stage1.5 run。

## 容易混淆的地方

- `xiaolunwen/model`的600/1200/1800系列是14维、无当前注意力键的LSTM。相邻`parll_lstm_normal.py:64–65`指向`sailboat-s14-nowind`和`saclstm_s14_final_2026`；目录叫“小论文”不代表它就是第五章避障模型。
- `nowind`在本项目语境中是无显式风场观测，不能解释成仿真没有风。
- `SAC/sac-lstm`内同时有导航训练入口和避障脚本，不能仅用父目录名称判断权重。分类按权重结构及同前缀/编号的normalizer、critic、stats配套关系进行。
- `SAC/lstm_att`存有避障注意力代码，而三组匹配的历史权重实际位于父级`SAC/model`。
- 同为18维不代表V2/V3语义相同，strict加载通过不代表策略在当前环境可用。

## 来源与完整性

- `yc`的416个权重/统计文件（109个同前缀同编号组，约853MB）已复制；保留来源相对路径及原文件名，不覆盖旧副本、不移动或修改`yc`原件。
- 每个文件核对旧清单SHA256、当前源文件复制前/后SHA256及目标SHA256，全部相同。结构分类复用的是哈希完全相同文件的既有weights-only检查；不冒称本轮重新加载了全部416个文件。
- 81个相关源码旁证保存在服务器`source_evidence/`，记录源路径、哈希和环境/序列配置定位。相邻源码不是历史训练配置的充分绑定证据。
- 原始ZIP与三件套上传后另行核对哈希。源码旁证、ZIP和说明文件不计入权重文件数量。
- 逐文件来源和校验：本地 `research/validation/weights_library_20260928.json`；服务器`manifest.json`为其镜像。
- 按模型组检索：本地 `research/validation/weights_catalog_20260928.csv`；服务器`catalog.csv`为其镜像。
- 附件结构与检查结果：`research/supplements/user_obstacle_0204_10800/inspection.json`。旧候选兼容性及行为边界仍以`docs/CHAPTER5_ARTIFACT_SEARCH.md`为准。

建议下一步先向提供者核实0204对应环境源码和评估入口，再进行协议匹配的少量CPU行为验证；尚未据本次整理启动该验证或续训。
