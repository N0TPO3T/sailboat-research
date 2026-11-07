from pathlib import Path
import re

p = Path(__file__).with_name('build.py')
s = p.read_text(encoding='utf-8')
changes = {
    '从旧仿真到 Yara · 组会草稿':'Yara 与原有帆船仿真环境对比',
    '<b>SIM → YARA</b><small>帆船控制迁移 · 组会草稿 v0.1</small>':'<b>帆船仿真环境对比</b><small>Yara / 原有环境</small>',
    '进入讲解模式':'分页阅读', '退出讲解模式':'连续阅读', '讲解模式：':'分页阅读：',
    '02 / 系统层次':'02 / 仿真结构',
    '两边都用 Gym 接口，底层仿真不同':'仿真结构与运行方式',
    '03 / 物理与任务尺度':'03 / 环境参数',
    '不是换一个渲染器，而是换了一条船':'船体、动力学与任务参数',
    '04 / 输入与执行器契约':'04 / 观测与动作',
    '最大的接口差异：风信息、帆缆与电机':'观测量与执行器接口',
    '历史 14D：用运动历史间接感知风':'原有14D观测',
    'Yara 5D：直接读入视风':'Yara 5D观测',
    '05 / 奖励与已运行演示':'05 / 奖励与运行记录',
    '回报衡量的目标不同，不能直接比较高低':'奖励函数与到达条件',
    '循环方法更大，性能差异不能只归因于记忆':'网络结构与训练配置',
    '参数来源要分层':'训练记录的来源',
    '07 / 迁移路径 · 建议，未实施':'07 / 方法迁移',
    '建议先迁移方法，在Yara上从头训练':'迁移可行性与重训调整',
    '08 / 详细参数库与下一步判据':'08 / 补充参数',
    '用可复现对照判断迁移价值':'验证项目与参数明细',
    '先验证能否正确执行':'接口检查',
    '再判断是否值得研究':'评价指标',
    '明确反证':'对照设置',
    '可视化的证据边界':'Yara运行记录',
    '只是接口/展示材料':'接口运行记录',
    '草稿定位：供组会讨论环境差异与迁移决策；不是新实验报告，也不构成Yara比旧环境更准确或旧方法必然优于原版策略的结论。':'数据范围：环境参数来自固定版本源码，航迹来自已有日志。迁移方案尚未实施，暂无新模型在Yara上的训练与对照结果。',
    '“需要重训”不等于“已经授权启动训练”，也不代表重训一定改善。当前阶段完成环境与接口核查，还没有新Yara训练结果。':'当前已完成环境安装、原策略运行与接口核查。迁移训练尚未开始，训练预算需根据实际吞吐与可用资源确定。',
    '# Yara 与历史仿真 · 组会HTML草稿':'# Yara 与原有帆船仿真环境对比',
    '可进入讲解模式':'可切换分页阅读',
}
for a,b in changes.items():
    s=s.replace(a,b)
start=s.index('<section id="s1">')
end=s.index('<section id="s2">',start)
s=s[:start]+'''<section id="s1"><div class="eyebrow">01 / 环境概况</div><h1>Yara 与原有帆船仿真环境对比</h1><p class="lead">两套环境在船体尺度、动力学、观测和执行器接口上均有差异。原有循环SAC的结构与训练流程可以复用，控制策略需要在Yara中重新训练和验证。</p><p class="scope">比较范围：原有14D环境与控制器、Yara Eboat53-v0。18D障碍控制器和后续导航扩展单独注明。</p><div class="grid two" style="margin-top:26px"><figure class="imagebox"><h3>Yara：Gazebo渲染</h3><img src="@@boat@@" alt="Yara帆船近景"><figcaption>原版PPO运行截图。红色球体为目标标记；策略控制帆缆、舵和电机。</figcaption></figure><figure class="imagebox"><h3>Yara：海面俯视</h3><img src="@@ocean@@" alt="Yara海面俯视"><figcaption>同一次运行的俯视画面。截图时刻52.71s，晚于最后一条导航记录50.01s。</figcaption></figure></div><figure class="imagebox" style="margin-top:26px"><h3>原有环境：1 / 3 / 5 km航迹</h3><img src="@@legacy@@" alt="R6历史1、3、5km航迹"><figcaption>R6连续导航实验的日志绘图，使用继承的动力学模型。灰色区域为障碍，虚线为安全边界，曲线为不同方法的实际航迹。这是旧环境的导航扩展结果，与Yara原始100m到点任务不构成同任务性能比较。</figcaption></figure></section>
''' +s[end:]
# Replace a repeated overview image with factual implementation summary.
old='<figure><img src="@@ocean@@" alt="Yara海面俯视实景"><figcaption>实际海面俯视截图；用于展示环境空间，不用于证明控制精度。</figcaption></figure>'
new='<div class="card"><h3>实现范围</h3><p>原有环境在Python中完成数值积分、观测构造与奖励计算。Yara将刚体和关节更新交给Gazebo，通过ROS交换动作与观测。</p><p class="note">两套环境均使用Gymnasium接口。Yara的三维渲染与更多自由度，不直接代表所有工况下的模型精度更高。</p></div>'
s=s.replace(old,new)
s=s.replace('<div class="caution">Gym 是交互接口，不是物理引擎。3D画面与更多自由度，并不自动证明所有工况下的物理模型更准确。</div>','')
# Simple values are clearer than a logarithmic chart for four model sizes.
start=s.index('<h3>Actor参数量 · 对数条形示意</h3>')
end=s.index('</div><div class="card"><h3>训练记录的来源</h3>',start)
s=s[:start]+'''<h3>Actor参数量</h3><table class="compact"><thead><tr><th>模型</th><th>参数量</th></tr></thead><tbody><tr><td>Yara PPO</td><td>1,350</td></tr><tr><td>Yara SAC</td><td>1,446</td></tr><tr><td>原有14D循环SAC</td><td>667,396</td></tr><tr><td>原有18D注意力Actor</td><td>866,820</td></tr></tbody></table><p class="note">按实际权重统计。14D Actor约为Yara SAC的462倍；评估记忆结构时需要考虑容量差异。</p>'''+s[end:]
s=s.replace("'环境实景与结论','系统层次','物理与任务尺度'", "'环境概况','仿真结构','环境参数'")
s=s.replace("'迁移路线与困难','参数库与验证判据'", "'方法迁移','补充参数与来源'")
# Embed the stylesheet in the standalone output.
s=s.replace("for k,v in replacements.items():template=template.replace('@@'+k+'@@',v)","template=template.replace('</style>', (ROOT/'style.css').read_text(encoding='utf-8')+'</style>')\nfor k,v in replacements.items():template=template.replace('@@'+k+'@@',v)")
s=s.replace('show(0);filter();', "show(0);filter();if(/^#s[1-8]$/.test(location.hash)){current=Number(location.hash.slice(2))-1;show(current);setTimeout(()=>sections[current].scrollIntoView(),100);}")
p.write_text(s,encoding='utf-8')
