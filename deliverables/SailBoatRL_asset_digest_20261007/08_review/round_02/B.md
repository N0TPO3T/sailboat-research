# R13 Round 02 — Reviewer B

- Role: persistent independent internal simulated CCDC reviewer B; not a conference official.
- Requested model: `gpt-6-astra`; requested reasoning: `xhigh`. Runtime model identity is not independently attested by this report.
- review_independence: `same-family`
- acceptance_status: `provisional` — internal simulation, not actual conference acceptance.
- Reviewed version: immutable `review_round_02_input`.
- Final verdict: **Major Revision**

## 1. Scope and independent checks

I reread the complete revised manuscript and Supplement S1–S12, the source follow-up, numerical plan, my own Round 01 report and the itemized response to B. I inspected all eight actual replacement PDF page images. I did not read reviewer A/C opinions or responses and do not infer their votes. The earlier disclosed exposure to the supplied R12 source/formula audit remains part of my review history; this round adds no exposure to another R13 reviewer.

The checked SHA256 identities match VERSION.json:

- manuscript.md: `9551e27615c08ca672968fb0ce17e503ac1b227830307a83c3763bacdcc48305`
- manuscript.pdf: `8bc6a5172d495db5e7987f4d9bfb61f41fc3cba01f5e856f34d6521584e0a5f8`
- SUPPLEMENT.md: `8e1e8708b8454af72be55426dc2feab4012d154931ed221288a5c93ab510791d`

I verified that the primary analysis, episode CSV, freeze, confirmation manifest, calibration, same-state candidate table and matched-prediction-quality files are byte-identical to Round 01. Their statistical interpretation therefore does not restart as a new experiment.

The new recovery evidence is substantive:

1. I inspected `R13_REPRODUCTION_internal.zip` without extracting or executing it. All **183 indexed files** match the packaged SHA256 index. The archive contains the expected Actor and normalizer, source dependencies, requirements lock, manifests, recovery script and **72 confirmation traces**.
2. I independently checked the existing fresh recovery directory on the server. Its 183 indexed files match, none of the 72 traces differs from the original confirmation trace, and the five frozen scientific source hashes match. A read-only symlink inventory returned none in that directory.
3. The actual recovery script places the recovered `src` and `scripts` first on its import path, verifies packaged hashes, constructs/closes `CausalModel`, imports the worker and recomputes stored-result summaries. The inspected runtime resolves inherited code/weights relative to the recovered source root. The supplied successful log is consistent with this script. I did **not** rerun the model-load check or execute any navigation experiment during review.
4. Independently reading the archived rows reproduces safe counts **19/23/24** and episode CPU **270.677/378.445/2133.232 s** for R/L/S15. Rechecking the unchanged CSV gives R-relative gains/losses **4/0** and **5/0**, common-safe counts **19/19**, means **+6.6316/+25.1579 s**, medians **0/0**, and maxima **+69/+308 s**. The previously checked 23-pair S15–L mean remains **+7 s**.

This establishes a real internal recovery/load/import and stored-result reconstruction check. It is not a fresh-environment installation test or a rerun of 72 navigation episodes. The revised supplement now makes that distinction. Reusing the existing Python environment is explicitly disclosed rather than concealed.

For source follow-up, I inspected the authoritative local identity/manifest records and verified the named local draft's SHA256 and cover. The cover identifies Yang Chao/Chao Yang, Zhejiang University, and December 2026; that future date does not establish an awarded or published thesis. I also opened the original [MathWorks software page](https://www.mathworks.com/matlabcentral/fileexchange/47981-sailingyachtmodel-zip) and its [linked license text](https://www.mathworks.com/matlabcentral/mlc-downloads/downloads/e5af5a09-4a80-11e4-9553-005056977bd0/7d340fc0-01b1-1f26-4a9f-f5153adf520a/licenses/license.txt). They support the original distribution's named author/date and its notice/disclaimer-based redistribution conditions; they do not establish the exact Python-port/checkpoint lineage. I did not inspect the original MATLAB distribution or establish executable equivalence.

## 2. Current scientific assessment

The paper still investigates the mismatch between a geometrically clear position reference and the trajectory executed by an inherited recurrent sailing controller. It reconstructs causal history, fits local wind, predicts reference/hold/feedback-restoration protocols and uses a nominal-first guard with finite alternatives. Its scope remains ideal-compute, noiseless, single constant-velocity target simulation with shared inherited own-vessel dynamics.

