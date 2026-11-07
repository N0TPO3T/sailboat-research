"""Evidence-preserving editorial revision of the supplied manuscript."""
from pathlib import Path
import re, difflib
P=Path(__file__).resolve().parent
s=(P.parent/'track_A_submit/manuscript.md').read_text(encoding='utf8')
original=s
def paragraph(starts,new):
    global s
    blocks=s.split('\n\n')
    matches=[i for i,b in enumerate(blocks) if b.startswith(starts)]
    assert len(matches)==1,(starts,matches)
    blocks[matches[0]]=new
    s='\n\n'.join(blocks)

paragraph('A geometrically clear waypoint can induce',
'''A geometrically clear waypoint can induce an unsafe sailing trajectory when wind, actuator dynamics and controller memory affect its execution. We present a supervisory interface that predicts candidate position references together with their holding and route-restoration rules using a frozen recurrent controller. Each branch preserves causal history and the pending control action, estimates local wind from observed motion, and evaluates synchronized obstacle clearance. In 24 frozen simulation tasks, reactive navigation, a calibrated low-order predictor and detailed prediction safely complete 19, 23 and 24 tasks, respectively. All differences occur in eight combined-pressure encounters. Detailed prediction adds one completion over the low-order comparator but adds 7 s mean and 308 s maximum travel time over 23 common-safe tasks; cumulative episode CPU is 2133.23 versus 378.44 s. Fixed-protocol checks expose decision-relevant prediction differences and a 106 m adverse error. These results characterize the conditional value and cost of predicting executable reference protocols under ideal computation, with physical time paused during planning.''')
paragraph('The missing interface is',
'''For the inherited recurrent sailing controller considered here, the supervisory input must specify a complete reference protocol. Changing a reference changes the local observation frame and reconstructed controller memory; holding it and restoring route feedback determine subsequent actions. We implement this interface within the control-induced prediction approach motivated by GVO. A local wind fit uses observed vessel motion; MoWe [4] motivates this information source, while our bounded inverse-dynamics fit is a separate implementation.''')
paragraph('Our contribution is',
'''The contribution has two parts. First, an execution-consistent interface carries the pending old-reference action, causal controller history, reference hold and route-manager restoration into each candidate prediction. Second, a matched simulation study measures the resulting avoidance decisions, travel-time penalties and computation against reactive navigation and a calibrated low-order predictor. The research question is whether detailed prediction changes a safety-relevant reference decision enough to justify its additional cost in this setting. The inherited controller and dynamics supply the execution model; the new work is their supervisory integration and assessment. The study includes both an additional safe completion and an endpoint case with 308 s extra travel time.''')
paragraph('The dynamics implementation and pretrained',
'''We use dynamics code and pretrained assets supplied with permission by Chao Yang from the codebase associated with Yang et al. [9]. The frozen controller is an 18-input recurrent soft actor-critic (SAC) policy [5] with temporal attention, hidden layers (256,256), persistent recurrent state, a ten-slot attention history and a matching normalizer. It uses deterministic tanh actions; no policy is trained in this study. This asset differs from the 14-dimensional formulation reported in [9], and its exact original training-run linkage is undocumented. All comparators execute the same 18-input asset.''')
paragraph('The inherited four-degree dynamics',
'''The four-degree-of-freedom sailing dynamics follow the model lineage of Xiao and Jouffroy [8]. The simulated state contains position, roll, heading, surge/sway velocities, roll/yaw rates and actual sail/rudder angles. Prediction and physical execution use independent instances of the same supplied model structure. Thus the experiment tests execution-conditioned prediction within that simulator, including wind-estimation error, but not structural model mismatch. Exact parameters, input mapping, source/weight hashes and reproduction commands appear in Supplement S9 and S11–S12.''')
paragraph('An active reference g defines',
'''An active reference g defines a rigid local frame with angle θ equal to its bearing at application and origin g − 500[cos θ,sin θ], placing g at (500,0) m without rescaling. The first 14 inputs encode local pose, body velocities/rates, actual actuator angles, progress and reference coordinates. Two obstacle distance/bearing pairs use max(0,d−R+40 m), where d is center distance and R is the exclusion radius, with a 150 m encoded-distance cutoff, distance/bearing sorting and zero-filled missing pairs. All comparators share this fixed input adapter; a historical matched check did not establish its independent necessity.''')
paragraph('Reference changes reconstruct recurrent state',
'''Reference changes rebuild controller memory from the recorded history, as specified in Section III-A. Predicted states never enter the physical controller's history. Commands are scaled by 10 degrees, signed-floor quantized to one-degree increments and accumulated into setpoints, clipped to ±90 degrees for sail and ±30 degrees for rudder. Actual angles move at most 10 degrees per second. A custom adaptive Dormand–Prince integrator advances one-second control intervals. All physically executed comparators share these actuation and integration rules.''')
paragraph('Prediction eligibility starts',
'''Prediction starts no earlier than 10 s, requires a valid target strictly within 600 m, and runs when the review timer is due. A non-nominal hold takes precedence while t<until. The evaluated configuration uses horizon H=60 s, review/hold period P=15 s and guard ρ=30 m. A branch starts from the observed physical state, accumulated actuator setpoints, active reference frame, route-manager state, recorded history and the action already computed for the current interval.''')
paragraph('Each branch clones the route manager',
'''Controller reconstruction and actuator reconstruction are separate. To rebuild memory at boundary t, the algorithm encodes all recorded states s₀,…,sₜ in the frame active at that boundary, using each state's historical target observations. It resets recurrent and attention state and performs exactly t forward calls for indices 0,…,t−1. Each call uses the encoded current and preceding observations and the actual preceding command; index 0 repeats the initial observation and uses a zero command. Replay outputs are discarded. The next call uses the encoded sₜ and actual command at t−1. Before branching, this call must exactly reproduce the pending old-reference action. Setpoints are reconstructed independently by accumulating the recorded commands through the quantization and clipping rules from zero initial setpoints.

When a changed reference is delivered, the physical controller rebuilds memory in its new frame using the same procedure. A prediction branch repeats that procedure on its own history, which contains the recorded prefix and its simulated continuation. Each branch also clones the route manager after the current nominal call. During a non-nominal hold the manager is not advanced; release clears its incumbent before restoring route feedback. These rules make each prediction correspond to a specified execution protocol. Matching the pending action checks initialization consistency; it does not establish future accuracy.''')
paragraph('The 20 m offset is common',
'''After nominal rejection, every feasible alternative receives the same 20 m offset, so this term does not determine whether intervention is worthwhile. It remains relevant to tied-margin fallback comparisons that include nominal. Search eligibility and the nominal guard trigger intervention; terminal cost ranks feasible alternatives.''')
paragraph('Table I reports all 24 frozen',
'''Table I reports all 24 frozen confirmation tasks. Gains/losses count paired changes in safe completion. Time differences use only pairs where both methods succeed, so their denominators differ from the completion counts. Table II stratifies the same tasks by prespecified family. These small, designed task sets support descriptive comparisons within their generation envelope, not a population-level estimate of collision risk.''')
paragraph('Against L, S15 gains',
'''Against L, S15 gains one safe completion and loses none. Their 23 common-safe pairs have mean S15−L time +7 s, median 0 and maximum +308 s. Episode CPU totals are 2133.23 s for S15 and 378.44 s for L. All five R failures and the one L failure occur in the combined-pressure family; all methods safely complete the other sixteen tasks. L reaches the goal on its failed task but incurs the safety buffer. S15 and L each activate on eleven tasks. The gain therefore concerns one additional completion under joint geometric, wind and static-obstacle pressure.''')
paragraph('Over the complete voyage, L reaches',
'''Over the complete voyage, L reaches at 566 s with minimum margin −1.115 m at 402 s; S15 arrives at 519 s with 42.096 m at 291 s. R exits at 392 s with −0.162 m. The methods subsequently replan and encounter different states and local wind. The equal-prefix comparison isolates their decision at 260 s, while the complete-voyage outcomes include all later interventions. Fixed-protocol diagnostics in Section V-D separately test prediction accuracy. The supplement provides the full candidate table and log locations.''')
paragraph('The largest time-cost counterexample',
'''The fourth endpoint instance shows the largest travel-time penalty: R and L safely arrive in 279 s, while S15 takes 587 s (Fig. 4). This +308 s intervention cost coexists with the pressure-case benefit.''')
paragraph('The study adapts control-induced prediction',
'''The supervisory interface makes reference prediction consistent with a recurrent sailing controller's execution: the pending action is preserved, memory is reconstructed in the active frame, and reference hold and route restoration are simulated explicitly. The selection rule first tests nominal clearance, then evaluates finite alternatives when needed. The 20 m cost offset does not control intervention in the nominal-rejected feasible branch.''')
paragraph('The matched experiment locates',
'''In the matched experiment, detailed prediction completes 8/8 combined-pressure tasks safely, compared with 7/8 for L and 3/8 for R; all methods complete the other sixteen tasks safely. The single additional completion over L accompanies +7 s mean and +308 s maximum travel time on common-safe pairs and higher episode CPU. L is therefore a computationally cheaper alternative with nearly the same completion count in these tasks. Its calibration on unchanged-reference 15 s windows limits the comparison: replacing the full predictor does not isolate which of recurrent memory, actuator, wind or speed modeling produces the difference. Fixed-protocol checks identify local decision-relevant fidelity, while the 106 m adverse error shows that detailed prediction can still be inaccurate.''')
paragraph('The results apply to',
'''The evidence is limited to the inherited dynamics, noiseless motion observations, a known static map and one low-speed constant-velocity target. The finite empirical guard and best-effort fallback provide no safety guarantee. Maneuvering targets, structural model mismatch, multi-vessel encounters and COLREGs behavior require separate evaluation. Planning pauses physical time, and a measured detailed call exceeds the 15 s review period; deployment therefore requires a protocol that accounts for motion during computation. Within the tested scope, executable reference protocols reveal both useful avoidance decisions and costly interventions, providing a basis for choosing prediction fidelity according to the application.''')
paragraph('The authors thank',
'''The authors thank Chao Yang for providing the research code and pretrained assets used in this study. AI tools assisted drafting, implementation and internal evidence review. The human authors are responsible for verifying the work and completing the applicable disclosure requirements.''')
s=s.replace('2009, doi: 10.1109/IROS.2009.5354175.','2009, pp. 5573–5578, doi: 10.1109/IROS.2009.5354175.')
s=s.replace('Authors and affiliations to be confirmed','Authors: Sheng Huang (1), Chao Yang (1), Buyu Guo (2)\n\nAffiliations: (1) Institute of Physical Oceanography and Remote Sensing, Ocean College, Zhejiang University, Zhoushan, China; (2) Donghai Laboratory, Zhoushan, China')
s=s.replace('Exact parameters, input mapping, source/weight hashes and reproduction commands appear in Supplement S9 and S11–S12.','The input ordering and reconstruction are specified in Supplement S2; model parameters, asset hashes and reproduction commands appear in S9 and S11–S12.')
s=s.replace('Six development snapshots also execute two fixed protocols each,','Six selected development snapshots also execute two fixed protocols each,')
s=s.replace('Real offline branches alone query the actual external evolution; predictors use causal inputs.','Three snapshots use the first non-nominal entry in selected tasks, one uses the first prediction, and two use specified diagnostic times (Supplement S7). These are selected cases, not a random accuracy benchmark. Real offline branches alone query the actual external evolution; predictors use causal inputs.')
s=s.replace('Delayed-execution tests use a different protocol and remain separate boundary evidence (Supplement S6/S14).','')
s=s.replace('Candidate histories remain separate; only actual observations and commands update the real history.','Memory replay and setpoint accumulation are separate operations. At t, the old-reference action is already fixed; the new reference applies at t+1 and first affects t+1 to t+2. Only executed observations and commands update real history.')
s=s.replace('Plus/cross marks identify each run’s minimum-margin endpoint.','Plus/cross marks identify each run’s minimum-margin endpoint. The gray disk is the static entity; its outer dashed circle adds the 60 m buffer.')
s=s.replace('Grouped by six source snapshots, with two protocols per group (circle/triangle; identities in Supplement S7).','Grouped by six source snapshots; circle/triangle denote their two protocols, identified on the horizontal axis. Filled markers are S15; open markers are L.')

