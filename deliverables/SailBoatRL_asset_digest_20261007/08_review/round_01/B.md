# R13 Round 01 — Reviewer B

- Role: persistent independent internal simulated CCDC reviewer B; not a conference official.
- Requested model: `gpt-6-astra`; requested reasoning: `xhigh`. This report does not independently attest the runtime model identity.
- review_independence: `same-family`
- acceptance_status: `provisional` — internal simulation, not real acceptance.
- Reviewed version: immutable `review_round_01_input`.
- Final verdict: **Major Revision**

## 1. Review boundary and inspected evidence

I read the complete manuscript and Supplement S1–S9 and visually inspected all eight rendered PDF pages, including the equations, six figures, tables and reference spillover on page 8. The manuscript Markdown, PDF and supplement SHA256 hashes match VERSION.json: `f300ac8d…d35d`, `85377ed8…b026`, and `0dde6811…1a`, respectively.

I inspected the frozen manifests, calibration grid, episode CSV, analysis JSON, matched fixed-protocol records, substep records, same-state candidate table and asset/source hashes. I also read the authoritative server implementations of `scripts/run_r8.py`, `src/sailboat_routing/r8_model.py` and `r8_planner.py`, and the supplied low-order model and preparation/analysis scripts. All server actions were read-only. I did not rerun physics, train models or modify scientific artifacts.

Independence disclosure: I opened the supplied `CODE_FORMULA_AUDIT.md` as an implementation map. It contains a prior internal source/formula audit, including interpretive comments. This is exposure to an author-supplied technical assessment and is not full blinding to author claims. I disclosed that exposure to the coordinator and independently checked the material source/raw-record claims below. I did not read any other R13 reviewer report or verdict and do not infer other votes. The audit document's approval language is not evidence for my verdict.

Independent arithmetic checks:

- Reading the 72 original confirmation `trace.json` files gives 24 tasks per method and safe counts R/L/S15 = **19/23/24**. Episode CPU totals reproduce **270.677/378.445/2133.232 s**.
- Recomputing synchronized relative-segment minima directly from all 72 raw own/target trajectories, using the stated 85 m exclusion distance, yields **0.0 m maximum disagreement** with stored dynamic minima.
- Recomputing the 23 common-safe S15–L time differences from the episode CSV gives mean **+7 s**, maximum **+308 s**, minimum **−136 s**.
- For `r12new_mixed_pressure_1`, physical states, recorded references and commands match through 260 s. The pending command computed at 260 s also matches, and the physical endpoint at 261 s is equal. This supports the stated delivery timing rather than an immediate physical change at selection.
- The critical complete-task minima recompute as R **−0.162187 m at 392 s**, L **−1.115322 m at 402 s**, S15 **42.095555 m at 291 s**. Each minimum is at a segment endpoint, fraction 1.0. In particular, the L negative margin is not created solely by interpolating a one-second chord between safe endpoints.

The server lacks `rg`; a read-only `grep` fallback succeeded. Bibliographic primary sources and external ownership records were not independently audited in this pass. A local hash is not treated as proof of publication provenance.

## 2. Problem, assumptions, method and observed effect

The paper studies an execution-interface problem: a finite position reference that looks geometrically clear can produce an unsafe trajectory when passed to a recurrent sailing controller. The proposed supervisor reconstructs causal controller and actuator history, estimates a local constant wind vector, and predicts finite reference/hold/feedback-restoration protocols. It retains nominal feedback when its prediction meets a guard and otherwise ranks finitely many alternatives. No network is trained and no safety certificate is established.

The declared evaluation is a simulation with ideal computation, shared inherited own-vessel dynamics, noiseless current state and target observations, a known static map and one constant-velocity target. The target predictor is matched to target motion. The physical clock pauses during computation, while reference delivery retains the stated one-step ordering. These assumptions sharply limit deployment claims, but they are explicit and are acceptable as the scope of an applied simulation study.

The primary effect is narrow but real in the supplied records. Against a matched low-order reference-conditioned predictor, detailed prediction adds one safe completion on 24 frozen tasks, with no paired loss. Its median common-safe time difference is zero, mean is +7 s, and one endpoint case costs +308 s. Fixed-protocol diagnostics show much smaller position error for detailed prediction on the selected branches while retaining a 106 m adverse error. This supports existence and local usefulness of an execution-prediction effect in this inherited system; it does not establish general superiority, necessary model complexity, real-time safety or a reliable population success-rate advantage.

## 3. Strongest reasons to retain the paper

