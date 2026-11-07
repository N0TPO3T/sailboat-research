# Internal simulated CCDC review — Reviewer A — Round 01

- Reviewer role: independent internal simulation, method/control/formula/execution emphasis; not a conference official.
- Requested model / reasoning: gpt-6-astra / xhigh. This records the requested configuration, not independently verifiable backend identity.
- review_independence: same-family
- acceptance_status: provisional (internal simulation, not real conference acceptance)
- Input: immutable `review_round_01_input/`, R13 text over unchanged frozen R12 main outcomes.
- Verdict: Major Revision

## Assessment

The technical result is credible within the declared ideal-compute, noiseless-observation, single constant-velocity target simulation. I found no fatal mathematical or execution-timing error in the inspected supervisor and predictor. The contribution is a modest but potentially publishable control-engineering integration: compare reference-and-hold protocols through a particular recurrent sailing controller, reconstruct the relevant causal execution state, and demonstrate both useful interventions and their costs. It does not need a new network, a new theorem, a physical boat, or full COLREGs compliance to be considered in this declared CCDC scope.

The current version is not yet ready for publication because the inherited system at the center of the study still lacks a verified scholarly source/asset attribution record. This is expressly acknowledged, which is preferable to incorrect attribution, but acknowledgment alone does not complete the record. Two smaller reporting corrections would improve the interpretability of the finite simulation evidence. This verdict does not allege fabricated results, require public release as an assumed venue rule, or discount completed verification.

The problem is that a clear waypoint chord need not equal the trajectory executed by the fixed sailing controller. Inputs include observed state, actual command/observation history, a full static map and current target position/velocity; the predictor has no actual future wind or target schedule. A local wind fit drives independent copies of the inherited policy and dynamics. Nominal feedback is tested first; otherwise finite continuation/side protocols are ranked under a predicted-clearance guard, with an explicitly uncertified fallback. A selected change follows the pending old-reference action and first affects the next physical interval. The 24 frozen tasks give R/L/S15 safe completions of 19/23/24. The one additional S15 completion over L accompanies +7 s mean time on their 23 common-safe tasks, a +308 s adverse task and much more computation. The proper conclusion is conditional usefulness for this implementation and test set, not a reliable population safety advantage or general efficiency dominance.

## Evidence read and independent checks

I read the full `manuscript.md`, all sections S1–S9 of `SUPPLEMENT.md`, and inspected all eight rendered PDF pages. I checked the manuscript, PDF and supplement SHA256 values against `VERSION.json`; all three match. PDF hash: `85377ed8573e6880541046c81a3db96a9c11a0a2e746c35f078f35b8ef64b026`.

I inspected the supplied source/evidence index, freeze/calibration records, confirmation generator/manifest, analysis and case records, all twelve compact fixed-protocol comparisons, numerical-substep records, and the fixed-branch implementation. Through read-only SSH I inspected the authoritative `r8_model.py`, `r8_planner.py`, `run_r8.py`, `r7_dynamic.py`, `frames.py`, simulator isolation/continuity wrappers, and the low-order model source. I did not run a navigation experiment or modify scientific files.