# Number bibliography in order of first appearance. Preserve source identities.
body,refs=s.split('## References\n\n')
order=list(dict.fromkeys(re.findall(r'\[(\d+)\]',body)))
assert set(order)==set(map(str,range(1,10)))
mapping={old:str(i+1) for i,old in enumerate(order)}
renumber=lambda t:re.sub(r'\[(\d+)\]',lambda m:'['+mapping[m[1]]+']',t)
entries={re.match(r'\[(\d+)\]',x)[1]:x for x in refs.strip().split('\n\n')}
s=renumber(body)+'## References\n\n'+'\n\n'.join(renumber(entries[k]) for k in order)+'\n'
(P/'manuscript.md').write_text(s,encoding='utf8')
supp=(P.parent/'track_A_submit/SUPPLEMENT.md').read_text(encoding='utf8')
(P/'original_support/SUPPLEMENT_original.md').write_text(supp,encoding='utf8')
for a,b in [('All24','All 24'),('all72','all 72'),('23common-safe','23 common-safe'),('seed202610612','seed 202610612'),('total12/12','total 12/12'),('All1s','All 1 s'),('original1s','original 1 s'),('substep0.1s','substep 0.1 s')]:supp=supp.replace(a,b)
extra='''
### Input ordering and replay contract

The unnormalized 18-element policy input, in zero-based index order, is:

| Index | Quantity | Unit / frame |
| --- | --- | --- |
| 0, 1 | x, y | m, active reference frame |
| 2 | Roll | rad |
| 3 | Wrapped heading minus frame angle | rad, active reference frame |
| 4, 5 | Surge, sway | m/s, body frame |
| 6, 7 | Roll rate, yaw rate | rad/s |
| 8, 9 | Actual sail angle, actual rudder angle | rad |
| 10 | Previous minus current distance to the active reference | m; zero at the initial state |
| 11 | Previous minus current absolute x-distance to local x=500 | m; zero at the initial state |
| 12, 13 | Active reference coordinates | (500,0) m |
| 14, 15 | First encoded obstacle distance, relative bearing | m, rad relative to actual vessel heading |
| 16, 17 | Second encoded obstacle distance, relative bearing | m, rad relative to actual vessel heading |

Obstacle pairs are sorted lexicographically by encoded distance then relative bearing. Encoded distance is max(0, center distance minus exclusion radius plus 40 m). Only values at most 150 m enter the policy; missing pairs are (0,0). Static obstacles and moving-obstacle observations at the historical state's own time are combined before sorting. Body velocities and angular rates are not rotated. The frozen normalization is (input-mean)/(sqrt(variance)+10^-6), applied to current and previous state inputs; preceding normalized Actor commands are used directly.

At boundary t, recorded states contain s_0 through s_t and commands contain a_0 through a_(t-1). Reset clears the recurrent and attention dictionaries; the Actor initializes zero hidden/cell state and a zero-padded ten-slot output history. Reencode every state in the frame active at reconstruction. Replay exactly t Actor calls using (encoded s_i, encoded s_(i-1), a_(i-1)); at i=0, repeat encoded s_0 and use the zero command. Discard replay action outputs. The subsequent current call uses encoded s_t, encoded s_(t-1), and a_(t-1). This rebuilds memory conditional on recorded actions, not a counterfactual past trajectory under the new reference.

Actuator setpoints are computed separately from the command prefix: scale each two-element command by 10 degrees, floor signed increments to integer degrees, add to the preceding setpoint and clip sail/rudder targets to ±90/±30 degrees. Initial setpoints are zero. Actual actuator angles come from the current physical state. Independent branches share the reconstructed initial state and pending action, then advance separate simulated histories. A new reference triggers the same frame-reencoding procedure after delivery.

Verified implementation locations in the recovery archive: src/sailboat_routing/frames.py (LocalFrame.encode, reencode_controller); r6_controller.py (ObstacleFrame.encode); r7_dynamic.py (HistoricalFrame); r8_model.py (initialize, rollout); obstacle_candidate.py (ObstacleController.act); third_party/obstacle_candidate/utils_lstm_att_normal.py (Actor).

'''
supp=supp.replace('## S3. Low-order comparator specification',extra+'## S3. Low-order comparator specification')
selection='''The six source tasks were explicitly listed in scripts/check_r12_branches.py, rather than sampled randomly. Snapshots 2, 3 and 6 use the first recorded non-nominal entry in their chosen task; snapshot 5 uses the first prediction. Snapshots 1 and 4 use fixed times 149 s and 341 s. The code establishes these rules but does not document a prospective statistical selection criterion for the two fixed times. Each state compares the selected protocol with nominal, or continuation when nominal was selected. Consequently the twelve-branch median is a descriptive diagnostic of selected development states, some of which overlap low-order calibration data.

'''
supp=supp.replace('Two protocols share one source state;',selection+'Two protocols share one source state;')
(P/'SUPPLEMENT.md').write_text(renumber(supp),encoding='utf8')
(P/'REVISION.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile='original/manuscript.md',tofile='revised/manuscript.md')),encoding='utf8')
print('Word count:',len(original.split()),'->',len(s.split()))
print('Citation mapping',mapping)
