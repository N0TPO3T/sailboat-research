"""One-time editorial transformations of the preserved 20261008 author manuscript."""
from pathlib import Path
import re
P=Path(__file__).resolve().parent
s=(P/'manuscript.md').read_text(encoding='utf8')
start=s.index('A geometrically clear waypoint');end=s.index('\n\nKeywords:',start)
s=s[:start]+'''A geometrically clear waypoint can induce an unsafe sailing trajectory because wind, actuator dynamics and controller memory affect its execution. We present a supervisory interface that predicts position references together with their delivery, holding and route-restoration rules using a frozen recurrent controller. Causal history, the pending action and a local wind estimate condition each prediction. In 24 frozen simulation tasks, reactive navigation, a calibrated low-order predictor and detailed prediction safely complete 19, 23 and 24 tasks, respectively. All safe-completion differences occur in eight combined-pressure encounters. Detailed prediction adds one completion over the low-order comparator, with mean and maximum travel-time increases of 7 and 308 s across 23 common-safe tasks and higher computation cost. The study measures and explains these observed safety, navigation-time and computation trade-offs under ideal computation, with physical time paused during planning.'''+s[end:]
start=s.index('The contribution has two parts.');end=s.index('\n\n## II.',start)
s=s[:start]+'''The interface treats a candidate as a position reference together with its delivery, holding and nominal-feedback restoration rules. History replay, actuator-setpoint reconstruction and pending-action preservation align prediction with this controller interface; action and recorded-prefix checks verify the covered execution correspondence. We evaluate the integrated predictor and its costs, without isolating the necessity or safety benefit of each reconstruction component.

We investigate how reference-protocol-conditioned prediction changes supervisory decisions and the resulting safety, navigation-time and computation trade-offs relative to reactive navigation and a calibrated low-order predictor. The inherited controller and dynamics supply the execution model; the contribution is their supervisory integration and assessment.'''+s[end:]
s=s.replace('A non-nominal hold takes precedence while t<until.','A non-nominal hold takes precedence while t<until, where until is the hold-expiry time. The next review time is next_plan, initially 10 s.')
s=s.replace('![Fig. 1. Prediction branches and actual execution. Memory replay and setpoint accumulation are separate operations. At t, the old-reference action is already fixed; the new reference applies at t+1 and first affects t+1 to t+2. Only executed observations and commands update real history.]','![Fig. 1. Nominal-first prediction and actual execution. A valid nominal rollout meeting the guard returns without predicting alternatives. Memory replay and command accumulation are separate branch-initialization operations; predicted histories stay isolated. The old action executes first, a changed reference applies at t+1, and its first possible effect is t+1 to t+2. Only executed feedback updates real history.]')
s=s.replace('Nominal feasible returns immediately.','The coefficients 20 and 10 in (4) have units of metres, as do J and d_G. Feasible nominal returns immediately without predicting alternatives.')
start=s.index('```text\nAlgorithm 1');end=s.index('\n```',start)+4
s=s[:start]+'''```text
Algorithm 1  Selection at a one-second boundary t
Input: observed state/history, pending old action, manager,
       current reference, next_plan, held, until; H, P, ρ.
Output: selected reference; updated manager and timers.
1  If t < until: return held; do not call the manager.
2  Call nominal manager; clear incumbent if hold expired.
3  If t < next_plan or no valid target is within 600 m:
       release any expired hold; return nominal.
4  Set next_plan = t+P; fit local wind from history.
5  Restore a branch and predict nominal to horizon H.
6  If valid, integration-successful and margin ≥ ρ:
       select nominal; skip all alternative predictions.
   Else:
       restore separate branches; predict available
       continuation and four side-reference protocols;
       select by guarded cost or the original fallback.
7  Nominal clears held; otherwise set held and until=t+P.
8  Return selection; after the old action, deliver any
   changed reference at t+1 (first effect: t+1 to t+2).
```'''+s[end:]
old='Their 23 common-safe pairs have mean S15−L time +7 s, median 0 and maximum +308 s.'
new=old+' Across the 23 common-safe pairs, S15 is faster in five tasks, has equal travel time in thirteen, and is slower in five; the differences range from −136 to +308 s. Equal travel time does not imply equal trajectories.'
assert old in s;s=s.replace(old,new)
s=s.replace('Within the tested scope, executable reference protocols reveal both useful avoidance decisions and costly interventions, providing a basis for choosing prediction fidelity according to the application.','Within the tested scope, executable reference protocols reveal both useful avoidance decisions and costly interventions. These observations characterize the measured trade-offs; they establish neither a generally worthwhile cost nor a validated rule for online predictor switching.')
s=s.replace('Supplement S9 and S11–S12 identify the versions and commands.','The lightweight supplement permits CSV reaggregation but does not include the full recovery archive or model weights. Editors and reviewers can request the complete archive through the manuscript\'s editorial correspondence channel; Supplement S5 and S11 describe its contents and recovery steps.')
(P/'manuscript.md').write_text(s,encoding='utf8')