The strongest retention reasons remain intact. The paper has a matched finite-response low-order candidate predictor rather than only a geometric comparator. The frozen primary data support the reported one additional safe completion over L, while also showing the +7 s conditional mean time cost, +308 s adverse case and much greater computation. The same-state contrast is not presented as sufficient causal attribution for the entire rescue. Fixed-protocol fidelity evidence retains the 106 m error, duplicate-source warning and development-data status. Task-level sampling, non-pooled historical groups and the absence of statistical or real-time superiority claims remain explicit.

The added scene envelope improves interpretation: the 24 primary tasks are all 1 km; the pressure family jointly changes encounter geometry, wind and static context; and novelty of supervisor-evaluation scenes is not falsely equated with a verified holdout from unknown inherited policy training. These are useful clarifications, not changes to the outcomes.

I find no newly exposed fatal validity defect in this revision. The contribution remains modest but technically coherent for the declared applied simulation scope. It does not require a new neural architecture, physical-vessel experiment, full COLREGs evaluation or a new theorem merely to satisfy my review.

## 3. Persistent issue ledger

### B1 — Inherited-system attribution and availability

**Status: partially resolved; one human-evidence item remains open.**

**Classification:** necessary evidence / publication-readiness blocker. This is not a demonstrated failure of the numerical results.

**Locations:** page 1, II-A; page 7, VI and Author Actions; Supplement S9, S11–S12; SOURCE_FOLLOWUP.md.

**Closed by this revision:**

- The former generic reproducibility wording has been replaced by a specified interface and an internally recovery-checked artifact.
- The concrete archive actually supplies the frozen weights, dependencies and traces for authorized internal use; it is not merely a list of unavailable filenames.
- The fresh-directory check and independent hash checks materially support internal recoverability.
- Local archive/PART5 evaluator lineage is distinguished from the separate runtime dynamics snapshot.
- The draft thesis, original software distribution, Python port and learned checkpoint are not collapsed into a single proven source. The future-dated thesis is not presented as an awarded publication. No original-distribution license is silently transferred to the inherited port/weights.

**Remaining evidence gap:** the paper still lacks authoritative confirmation of the creator/provider attribution for the exact inherited assets and what paper/reviewer/public access can actually be offered. The current local draft and filename/hash trail narrow the search but do not by themselves establish that confirmation. The manuscript and S12 correctly say this remains unresolved. A candid limitation is necessary, but it does not close the attribution/access record that blocked publication readiness in Round 01.

**Minimum remaining remedy requiring a human/source owner:** obtain a concise, attributable confirmation identifying the creators/providers and the relation of the supplied code, normalizer and checkpoint to the identified work; record appropriate scholarly credit and the concrete authorized access status. The answer may legitimately be that some assets remain private and only a specified review or institutional access route is available. Do not invent a license or require public redistribution as a substitute for accurate attribution. Then incorporate that confirmation in the final attribution/availability text.

The exact training-run linkage remains unknown. Full training logs or retraining are **not** separate mandatory demands from this reviewer if those records do not exist and the paper continues to make only fixed-controller evaluation claims. The authors must distinguish what can be confirmed from what cannot; an undocumented training history cannot be upgraded to a verified benchmark holdout. A source-owner confirmation about identity and access can close the necessary part while retaining an honest training-history limitation.

**Small autonomous correction still available:** II-A currently points to S9 for the new lineage/primary-metadata separation, but the substantive new recovery and source-follow-up material is in S11–S12. Change that pointer to S9 and S11–S12. This is a cross-reference correction, not a new scientific issue or a reason to rerun anything. Its repair alone cannot close the human-evidence gap.

**Impact on verdict:** the internal recovery subproblem is closed. The unresolved creator/access confirmation keeps B1 open under the same criterion as Round 01. More simulation, more favorable outcomes, another hash list or another self-review round cannot supply the missing human evidence.

### B2 — Predictor-specific inference boundary

**Status: accepted boundary retained; no additional experiment required.**

**Classification:** accepted scope; optional future evidence for a stronger claim.

**Locations:** abstract; pages 4–7, IV-B, V and VI; Supplement S3, S7 and S10.

The manuscript still discloses that L is calibrated on 15 s unchanged-reference windows, extrapolates its first interval, retains fixed speed/drift and replaces recurrent policy, actuator, wind and speed dynamics together. Its 60 s/new-reference accuracy is not claimed from its short calibration error. The one discordant completion does not become population superiority, and the fixed-protocol diagnostics do not become independent confirmation trials. The added pressure-family description also prevents attributing that family's difficulty to one isolated factor.

The author's response implements the required restraint in the actual manuscript. B2 therefore remains nonblocking. A better low-order predictor could still close the remaining task difference, but testing that possibility is optional under the current descriptive claim. I do not convert an explicitly accepted limitation into a new mandatory ablation in this round.

### B3 — Method-equation rendering

**Status: closed on the actual replacement PDF.**

