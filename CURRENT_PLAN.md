# Current Plan — R7 dynamic vessel avoidance

R7: low-speed moving-vessel collision avoidance and continuous mission completion. Static-only, fixed low-level/18D, old memory and timing restrictions are superseded. Controller, representation, causal memory, reference timing and training may change; preserve old assets/results, shared-resource permissions, causal inputs and common evaluation. No automatic push.

Budget: shared24h,4 single-thread CPU experiment workers; GPU requires actual assignment (max1/12GPUh). Existing CPU env warm-reused; do not build services.
Run: runs/r7_dynamic_20261005T033700Z/plan.json

Objective: evidenced low-speed dynamic avoidance with mission resumption; decide main contribution versus extension versus defer.
Next: verify synchronization/history/safety, source CPA/encounter supervision and short-horizon candidate mechanisms; measure existing response, implement current-position R6 and causal relative-motion alternative; develop then freeze/new-instance confirm, static and long-range checks; real synchronized tracks and reports.
Unknown: controller response adequacy, prediction benefit and unnecessary-detour costs. Training is permitted, not required.
