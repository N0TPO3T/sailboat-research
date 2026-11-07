"""Small review bundle; full checkpoint/replay and all raw runs remain separate."""
from pathlib import Path
import zipfile,json
ROOT=Path(__file__).resolve().parents[1];run=ROOT/'runs/round2_20261011'
summary=json.loads((run/'confirmation50/summary.json').read_text());assert summary['physical_rollouts']==350
paths=[]
for name in ('REPORT_ROUND2_ZH.md','HANDOFF.md','README.md','requirements.lock'):paths.append(ROOT/name)
for folder in ('src','scripts','configs'):
    paths.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
for name in ('PROTOCOL.md','COMMANDS.md','freeze.json','implementation_check.json','targeted_checks.json'):
    paths.append(run/name)
for name in ('DIAGNOSIS_ZH.md','key_cases.json','round1_pairs.json','historical_checkpoint.json'):
    paths.append(run/'diagnosis'/name)
for name in ('protocol.json','results.jsonl'):paths.append(run/'diagnosis/branches'/name)
paths.extend((run/'diagnosis').glob('*.png'))
for seed in (20261011,20261012):
    for name in ('learning.jsonl','development.jsonl','initialization.json','config.json','complete.json','takeover_coverage.json'):
        paths.append(run/f'train_{seed}'/name)
    for name in ('selection.json','checkpoint_verification.json'):
        paths.append(ROOT/f'checkpoints/round2/{seed}'/name)
    folder=run/f'confirmation50/seed_{seed}'
    for name in ('summary.json','episodes.csv','pairs.csv','paired_scenes.csv','pairs.json','case_events.json','trajectory_checks.json'):
        paths.append(folder/name)
    paths.extend((folder/'figures').glob('*'))
    paths.extend((run/f'retrained_key_cases/seed_{seed}').glob('*.json'))
for name in ('bank.json','summary.json'):paths.append(run/'confirmation50'/name)
dest=ROOT/'DualPolicy_Round2_preview.zip'
with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
    for path in sorted(set(paths)):
        assert path.is_file(),path
        z.write(path,path.relative_to(ROOT).as_posix())
    z.writestr('ARCHIVE_README.txt',
        'Review bundle, not a standalone environment. Full code, original dependencies, raw trajectories and selected training states remain at:\n'
        '/home/ot/Students/hs/sailboat-dynamic-routing-v0\n'
        'C:/Users/74095/hs/SailBoat/sailboat-dynamic-routing-v0\n'
        'Selected expert/replay/optimizer/RNG checkpoints: checkpoints/round2/20261011/resume.pt and checkpoints/round2/20261012/resume.pt.\n'
        'All 350 unique raw trajectories: runs/round2_20261011/confirmation50/parts/*/trajectories. Per-seed combined tables reuse normal50 explicitly.\n'
        'This ZIP intentionally excludes large weights, replay, full raw traces and full process logs.\n')
print(dest, dest.stat().st_size)
