from pathlib import Path
p=Path(__file__).parent;r=p/'review/round_01'
common='''# Author response — actual revision for Round02

No algorithm, model, safety threshold, main-scene manifest or old result changed. The new material is source follow-up, a real dependency/weight recovery check, three numerical replays of existing commands, scene descriptions and repaired mathematical typesetting. All revisions are implemented in the new manuscript/PDF/supplement, not promised work.

'''
responses={
'A':'''| ID | Position | Completed action/evidence | Status |
| --- | --- | --- | --- |
| A1 | Agree; partially resolved | SOURCE_FOLLOWUP.md establishes user archive/PART5 evaluator lineage and identifies a relevant named local thesis draft. The original author’s MathWorks release and license were checked. Internal reproduction archive now includes dependencies, weights and all72traces; a fresh-directory hash/model-load/worker-import/table check passed (evidence/recovery_check.json). II-A/VI/S9/S11/S12 now distinguish actual restricted artifact access from public reproduction. New supervisor scenes are not claimed as certified policy-training holdouts. | Basic local identity/access is supported; human creator attribution, exact training linkage and inherited-port/weight release authorization remain unconfirmed. We do not claim this concern fully closed. |
| A2 | Agree | IV-A and Supplement S10 now report all1km tasks, target speed ranges, exact family geometry, wind directions, static circle and the confounding of pressure construction. Uses existing generator/manifest only. | Implemented. |
| A3 | Agree | Eq5 uses M and M-hat explicitly restricted to gamma/T/O, distinguished from whole-task m_real. Word math uses real accent and lower-limit objects rather than misplaced upper-limit hats; Eq3 min limits repaired. | Implemented; inspect regenerated PDF. |
''',
'B':'''| ID | Position | Completed action/evidence | Status |
| --- | --- | --- | --- |
| B1 | Agree; partially resolved | SOURCE_FOLLOWUP.md identifies exact user archive/PART5 evaluator lineage, relevant named unpublished local thesis draft, and verified original author software metadata. A separate complete internal source/weights/72trace archive was recovered in a new directory; hash check, model load, worker import and table reconstruction passed. Manuscript II-A/VI and S9/S11/S12 narrow reproducibility to this actual internal delivery. | Formal creator confirmation, training linkage and inherited-port/weight release authority remain unconfirmed. No invented publication/license, no claim that a hash proves origin. |
| B2 | Agree with accepted boundary | Abstract/IV-B/VI still state the calibrated predictor-specific comparison, whole predictor replacement, conditional23pair time statistic,106m error,308s cost and lack of population superiority. No new task or claim expansion. | Retained. |
| B3 | Agree | Repaired MathML-to-OMML hats as native accents and min as lower-limit operators; explicit restricted M/M-hat replaces ambiguous Eq5 domain. Re-exported and visually checked PDF. | Implemented; inspect actual replacement. |
''',
'C':'''| ID | Position | Completed action/evidence | Status |
| --- | --- | --- | --- |
| C1 | Agree; partially resolved | A real internal recovery archive supplies source dependencies, exact Actor/normalizer, requirements.lock, manifests and72rawtraces. New-directory verification loads weights/imports worker and rebuilds primary counts and timing (evidence/recovery_check.json/log). SOURCE_FOLLOWUP.md records user archive/PART5 lineage and a named local thesis draft, plus original author model page/license. S9/S11/S12 specify access and limits. | Executable internal recovery closed; human origin/attribution and inherited-port/weight release authorization still unconfirmed. We do not disguise this as an administrative-only matter or ask you to accept a promise. |
| C2 | Agree | IV-A and readable Supplement S10 list1km task lengths, five generation envelopes, speeds, pressure wind/static combination and lack of factor isolation. | Implemented using existing data; no additional sampling. |
| C3 | Agree | Native editable math hat/min conversion repaired. Fig2 caption specifies symmetric-log axis and3m linear region. No font reduction; regenerated PDF retains official template. Official CCDC2027 first-submission page permits8pages (VENUE_CHECK.md); final rules remain distinct. | Implemented; actual pages supplied. |
'''}
for k,v in responses.items():(r/('AUTHOR_RESPONSE_'+k+'.md')).write_text(common+v+'\nAdditional numerical evidence: three same-command substep replays preserve all1s endpoints; R/L/S15 margins −0.162/−1.117/42.094m. This is not needed to refute a chord-only false positive once the negative endpoint is known, but corroborates the label. No new independent task claimed.\n',encoding='utf8')
(p/'REVIEW_PROCESS.md').write_text('''# Actual independent review process

Three real persistent subagents: /root/r13_reviewer_a, /root/r13_reviewer_b, /root/r13_reviewer_c. Requested backend gpt-6-astra/xhigh per ARIS auto-review-loop. Three separate contexts (fork_turns none), no access to others’ first-round opinions, shared immutable manuscript/PDF/supplement and VERSION hashes. Each read whole manuscript and all8PDF pages. These are same-family internal simulated reviews, not cross-family certification or CCDC officials. No predetermined verdict was passed to reviewers.

A/B disclosed reading the supplied R12 CODE_FORMULA_AUDIT author source-audit narrative. They then independently verified source and72rawlogs. This is not full blinding to author technical assessment; it is not exposure to the other R13 reviewers. C reports no prior review exposure. We retain those disclosures, rather than claiming complete blindness. Raw A/B/C reports remain unedited. Allthree first verdicts: Major Revision. Responses are individual files; each reviewer receives only their own prior report/response plus the same revised full evidence package. No reviewer replacement or requested vote change.
''',encoding='utf8')
print('Itemized responses saved; unresolved provenance explicitly retained')
