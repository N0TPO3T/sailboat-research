# V2 ↔ V3 Static Parity Audit

## 结论与训练门

`V3_STATIC_ENV_STATUS = CORRECTED_BUT_INTENTIONAL`

**V2/V3不是语义等价环境。** V3明确改为距离/相对方位、限制缓存输出距离、重写奖励和执行器积分，并替换风模型。上述变化有当前源码和同状态探针支持；不恢复V2行为，也不声称这些变化已经提高性能。当前范围没有发现需要撤销的V3障碍bearing符号、索引顺序或奖励正负号错误。

另发现并修复了**我们适配器的V2噪声配置BUG**：V3 SensorNoise把V2全局y坐标当弧度wrap。修复是拒绝此不兼容配置；未虚构旧噪声模型。该bug不影响此前无噪声V2 sanity，也不改变V3的26/100收据。

此状态表示语义审计门通过，后续只能按**corrected V3 + Aligned新训练**定义基线；不能继续把Legacy旧normalizer/权重直接迁移作为匹配基线。正式训练本轮仍为0步；没有启动GPU、CPA或动态障碍。历史环境hash/训练分布未绑定仍为Unknown，限制“复现/难度归因”结论，不阻塞明确声明的重实现。

## 1. 冻结协议与可恢复证据

- 根仓库main/`ce83544e8dfd6a6833da03d626025b4e0a2ba000`，工作区已有大量未提交修改；审计针对本机实际文件。参考子模块`19422525cb337831ca68f53a45661d34f3683ee1`未修改。
- 权重统一1213/15600，Actor/Q/normalizer严格加载，K5，Legacy streaming，dropout ON，`deterministic=True`取tanh(mu)，每回合重置torch RNG和hidden。没有重新估计旧normalizer，没有网络修改。
- 正式配对证据：`research/validation/v2_v3_parity_clean_20260915/`。`identity.json`保存代码/三件套hash和normalizer统计；`paired_scenarios.json`保存完整18维初态、坐标、所有种子及hash。
- 两环境均从(0,0)、psi=0、u=v=0出发，目标(500,0)，均风8m/s；前9例90°、最后无障碍对照0°。3 simple、3 medium、2 turn、2 control是事先几何设计标签，不是事后难度认证。
- 相同wind seed整数，但V2原AR与V3 Dryden过程不同，**不能称相同Dryden风轨迹**。保留原生过程，未偷偷注入共同风。首步使用的风相同，第一次wind update后不同。
- 正式配对双方关闭外部sensor/actuator noise，seed仍保存但不消费。原因是V2匹配噪声版本未知，当前角度噪声不兼容坐标；原生执行器动力学仍启用。原始探索性含噪结果保留于`v2_v3_parity_20260915/`，**不用于正式配对统计**。
- 主bank重新记录保留原V3、3%噪声、原所有seed/初态/布局、Legacy协议：`research/validation/v3_bank_parity_20260915/`。未删改困难场景。

### Paired scenarios

| 场景 | 障碍坐标(m) | V2安全/步数 | V3安全/步数 |
|---|---|---|---|
| simple_00 | [[170, 25]] | True / 165 | False / 83 |
| simple_01 | [[210, -25]] | True / 159 | True / 164 |
| simple_02 | [[270, 30]] | True / 164 | True / 154 |
| medium_03 | [[160, 35], [290, -40]] | True / 166 | False / 77 |
| medium_04 | [[190, -35], [330, 40]] | True / 169 | False / 119 |
| medium_05 | [[140, 40], [260, -45], [370, 45]] | True / 172 | False / 122 |
| turn_06 | [[110, 0], [230, 70]] | True / 173 | False / 86 |
| turn_07 | [[120, 0], [240, -70]] | True / 157 | True / 158 |
| control_08 | [] | True / 155 | True / 161 |
| control_09 | [] | True / 162 | True / 177 |

V2静态8/8，V3静态3/8；无障碍各2/2。此开发样本没有总体成功率或泛化解释；风/执行器仍是并存的干预。

## 2. Trace字段与FIRST DIVERGENCE

每个`<id>_v2/v3.jsonl.gz`一行一次动作：`step=0`表示首次控制，`boat_before/after`依次x,y,phi,psi,u,v,p,r,sail,rudder。`obstacle_before/after`含全局坐标、稳定ID（场景坐标列表索引）、距离、方位、检测/缓存/选中ID；`observation`含raw、sensor、normalized。`history`保存实际stream输入的状态/动作及索引、归一化历史状态、attention token索引、hidden前后norm。完整历史state-action pairs可按逐行stream重建；不是把训练collector deque冒充推理窗口。初始token为(s0,zero)，action index=-1。

