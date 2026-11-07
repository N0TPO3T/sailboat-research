"""Review bundle; all full trajectories and selected states remain separate."""
from pathlib import Path
import zipfile,json
ROOT=Path(__file__).resolve().parents[1];run=ROOT/'runs/round3_20261011_2308'
summary=json.loads((run/'confirmation50/summary.json').read_text());assert summary['physical_rollouts']==600
paths=[ROOT/x for x in ('REPORT_ROUND3_ZH.md','HANDOFF.md','README.md','requirements.lock')]
for folder in ('src','scripts','configs'):
    paths.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
for name in ('PROTOCOL.md','COMMANDS.md','CONCLUSIONS_ZH.md','freeze.json','implementation_check.json','targeted_checks.json','w0_identity.json','delivery_checks.json'):
    paths.append(run/name)
paths.extend((run/'figures').glob('*'))
for name in ('DIAGNOSIS_ZH.md','key_case_timelines.json','old50_pairs.json','old50_summary.json','old50_episodes.jsonl'):
    paths.append(run/'diagnosis'/name)
for name in ('protocol.json','results.jsonl'):paths.append(run/'diagnosis/branches'/name)
for name in ('summary.json','pairs_20261011.json','pairs_20261012.json','processes.json','equivalence.json'):paths.append(run/'screen'/name)
for seed in (20261011,20261012):
    for name in ('learning.jsonl','development.jsonl','initialization.json','config.json','complete.json','takeover_coverage.json'):
        paths.append(run/f'train_{seed}'/name)
    for name in ('selection.json','checkpoint_verification.json'):
        paths.append(ROOT/f'checkpoints/round3/{seed}'/name)
    folder=run/f'confirmation50/seed_{seed}'
    for name in ('summary.json','episodes.csv','pairs.csv','paired_scenes.csv','pairs.json','case_events.json','functional_equivalence.json','trajectory_checks.json'):
        paths.append(folder/name)
for name in ('bank.json','summary.json','matrix.json','processes.json'):paths.append(run/'confirmation50'/name)
dest=ROOT/'DualPolicy_Round3_preview.zip'
with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
    for path in sorted(set(paths)):
        assert path.is_file(),path
        z.write(path,path.relative_to(ROOT).as_posix())
    z.writestr('ARCHIVE_README.txt',
      'Preview bundle, not a standalone environment. Full artifacts remain at:\n'
      '/home/ot/Students/hs/sailboat-dynamic-routing-v0\nC:/Users/74095/hs/SailBoat/sailboat-dynamic-routing-v0\n'
      'Selected SAC states: checkpoints/round3/20261011/resume.pt and checkpoints/round3/20261012/resume.pt.\n'
      'Use AdaptNormalizer and round3 entrypoints; FixedNormalizer omits the new input constraint.\n'
      '600 unique raw confirmation traces: runs/round3_20261011_2308/confirmation50/parts/*/trajectories.\n'
      'Normal/W0 are shared across training seeds; the two combined tables contain 700 rows, not 700 executed trials.\n'
      'Large weights, replay, raw traces and full process logs are excluded from this preview.\n')
print(dest,dest.stat().st_size)
