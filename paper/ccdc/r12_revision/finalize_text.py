"""Build evidence-bearing text after all prescribed tasks are complete."""
from pathlib import Path
import json
P=Path(__file__).resolve().parent
S=json.loads((P/'evidence/analysis.json').read_text())
C=S['confirmation'];G=S['guard'];D=S['detailed_vs_simple']
assert all(C[v]['tasks']==24 for v in ['reactive','sampled','simple'])
assert all(G['guard'+str(g)]['tasks']==12 for g in [0,15,30,60])
def f(x):return f'{x:.2f}'
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])
hist=table(['Evidence group','n','R','S15','S60','NH'],[
 ['R8 short','30','28','30','30','—'],['R8 long','4','3','4','4','—'],['R10 seen*','13','11','13','13','9'],['R10 new','12','12','12','12','11']])
new=table(['Method','Safe /24','Gain/loss vs R','Δt median/max (s)'],[[v,C[k]['safe'],str(C[k]['rescues'])+'/'+str(C[k]['losses']),f(C[k]['common_safe_time_delta_vs_R']['median'])+'/'+f(C[k]['common_safe_time_delta_vs_R']['max'])] for k,v in [('reactive','R'),('sampled','S15'),('simple','L')]])
guard=table(['ρ (m)','Safe /12','Worst dynamic (m)','Δt median/max (s)'],[[g,G['guard'+str(g)]['safe'],f(G['guard'+str(g)]['min_dynamic_margin']),f(G['guard'+str(g)]['common_safe_time_delta_vs_R']['median'])+'/'+f(G['guard'+str(g)]['common_safe_time_delta_vs_R']['max'])] for g in [0,15,30,60]])
results=f'''### A. Historical gains and intervention costs

Table I preserves the original evidence groups. The 13 seen mechanism instances overlap R8 and cannot be added to it. R8 S15 rescues two short and one long reactive failures. R10 new confirmation has no additional safe completions over R; ten of its twelve R/S15 trajectories are identical. Its mean common-safe S15−R time is +27.08 s, with an endpoint case at 584 versus 313 s (+271 s). Holding without comparing alternatives is not a sufficient substitute: NH succeeds on 9/13 seen and 11/12 new tasks. S60 remains competitive; on the twelve new tasks S15 is 9.25 s faster on average than S60 but uses 777.05 versus 328.77 s total episode CPU. These historical comparisons do not determine the new predictor comparison.

Table I. Historical safe completions, reported separately. *Overlaps R8; no pooled total.

{hist}

### B. Newly frozen matched comparison

Table II and Fig. 2 report all 24 new tasks. Gains/losses are paired changes in safe completion against R, not percentage-point differences. Common-safe time statistics condition on both methods succeeding: S15 has n={C['sampled']['common_safe_time_delta_vs_R']['n']} and L has n={C['simple']['common_safe_time_delta_vs_R']['n']}. Against L, S15 gains {D['rescues']} safe completions and loses {D['losses']}; their {D['common_safe_time_delta']['n']} common-safe pairs have S15−L median {f(D['common_safe_time_delta']['median'])} s and maximum {f(D['common_safe_time_delta']['max'])} s. No scenes are removed for failure or low activation. The per-task CSV also reports path length, exit reason and margins.

Table II. New R12 confirmation. Δt compares common-safe pairs with R.

{new}

![Fig. 2. All 24 frozen tasks. Time differences use common-safe pairs; crosses at zero mark excluded failed pairs, not zero time cost. The lower panel includes every actual dynamic margin. Indices 1–8 are pressure crossings; 9–12 ordinary crossings; 13–16 overtaking; 17–20 endpoint; 21–24 non-conflict.](figures/figure2_confirmation.png)

@NEW_INTERPRETATION@

### C. Guard sensitivity

Table III shows all four guards on the same twelve old tasks; 30 m reuses exact original results after parity verification. Reactive succeeds on {G['reactive']['safe']}/12. The guard changes complete closed-loop decisions, not the true exclusion boundary. Non-nominal selection totals for 0/15/30/60 m are {', '.join(str(G['guard'+str(g)]['non_nominal_selections']) for g in [0,15,30,60])}; no-guard-feasible fallback totals are {', '.join(str(G['guard'+str(g)]['fallbacks']) for g in [0,15,30,60])}. Figure 3 shows the navigation-cost tail and actual worst dynamic margin as well as completion. The experiment does not identify an optimal guard or a monotone safety guarantee. The original 30 m configuration retains its identity.

Table III. Guard sensitivity; common-safe Δt is relative to R. True safety is unchanged.

{guard}

![Fig. 3. Guard sensitivity on twelve prespecified development tasks. Original 30 m results are reused. Common-safe time differences and worst actual margin are different outcomes; larger guard need not improve both.](figures/figure3_guard.png)

### D. Prediction agreement, numerical safety and cost

From 46 distinct historical source tasks, 1083 selected-protocol windows yield 1048 complete 15 s prefixes and 35 truncated prefixes. These are clustered windows, not 1083 independent tasks. Maximum position errors for entering, ordinary feedback, reevaluation and release are 1.039, 30.506, 2.090 and 0.626 m. No compared prefix has a predicted positive margin followed by a nonpositive actual margin; nor does a predicted 30 m guard become an actual guard shortfall on these short prefixes. This limited observation does not validate unexecuted candidates or later replanned tails.

All twelve fixed real branches from six snapshots reproduce their full physical prefixes and the selected first 15 s exactly. Detailed predictions and real branches share the full 60 s in all twelve. Three-way comparisons with L share 60 s in ten branches and 58 s in two because L predicts arrival earlier while the real branch continues. The median branch-maximum position error on those common intervals is 1.104 m for detailed prediction and 53.818 m for L. Three L nominal predictions meet 30 m while actual margins are 17.868, 23.384 and 16.430 m. These are guard shortfalls, not buffer incursions. Conversely, detailed prediction reaches 106.064 m position error at one endpoint snapshot; its nominal and continuation paths coincide and are not independent failures. Its predicted/actual minimum margins remain 140.990/146.171 m. Figure 4 makes both the local accuracy advantage and the adverse error explicit.

![Fig. 4. Predictions versus actual fixed-protocol execution. Each point/branch represents an executed protocol; twelve branches come from six snapshots. Ten common intervals are 60 s and two are 58 s. Duplicate protocols at one endpoint snapshot are retained but not counted as independent scenes.](figures/figure4_prediction.png)

At the historical pressure snapshot t=149 s, detailed nominal predicts 17.706 m and rejects the 30 m guard; the selected −90-degree side protocol predicts 94.815 m. Fixed execution gives 17.868/95.098 m for the two protocols. The low-order predictor instead accepts nominal at 75.748 m in this same state. This isolates a decision-relevant prediction difference without attributing an entire later voyage to a single branch. Figure 5 shows the complete historical encounter and the largest new common-safe S15 time-cost case.

![Fig. 5. Actual own-vessel and target trajectories: a prespecified historical rescue and the largest new common-safe S15 time increase relative to R. Circle/square markers identify a common time; dotted circles show the 85 m exclusion distance at that time. Crosses mark failed termination.](figures/figure5_encounters.png)

Accepted-integrator-substep checks preserve every one-second endpoint exactly. The two historical reactive incursions remain −1.225 and −0.872 m. Their S15 minimum margins change from 43.589/38.455 m under one-second segments to 43.597/38.425 m under accepted-substep segments (maximum substep 0.1 s). Thus these particular gain labels do not arise solely from a one-second chord sign error. This is still a numerical circular-proxy check, not swept-hull or formal continuous safety.

Nine measurements of the estimation/rollout/selection core per model at three fixed states give detailed median/p95/maximum wall times 17.009/17.662/17.685 s, compared with 0.067/0.136/0.136 s for L. The states include two risk decisions and ordinary feedback, each repeated three times. The timer excludes initial nominal/candidate setup and model loading. Nominal early return can evaluate different candidate counts, so this is not an equal-work per-candidate speed ratio. Complete new-confirmation episode CPU totals are {f(C['reactive']['cpu_total'])}, {f(C['sampled']['cpu_total'])} and {f(C['simple']['cpu_total'])} s for R, S15 and L. These measures include different work and are not interchangeable. Detailed calls can exceed the 15 s review period; physical time remains paused here. Separate R9 delayed-execution failures are boundary evidence, not pooled main-method outcomes.
'''
refs=(P/'input/manuscript_revised.md').read_text(encoding='utf8').split('## References')[1].strip()
s=(P/'manuscript_base.md').read_text(encoding='utf8').replace('@RESULTS@',results).replace('@REFERENCES@',refs)
# Author supplies interpretation only after inspecting all paired outcomes.
for key,name in [('@ABSTRACT@','abstract.txt'),('@NEW_INTERPRETATION@','interpretation.txt'),('@CONCLUSION@','conclusion.txt')]:
 s=s.replace(key,(P/name).read_text(encoding='utf8').strip())
assert '@' not in s
(P/'manuscript.md').write_text(s,encoding='utf8')
print('Final evidence-bearing manuscript assembled')
