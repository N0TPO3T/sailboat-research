"""Read-only source check. No navigation, model inference, or source mutation.
Usage: python check_existing_evidence.py --project-root PATH
Prints JSON; redirect to a new receipt file if desired.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--project-root', type=Path, required=True)
root = p.parse_args().project_root.resolve()
sources = {
    'journal_14d': root / 'main.pdf',
    'thesis_131_pages': root.parent / 'sailboat-research/大论文-Final.pdf',
    'thesis_101_pages': root.parent / 'sailboat-research/师兄大论文.pdf',
    'inherited_protocol': root / 'docs/OBSTACLE_PROTOCOL.md',
    'checkpoint_identity': root / 'docs/obstacle_candidate_identity.json',
    'a_results': root / 'runs/a_fair_20261105/RESULTS_ZH.md',
    'episodes': root / 'runs/a_fair_20261105/episodes.csv',
    'original_environment': root / 'runs/a_fair_20261105/frozen/third_party/obstacle_candidate/sailboat_s14_obst_V3.py',
    'observation_adapter': root / 'runs/a_fair_20261105/frozen/src/sailboat_routing/r6_controller.py',
}
manifest = {key: {'path': str(path), 'exists': path.is_file(),
                 'sha256': hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None}
            for key, path in sources.items()}
rows = list(csv.DictReader(sources['episodes'].open(encoding='utf-8')))
new = [r for r in rows if r['stage'] != 'old_Lstar']
assert len(new) == 48
summary = {}
for variant in sorted({r['variant'] for r in new}):
    rr = [r for r in new if r['variant'] == variant]
    assert len(rr) == 16
    summary[variant] = {
        'n': len(rr), 'successes': sum(r['success'].lower() == 'true' for r in rr),
        'max_planning_seconds': max(float(r['max_planning_seconds']) for r in rr),
        'max_reencoding_seconds': max(float(r['max_reencoding_seconds']) for r in rr),
        'episodes_reencoding_over_one_second': sum(float(r['max_reencoding_seconds']) > 1 for r in rr),
        'failures': [{k: r[k] for k in ['scene_id', 'reason', 'min_dynamic_margin', 'min_entity_margin']}
                     for r in rr if r['success'].lower() != 'true'],
    }
print(json.dumps({'source_manifest': manifest, 'existing_new_batch_summary': summary,
                  'new_navigation_runs': 0, 'thesis_raw_results_verified': False,
                  'scope': 'read-only local evidence; no server synchronization'}, ensure_ascii=False, indent=2))
