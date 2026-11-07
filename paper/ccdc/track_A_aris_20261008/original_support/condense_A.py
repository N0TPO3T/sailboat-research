from pathlib import Path
import re,difflib
P=Path(__file__).resolve().parent;s=(P/'manuscript.md').read_text(encoding='utf8');moved=[]
def para(start,new,save=True):
 global s
 b=s.split('\n\n');hits=[i for i,x in enumerate(b) if x.startswith(start)];assert len(hits)==1,start
 if save:moved.append(b[hits[0]])
 b[hits[0]]=new;s='\n\n'.join(b)
para('The midpoint s̄ uses', 'The midpoint uses endpoint averages with shortest-angle heading interpolation and observed sail/rudder angles. D=diag(1,1,5,5) scales residuals empirically. A bounded local least-squares solver fits w∈[−16,16]² m/s, with multiple initializations on the first fit and causal warm starts thereafter. Insufficient history retains the preceding estimate. Supplement S14 gives solver settings; this local fit does not establish wind identifiability.')
para('Within each task, physical policy', 'Within each task, physical policy, normalizer, dynamics, initial conditions, map, external wind parameters, target motion, execution timing and evaluation are shared. Different paths may encounter different local wind. Reactive relay R uses nominal feedback without future candidate rollout. Detailed prediction S15 uses P=15 s. Historical long-hold search and nominal-prediction hold comparators are defined separately in Supplement S14.')
para('Existing detailed-prediction logs provide', 'Prediction logs are compared only with the actually executed prefix before replanning or termination. Six development snapshots also execute two fixed protocols each, for up to 60 s, after exact physical-prefix and selected-first-15-s reproduction. Real offline branches alone query the actual external evolution; predictors use causal inputs.')
para('For two decisive meter-scale incursions', 'Observation-only integrator-substep replays check selected meter-scale incursions and safe pairs without changing commands or endpoints. They supplement the one-second metric. Experiments use an AMD EPYC 7V12 host, at most four single-thread CPU workers and no GPU.')
para('An additional same-command check', 'Same-command accepted-substep replays preserve all one-second endpoints. The unique confirmation case remains R/L/S15 unsafe/unsafe/safe, with margins −0.162/−1.117/42.094 m. Two historical reactive incursions also retain negative margins, while their S15 pairs remain positive. Maximum accepted step is 0.1 s. This numerical circular-proxy evidence addresses a possible one-second chord artifact; it is not exact hull safety. Full values are in Supplement S4/S11/S14.')
para('Nine measurements of the estimation', 'At three fixed states with three repetitions per predictor, the median estimation/rollout/selection wall time is 17.009 s for detailed prediction and 0.067 s for L. This excludes loading and initial setup; nominal early return can produce different candidate counts. The episode CPU totals in Table I measure different work and are not planning deadlines. A detailed call can exceed P=15 s while physical time remains paused. Delayed-execution tests use a different protocol and remain separate boundary evidence (Supplement S6/S14).')
(P/'manuscript.md').write_text(s,encoding='utf8')
f=P/'SUPPLEMENT.md';sup=f.read_text(encoding='utf8')+'\n\n## S14. Detailed settings and diagnostic records\n\n'+'\n\n'.join(moved)+'\n';f.write_text(sup,encoding='utf8')
old=(P.parent/'r13_revision/manuscript.md').read_text(encoding='utf8');(P/'REVISION.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='R13',tofile='A')),encoding='utf8')
print(len(s.split()))
