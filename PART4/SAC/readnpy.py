import numpy as np
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import rcParams

# ── 全局样式：Nature 风格 ──────────────────────────────────────
rcParams.update({
    'font.family':        'serif',
    'font.serif':         ['Times New Roman', 'DejaVu Serif'],
    'font.sans-serif':    ['SimSun', 'Arial', 'Helvetica'],
    'mathtext.fontset':   'stix',
    'font.size':          8,
    'axes.labelsize':     9,
    'axes.titlesize':     10,
    'xtick.labelsize':    8,
    'ytick.labelsize':    8,
    'axes.linewidth':     0.6,
    'xtick.major.width':  0.6,
    'ytick.major.width':  0.6,
    'xtick.major.size':   3,
    'ytick.major.size':   3,
    'axes.unicode_minus': False,
    'figure.dpi':         300,
    'savefig.dpi':        300,
    'savefig.bbox':       'tight',
    'savefig.pad_inches': 0.05,
})

# ── 加载数据 ───────────────────────────────────────────────────
_dir = os.path.dirname(os.path.abspath(__file__))
data = np.load(os.path.join(_dir, 'sensitivity_saclstm_s14nowind_final_9000.npy'),
               allow_pickle=True).item()

weighted   = data['weighted_sensitivity']
weighted_n = weighted / (weighted.max() + 1e-10)   # 归一化到 [0,1]

# 状态变量 LaTeX 标签
STATE_LABELS = [
    r'$x$', r'$y$', r'$\phi$', r'$\psi$',
    r'$u$', r'$v$', r'$p$', r'$r$',
    r'$\delta_s$', r'$\delta_r$',
    r'$\Delta L$', r'$\Delta l$',
    r'$x_f$', r'$y_f$',
]

# ── 按加权敏感度降序排列 ──────────────────────────────────────
order   = np.argsort(weighted_n)[::-1]
vals    = weighted_n[order]
labels  = [STATE_LABELS[i] for i in order]

# ── Nature 配色（取自 Nature Methods 调色板） ─────────────────
# 主色：深蓝灰，高亮前3名用渐变强调色
n = len(vals)
base_color    = '#4C72B0'          # 柔和钴蓝
highlight_rgb = [
    '#C44E52',                     # 砖红（Top‑1）
    '#DD8452',                     # 橙（Top‑2）
    '#CCB974',                     # 金（Top‑3）
]
colors = []
for i in range(n):
    if i < 3:
        colors.append(highlight_rgb[i])
    else:
        # 蓝灰色逐渐变淡
        alpha = 0.90 - 0.04 * (i - 3)
        colors.append(base_color + format(int(max(alpha, 0.35) * 255), '02x'))

# ── 绘图 ──────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(5.5, 3.2))        # 单栏宽度 ~89 mm

bars = ax.barh(np.arange(n)[::-1], vals, height=0.65,
               color=colors, edgecolor='white', linewidth=0.3)

# 数值标注
for i, (v, bar) in enumerate(zip(vals, bars)):
    ax.text(v + 0.015, bar.get_y() + bar.get_height() / 2,
            f'{v:.2f}', va='center', ha='left', fontsize=7,
            color='#333333')

# 坐标轴
ax.set_yticks(np.arange(n)[::-1])
ax.set_yticklabels(labels, fontsize=9)
ax.set_ylabel(r'观测空间状态变量', fontsize=9, fontfamily='SimSun')
ax.set_xlim(0, 1.18)
ax.set_xlabel(r'标准化加权敏感度',
              fontsize=9, fontfamily='SimSun')

# 简洁边框：仅保留左和下
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# 浅色参考线
ax.xaxis.grid(True, linestyle='--', linewidth=0.3, alpha=0.5)
ax.set_axisbelow(True)

plt.tight_layout()

save_path = os.path.join(_dir, 'weighted_sensitivity_nature.png')
fig.savefig(save_path)
fig.savefig(save_path.replace('.png', '.pdf'))      # 同时输出矢量版
plt.close()
print(f'图表已保存: {save_path}')
print(f'PDF 版本:   {save_path.replace(".png", ".pdf")}')