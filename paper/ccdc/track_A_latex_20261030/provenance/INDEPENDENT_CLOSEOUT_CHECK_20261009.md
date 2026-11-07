# Independent bounded closeout check — 2026-10-09

The requested M1–M4 changes and minor editorial items are closed in the final artifacts identified below. One Algorithm 1 wording-order ambiguity was found, corrected by the author, and checked once after export. No other factual or presentation error was identified within this bounded closeout. Corresponding-author, contact-email and applicable-funding metadata remain explicitly pending.

This check was performed by a separate same-family agent with a fresh task context. It is not an external human review, cross-model certification, acceptance recommendation or score. The scope was the supplied closeout prompt and independent review, not a new scientific review.

## Final artifact identity

| File | SHA256 |
| --- | --- |
| manuscript.pdf | `2c93256041b157b0de6d9728c6a77a2e3dfdb8354a3b0a4052b44d7e0922ddc4` |
| manuscript.md | `ea54b9fbf892a3d309503f808b69193b059b791e127479d558f68e173db14f2f` |
| SUPPLEMENT.md | `dfcab9ee52b4d9fb465faed3cd32f3d1165cacc33e4d5f1e0dd62a74cd468fd6` |
| CLOSEOUT_RESPONSE.md | `fec16366ac92451a8ac89357a6a9e1d87ce9f5b3ce7b9f82a1624d743734948d` |
| evidence/episodes.csv | `b41dcb4e1fc416749e17f68566748ce9240cbd6d68b8052cdd1971e3fb407568` |

The initial author PDF supplied to this checker had SHA256 `9eb491b45fa37357ac72e4971c7847753c8960a5c8c98986a6737664252002a2`. The final PDF above incorporates the single wording correction described below. The historical starting edition remains the separate `track_A_aris_20261008` directory.

## What was actually inspected

- Read the full manuscript Markdown, supplement, closeout response, README, author checklist and PAIRED_TIME_CHECK.json. Read both supplied request/review documents under provenance: SailBoatRL_Track_A_ARIS_Closeout_Prompt.md and CCDC_Track_A_Independent_Review_20261008.md.
- Extracted text and page metadata from the actual PDF using bundled Python/pypdf. Visually inspected every page, including all figures, tables, equations and references, using checkpage-1.png through checkpage-8.png. Repeated the visual inspection after the single correction. Independently rendered every final PDF page with Poppler into memory at a 1500-pixel long edge; all eight images matched the supplied final page PNGs pixel-for-pixel. The PDF has eight A4 pages.
- Inspected Fig. 1 PNG, parsed its editable SVG text, and read draw_interface.py. Compared its paths, branch labels, history separation and timing against the caption, Algorithm 1 and Supplement S2.
- Independently read and aggregated evidence/episodes.csv with Python standard-library csv and Decimal, without running the author's output-writing script. Compared every accepted pair and the excluded pair with PAIRED_TIME_CHECK.json. Read check_paired_times.py to confirm its portable input path and stated filtering.
- Compared all 44 evidence files and all 18 non-interface figure files byte-for-byte with the previous author directory. Compared the six displayed Markdown equation blocks, all numerical table rows and ten bibliography entries with that edition. Inspected Word XML for styles, page margins, table/equation content and direct font-size settings; the template, styles, margins and existing size settings were preserved.
- Read the provenance/version_check.json receipt for the recorded local/server distinction. Did not make a new server connection. Verified the separately available R13_REPRODUCTION_internal.zip hash as `d0fdc80b40b5252ced7dfd15370a30e092b3232cc1b7ef65e131bedac50ce640`, matching S5/README, and read its src/sailboat_routing/r8_planner.py directly from the ZIP for the bounded control-order check. Did not extract or execute the simulator.

## Request-by-request result

