from pathlib import Path
import re,json
P=Path(__file__).resolve().parent
s=(P/'manuscript.md').read_text(encoding='utf8')
s=s.replace('c_t=\\|r_0+\\alpha^*d\\|-85\\,\\mathrm{m}', 'c_{j,t}=\\|r_0+\\alpha^*d\\|-D_j')
s=s.replace('The static calculation fixes q at the obstacle center.', 'Here D_j=85 m for a dynamic target; for a static obstacle D_j is its entity radius plus 60 m, and q is its fixed center. The actual task minimum m_real is the minimum of c_{j,t} over all true obstacles and all executed intervals, including failed tasks.')
s=s.replace('Let V contain valid integration-successful candidates,', 'For a candidate protocol γ, let K_γ be its number of completed one-second predicted intervals and O_t the union of the full static map and targets valid in the current observed list. Define\n\n$$\n\\hat m(\\gamma)=\\min_{j\\in\\mathcal O_t}\\min_{0\\le k<K_\\gamma}\\hat c_{j,k}(\\gamma).\n$$\n\nEach ĉ uses the synchronized segment expression with the same obstacle-specific D_j. H=60 s bounds the rollout; K_γ≤60 ends at predicted arrival or failure, so K_γ seconds is its effective horizon. A valid early arrival includes the arrival interval; it does not certify later occupancy. Empty obstacle sets give +∞ for a nonempty rollout. A zero-step rollout uses the implementation sentinel −10⁹ m and does not pass the guard. Failed route or integration predictions are excluded regardless of recorded margin. P=15 s is the hold/review period; ρ=30 m is an extra predicted margin above the unchanged true exclusion boundary. Let V contain valid integration-successful candidates,')
s=s.replace('Here Δt=1 s, eₖ=', 'Here r and r̄ are actual modeled and desired course rates (rad/s), χ is course in radians, κ has units s⁻¹, and τ is a response time in seconds. Δt=1 s, eₖ=')
a=s.index('### A. Historical gains and intervention costs');b=s.index('### C. Guard sensitivity',a)
old=s[a:s.index('### B. Newly frozen matched comparison',a)]
(P/'historical_results.md').write_text(old,encoding='utf8')
new='''### A. Matched 24-task comparison

Table I is the primary comparison: all 24 prespecified R12 confirmation tasks, with no outcome filtering. At the time of R12 evaluation, these were new and all methods were frozen; this revision reuses their outcomes and does not relabel post-hoc analyses as new confirmation. Gains/losses denote paired changes in safe completion. Time differences condition on both methods succeeding and are not an overall efficiency measure that assigns an artificial time to failures.

Table I. Matched 24-task results. Δt is relative to R on common-safe pairs; CPU is cumulative episode CPU, not navigation time.

| Metric | R | L | S15 |
| --- | --- | --- | --- |
| Safe /24 | 19 | 23 | 24 |
| Gain/loss vs R | — | 4/0 | 5/0 |
| Common-safe n | — | 19 | 19 |
| Mean Δt (s) | — | +6.63 | +25.16 |
| Median Δt (s) | — | 0 | 0 |
| Maximum Δt (s) | — | +69 | +308 |
| Episode CPU (s) | 270.68 | 378.44 | 2133.23 |

Against L, S15 gains one safe completion and loses none. Their 23 common-safe pairs have mean S15−L time +7 s, median 0 and maximum +308 s. These are descriptive paired results, not population superiority or a statistically established safety advantage. All five R failures and the one L failure are pressure-crossing buffer incursions. L reaches the goal on its failed task, which remains unsafe. S15 and L each activate on 11 tasks. The designed pressure-enriched mix does not estimate natural traffic frequency.

![Fig. 2. All 24 matched tasks: common-safe time differences, every actual dynamic margin with an expanded near-zero scale, and a separate safety-status strip. Missing time points are failed pairs, not zero cost. Indices 1–8: pressure; 9–12: crossing; 13–16: overtaking; 17–20: endpoint; 21–24: non-conflict.](figures/figure2_confirmation.png)

### B. A decision difference and an adverse case

The unique L-unsafe/S15-safe task is r12new_mixed_pressure_1. The two methods have exactly equal recorded physical states, reference histories and issued commands through t=260 s. At that state, detailed nominal prediction gives 11.893 m minimum margin, below ρ=30 m, whereas L gives 59.832 m and returns nominal. Detailed prediction selects +90 degrees with predicted margin 36.546 m and cost 509.528 m; the feasible −90-degree alternative has margin 70.147 m and cost 513.228 m. The selected target is (627.068,163.231) m, versus nominal (575,−200) m. Selection occurs at 260 s, delivery at 261 s, and its first possible physical effect is the 261–262 s interval. This is a verified same-input decision difference; L does not evaluate alternatives after nominal passes.

![Fig. 5. Unique new-confirmation L incursion with complete R/L/S15 and target tracks. Circles and square mark synchronized positions at 260 s; the dotted circle is the target’s 85 m exclusion boundary then. Plus/cross marks identify each run’s minimum-margin endpoint. Lower panel shows the encounter interval, not separate-time closest points.](figures/figure5_rescue.png)

Over the complete voyage, L reaches at 566 s with minimum −1.115 m at 402 s; S15 arrives at 519 s with minimum 42.096 m at 291 s. R exits at 392 s with margin −0.162 m. Later states, subsequent interventions and encountered wind differ. We therefore do not attribute the full-voyage outcome solely to the first target change or infer its counterfactual 60-second effect from a later replanned trajectory. The full candidate table and exact log locations are supplied in the supplement.

The strongest new time-cost counterexample is r12new_endpoint_3: R and L safely arrive in 279 s, while S15 takes 587 s. That +308 s penalty remains in the primary table and Fig. 6. Useful risk intervention and unnecessary intervention must both be evaluated.

![Fig. 6. Adverse endpoint task: S15 adds 308 s over safe R and L. All complete actual tracks and synchronized target motion are shown. Circles/square mark 200 s; the dotted circle is the exclusion boundary at that time. The lower panel reports synchronized clearance throughout each run.](figures/figure6_adverse.png)

Historical R8 evidence rescues two of 30 short and one of four long reactive failures. R10’s twelve separate new tasks show no extra completion over R and include a +271 s endpoint detour. Its 13 seen mechanism tasks overlap R8. These groups remain separate in Supplement S6; they are supporting context, not additional independent trials for Table I. S60 still searches candidates and NH still predicts nominal. Neither is described as a no-prediction baseline.

'''
s=s[:a]+new+s[b:]
s=s.replace('Table III','Table II').replace('as well as completion','without a redundant constant-completion panel')
s=s.replace('Each point/branch represents an executed protocol; twelve branches come from six snapshots. Ten common intervals are 60 s and two are 58 s. Duplicate protocols at one endpoint snapshot are retained but not counted as independent scenes.', 'Grouped by six source snapshots, with two protocols per group (circle/triangle; identities in Supplement S7). Errors and margin residuals share ten 60 s and two 58 s intervals. Duplicate nominal/continuation at snapshot 4 is one source state, not independent evidence.')
s=s.replace('Figure 5 shows the complete historical encounter and the largest new common-safe S15 time-cost case.', 'This development snapshot illustrates fidelity on a fixed protocol; it is distinct from the new-confirmation complete-task comparison in Figs. 5–6.')
s=re.sub(r'!\[Fig\. 5\. Actual own-vessel.*?\]\(figures/figure5_encounters.png\)\n\n','',s,flags=re.S)
s=s.replace('Formal attribution and distribution permission for the inherited controller and simulator remain author-verification items.', 'The supplied artifact identifies the local source files and checkpoint by hash, but a verified original publication/training record and redistribution license have not been supplied. This is a provenance and public-reproducibility gap, not merely missing author metadata. Results characterize this inherited system, not a verified reproduction of [8].')
s=s.replace('R12 adds the specified simulation comparisons and offline checks, with no policy training or physical experiment.', 'The experiments are simulation comparisons and offline checks; this revision reorganizes their evidence without policy training or a physical experiment.')
(P/'manuscript.md').write_text(s,encoding='utf8')
sp=(P/'SUPPLEMENT.md').read_text(encoding='utf8').replace('# R12 Supplementary Method and Reproduction Notes','# R13 Supplementary Method and Reproduction Notes')
sp+='\n\n## S6. Separate historical evidence and version map\n\n'+old+'\nR8: detailed predictor original closed-loop study. R10: same main ideal-compute method with new confirmation and overlapping mechanism cases. R12: same frozen detailed method plus calibrated L; 24 frozen tasks. R13: textual/figure revision and log reanalysis; no changed algorithm or new main-task outcomes. R9 delayed execution is a different protocol, not pooled.\n'
sp+='\n## S7. Grouped fixed-protocol diagnostics\n\n| Snapshot | Source / time | Circle protocol | Triangle protocol | Common time |\n| --- | --- | --- | --- | --- |\n'
q=json.loads((P/'evidence/matched_prediction_quality.json').read_text())
for i in range(0,12,2):
 x,y=q[i:i+2];sp+=f"| {i//2+1} | {x['scene']} / {x['time']} s | {x['candidate']} | {y['candidate']} | {x['common_steps']}/{y['common_steps']} s |\n"