p=P/'SUPPLEMENT.md';s=p.read_text(encoding='utf8')
s=s.replace("The selected branch's first 15 seconds must also match its source.","For the six actually selected branches, the first 15 seconds of positions must also match their sources; this check does not apply to the six alternative branches.")
s=s.replace('Table I preserves','Table S2 preserves').replace('Table I. Historical','Table S2. Historical')
s=s.replace('The unnormalized 18-element policy input, in zero-based index order, is:','The unnormalized 18-element policy input, in zero-based index order, is listed in Table S1.\n\nTable S1. Policy input ordering, before normalization.')
s=s.replace('## S7. Grouped fixed-protocol diagnostics\n\n','## S7. Grouped fixed-protocol diagnostics\n\nTable S3. The six source snapshots and protocols plotted in main-paper Fig. 6.\n\n')
s=s.replace('| Family (n) | Initial target position','Table S4. Primary confirmation scene-generation envelope.\n\n| Family (n) | Initial target position')
start=s.index('## S5. Reproduction records');end=s.index('## S6.',start)
s=s[:start]+'''## S5. Reproduction records and access

The supplied lightweight closeout package contains the full manuscript, this supplement, editable Word source, build/figure scripts, publication figures and the unchanged lightweight evidence directory. It does not contain the complete model weights, all raw trajectories or a runnable simulator. Paths beginning evidence/ are relative to the extracted lightweight package. Paths beginning runs/, src/ or checkpoints/ identify content in the separately supplied recovery archive, not paths required on the reader's machine.

Run `python check_paired_times.py` from any extracted package location; it uses only the Python standard library and resolves evidence/episodes.csv relative to its own file. It filters stage=confirmation, verifies all 72 rows and 24 scene IDs, and pairs S15 (sampled) with L (simple) only when both success fields are True. Exact original time values give 23 pairs: five faster, thirteen equal and five slower, with minimum −136 s, maximum +308 s, mean +7 s and median 0. Equal times do not imply identical trajectories. PAIRED_TIME_CHECK.json includes every included pair and the excluded unsafe L arrival. No simulation is run.

The same CSV supports reaggregation of main-paper Tables I–II (completion counts, family groups, common-safe times and cumulative episode CPU). Guard records in evidence/guard.json and analysis.json document Table III; fixed_branches.json, matched_prediction_quality.csv, prediction_windows.csv and planning_profile.json provide the reported diagnostics. These supplied logs do not independently establish raw-trajectory correctness. The earlier 20261008 trajectory-recomputation receipt is preserved under provenance/ and is not a new check in this closeout.

The separate archive is named R13_REPRODUCTION_internal.zip, SHA256 d0fdc80b40b5252ced7dfd15370a30e092b3232cc1b7ef65e131bedac50ce640. It is not attached to the lightweight package and has no public download URL. Permission to provide it to editors/reviewers is already confirmed. During review, request it through the manuscript's editorial correspondence channel; the authors can provide the archive through the journal/conference's private material-exchange channel or another agreed private transfer. The corresponding author and contact address remain submission metadata to be supplied, not a presently available contact in this package.

The archive identifies the evaluated code, inherited assets and frozen configuration. Its plan.json, freeze.json, calibration.json and development/guard/confirmation manifests specify experiment identities. The 72 primary raw traces contain scene definitions, states, commands, target observations, reference changes, candidate predictions and failure reasons. The low-order model is src/sailboat_routing/r12_model.py; detailed prediction and supervision are r8_model.py and r8_planner.py. scripts/run_r12.py imports the unchanged physical worker. Calibration, generation and diagnostics are defined by prepare_r12.py, prepare_r12_confirmation.py, analyze_r12_prefix.py, check_r12_branches.py, profile_r12.py and analyze_r12.py. S11 separates archive validation from running new simulations.

'''+s[end:]
s=s.replace('Extract to a new directory, prepare the documented dependency environment, and run python verify_recovery.py.','After obtaining it through S5, verify the archive SHA256, extract it to a new directory of the reader\'s choice, follow its included environment/reproduction instructions, and run python verify_recovery.py from that extraction root. No sibling directory on an author machine is required. The bundled source, model files and frozen manifests support rerunning the primary confirmation protocol in a compatible environment; historical diagnostic summaries alone are not a complete set of all older raw traces.')
s+='\nSupplement tables use the independent labels Table S1–S4. This supplement contains no additional figures; references to Fig. 1–6 refer to the main paper. Historical evidence groups retain their original identities and are not new confirmation data.\n'
p.write_text(s,encoding='utf8')
print('M1–M3, algorithm, units, supplement numbering and reproduction text updated.')