`policy`保存mu、tanh(mu)与实际物理动作；`reward`分解progress/velocity/action/obstacle/milestone/arrival/terminal/fixed/total，逐步对实际环境总奖励校验。`termination`分开arrival/timeout/range/endpoint/segment violation/truncated。未采样另一随机动作；这里deterministic action是实际执行命令。

自动比较数值阈值atol=rtol=1e-6，按通道保存最早不同变量，轨迹长度不同只比较共同前缀：`paired_results.json`、`trace_checks.json`。ID按离散值比较。控制步内没有记录每个RK stage，因此下面“最早”指trace可观测边界，不冒称已测出第一条机器指令。

**全部10对的首次输入、hidden和动作完全相同；第一次动作执行后的boat_after[0]即不同。** 原生V2导数函数每次RK stage写入帆/舵全局状态，V3每控制步确定限速增量后按积分时间插值；首步差异早于wind update，也早于大部分障碍首次探测。它解释了为什么不能将轨迹首次差异归于bearing。

例如simple_00：step0动作执行后`boat_after[0]`（x，m）V2=0.027499676、V3=0.046292394；step1 `policy.actor_mean[0]` V2=-0.186940461、V3=-0.171531945；step2历史输入不同。详细数值在paired_results。障碍通道另外独立检索如下：

| 场景 | 首次障碍槽差异：step / 变量 / V2 → V3 |
|---|---|
| simple_00 | 26 / raw_obstacle_slots[0] / 170.00000 → 0.00000 |
| simple_01 | 64 / raw_obstacle_slots[0] / 210.00000 → 0.00000 |
| simple_02 | 70 / raw_obstacle_slots[0] / 270.00000 → 146.87665 |
| medium_03 | 24 / raw_obstacle_slots[0] / 160.00000 → 0.00000 |
| medium_04 | 54 / raw_obstacle_slots[0] / 190.00000 → 0.00000 |
| medium_05 | 0 / raw_obstacle_slots[0] / 140.00000 → 145.52061 |
| turn_06 | 0 / raw_obstacle_slots[0] / 110.00000 → 109.95378 |
| turn_07 | 0 / raw_obstacle_slots[0] / 120.00000 → 119.95378 |
| control_08 | 未出现 |
| control_09 | 未出现 |

若一侧先探测到、另一侧未探测到，不能把该时刻的零槽差异单独归因于表示转换；必须看同状态探针。

### 排除动力学混杂的同状态探针

船(0,0), psi=0，同一已缓存障碍(90,30)：两者检测ID/真实距离相同；V2槽(90,30)，V3槽(94.8683298,0.32175055rad=18.43495°)。归一化前两槽分别(-0.172831,0.312931)与(-0.136312,-0.078890)。没有bearing sign翻转：V2根本没有输出bearing。

相同初始历史、hidden=0、torch seed=111，仅当前障碍槽按两种语义编码，实际动作分别：

- V2: `[-0.7767762541770935, -0.7168201804161072]`
- V3: `[-0.774857223033905, -0.7022698521614075]`

这证明表示改变能改变旧策略输出，**没有证明它单独造成74次失败**。证据`controlled_policy_reward.json`；同文件运行原reward函数，对39/40/50/75/100/150/151m分解并校验。

## 3. A–Q语义审计与分类

下表V2/V3均指`sailboat_RL/gymnasium/envs/sailboat/sailboat_s14_obst_V2/V3.py`。相同项标“无差异”，不强行分到bug类别。INTENTIONAL_CORRECTION指显式设计变更/修正，**不等于实验证明更优**。

