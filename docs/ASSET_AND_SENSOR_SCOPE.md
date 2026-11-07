# B inherited assets and information boundary

This workspace contains a byte-tracked copy of the existing physics/runtime sources, not a newly licensed public release. Explicit user confirmation authorizes research use and provision of inherited reproduction materials to editors/reviewers. Original copyright and third-party conditions remain. No new code/weight license is assigned.

Related source research: Chao Yang et al., Learning to sail without wind information: reinforcement learning-based control for unmanned sailing vessels under partial observability, Applied Ocean Research175(2026)105246, doi:10.1016/j.apor.2026.105246. The journal14D and inherited18D model assets are distinct. B does not load either checkpoint or normalizer: only inherited dynamics/actuator/runtime are used. Thus B is a conventional-control adaptation study, not an RL model improvement.

The independent snapshot was made from the existing actual worktree, including required untracked dependencies. docs/INITIAL_SNAPSHOT.json records original source identity and hashes; scripts/station.py is the new B runner. Runtime may be read-only reused from the original .venv, but Python scientific source imports resolve within B/third_party and B/src. Source paths are captured in every run. Caches/temp/results belong to B. Existing main and A are not imported as mutable project source or modified.

Current ideal local wind is intentionally exposed to all B comparators. This is a different task/sensor setting from A. The controller never calls future field samples. Environment alone owns SyntheticWindField and updates the current measured value at physical step boundaries.

The inherited physical mass is25900kg (third_party/senior/sailboat_s14.py), not the300kg example in Viel2018. Classical guidance comparison here cannot reproduce another boat's theoretical assumptions or experimental outcome.