sp+='\nTwo protocols share one source state; snapshot 4 even duplicates the paths. Branch/window counts are diagnostic workload, not independent sample sizes.\n\n## S8. Unique confirmation difference\n\n`evidence/decision_260.csv` contains all evaluated candidates at the same physical/history state at 260 s in `runs/r12_revision_20261006/confirmation/r12new_mixed_pressure_1__{sampled,simple}/trace.json`. `evidence/case_analysis.json` records the prefix equality check and complete-task minima. No unexecuted L alternative is invented after its nominal early return. The matched state validates a decision contrast, not a claim that this single intervention caused the whole-voyage rescue.\n'
sp+='\n## S9. Reproduction assets and limitations\n\n`evidence/ASSET_HASHES.json`, `dynamics_parameters.json`, and `INHERITED_SOURCE_CHECK.json` specify exact inherited files. The associated R12 raw-results archive and R10 inherited-asset/source archives are indexed in EVIDENCE_INDEX.md. A recipient with the private inherited assets can reproduce the supplied worker; a public reader without those weights cannot yet reproduce that exact policy. Original training provenance and release permission remain unresolved scientific-reproducibility and submission issues. Xiao and Jouffroy is background, not certified provenance. No claim is made that an available filename establishes publication identity.\n'
(P/'SUPPLEMENT.md').write_text(sp,encoding='utf8')
m=(P/'math_docx.py').read_text(encoding='utf8').replace("mn(85),text(' m')","sub(mi('D'),mi('j'))").replace("sub(mi('c'),mi('t'))","sub(mi('c'),row(mi('j'),mo(','),mi('t')))")
m=m.replace("return {f'EQ{i+1}':x for i,x in enumerate([eq1,eq2,eq3,eq4,eq5])}","eqmin=[row(hat(mi('m')),par(mi('γ')),mo('='),sub(mi('min'),row(mi('j'),mo('∈'),sub(mi('O'),mi('t')))),sub(mi('min'),row(mn(0),mo('≤'),mi('k'),mo('<'),sub(mi('K'),mi('γ')))),sub(hat(mi('c')),row(mi('j'),mo(','),mi('k'))),par(mi('γ')))]\n return {f'EQ{i+1}':x for i,x in enumerate([eq1,eq2,eqmin,eq3,eq4,eq5])}")
(P/'math_docx.py').write_text(m,encoding='utf8')
(P/'STAGE_A_CHANGES.md').write_text('# Stage A: actual changes versus R12\n\nPrimary matched24 table moved before history; means, tails, denominators and CPU exposed. Added predicted minimum, effective horizon, empty-set/sentinel/failed-forecast definitions and static D_j; retained nominal-first, conditional20m and real timing. Replotted all24 with separate status strip and near-zero margin expansion. Added unique L failure with same-history260s decision table; retained+308s full-track counterexample. Grouped12 branches by6 snapshots. Source attribution/public reproducibility gap explicitly distinguished from administrative author metadata. No algorithm modification or new full voyage.\n',encoding='utf8')
print('R13 manuscript and supplement revised')