| 项 | 核查结论 | 分类、证据与处理 |
|---|---|---|
| A bearing | V2槽为世界x/y；V3 atan2(dy,dx)-psi，wrap[-pi,pi]，正为数学逆时针左侧 | INTENTIONAL_CORRECTION；V2:217–248、V3:231–293明确注释改变格式；保留V3 |
| B global/body | V3水平相对角等价于atan2(-sinψ·dx+cosψ·dy,cosψ·dx+sinψ·dy)，不另做横摇修正；检测函数两版相同 | 无符号差异；90°旋转同状态探针返回0；与4DOF速度变换含cos(phi)分开 |
| C units | x/y及distance用m，V3 bearing用rad；两版FOV角用rad；动作±π/18 | 格式变化非度弧误换；V2世界y绝不能wrap成角 |
| D scaling | V3原始d未除150，之后统一Zscore；V2世界坐标也未缩放 | 无隐藏距离缩放bug |
| E padding | 不足2槽均(0,0)，没有mask；V2(0,0)真障碍与padding冲突，V3 d=0也按空槽影响reward | 共同已知边界；当前bank无起点障碍。新动态设计不在本轮 |
| F 最近两排序 | 缓存按当前欧氏距离稳定升序；相同距离保留缓存插入顺序 | 无差异；sort_tie探针 |
| G slot switching | 距离排序会交换ID，槽不固定绑定目标；V3还会因150m过滤入/出槽 | INTENTIONAL_CORRECTION；逐步ID trace；当前历史模型应承受此定义，未改网络 |
| H cache | 都按世界坐标<1m去重、持续缓存、不因FOV消失清除；V2无限距离仍选，V3只选<=150m | INTENTIONAL_CORRECTION；cached_behind两者保留，cached_outside_range仅V3空槽；不是动态跟踪 |
| I FOV | 总120°，半角60°，边界<=；±59.999°内、60.001°外 | 无差异；docstring90°过时，实际常量2π/3 |
| J range | 初次检测<=150m，两版一样；V3选槽再次过滤<=150 | 初检无差异，cache过滤为显式变更；150/150.001边界探针 |
| K normalization | 完全相同旧统计、epsilon1e-6、无clip；但V2世界坐标统计用于V3距离角导致语义迁移 | EVALUATION_CHANGE；identity保存完整mean/var；严加载不能消除统计语义不匹配 |
| L index order | 0:14相同；14,15,16,17位置不变，**含义**从x1,y1,x2,y2变d1,b1,d2,b2 | INTENTIONAL_CORRECTION；非无意slot permutation |
| M 40m终止 | 两版原生都是动作末对全局全部障碍严格<40，非<=；arrival<=10，range>=750,time>=1000 | 无原生差异；V2:747–763、V3:647–659；arrival和truncated可同时为真，safe success要排除违反 |
| N continuous | 两个原生版本均无连续检查。research适配器额外计算接受节点间线段最小距离；Legacy只评分，Aligned还终止并设dt cap=.05 | EVALUATION_CHANGE；chapter5_static.StaticEnvironment.step；不是“原V3新增”。线性扫掠近似不是精确连续安全 |
| O reward | V2两坐标重算距离，用50–100m反距离平方、乘总scale；V3用d槽指数惩罚独立于scale；动作系数.2→.5 | INTENTIONAL_CORRECTION；V2:800–876、V3:775–855。均负惩罚，未发现正负号bug |
| P generation | V2 reset实际随机5–8，生成器x∈[120,380],y∈[-250,250],间距120、最多600尝试可少生成；V3 reset固定7点，同一随机生成器未启用 | EVALUATION_CHANGE；V2:947–1007，V3:932–990；论文140m不能当源码120m |
| Q bank难度 | 当前bank静态50固定+50随机，随机x[0,500]、间距140；多风向8m/s，与旧V2默认随机风向5m/s/u∈[0,1]不同 | EVALUATION_CHANGE；实际历史train/test分布及“明显更难”的因果份额UNKNOWN；下节量化代理 |
| 执行器 | V2在RK导数求值时累加帆舵；V3每步限速后时间插值，避免依赖求值次数 | INTENTIONAL_CORRECTION；V2:276–308,V3:316–329及导数。未回退数值副作用 |
| wind | V2速度/方向AR，V3沿风/横风两个滤波状态后转回速度角，均1Hz | INTENTIONAL_CORRECTION；V2:768–778,V3:681–746；相同seed不等于相同扰动，谱标定未核验 |
| 噪声adapter | V2全局y被当前SensorNoise当angle并wrap | BUG（已加拒绝保护）；chapter5_static构造函数与新回归测试；V3协议未改，匹配V2噪声模型UNKNOWN |

### 奖励公式（可执行代码）

令scale=.2+.02·I小帆动作+.02·I小舵动作，P=2Δdistance+Δx+.5u/(1+|v|)。

- V2：scale·[P−Σ100000(1/max(d,50)−1/100)²·I(d<=100)−.2Σfloor(|a|/1°)·I(|a|>1°)]。
- V3：scale·[P−.5Σfloor(|a|/1°)·I(|a|>1°)]−Σexp(−(d−40)/20)·I(0<d<150)。
- 两版再加里程碑3/5/12、到达40、truncated−100、每步−.2。V2零坐标padding排除；V3零距离padding排除。
- V3注释“系数3/第二个减半”与执行的1/同权不符；保留执行值。论文印刷正指数项不作为反转代码负号依据。

## 4. 当前100静态bank难度

全100条重新记录与旧收据逐场景steps/safe_success/violation/minimum separation一致（100/100）；安全成功26/100，违规74/100，其中动作末也违规74/100。因此本bank的74次失败**不能归因于仅段内检查新增惩罚**；原生末端也发现它们。