1. **The comparison is stronger than a geometric-only baseline.** L uses finite course-rate response, causal motion initialization and the same outer candidate/guard/hold/manager/selection machinery. Its parameters and 24 confirmation tasks were frozen. The inspected preparation script generates all 24 tasks before evaluation, with no outcome-based scene filtering in that script. I found no evidence of post-confirmation parameter tuning in the supplied records.
2. **The main task results and central decision contrast are directly checkable.** The raw-count, clearance and same-state checks above agree with the manuscript. The manuscript correctly avoids attributing the entire later rescue solely to the first reference change. The historical fixed-protocol example supplies a separate, appropriately scoped mechanism diagnostic.
3. **Negative evidence is prominent.** The 308 s detour, competitive low-order predictor, 106 m error, lack of a uniform error bound, and calls exceeding the 15 s period are not hidden. The four guards and historical groups are kept separate. NH and S60 are not mislabeled as prediction-free baselines.
4. **Statistical claims are calibrated to the design.** The task is the sampling unit; clustered windows and paired protocols are not treated as independent trials. The manuscript does not claim statistical superiority from one discordant L/S15 task. Additional significance testing is not required to sustain the current descriptive claim.
5. **A modest applied contribution is identifiable.** The specific command-delivery, history reconstruction and feedback-restoration interface is sufficiently concrete to be useful to a controls/simulation audience. I do not require a novel network, a theorem, a physical vessel or a complete COLREGs stack merely to qualify this declared contribution for consideration.

## 4. Most important issues

There are two open revision items below, B1 and B3. B2 records a consequential but already acknowledged evidence boundary; it is not an invented additional blocker.

### B1 — Inherited-system attribution and availability are still unresolved

- **Classification:** necessary evidence; publication-readiness blocker, not a demonstrated fatal validity error.
- **Location:** page 1, II-A; page 7, VI and Acknowledgment and Author Actions; Supplement S5 and S9.
- **Evidence:** the manuscript explicitly states that a verified original publication/training record and redistribution license have not been supplied. The assets are identified by local filenames and hashes. Generic SAC reference [5] does not attribute this specific recurrent-attention controller or checkpoint. Reference [8] is explicitly only background, not verified implementation provenance. The conclusion nevertheless describes the interface as “reproducible,” while S9 says that public readers lacking the private assets cannot reproduce the exact policy.
- **Impact:** the internal experiment is identifiable and its logged outcomes can be audited, but a reader cannot yet determine the correct credit for the central inherited controller/dynamics or the actual route to reproducing this specific system. This is not cured by repeating that provenance is unknown. It also prevents a clean assessment of which implementation work belongs to this paper versus its source. I am not asserting that the assets were used improperly; the relevant facts remain unverified.
- **Minimum actual remedy:** obtain an authoritative author/source-owner confirmation identifying the provider/creator and source/version of the dynamics, policy implementation, normalizer and checkpoint, and describing what use and access can actually be offered. Cite an appropriate published, thesis, repository, archived or explicitly unpublished source according to what that confirmation establishes. State the verified inherited-versus-new boundary. Supply a precise availability statement for code, parameters, weights and raw traces, with a concrete reviewer/reproduction access route when available. Change the unqualified “reproducible” conclusion to the exact supported claim, such as an auditable documented interface with reproduction conditional on access to the listed private assets.
- **Limits of this request:** no new policy training is required merely because full training logs are unavailable; report that limitation honestly. I am not imposing mandatory public redistribution or claiming a specific CCDC open-source rule. Private assets can be described as private. The necessary correction is credible attribution and an accurate, supportable access statement, not an invented license or an assumed equivalence to [8]. Author names/affiliations must also be completed, but those placeholders alone are not the reason for this verdict.

### B2 — The observed advantage is against this restricted predictor, not established necessity of detailed simulation

- **Classification:** accepted scope for the current wording; optional future evidence if the claim is expanded.
- **Location:** page 4, IV-B and Table I; pages 6–7, V-D and VI; Supplement S3 and S7.
- **Evidence:** L is calibrated on unchanged-reference 15 s windows but used for up to 60 s, including new side-reference proposals. It holds speed and heading–course offset constant and omits wind, recurrent policy, actuator and speed dynamics together. Its first interval extrapolates motion instead of evaluating the pending action. The six fixed-protocol source snapshots are development diagnostics, and one source has duplicate nominal/continuation paths. The paper discloses all of these limitations. L still achieves 23/24 safe completions and substantially lower computational cost.
- **Impact:** neither the one extra completion nor the 1.104/53.818 m branch-error comparison isolates a particular removed component or proves that detailed recurrent physics is generally needed. Under the current local and descriptive claims, that is an inference boundary rather than an invalid comparison. A stronger low-order predictor might close the remaining gap; the current evidence does not decide this.
- **Minimum actual remedy for this version:** retain the present restricted wording in the abstract, conclusion and any submission summary. Explicitly preserve that this is a full predictor replacement and that lower prediction error on selected protocols is not a population safety result. No further experiment is necessary merely to retain the present bounded claim.
- **If expanded later:** calibration/validation should cover the actual reference-switch/hold/restore protocol and horizon, using separate development data and a fresh frozen test set. Do not tune against the already inspected 24 tasks and relabel them as fresh confirmation. This extension is optional for the current manuscript and is not an acceptance condition in this review.

