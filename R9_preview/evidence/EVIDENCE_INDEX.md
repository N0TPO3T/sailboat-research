# R9 evidence and reproduction index

Canonical reports: docs/R9_METHOD_NOTE.md, docs/R9_RESEARCH_REPORT.md; paper/ccdc/R9_POSITIONING.md. R3draft unchanged.

- plan.json / authorization prompt: budget and scope; resource_receipt.json: actual recorded use, asset hashes; profile_hardware.txt: hardware and numerical threads.
- freeze_design.md / freeze.json / frozen_configs.json: selection, scope, immutable source/config hashes before new test outcomes.
- profile.json / replay_equivalence.json / profile_summary.json:6saved states, instrumentedvsnormal timing, exact candidate path equality. full_replay_equivalence.json:4whole ideal task state/action matches.
- development.json + development/:20original development traces; source snapshot retained. development_caveats.md marks unfair initial reactive config and preliminary instrumentation.
- development2.json + development2/:12corrected fair reactive/optimized60/wait-aware cases. development3/:8fast15andignore_wait cases. All old material, no unseen claim.
- confirmation.json + confirmation/:12predefined new1km scenes×5methods. long_confirmation/:new3km/5km×5methods. No discarded test instances.
- sensitivity/:activated+15deg turn and5sadditional waiting; static_regression/:2oldstatic×2methods.
- Each trace.json contains true own/target synchronized history, commands, changes, public observations, predictions, timeline and control timing. Each job.json is runnable configuration; row.json is original outcome. Each batch has source/,provenance.json,rows.json,completion.json.
- analysis.json / all_rows.csv / family_analysis.json / paired_identities.json:outcome and paired cost with failures preserved.
- timing_analysis.json:compute/age/control distributions and executed-prefix predictions. guard_fallbacks.json:5new-short fallback selections; mechanism_case.json:same-state t150 discrimination.
- final_audit.json:99postfix episodes synchronous distance/timing/reference/control coverage checks; protocol_test.json:deterministic queue/deadline/age cases.
- review-stage/:finite same-family/provisional design/implementation/claim checks, no scores or new experimental authority.
- figures/*.png,*.svg and gallery.html:actual1/3/5km, timing, costs, adverse examples and false-safe sensitivity; source scripts/plot_r9.py and raw tables/logs.

Fresh output reproduction (existing environment):
```
.venv/bin/python scripts/reproduce_r9.py --manifest runs/r9_timing_20261005T085308Z/confirmation.json --out runs/r9_reproduction_new --variant main
```
Original records are never overwritten. Measured-delay methods may take different event branches under different host timings; report hardware/load, do not claim bitwise wall-time replay. Fixed-slot sources and original per-event timing remain available.
