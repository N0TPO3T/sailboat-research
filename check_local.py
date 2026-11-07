from pathlib import Path
import json,hashlib
p=Path(r'C:/Users/74095/hs/SailBoat/sailboat-track-b')
f=p/'analysis_v2/gallery.html';s=f.read_text(encoding='utf-8').replace('<h2>06_recovery_all_tasks</h2>','<h2>06 — All predefined tasks</h2><p>Release vs matched luff: 3 wins, 8 ties, 1 loss; mean +0.4931 percentage points and +3.9823 rad actuator variation. All eight inside-start tasks tie. Four entry differences: -19, +28, +32, +30 seconds inside.</p>').replace('<h2>08_recovery_mechanism</h2>','<h2>08 — Actual actuator and recovery timeline</h2><p>Recovery exits at t=25 s while surge velocity is still negative. Exit means reaching the beam/downwind heading half-plane, not restored forward speed. The signed 90-degree command is an ideal angle-positioning interface, not validated passive sheet release.</p>').replace('<h2>09_recovery_counterexample</h2>','<h2>09 — Unfavorable matched comparison</h2><p>Release spends 19 seconds less inside than matched luff. Initial entry time is included in the longest-outside metric.</p>');f.write_text(s,encoding='utf-8')
f=p/'package_final.py';s=f.read_text(encoding='utf-8').replace("'figures','reviews']","'figures','reviews','.aris/traces/research-review/2026-10-08_ab']");f.write_text(s,encoding='utf-8')
d=json.loads((p/'RESULTS_INDEX.json').read_text(encoding='utf-8'));n=0
for b in d:
 for x in b['files']:
  assert hashlib.sha256((p/x['path']).read_bytes()).hexdigest()==x['sha256'],x['path'];n+=1
(p/'docs/LOCAL_SYNC_CHECK.json').write_text(json.dumps({'raw_files_checked':n,'all_hashes_match':True,'archive_sha256':'84a377488768949f6361b893d686c4f15566116fafdb33030b1f43a533b897d4','truncated_first_transfer':'detected and replaced; not delivered'},indent=2),encoding='utf-8')
print(n)
