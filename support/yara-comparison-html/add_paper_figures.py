from pathlib import Path
import re
R=Path(__file__).resolve().parent
p=R/'paper_page.html';s=p.read_text(encoding='utf-8')
insert='''<div style="margin-top:26px"><h3>原文图27：七航点任务的实际航迹</h3><figure class="imagebox" style="max-width:720px;margin:0 auto"><img src="@@paper27@@" alt="Yara原文图27，PPO、SAC和PID七航点航迹"><figcaption>蓝色PPO、橙色SAC、红色PID；黑点为航点，箭头为风向。</figcaption></figure></div><div style="margin-top:26px"><h3>原文图28：航速与控制指令</h3><figure class="imagebox"><img src="@@paper28@@" alt="Yara原文图28，船速、舵角、帆杆角和推进器指令"><figcaption>(a)纵向船速；(b)舵角；(c)帆杆角；(d)电动推进器指令。图中结束时间：PID 368s，PPO 412s，SAC 562s。</figcaption></figure></div>'''
assert '@@paper27@@' not in s
s=s.replace('<h3 style="margin-top:26px">七航点任务的结果</h3>',insert+'<h3 style="margin-top:26px">结果概括</h3>')
s=s.replace('来源：Vasconcellos等，2025，§5.2，图27–28。','图27–28转载自Vasconcellos等，2025，第16–17页；保留原图。© The Author(s)，<a href="https://creativecommons.org/licenses/by-nc-nd/4.0/">CC BY-NC-ND 4.0</a>。')
s=s.replace('查看原文</a>','查看原文</a> · <a href="sources/Yara_2025.pdf#page=16">离线PDF</a>')
p.write_text(s,encoding='utf-8')
p=R/'environment_content.html';alltext=p.read_text(encoding='utf-8');alltext=re.sub(r'<section id="s2">.*?</section>',lambda m:s,alltext,count=1,flags=re.S);p.write_text(alltext,encoding='utf-8')
p=R/'build_environment.py';s=p.read_text(encoding='utf-8').replace("'demo':A/'demo_trajectory.png'","'demo':A/'demo_trajectory.png','paper27':R/'yara_paper_fig27.png','paper28':R/'yara_paper_fig28.png'")
p.write_text(s,encoding='utf-8')