### B3 — The PDF damages notation in the method-defining equations

- **Classification:** prose-layout; mandatory production correction, not an experimental validity failure.
- **Location:** page 3, equations (3)–(5), especially the displayed minimum-margin definition and the predicted/real margin bound.
- **Evidence:** visual inspection shows detached or nearly invisible hat accents and crowded minimum-operator indices in (3). In (5), predicted-margin hats are not reliably distinguishable at the rendered size. Some adjacent inline symbolic text is also flattened/crowded. The Markdown mathematical source is clearer than the PDF. Figures and primary numerical tables are readable; this is a targeted equation-conversion problem, not wholesale figure illegibility.
- **Impact:** these equations define the scoring rule and distinguish predicted from actual clearance. A reader should not need the Markdown source to recover those distinctions.
- **Minimum actual remedy:** repair the equation conversion/typesetting and inspect the regenerated PDF at normal and enlarged scale. Ensure hats are attached to their symbols, both minimizations retain clear index placement, the two margin quantities in (5) are visually distinct, and equation numbers are separated from mathematical content. Compare the rendered expression against the unchanged mathematical source and code. No scientific algorithm change is needed.

## 5. Additional boundaries, not new rejection grounds

The common-safe time statistic is conditional on paired success and should remain labeled that way. The pressure-enriched strata do not estimate natural traffic frequency. The initial-target scoring set, short-prefix checks, early prediction stops and fixed-protocol comparisons have different domains and should remain distinguished. The existing accepted-substep checks concern four historical trajectories; they should not be renamed a universal continuous-safety validation. For the unique new L failure, the independently verified negative endpoint margin already rules out a chord-only false incursion under the recorded dynamics.

The noisy-sensor, target-maneuver, model-mismatch, multiple-vessel, real-time-computation and full maritime-rule questions are legitimate future work. I do not require them for this explicitly scoped ideal-compute, single-target simulation manuscript. The lengthy page-8 reference spillover could be tightened during production; I have not independently verified a current venue page-limit rule and do not classify it as a violation.

## 6. Verdict and unresolved items

**Major Revision.** The current experiment supports a technically coherent, modest simulation paper. I found no fatal arithmetic, outcome-filtering or clearance-evaluation defect in the checked primary comparison. The serious unresolved item is B1: publication-critical inherited-system attribution and a defensible availability/reproducibility statement need actual author/source evidence, rather than another caveat or a promise. B3 also requires a PDF correction. B2 is a retained claim boundary, not a requirement to launch a new experimental program.

This verdict evaluates the current supplied version and its evidence, not the amount of author effort. It is not a prediction of an actual CCDC decision. Successful closure of B1 and B3 would permit reconsideration without demanding a new network, physical experiment or broad benchmark expansion.

## 7. Persistent reviewer Memory update

- **Version identity:** R13 Round 01 is the frozen manuscript/PDF/supplement identified above. R13's new same-state analysis is log-only; the primary 24 outcomes are R12 outcomes.
- **Retain as verified:** all 72 raw confirmation dynamic minima independently recompute exactly; R/L/S15 = 19/23/24; common-safe S15–L mean +7 s on 23 tasks; the unique L failure occurs at an actual integration endpoint; t=260 action ordering and t=261 endpoint equality are consistent with delayed reference effect.
- **Retain as bounded evidence:** selected fixed-protocol fidelity benefit, 106 m adverse error, 308 s endpoint cost, competitive L, task-level sampling, no general safety or real-time guarantee. Do not pool historical overlap or count twelve protocols as twelve independent source states.
- **B1 status:** unresolved; needs authoritative attribution/access confirmation and correctly qualified reproducibility text. A hash list or repetition of “unknown” alone does not close it. Public weight release itself is not mandated by this review.
- **B2 status:** accepted boundary; reopening requires a stronger claim or new evidence, not simply another review round. No demanded extra experiment for the current local descriptive claim.
- **B3 status:** unresolved; requires visually verified equation rendering in the actual replacement PDF.
- **Review-process memory:** exposed to the supplied source/formula audit as author evidence; no other R13 reviewer reports/votes read. Independent primary-record checks, rather than that audit's judgments, ground this report.
- **Next-round criterion:** verify B1 evidence and the concrete final availability/attribution language; recheck corrected formulas and confirm numerical claims/algorithm identity remain unchanged. Do not reset solved statistical and timing issues without contrary evidence.