| Criterion | Result and checked location |
| --- | --- |
| M1: measure observed trade-offs | Closed. PDF p. 1 abstract/introduction and p. 8 conclusion frame the question as decision, safety, navigation-time and computation trade-offs. They do not establish a generally worthwhile cost, a common utility score or an online predictor-switching rule. The positive completion result and adverse costs remain. |
| M2: design, consistency and integrated effects | Closed. The p. 1 contribution paragraph separates the reference protocol, covered execution-correspondence checks and integrated-predictor comparison. Sections III-A and V-D/S2/S4 distinguish memory replay from command/setpoint accumulation, and twelve physical prefixes from six selected 15-second position continuations. No independent safety benefit is assigned to an unisolated reconstruction component. Attribution of inherited assets and GVO remains. |
| M3: paired time distribution | Closed. PDF p. 5 and S5 agree with the independent exact-precision calculation below: 23 common-safe pairs, 5 faster/13 equal/5 slower, −136 to +308 s, mean +7 s and median 0. Equal time is explicitly distinguished from equal trajectories. The unsafe L arrival is excluded. |
| M4: nominal-first prediction | Closed after one wording repair. Fig. 1 on p. 2 explicitly tests nominal validity/integration/guard before alternatives. Its pass branch skips alternative predictions; its fail branch restores and predicts continuation/four sides before ranking/fallback. Separate memory/setpoint operations, isolated branch history, actual-feedback-only history updates, pending old action, t+1 delivery and t+1→t+2 first effect are present. Algorithm 1 on p. 3 now states the correct incumbent-clearing order. |
| Abstract density and adverse evidence | Closed. The abstract retains 19/23/24, the eight combined-pressure cases, +7/+308 s common-safe costs and paused physical time. Detailed CPU values and the 106.064 m error remain in Results; computation cost and the adverse error remain in Discussion. No small-cost generalization was introduced. |
| Algorithm, timers and units | Closed. Inputs/outputs and branches are readable on p. 3. until, next_plan, H, P and ρ are defined. Equation (4)'s 20 and 10 coefficients are explicitly metres. Feasible-alternative cancellation and tied-margin fallback relevance remain distinct. |
| Supplement numbering and references | Closed. The four supplement tables have unique Table S1–S4 labels. The supplement has no added figures and explicitly identifies Fig. 1–6 as main-paper figures. Historical groups retain separate identities and denominators. Main-paper supplement references point to the corresponding sections. |
| Pagination and final rendering | Closed. All eight final pages are readable at the inspected resolution; no clipping, overlapping text, missing symbols or split reference entries were observed. All ten references are on p. 8 and no entry crosses columns. The PDF font resources are embedded; this is not conference-system certification. |
| Reproduction access | Closed as a disclosure/access-description request. README, p. 8 availability text and S5/S11 distinguish CSV/log reaggregation from the separate complete archive, identify what can be rerun with that archive and give the editorial/private-transfer route under existing permission. They do not claim a public download or attached weights. No author-machine sibling path is required as the external entry point. Contact metadata is honestly pending. Actual future delivery was not tested. |
| Authors and pending metadata | Closed as an editorial request, with the disclosed metadata still pending. Confirmed author order and affiliations are retained. AUTHOR_CHECKLIST_ZH.md requests only corresponding author, email and applicable funding; it does not invent these or claim immediate submission readiness. Its no-server-sync statement matches the supplied receipt; current server state was not independently queried by this checker. |
| Frozen evidence and numerical figures | Closed for artifact preservation. All 44 evidence files and 18 non-Fig. 1 figure files are byte-identical to the prior author edition. Only Fig. 1's SVG/PDF/PNG changed among figure files. The six equation blocks, three numerical tables and ten bibliography entries are unchanged. No navigation experiment, training, recalibration, guard search or raw-trajectory recomputation was executed by this checker. |

## Independent CSV confirmation

The calculation selected exactly stage=confirmation, checked unique scene_id/variant keys, and required all three variants for every scene. It produced 72 records and 24 scenes. R=reactive, L=simple and S15=sampled.

For each scene, inclusion required both sampled.success and simple.success to equal the literal True field. The difference was Decimal(sampled.time_s) minus Decimal(simple.time_s), using the original CSV strings and no tolerance or rounding for equality.

| Quantity | Independently obtained result |
| --- | --- |
| Safe completions R/L/S15 | 19/23/24 |
| Combined-pressure safe completions, n=8 | 3/7/8 |
| Other four families | 4/4/4 in each family; sixteen safe tasks for every method |
| Common-safe S15/L pairs | 23 |
| S15 faster/equal/slower | 5/13/5 |
| Sum of S15−L time differences | 161 s |
| Minimum/maximum | −136/+308 s |
| Mean/median | +7/0 s |
| Excluded unsafe arrival | r12new_mixed_pressure_1: S15 success=True, L success=False, L arrived=True |
| Rounded cumulative episode CPU R/L/S15 | 270.68/378.44/2133.23 s |

Every one of the 23 included scene IDs, original time strings and exact differences matches PAIRED_TIME_CHECK.json. The single exclusion also matches. Independent R-relative common-safe calculations reproduce Table I's n=19, L mean +6.63 s/max +69 s, S15 mean +25.16 s/max +308 s, and both zero medians. These calculations confirm the supplied aggregate evidence; they do not independently validate raw trajectories.

## Single correction and final recheck

The initial checked PDF's Algorithm 1 line 2 said “Call nominal manager; clear incumbent if hold expired.” Read sequentially, this could describe a different nominal input: the frozen implementation at r8_planner.py lines 39–41 first resolves the incumbent to None after a held interval, then calls the nominal manager. Supplement S2 already described the cleared-incumbent call correctly.

The author changed the line to “Clear incumbent if hold expired; call nominal manager.” The checker confirmed this wording in the regenerated PDF p. 3 and final Markdown, then inspected all eight final pages and reconfirmed their pixel identity to the actual final PDF. The final response records this correction. No second issue/revision cycle was opened.

There is no remaining closeout-content correction identified by this check. The previously disclosed scientific limitations remain limitations, and were not converted into new experimental requirements. The remaining submission-metadata fields still require author input. ZIP assembly, submission-system validation, fresh server synchronization, native LaTeX compilation and a full simulator rerun are outside this check's verified work.
