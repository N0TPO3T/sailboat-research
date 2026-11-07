from pathlib import Path
import re
R=Path(__file__).resolve().parent
p=R/'environment_content.html';s=p.read_text(encoding='utf-8')
sources=re.search(r'<details><summary>来源与版本</summary>.*?</details>',s,re.S).group(0)
s=s[:s.index('<section id="s5">')]
s=s.replace('03 / 还原程度','03 / 迁移内容与困难').replace('<h2>环境迁移内容</h2>','<h2>18D环境迁移的主要工作与难点</h2><p>任务设置和障碍场景可以按原定义重建。主要困难集中在船体动力学、帆舵动作含义，以及ROS通信下的控制时序。</p>')
start=s.index('<h3>迁移路线</h3>');end=s.index('<section id="s4">')
s=s[:start]+'''<h3>工作量主要集中在哪里</h3><div class="tablewrap"><table><thead><tr><th>部分</th><th>难点</th><th>处理方式</th></tr></thead><tbody><tr><td>地图、目标与评价</td><td>接入工作相对明确，主要是配置和坐标转换。</td><td>复用原障碍坐标、起终点、时限与安全判据。</td></tr><tr><td>船体动力学</td><td>工作量最大。原有大型船体与Yara现成小型船的质量、惯量、受力和机动响应差异大。</td><td>建立原尺度模型，核对惯量、浮力、阻尼和帆舵受力；检查直航、转向和速度响应。</td></tr><tr><td>帆舵动作</td><td>旧控制器输出角度增量，Yara现成接口使用帆缆范围和绝对舵角。</td><td>增加动作适配，统一角度、限幅、变化速率与实际反馈。</td></tr><tr><td>18D观测与时序</td><td>需要同步船体、障碍和历史动作，并保持原1s控制周期。</td><td>按同一仿真时间构造18D观测，核对复位、历史更新与命令生效顺序。</td></tr></tbody></table></div></section>
'''+s[end:]
s=s.replace('<p class="scope">只为复现任务和增加可视化，不必立即更换动力学或重训。要验证控制方法在另一套船体模型中是否有效，则需要独立迁移评估。</p>','')
s+='''<section id="s5"><div class="eyebrow">05 / 迁移顺序与权重测试</div><h2>先迁移任务与场景，再测试现有权重</h2><p>先把原有18D避障任务在Yara中运行起来，完成场景、船体和控制接口接入，再加载现有模型进行测试。</p><div class="steps"><div class="step"><h3>迁移任务设置与仿真场景</h3><p>重建船体、障碍布局、风场和起终点；沿用对应版本的到达、碰撞、安全缓冲与超时规则。</p></div><div class="step"><h3>对齐18D观测与帆舵接口</h3><p>统一观测顺序、坐标、单位、动作含义和控制周期，接入配套normalizer及历史管理。</p></div><div class="step"><h3>加载现有权重测试</h3><p>先保持权重不变，观察航迹、避障完成情况、碰撞、超时与航时；根据测试结果决定后续调整。</p></div></div>'''+sources+'</section>\n'
p.write_text(s,encoding='utf-8')
p=R/'build_environment.py';s=p.read_text(encoding='utf-8')
s=s.replace("labels=['Yara平台','原有18D环境','迁移还原程度','收益与代价','旧权重适用性','当前证据与来源']","labels=['Yara平台','原有18D环境','迁移内容与困难','收益与代价','迁移顺序与测试']")
s=s.replace('/^#s[1-6]$/','/^#s[1-5]$/').replace("toggle();show(5);let ok=ss[5].classList.contains('current');","toggle();show(ss.length-1);let ok=ss[ss.length-1].classList.contains('current');")
s=s.replace("print('Built six sections; replotted three 18D tracks.');print(json.dumps(summary,ensure_ascii=False))","print('Built', len(labels), 'sections.')")
p.write_text(s,encoding='utf-8')
