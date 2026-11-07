from pathlib import Path
import json, base64, html, re, shutil, hashlib, zipfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

R=Path(__file__).resolve().parent
P=R.parent/'sailboat-routing-v0'; A=R.parent/'yara-transfer-audit/output'
S=R/'sources'; S.mkdir(exist_ok=True)
plt.rcParams.update({'font.sans-serif':['Microsoft YaHei'],'axes.unicode_minus':False,'font.size':10})
obs=[(190,10),(90,-90),(300,-76),(330,57),(197,150),(160,-220),(350,-205)]
fig,ax=plt.subplots(figsize=(7,3.94))
for x,y in obs:ax.add_patch(Circle((x,y),40,fc='#ccd4d9',ec='#7a8b97',lw=.8))
ax.scatter([0],[0],c='#356983',s=30,label='起点');ax.scatter([500],[0],marker='*',s=100,c='#c79032',label='终点')
ax.set(xlim=(-60,550),ylim=(-280,220),xlabel='x / m',ylabel='y / m');ax.set_aspect('equal');ax.grid(alpha=.15);ax.legend(loc='upper right',fontsize=8);fig.tight_layout();fig.savefig(R/'source18_scene.png',dpi=180);plt.close(fig)
ids=['s8371_005_channel_slow_1000','s8371_021_channel_fast_3000','s8371_034_staggered_fast_5000']
names=['1 km：通道 / 慢变风','3 km：通道 / 快变风','5 km：交错障碍 / 快变风']
fig,axes=plt.subplots(1,3,figsize=(15,4.8)); summary=[]
for ax,id,name in zip(axes,ids,names):
 f=P/'runs/r6_reset_20261004T115808Z/figure_data'/f'{id}__obstacle18_boundary120.json'; d=json.loads(f.read_text());shutil.copy2(f,S/f.name)
 for ob in d['obstacles']:
  xy=ob['center_xy'];rad=ob['entity_radius'];ax.add_patch(Circle(xy,rad,fc='#ccd4d9',ec='#8c979f',lw=.6));ax.add_patch(Circle(xy,rad+ob['safety_buffer'],fill=False,ec='#8c979f',ls='--',lw=.8))
 pts=d['points']; ax.plot([p['x'] for p in pts],[p['y'] for p in pts],color='#286d96',lw=1.7)
 ax.scatter([pts[0]['x']],[pts[0]['y']],s=22,c='#286d96');ax.scatter(*d['scene']['goal'],marker='*',s=90,c='#b08229',zorder=5)
 ax.set_title(name);ax.set_xlabel('x / m');ax.set_ylabel('y / m');ax.set_aspect('equal',adjustable='datalim');ax.autoscale_view();ax.grid(alpha=.15)
 row=d['row'];summary.append({'scene_id':id,'time_s':row['time_s'],'path_length_m':row['path_length_m'],'min_safety_clearance_m':row['min_safety_clearance_m'],'obstacles':len(d['obstacles']),'source_sha256':d['source_sha256'],'safe_arrival':row['success']})