Independent log arithmetic on all 72 authoritative confirmation traces reproduced every dynamic minimum from synchronized actual boat/target positions and reproduced every safe-completion flag (with the artifact's null static margin interpreted as no static obstacle, verified against the scene). It reproduced the 19/23/24 counts, episode CPU totals, and S15−L common-safe mean 7 s, median 0 s, maximum 308 s. The entire recorded trajectory prefixes of S15 and L through 260 s in `r12new_mixed_pressure_1` are exactly equal. Their recorded candidate predictions reproduce the manuscript's 11.893/59.832 m nominal discrepancy and S15's selected `turn90`. All five scientific source hashes in the R12 freeze record match the current inspected server files.

Independence disclosure: I opened supplied `CODE_FORMULA_AUDIT.md` expecting a source map and found an earlier author/source-audit narrative containing technical opinions. I have not read any R13 reviewer opinion or vote. The parent confirmed that this is supplied source-audit material, not an R13 review. My code/timing/result conclusions above come from direct source/log inspection; I do not count the source audit as an independent endorsement. This exposure prevents describing the review as entirely blind to earlier technical discussion.

## Strongest reasons to retain the paper

1. **The control interface is specified and matches inspected code.** `run_r8.py:39–76`, `r8_model.py:62–90` and `r8_planner.py:38–73` support old-action-first timing, next-step delivery, state/history reconstruction, post-nominal manager cloning, nominal-first selection and the finite fallback. I did not find future-information leakage in these interfaces. The predicted tail runs nominal management rather than silently receiving later online-search decisions.
2. **The comparison is substantially more informative than a geometric-only baseline.** L retains the supervisor and actual physical execution, changes the predictor, and is calibrated before frozen confirmation. Its approximation limitations are stated. The manuscript retains L's competitiveness and does not pretend the full replacement isolates only ODE order.
3. **The evidence has meaningful negative controls and limits.** Historical overlap is not pooled; the 106 m detailed prediction error, the 308 s detour, all four guard values, failures after eventual arrival, unequal planning work, and computation beyond the nominal review period remain visible. Common-prefix and fixed-protocol evidence are distinguished. The substep checks support their specific historical incursion labels without being promoted to a hull-safety proof.
4. **The mathematics is appropriately conditional.** Equation (1) is the synchronized relative-segment minimizer. The wind residual is an approximate inverse-dynamics objective, not a claimed identifiable wind estimator. Equation (5)'s triangle-inequality reasoning is correct on the stated common domain, and the manuscript explicitly lacks the error bound needed for certification.

## Material issues, ranked

### A1 — Establish the inherited-system source and attribution record

- Classification: **necessary evidence**; publication-blocking in the current version, not a demonstrated fatal validity error.
- Location: p. 1, II-A; p. 7, VI and Acknowledgment; Supplement S5/S9.
- Evidence: the manuscript explicitly says the original publication/training record and redistribution license have not been supplied. The source/asset hashes identify bytes and the code identifies the implemented 18-input Actor and dynamics, but neither establishes their original authorship, scholarly identity, or the relationship between the checkpoint and an attributed controller. SAC [5] and yacht modeling [8] are explicitly only background. The conclusion still calls the interface reproducible, while S9 correctly limits exact-policy reproduction to recipients with private assets.
- Impact: readers cannot yet place the inherited controller/dynamics contribution relative to the current paper or reliably obtain/identify the exact foundational system. Unknown original training conditions also limit what “new tasks” means beyond being newly generated for this supervisor evaluation. The numerical supervisor comparison remains internally interpretable, but the publication attribution and reproducibility boundary are incomplete.
- Minimum actual remedy: provide a verified asset/source record identifying the original creator or owning project, the actual source document/repository/version if one exists, the precise Actor/normalizer/dynamics identity, what is inherited versus changed here, and the concrete access/release status. Supply only training facts that can be verified; if parts of the training record are unavailable, keep them explicitly unknown and state that new confirmation means new supervisor-evaluation scenes, not a certified holdout from policy training. Correct/complete the corresponding citation or acknowledgment. Align “reproducible” with the access actually supplied, for example an executable artifact for authorized recipients or a documented restricted-access reconstruction. I am **not** requiring a public license as an inferred CCDC rule, full retraining, or an invented source attribution. If the author cannot establish the basic origin/permission/attribution record, this item remains unresolved; more simulated success cases do not repair it.

### A2 — Quantify the actual encounter and wind domain, including the pressure-family confounding

- Classification: **prose-layout / experimental reporting**; correction from existing evidence, not a demand for new experiments.
- Location: pp. 3–4, IV-A; p. 5, V-A/B; Supplement S6/S8.
- Evidence: the manuscript gives family counts and calls the target low-speed, but does not quantify target speed or summarize how a pressure scene differs from an ordinary crossing. `prepare_r12_confirmation.py` fixes all 24 new tasks at 1 km, draws ordinary-family base wind directions from 45–80 degrees and pressure-family directions from 115–135 degrees, and adds the pressure family's static circle at (850,300) m with entity radius 45 m. General target speeds are drawn from 0.65–0.95 m/s, except endpoint speeds from 0.8–1.0 m/s; the realized new set is about 0.679–0.976 m/s. Every new completion gain occurs in that pressure family.
- Impact: without these few domain facts in the paper, “pressure-enriched” can be read as enrichment only in traffic geometry, although wind direction and static geometry also change. A reader cannot assess which sailing regime actually provides the evidence for detailed prediction. This does not invalidate the paired within-task comparisons, since all methods share each scene.
- Minimum actual remedy: add a compact scene-envelope table or paragraph reporting 1 km for new confirmation, target speed/generator ranges, base-wind direction ranges by family, the pressure static obstacle, and the family construction rule or a precise supplement pointer. Say that the pressure family jointly changes encounter geometry, wind direction and static context. Do not attribute all observed gains specifically to traffic severity or wind without a separate factor-isolating experiment. No such new experiment is needed for the current conditional implementation claim.

### A3 — Make the common-domain clearance bound use explicit local notation

- Classification: **prose-layout / mathematical notation**; minor correction, not an incorrect triangle inequality.
- Location: p. 2, definition of `m_real`; p. 3, equations (3) and (5); Supplement S1.
- Evidence: II-B first defines `m_real` as the minimum over the whole executed task. Equation (5) then uses the same symbol for comparison on a shared finite protocol/time/obstacle domain. The preceding qualification makes the intended theorem recoverable, but the change in domain is implicit. In the rendered equation (3), both minimum index sets also appear crowded inline rather than cleanly placed as operator limits.
- Impact: the whole-voyage metric must not be mistaken for the common-domain minimum that the finite-horizon error bound controls. The no-certificate prose already prevents the strongest overclaim, so this is a precision/readability issue.
- Minimum actual remedy: write the bound with explicit restricted quantities, such as `m_real(gamma; T, O)` and `m_hat(gamma; T, O)`, define both using the same T and O, and reserve the original `m_real` for whole-task evaluation. Re-render equation (3) with unambiguous minimum limits. No new proof or empirical bound is requested.

## Accepted scope and optional future work

Ideal computation, one constant-velocity target, noiseless state/velocity observations, circular proxies, the same inherited plant family, and no formal safe fallback are accepted declared scope. They are not independently sufficient reasons to reject this simulation paper. The 24-task sample and selected development snapshots do not support a population safety advantage; the present text correctly says so. A novel neural architecture, formal certificate, hardware trial and complete COLREGs system are not required repairs.

The 15 s unchanged-reference calibration of L does not establish its quality for 60 s side-reference protocols. The manuscript already discloses that limitation and frames the result against this particular L. Better long-horizon/reference-switch calibration or a second simple predictor would be useful **optional future** work if stronger general superiority were claimed. I do not require that experiment to substantiate the existing descriptive comparison, and I do not treat the one added completion as statistically established superiority.

## Unresolved items and decision boundary

A1 remains necessary evidence. A2 and A3 can be corrected using the current frozen artifacts and text. There is no identified fatal validity defect and no requirement here to rerun the 72 main episodes. Original creator/source identity, available training provenance, release/access rights and the final author/attribution record remain unknown to this reviewer. I did not independently audit every bibliography item or claim that hashes establish legal permission.

For a later round, I will check the actual A1 evidence rather than accept a promise to supply it. If basic origin/attribution and the real artifact-access boundary are resolved, the bounded technical contribution and verified outcomes provide a credible basis for publication consideration within this CCDC simulation scope. The verdict is on the current version, not on author effort or future promises.

## Persistent reviewer memory update

- Frozen identity: R13 manuscript SHA256 `f300ac8d2c6a781832ec810b72be2ecb21e8ed3066cd2b2644c68a3e8b15435d`; unchanged R12 24-task confirmation is reused, not newly rerun in R13.
- Verified this round: all eight pages inspected; whole manuscript/supplement read; 72 raw-trace dynamic minima and safe labels independently recomputed; counts 19/23/24; S15−L 23 common-safe mean +7 s/max +308 s; exact entire prefix equality through 260 s; all five frozen scientific source hashes match.
- Preserve: source isolation, old-action-first delivery, hold/release semantics, common-domain error qualification, no safety certificate, negative results, separate historical groups and task-level sample unit.
- Open: A1 provenance/attribution/access record; A2 scene-domain summary; A3 common-domain notation.
- Do not re-demand: a new network/theorem, physical deployment, COLREGs completeness, public release under an unverified venue rule, or repeated main experiments merely because the method has limitations already accepted in scope.
- Independence limit: supplied earlier source-audit narrative was read; no R13 other-reviewer opinion or vote was read or inferred.

Final verdict: Major Revision
