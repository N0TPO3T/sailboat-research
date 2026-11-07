from pathlib import Path
import re
R=Path(__file__).resolve().parent
p=R/'paper_page.html';old=p.read_text(encoding='utf-8')
assert '@@paper23@@' not in old
inner=old[old.index('<h2>'):old.rindex('</section>')]
page='''<section id="s2"><div class="eyebrow">02 / 论文中的纯风力实验</div><h2>仅靠风力推进的换舷测试</h2><p>关闭电动推进器，让E-Boat从静止起航；在不同风速下，于约40s时尝试迎风换舷。</p><figure class="imagebox"><img src="@@paper23@@" alt="Yara论文图23：四种风速下纯风力换舷的航迹和纵向速度"><figcaption>原文图23。(a)本船航迹；(b)纵向速度。图例为真实风速：2.57、3.60、4.63、6.17m/s。</figcaption></figure><div class="grid two" style="margin-top:24px"><div class="card"><h3>航迹变化</h3><p>6.17m/s风速下，红色航迹完成转向并继续航行；较低风速下，船在转向过程中逐渐失速。</p></div><div class="card"><h3>速度变化</h3><p>换舷时各组船速均明显下降。红色曲线在换舷前约2.3m/s，之后恢复；其余曲线降至接近零。</p></div></div><p class="note">本组实验展示纯风力下的机动响应。论文还提供禁用推进器的Eboat62-v0纯帆训练环境。</p><p class="note">图23转载自Vasconcellos等，2025，第13页，实验说明见§5.1。© The Author(s)，<a href="https://creativecommons.org/licenses/by-nc-nd/4.0/">CC BY-NC-ND 4.0</a>。<a href="sources/Yara_2025.pdf#page=13">离线原文</a> · <a href="https://link.springer.com/content/pdf/10.1007/s10846-024-02212-1.pdf#page=13">在线原文</a></p><details><summary>补充：允许电机辅助的PPO / SAC / PID七航点实验</summary>'''+inner+'</details></section>\n'
p.write_text(page,encoding='utf-8')
p=R/'environment_content.html';s=p.read_text(encoding='utf-8');s=re.sub(r'<section id="s2">.*?</section>',lambda m:page,s,count=1,flags=re.S);p.write_text(s,encoding='utf-8')
p=R/'build_environment.py';s=p.read_text(encoding='utf-8').replace("'论文方法与结果'","'论文纯风力实验'").replace("'paper27':R/'yara_paper_fig27.png'","'paper23':R/'yara_paper_fig23.png','paper27':R/'yara_paper_fig27.png'");p.write_text(s,encoding='utf-8')