fig.tight_layout();fig.savefig(R/'tracks_18d.png',dpi=180);plt.close(fig)
(S/'track_summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
def tab(headers,rows):
 return '<div class="tablewrap"><table><thead><tr>'+''.join('<th>'+html.escape(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>'
physics=[('接口/引擎','Gymnasium＋Python自有动力学','Gymnasium＋ROS Noetic＋Gazebo 11 / ODE'),('自由度','水平位置、横滚、偏航及对应速度：4DOF','刚体6DOF及帆、舵、推进器关节'),('船体质量','25,900 kg','160.3357 kg；各link声明质量之和，不含附加质量'),('帆面积','170 m²','3.18776 m²'),('舵面积','1.17 m²','0.10064 m²'),('龙骨面积','8.7 m²','0.23779 m²'),('水 / 空气密度','1025 / 1.2 kg/m³','997 / 1.201 kg/m³'),('船体几何','未在本次核验中确定统一船长','动力学插件长2.4m；碰撞盒2.7×1×0.63m'),('物理更新','Dormand–Prince数值积分；初始dt=0.05s','物理步长0.01s'),('控制/观测周期','每个动作推进1s','约2s；受ROS交付与取观测时序影响'),('加速方式','CPU数值计算','当前实时更新率100；训练helper可解除上限'),('源任务初始状态','原点出发，航向随机[−π,π]，u=0','重置到模型初态，当前reset未随机航向'),('源任务风','当前reset基准8m/s、0°；叠加Dryden形式扰动','5…12kn离散风速，24个方向；每回合发布恒定风向量'),('风扰动参数','Lu=300m、Lv=150m；σu=1.2、σv=1.0','当前任务未配置同类Dryden风扰动'),('显示','二维场景与日志航迹图','三维海面、船体与关节渲染')]
tasks=[('任务长度','源任务500m；长程扩展1/3/5km','当前Eboat53为100m到点'),('障碍表示','源任务：坐标点＋40m碰撞距离；扩展：圆形实体＋60m安全缓冲','Eboat53无障碍；需要新接入避障任务'),('障碍布局','当前源reset固定7个坐标；扩展由场景清单生成','当前Eboat53未配置障碍场'),('可用地图','源任务按视场发现；长程扩展已知完整静态地图','当前5D策略没有障碍或地图输入'),('探测范围','源任务150m、120°视场；保留发现记录','Eboat53无对应探测；Eboat103的激光另行核验'),('到达阈值','源任务及R6扩展为10m','3D目标距离<5.1m'),('碰撞 / 安全判定','源任务距任一障碍中心<40m触发截断；R6分别统计实体碰撞和60m缓冲侵入','Eboat53未提供匹配的避障任务判分'),('越界','源任务距原点≥750m；长程扩展用独立任务配置','距目标>120m或NaN终止'),('时限','源任务1000s；R6的1/3/5km为1800/5400/9000s','step_count>300在递增前判断，第302次step触发截断'),('结果口径','安全完成要求到达且没有安全缓冲侵入（R6）','现有记录仅为无障碍到达，不能称避障成功')]
interfaces=[('策略观测','18维：位置/目标4，姿态2，运动4，帆舵2，进展2，障碍4','5维：目标距离、相对目标角、纵向速度、视风速、视风角'),('障碍输入','最近两障碍的距离和相对船首方位；不足时补零','当前5D策略没有障碍输入'),('风信息','无直接风观测','直接使用视风速、视风角'),('动作','2维：帆角、舵角调节量','3维：帆缆张开范围、舵角、电机档位'),('帆动作','每步约±10°增量，目标角限于±90°','绝对帆缆范围0…90°；不等于实际有符号帆角'),('舵动作','每步约±10°增量，目标限于±30°','绝对舵目标±60°'),('执行器速率','帆、舵10°/s','帆默认0.5rad/s、舵0.4rad/s，并受关节约束'),('电机','无','int(5a)，−5…5档'),('归一化','18D配套normalizer','距离、角度、速度分别按固定尺度映射')]
transfer=[('可以复用','18D障碍观测的组织思路、控制代码与训练流程；已有场景用于参考。'),('需要重建','Yara中的障碍实体、观测接口、碰撞与安全余量判定、终止条件及场景生成。'),('需要调整','按小型船尺寸设置目标距离和障碍间距；核对帆缆/舵动作、控制周期、坐标和单位，重新计算归一化。不能照搬旧船40m/60m判据作为既定答案。'),('是否重训','建议在Yara中重新训练18D避障控制器。输入维数即使相同，船体响应与动作语义也不同，旧权重表现不能直接沿用。'),('公平比较','在相同Yara地图、风、障碍信息、推进方式和判分下比较；若研究纯帆航行，所有方法均禁用电机。'),('需要的结果','避障到达率、实体碰撞、缓冲侵入、超时、航时与操纵量。方法结果单独报告，不把当前无障碍演示当成避障基准。')]
content=(R/'environment_content.html').read_text(encoding='utf-8')
values={'PHYSICS':tab(['维度','原有18D源环境','Yara当前配置'],physics),'TASKS':tab(['维度','原有18D与长程扩展','Yara当前配置'],tasks),'INTERFACES':tab(['维度','原有18D控制器','Yara Eboat53'],interfaces),'TRANSFER':tab(['事项','内容'],transfer),'TRACKTABLE':tab(['起终点距离 / 场景','障碍数','实际航程','航时','最小安全余量','结果'],[(names[i],r['obstacles'],f"{r['path_length_m']:.1f} m",f"{r['time_s']:.0f} s",f"{r['min_safety_clearance_m']:.2f} m",'安全到达') for i,r in enumerate(summary)])}
for key,path in {'boat':A/'boat_close.png','map':R/'source18_scene.png','tracks':R/'tracks_18d.png','demo':A/'demo_trajectory.png','paper23':R/'yara_paper_fig23.png','paper27':R/'yara_paper_fig27.png','paper28':R/'yara_paper_fig28.png'}.items():values[key]='data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode()
for k,v in values.items():content=content.replace('@@'+k+'@@',v)
assert '@@' not in content
labels=['Yara平台','论文纯风力实验','原有18D环境','迁移内容与困难','收益与代价','迁移顺序与测试']
# Keep the checked document styling, without previous method content.
base=R/'base.css'
if not base.exists():
 old=(R/'index.html').read_text(encoding='utf-8');base.write_text(re.search('<style>(.*?)</style>',old,re.S)[1],encoding='utf-8')
css=base.read_text(encoding='utf-8')+'\n.tablewrap{margin-bottom:26px}.scope{line-height:1.9}section{min-height:0}'
nav=''.join(f'<a href="#s{i+1}">{i+1:02d}　{x}</a>' for i,x in enumerate(labels))
js='''const ss=[...document.querySelectorAll('section')],aa=[...document.querySelectorAll('nav a')];let i=0;function show(n){i=Math.max(0,Math.min(ss.length-1,n));ss.forEach((s,j)=>s.classList.toggle('current',i===j));aa.forEach((a,j)=>a.classList.toggle('active',i===j));document.querySelector('#page').textContent=(i+1)+' / '+ss.length;if(document.body.classList.contains('presentation'))scrollTo(0,0)}function toggle(){document.body.classList.toggle('presentation');show(i)}document.querySelector('#present').onclick=toggle;document.querySelector('#prev').onclick=()=>show(i-1);document.querySelector('#next').onclick=()=>show(i+1);aa.forEach((a,j)=>a.onclick=()=>show(j));document.addEventListener('keydown',e=>{if(document.body.classList.contains('presentation')){if(e.key==='ArrowRight')show(i+1);if(e.key==='ArrowLeft')show(i-1);if(e.key==='Escape')toggle()}});const d=document.querySelector('dialog');document.querySelectorAll('figure img').forEach(im=>im.onclick=()=>{d.querySelector('img').src=im.src;d.showModal()});document.querySelector('#closezoom').onclick=()=>d.close();show(0);if(/^#s[1-6]$/.test(location.hash)){show(Number(location.hash.slice(2))-1);setTimeout(()=>ss[i].scrollIntoView(),150)}if(location.search.includes('selftest')){toggle();show(ss.length-1);let ok=ss[ss.length-1].classList.contains('current');toggle();show(0);document.body.dataset.selftest=ok?'passed':'failed'}'''
doc=f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>18D避障环境向Yara迁移</title><style>{css}</style><body><nav><b>18D避障环境迁移</b><small>Yara平台与适用性分析</small><div class="links">{nav}</div><button id="present">切换分页阅读</button><p class="foot">2026-11-06<br>图片点击放大</p></nav><main>{content}</main><div class="deckcontrols"><button id="prev">←</button><span id="page"></span><button id="next">→</button></div><dialog><button id="closezoom">关闭</button><img alt="放大图"></dialog><script>{js}</script></body></html>'
(R/'index.html').write_text(doc,encoding='utf-8')
for name in ['R6_RESEARCH_REPORT.md','R6_METHOD_NOTE.md']:shutil.copy2(P/'docs'/name,S/name)
f=P/'third_party/obstacle_candidate/sailboat_s14_obst_V3.py'
(S/'ENVIRONMENT_18D_SCOPE.md').write_text('# 18D环境核验\n\n当前源文件：'+str(f)+'\nSHA256: '+hashlib.sha256(f.read_bytes()).hexdigest()+'\n\n当前reset固定7障碍、风8m/s和0°、初始u=0；Dryden Lu=300、Lv=150。原网页14D的随机风、u随机和Lv=300不能沿用。源码定义观测18维；150m探测范围、120°视场、40m中心距离碰撞阈值。\n\nR6长程扩展另用完整静态地图、圆形实体及60m缓冲，并通过Relay120接力；图中的三场仅保留obstacle18_boundary120实际轨迹。原图选例偏向相对旧对照的效率收益，不能当随机代表。轨迹汇总和源JSON同目录。没有新仿真。\n',encoding='utf-8')
(R/'README.md').write_text('# 18D避障环境向Yara迁移\n\n打开index.html。图片内嵌，离线可用。\n\n'+ '\n'.join(f'{i+1}. {x}' for i,x in enumerate(labels))+'\n\n重新构建：python build_environment.py。environment_content.html为正文，base.css为内嵌样式来源。重画仅使用旧日志，不运行仿真。\n',encoding='utf-8')
print('Built', len(labels), 'sections.')