**Classification:** prose-layout, resolved.

**Location:** page 3, equations (3)–(5).

I visually confirmed that the predicted-margin and predicted-position hats are attached and readable; the two minimum operators have clear lower limits; and the predicted versus actual margin distinction is visible. The DOCX XML also contains native accent and lower-limit structures, consistent with an actual math conversion repair. Equation (5) now uses M and M-hat defined on the same protocol/time/obstacle domain and explicitly distinguishes that restricted comparison from the unrestricted whole-task metric. This is a useful precision improvement, not a new safety guarantee.

The full eight-page inspection found no new material clipping or unreadable result figure/table. Page 8 still contains a short reference tail; this is a production-efficiency issue rather than a new validity defect. I do not infer an unverified venue page-limit violation. The uncompiled supplementary LaTeX source is not used as evidence of a compiled PDF; the reviewed native Word-export PDF is the actual deliverable.

## 4. Added numerical evidence

The three new records are same-command, observation-only accepted-substep replays of the existing unique new-confirmation case. I inspected their script, plan and results. Endpoint maximum discrepancy is **0.0** for all three. The recorded finer-segment minima are:

| Method | Original one-second margin (m) | Accepted-substep margin (m) |
| --- | ---: | ---: |
| R | −0.162187 | −0.162187 |
| L | −1.115322 | −1.117383 |
| S15 | 42.095555 | 42.094165 |

The reported maximum accepted step is approximately 0.1 s. These records corroborate the numerical labels. They do not create three new tasks, a new confidence interval, a swept-hull proof or an independent replication. The manuscript calls them numerical replay and retains the same primary sample size, which is correct. Round 01 had already independently established that the L negative margin occurred at an actual integration endpoint, so this extra check strengthens documentation without being necessary to rescue a doubtful primary label.

## 5. Verdict and work boundary

**Major Revision.** B3 is closed, B2 is appropriately retained, and the technical recovery portion of B1 is now supported by real artifacts and a documented successful check. The empirical case remains credible within its declared scope. The single material unresolved item is the authoritative inherited-asset attribution/access confirmation within B1. It remains a current publication-readiness gap rather than a promise whose future completion can be assumed.

The author can autonomously correct the supplement cross-reference and maintain the precise evidence wording. I do not identify a remaining mandatory new experiment, model change, benchmark expansion or broad rewrite. The next material step belongs to the human authors and asset providers. Repeating automated revision/review cycles while that evidence is unchanged should not be represented as progress toward closing B1 or used to manufacture a different verdict.

This is an internal simulated judgment about the current version, not a real CCDC decision. The unchanged verdict does not deny the substantial closure of the technical recovery and typesetting items. Once the narrowly specified human evidence arrives, the appropriate next review is a focused check of that record and final attribution/access text, not a reset of already verified results.

## 6. Persistent reviewer Memory update

- **Round 02 identity:** Markdown `9551e276…48305`, PDF `8bc6a517…0a5f8`, supplement `8e1e8708…0791d`; all eight PDF pages inspected.
- **Scientific identity:** main analysis, episode CSV, freeze, scenes, calibration, decision table and matched-prediction-quality records unchanged from Round 01. Five packaged scientific source hashes match the frozen record; all 72 recovered traces match originals.
- **New verified recovery facts:** 183 indexed archive and recovered-directory files match. Actual weights are present. The supplied log documents successful CausalModel construction/closure and worker import with the existing project Python environment. Independent review reconstructed stored-result summaries; no new navigation was executed by this reviewer.
- **B1 substatus:** local lineage, internal availability/recovery and overbroad reproducibility wording resolved. Authoritative creator/provider attribution and actual access authorization remain open and require human/source-owner evidence. Unknown training linkage must remain a limitation; full training logs/retraining are not added as a blanket requirement. II-A's S9 pointer should include S11–S12.
- **B2:** accepted limitation retained; no experimental escalation without a stronger claim or contrary evidence.
- **B3:** closed after actual PDF inspection and native accent/lower-limit inspection. Do not reopen because the alternative LaTeX source was not compiled.
- **Numerics:** three added same-command replays preserve endpoints and all labels; they are not new independent samples. Retain original 24-task denominator.
- **Source status:** local future-dated draft verified as such; original MathWorks author/date/license checked. Exact inherited port/checkpoint authorship and source equivalence are still not established by these records.
- **Review independence:** same-family internal simulation; no A/C opinions, responses or votes read. Prior author-audit exposure remains disclosed.
- **Next-round trigger:** actual human attribution/access evidence or a substantive scientific change. Mere repetition of unchanged caveats does not close B1. Current final verdict remains Major Revision for that bounded reason.
