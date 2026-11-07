from pathlib import Path
import re
P=Path(__file__).resolve().parent
s=(P/'manuscript.md').read_text(encoding='utf8')
blocks=s.split('\n\n');fig=next(b for b in blocks if b.startswith('![Fig. 1.'))
blocks.remove(fig);idx=next(i for i,b in enumerate(blocks) if b.startswith('Prediction starts no earlier'))
blocks.insert(idx+1,fig);s='\n\n'.join(blocks)
s=s.replace('Filled markers are S15; open markers are L.','Filled markers are S15; open markers are L. N: nominal; C: continuation; signed angles: side protocols.')
s=s.replace('The authors thank Chao Yang for providing the research code and pretrained assets used in this study. AI tools assisted drafting, implementation and internal evidence review. The human authors are responsible for verifying the work and completing the applicable disclosure requirements.','AI tools assisted drafting, implementation and internal evidence review.')
(P/'manuscript.md').write_text(s,encoding='utf8')
supp=(P/'SUPPLEMENT.md').read_text(encoding='utf8')
def section(n,title,text):
    global supp
    pattern=rf'## S{n}\. .*?(?=\n## S{n+1}\. |\Z)'
    supp,count=re.subn(pattern,lambda m:f'## S{n}. {title}\n\n{text.strip()}\n\n',supp,flags=re.S)
    assert count==1,n
section(5,'Reproduction records', '''The recovery archive identifies the evaluated code, inherited assets and frozen configuration. Its plan.json, freeze.json, calibration.json and development/guard/confirmation manifests specify the experiment identities. The primary dataset is the 24-task confirmation with all three methods and all failures retained. Raw traces contain scene definitions, actual states, commands, target observations, reference changes, candidate predictions and failure reasons.

The low-order model is src/sailboat_routing/r12_model.py. Detailed prediction and supervision are r8_model.py and r8_planner.py; scripts/run_r12.py imports the unchanged physical worker. Scripts prepare_r12.py, prepare_r12_confirmation.py, analyze_r12_prefix.py, check_r12_branches.py, profile_r12.py and analyze_r12.py define calibration, task generation and diagnostics. The evidence index locates the complete archive; the lightweight manuscript package alone does not contain all model weights and raw traces.''')
section(9,'Reproduction assets and model provenance', '''The supplied dynamics implementation, 18-input Actor and matching normalizer come from the codebase associated with Yang et al. [7] and were provided by Chao Yang. Permission covers research use and provision of reproduction materials to editors and reviewers upon request. Public release of these exact assets is not established. The original training-run linkage remains undocumented; the 14-input policy described in the journal article is not used as an identical checkpoint baseline.

The asset files are checkpoints/obstacle_candidate/saclstm_s14obst_noise_0204_actor10800.pth and its matching normalizer10800.pth. evidence/ASSET_HASHES.json and asset_resume_check.json record exact identities. evidence/dynamics_parameters.json records the inherited physical parameters; INHERITED_SOURCE_CHECK.json identifies source versions. Numerical details and the complete recovery procedure appear in S11 and S14.''')
section(11,'Recovery procedure and numerical checks', '''The separate R13_REPRODUCTION_internal.zip archive contains source dependencies, the Actor and normalizer, requirements.lock, manifests and all 72 primary confirmation traces. CONTENTS_SHA256.json and verify_recovery.py are included. Extract to a new directory, prepare the documented dependency environment, and run python verify_recovery.py. The stored recovery check verified all packaged hashes, constructed and closed CausalModel with the actual weights, imported the physical worker and recomputed the primary counts and common-safe time differences. evidence/recovery_check.json and recovery_check.log record that check; it was not a new navigation experiment.

Three observation-only accepted-substep replays of r12new_mixed_pressure_1 use unchanged original commands and tolerances. All one-second endpoints match exactly. R/L/S15 minima are −0.162187/−1.117383/42.094165 m on accepted-substep segments and −0.162187/−1.115322/42.095555 m on the original one-second segments. Maximum substep is 0.1 s. These replays support the numerical labels for the circular exclusion proxy. They do not establish exact swept-hull safety. evidence/new_case_substeps.json records the values.''')
section(12,'Relation to the published sources', '''Yang et al. [7], Applied Ocean Research 175 (2026) 105246, describes a 14-dimensional wind-input-free observation in Section 2.3, equation (27). The present 18-input attention asset is identified independently by code, observation ordering, normalization and checkpoint hashes. The journal's reported benchmark performance is not assigned to this asset. The article reports a public v1.0.3 software release, but membership of the evaluated actor10800 and normalizer in that release has not been established; no released asset was substituted in these experiments.

The model lineage is Xiao and Jouffroy [9]. The original author's software page identifies the corresponding 2014 sailing-yacht model release. The supplied Python implementation retains its existing notices; exact equivalence to the original implementation is not established. An article license is not assumed to license separate code or weights. These source distinctions separate bibliographic attribution, numerical model identity and access to reproduction materials.''')
section(13,'Implementation edge cases', '''A nonempty rollout with no obstacles has predicted minimum +infinity; a zero-step rollout uses −10^9 m and fails the guard. The prediction-local physical clock starts at zero, while nominal management uses absolute task time. Inherited dynamics parameters include mass 25,900 kg and sail/rudder/keel areas 170/1.17/8.7 square meters. These settings are implementation details, not additional contributions.

The low-order comparison replaces recurrent-policy, actuator, wind and speed dynamics together. Its calibration covers unchanged-reference 15-second windows and does not establish 60-second hold/release fidelity. Historical input-adapter checks and detailed-prediction experiments retain their own datasets; they are not pooled with the 24-task primary confirmation.''')
supp=supp.replace('R9 delayed execution is a different protocol, not pooled.','')
supp=supp.replace('Separate R9 delayed-execution failures are boundary evidence, not pooled main-method outcomes.','')
(P/'SUPPLEMENT.md').write_text(supp,encoding='utf8')
print('Polished current manuscript and scientific supplement')