| 指标 | 结果 |
|---|---|
| 障碍数量分布 | {7: 63, 6: 12, 5: 10, 8: 15} |
| 最近障碍到nominal直线段(0,0)→(500,0)距离m | {'min': 0.35548554441783287, 'median': 10.0, 'mean': 27.995733077614982, 'max': 102.6130729501547} |
| 40m圆与nominal线相交场景 | 75/100 |
| 存在两40m安全圆重叠 | 0/100 |
| 保守栅格未找到连通路径 | 0/100 |
| 障碍密度（个/km²，按500×500m矩形） | {'min': 20.0, 'median': 28.0, 'mean': 27.32, 'max': 32.0} |
| 第一次实际探测的最近距离m | {'min': 108.4224973094308, 'median': 148.50854741393005, 'mean': 142.7869865579401, 'max': 149.99602227363496} |
| 从未探测到障碍 | 0/100 |
| nearest-two有序ID列表变化次数/episode | {'min': 1.0, 'median': 4.0, 'mean': 4.66, 'max': 12.0} |
| 风向场景数（度） | {0.0: 26, 90.0: 26, 135.0: 24, 180.0: 24} |

“第一次感知”是实际轨迹受FOV约束后的检测，不是理论圆边界穿越；记录从首次动作后开始，与环境首次探测调用相同。slot变化包括入/出槽和顺序交换，首次列表初始化不计；不能直接当身份跟踪错误。

近似不可通行代理：在x[0,500]、y[-250,250]矩形上用5m四邻接网格，障碍半径40+半格对角线保守膨胀，检查起终点连通。全部找到几何路径；这不证明帆船在风向、转弯半径、有限FOV及1000步内可通过。nominal路线也不是逆风可行最优航迹。

为比较代码分布，额外调用当前V2生成器100次（seed260915+i，非历史实验）：障碍数{5: 35, 7: 23, 8: 18, 6: 24}，最近路线距离{'min': 0.07867335593675762, 'median': 25.769261026905085, 'mean': 27.695644362950556, 'max': 82.7205109521546}，路线40m相交78/100。主bank并没有在这些简单几何指标上表现为整体明显更难；固定50布局将近线距离集中到10m，随机布局的140m间距反而比V2生成器120m更稀。不能根据这些几何统计量断言两者闭环难度相等。

## 5. 对26% static success的证据解释

**Verified：** 当前V3 + 旧权重/旧normalizer是跨观测语义、动力学和风模型的迁移评估；旧模型在本轮V2配对中能安全完成全部8个静态诊断例。仅表示转换就能在相同历史/种子下改变动作。V3 26/100可精确复得；不是旧模型永久无效的证据，也不是原论文95.3%的复现失败率。

**Hypothesis：** 坐标语义/normalizer失配是迁移损失的重要来源，执行器与风改变也可能贡献。没有完成逐因素闭环因果分解，不能把74次失败分配给某一因素。奖励函数不同不会在冻结策略推理时直接改变动作（actor不读reward）；它影响后续训练目标，不能当本轮即时动作差异的直接原因。

**Unknown：** 原checkpoint实际训练噪声、风场、最终环境hash及论文原测试bank；当前bank相对它的难度增幅及失败归因比例无法定量。无需为提高分数删除困难场景；本轮一条未删。

**Durable lesson：** 18维/strict loading/K匹配不足以建立environment compatibility；必须绑定障碍槽语义及normalizer单位。V2噪声保护已修复，不把保护误说为获得历史噪声复现。

## 6. 验证、限制与接续

- 10对完整轨迹、100条主bank轨迹均完成；所有奖励分解与实际总奖励误差<2e-4（配对最大约6.4e-6）。全部trace有限值检查通过；无障碍无穷最小间距序列化为null。
- 原9项静态回归通过（17.984s）；新V2噪声拒绝回归通过（0.913s）。测试内部短更新仅验证恢复/隔离，不是Aligned正式训练。
- 主bank、Actor/Critic、旧normalizer、参考子模块均未修改。只在自有适配器添加不兼容配置检查及相关测试；其余新代码为审计与日志。
- 没有进行外部独立审查；以上是本机源码、探针和CPU闭环证据，不声称跨模型验收。
- 保留V3当前定义重新训练Aligned是合理接续；仍需运行前GPU/真实路径检查、单seed分阶段预算及原静态行为门。**本轮不执行训练。** 远端部署仍是旧快照，本次修改/审计未同步、未提交、未推送。

### 复核命令

使用新的输出目录，避免覆盖；以下只执行CPU评估：

```sh
.venv/bin/python -B research/v2_v3_static_parity.py --output research/validation/NEW_PAIRED_AUDIT
.venv/bin/python -B research/v2_v3_static_parity.py --bank-only --output research/validation/NEW_BANK_AUDIT
```

`summarize_static_parity.py`为本次固定目录的衍生检查脚本；已有输出拒绝覆盖。原始含噪探索trace只保留为bug证据。审计结论入口为本文件；统计细表为`v3_bank_parity_20260915/difficulty_summary.json`。
