from pathlib import Path
import re
p=Path(__file__).parent;s=(p/'manuscript.md').read_text(encoding='utf8')
s=s.replace('For the same protocol, obstacle identities/radii and common time domain T, the triangle inequality gives', 'For the same protocol γ, obstacle set O, radii and common time domain T, define M=m_real(γ;T,O) and M̂=m̂(γ;T,O) as the actual and predicted minima restricted to that domain. These differ from the whole-task metric m_real. The triangle inequality gives')
s=s.replace(r'|m^{\mathrm{real}}-\hat m|\le E,\qquad m^{\mathrm{real}}\ge\hat m-E.',r'|M-\widehat M|\le E,\qquad M\ge\widehat M-E.')
s=s.replace('Empty obstacle sets give +∞','An empty O_t gives +∞')
s=s.replace('All targets in these main tests have constant world-frame velocity', 'All 24 primary confirmation tasks are 1 km. Targets are generated at 0.65–0.95 m/s except endpoint tasks at 0.8–1.0 m/s. The pressure family jointly changes encounter geometry, base wind direction (115–135 degrees rather than 45–80 degrees), and a static circle at (850,300) m of entity radius 45 m. Gains within this family do not isolate those factors. Supplement S10 gives each family’s generation envelope. These are new supervisor-evaluation scenes; separation from the inherited policy’s undocumented training scenes is not certified.\n\nAll targets in these main tests have constant world-frame velocity')
s=s.replace('with an expanded near-zero scale,','on a symmetric-log axis (linear for |margin|≤3 m),')
s=s.replace('Accepted-integrator-substep checks preserve every one-second endpoint exactly.', 'An additional same-command check of the unique new case preserves every one-second endpoint exactly and gives R/L/S15 substep minima −0.162/−1.117/42.094 m, retaining all three labels. This is a numerical replay, not three new tasks. Historical accepted-integrator-substep checks also preserve every one-second endpoint exactly.')
s=s.replace('Sailing-yacht models are discussed in [8]; code-level equivalence to that publication is not asserted.', 'The author-maintained model release associated with [8] describes the same four-degree modeling family; the inherited local thesis draft also cites it. Exact equivalence of the Python port to that release is not established.')
s=s.replace('The supplied artifact identifies the local source files and checkpoint by hash, but a verified original publication/training record and redistribution license have not been supplied. This is a provenance and public-reproducibility gap, not merely missing author metadata. Results characterize this inherited system, not a verified reproduction of [8].', 'The checkpoint is traced to a user-supplied archive and PART5/SAC-LSTM-att evaluation entries; the dynamics is a separate byte-identified source snapshot. An internal recovery bundle loads the exact weights and reproduces Table I from all 72 traces. Original training-to-checkpoint linkage and permission for the inherited port/weights remain unconfirmed. Supplement S9 separates verified local lineage, primary-source metadata and these outstanding provenance/access limits.')
s=s.replace('the paper provides a reproducible reference-execution interface and evidence', 'the paper provides a specified reference-execution interface, an internally recovery-checked artifact and evidence')
(p/'manuscript.md').write_text(s,encoding='utf8')
sp=(p/'SUPPLEMENT.md').read_text(encoding='utf8')
sp=sp.replace('taking minima gives |m−m̂|≤E.', 'taking minima on the same protocol/time/obstacle domain gives |M−M̂|≤E, with M=m_real(γ;T,O) and M̂=m̂(γ;T,O). This is not a bound on the unrestricted whole-task metric.')
sp+='''

## S10. Primary confirmation scene envelope

All24 tasks: start(0,0), goal(1000,0)m, one constant-velocity target. Random generation seed202610612, physical seed2026106120+i. Each family alternates stable/fast wind (total12/12). No outcome filtering or new R13 sampling.

| Family (n) | Initial target position (m) and velocity (m/s) | Base wind (degrees) | Static context |
| --- | --- | --- | --- |
| Pressure (8) | q=(x,sT), x∈[620,710], T∈[185,230]s, s∈[.65,.95]; v=(0,−s) | [115,135] | Circle center(850,300), entity radius45m |
| Crossing (4) | q=(x,−sT), x∈[420,540], T∈[140,220]s; v=(0,s), s∈[.65,.95] | [45,80] | None |
| Overtaking (4) | q=(x,y), x∈[230,300], y∈[−15,15]; v=(s,0), s∈[.65,.95] | [45,80] | None |
| Endpoint (4) | q=(x,y), x∈[610,650], y∈[−15,15]; v=(s,0), s∈[.8,1.0] | [45,80] | None |
| Non-conflict (4) | q=(x,±y), x∈[500,600], y∈[340,390]; v=(s,0), s∈[.65,.95] | [45,80] | None |

All draws use the exact ordering in code/scripts/prepare_r12_confirmation.py; the manifest lists realized values. “Pressure” changes several factors jointly. Paired method contrasts remain matched within each scene, but this study does not assign the gains to one of those factors alone. These are newly generated supervisor tests, not verified holdouts from unknown inherited policy training.

## S11. R13 recovery and numerical checks

R13_REPRODUCTION_internal.zip is a separate internal archive containing source dependencies, Actor/normalizer, requirements.lock, manifests and all72 confirmation traces. It is supplied for the user's authorized project work, not offered as a public release or grant of redistribution permission. SHA256 index and verify_recovery.py are inside it. In a new directory with the existing project Python environment, the script verified every packaged hash, constructed/closed CausalModel with actual weights, imported run_r12.worker, and recomputed19/23/24 plus23common-safe S15−L mean7s and maximum308s. No new navigation trial was needed for this recovery check. evidence/recovery_check.json/log identify the real directory and outputs. Reproduction command after extraction: python verify_recovery.py. Dependencies remain those in requirements.lock; no new packages were installed.

Three observation-only accepted-substep replays of r12new_mixed_pressure_1 use unchanged original commands and tolerances. All1s endpoints match exactly. R/L/S15 minima at accepted-substep segments are−0.162187/−1.117383/42.094165m; corresponding original1s minima are−0.162187/−1.115322/42.095555m. Maximum substep0.1s. This supports numerical labels, not exact hull safety. Plan, script and evidence: NUMERIC_PLAN.md, check_case_substeps.py, evidence/new_case_substeps.json.

## S12. Source follow-up and access status

SOURCE_FOLLOWUP.md records a targeted source check. The locally supplied draft “The Research on Unmanned Sailboat Control Model Based on Reinforcement Learning” names Chao Yang and Zhejiang University. Its cover date is December2026 (later than this verification), so it is treated as an unpublished local draft, not a verified awarded thesis. Its Section2.3 credits Xiao/Jouffroy for dynamics; Chapter5 describes attention-based static avoidance. The draft does not establish the hash-to-training-run mapping of the current10800checkpoint. The earlier anonymous draft cannot establish authorship either.

The original author's software page https://www.mathworks.com/matlabcentral/fileexchange/47981-sailingyachtmodel-zip identifies JeromeJouffroy, version1.0.0.0,2014-10-02, and cites Xiao/Jouffroy2014 as its model/parameter source. Its linked license permits redistribution of that original distribution under notice/disclaimer conditions. This does not automatically license the inherited Python port or weights. No source-code equivalence to the downloaded original was verified. Actual file identities, user archive lineage, and runtime adaptations are supplied; creator confirmation, original training linkage and inherited-asset release/access authorization remain explicitly unresolved. The authors must close this record before claiming publication readiness. More simulations cannot close it.
'''
(p/'SUPPLEMENT.md').write_text(sp,encoding='utf8')
f=p/'math_docx.py';m=f.read_text(encoding='utf8')
m=m.replace("eq4=[row(mo('|'),sup(mi('m'),text('real')),mo('−'),hat(mi('m')),mo('|'),mo('≤'),mi('E'),mo(','),text('   '),sup(mi('m'),text('real')),mo('≥'),hat(mi('m')),mo('−'),mi('E'))]", "eq4=[row(mo('|'),mi('M'),mo('−'),hat(mi('M')),mo('|'),mo('≤'),mi('E'),mo(','),text('   '),mi('M'),mo('≥'),hat(mi('M')),mo('−'),mi('E'))]")
# Correct Office's interpretation of hat as upper limit; preserve editable native math.
m=m.replace("return transform(E.fromstring(('<math xmlns=\"http://www.w3.org/1998/Math/MathML\">'+src+'</math>').encode())).getroot()",'''root=transform(E.fromstring(('<math xmlns="http://www.w3.org/1998/Math/MathML">'+src+'</math>').encode())).getroot()
 ns={'m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}; Q=lambda x:'{'+ns['m']+'}'+x
 for node in list(root.findall('.//m:limUpp',ns)):
  if ''.join(node.find('m:lim',ns).itertext())=='ˆ':
   acc=E.Element(Q('acc'));pr=E.SubElement(acc,Q('accPr'));ch=E.SubElement(pr,Q('chr'));ch.set(Q('val'),'̂');acc.append(node.find('m:e',ns));node.getparent().replace(node,acc)
 for node in list(root.findall('.//m:sSub',ns)):
  base=node.find('m:e',ns)
  if ''.join(base.itertext())=='min':
   lim=E.Element(Q('limLow'));lim.append(base);b=node.find('m:sub',ns);b.tag=Q('lim');lim.append(b);node.getparent().replace(node,lim)
 return root''')
f.write_text(m,encoding='utf8')
# Keep LaTeX symbol conversion aligned with revised text.
f=p/'convert_to_latex.py';m=f.read_text(encoding='utf8').replace("('m_real',", "('M̂',r'$\\widehat M$'),('m_real',");f.write_text(m,encoding='utf8')
print('Round2 text and editable math repaired')
