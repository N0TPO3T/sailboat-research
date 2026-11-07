"""Bounded caption/access edits for the 2026-10-13 visual edition."""
from pathlib import Path
import re
P=Path(__file__).resolve().parent
src=P.parent/'track_A_closeout_20261009'
s=(src/'manuscript.md').read_text(encoding='utf8')
captions={
1:'Nominal-first prediction and actual execution. A valid, integration-successful nominal rollout meeting the guard returns without predicting alternatives. Memory replay and command accumulation restore distinct states; predicted histories stay isolated. The old action executes first, a changed reference applies at t+1, and its first possible effect is t+1 to t+2. Only executed feedback updates real history.',
2:'All 24 matched tasks. (a) Time differences use 19 common-safe pairs per predictor; missing points are failed pairs, not zero cost. (b) Every actual dynamic margin; the symmetric-log axis is linear for |margin|≤3 m. (c) Circles: safe completion; crosses: failure. Indices 1–8: pressure; 9–12: crossing; 13–16: overtaking; 17–20: endpoint; 21–24: non-conflict.',
3:'Unique new-confirmation L incursion: complete R/L/S15 and target tracks. Run durations are 392/566/519 s. Circles/square mark synchronized positions at 260 s; the dotted circle is the target’s 85 m exclusion boundary. Plus/cross marks identify minimum-margin endpoints. The gray disk is the static entity; its dashed ring adds 60 m. The lower panel shows the encounter interval.',
4:'Adverse endpoint task: S15 takes 587 s versus 279 s for safe R and L, adding 308 s. R and L coincide. Complete actual tracks and synchronized target motion are shown. Circles/square mark 200 s; the dotted circle is the exclusion boundary then. The lower panel reports synchronized clearance throughout each run.',
5:'Guard sensitivity on twelve prespecified development tasks; original 30 m results are reused. (a) Time differences use ten common-safe pairs. (b) Worst actual margin uses all twelve tasks. Larger guard need not improve both outcomes.',
6:'Predictions versus actual fixed-protocol execution, grouped by six source snapshots. Circle/triangle denote two protocols; filled/open markers denote S15/L. N: nominal; C: continuation; signed angles: side protocols. Margin residual is predicted minus actual. Common intervals are ten 60 s and two 58 s. Duplicate nominal/continuation at snapshot 4 is one source state, not independent evidence.'}
for n,caption in captions.items():
 s,count=re.subn(r'!\[Fig\. '+str(n)+r'\..*?\]\((figures/.*?)\)',lambda m:'![Fig. '+str(n)+'. '+caption+']('+m[1]+')',s,flags=re.S)
 assert count==1
(P/'manuscript.md').write_text(s,encoding='utf8')
s=(src/'SUPPLEMENT.md').read_text(encoding='utf8')
s=s.replace('The supplied lightweight closeout package contains the full manuscript, this supplement, editable Word source, build/figure scripts, publication figures and the unchanged lightweight evidence directory.',
'The supplied lightweight closeout package contains the full manuscript, this supplement in Markdown/Word/PDF, editable Word sources, build/figure scripts, publication figures and the unchanged lightweight evidence directory. The visual edition also supplies plot_data.json: extracted plotting columns for Figures 2–6, including all displayed trajectory samples. These columns permit figure regeneration but do not constitute complete simulator recovery or additional experiments.')
(P/'SUPPLEMENT.md').write_text(s,encoding='utf8')
