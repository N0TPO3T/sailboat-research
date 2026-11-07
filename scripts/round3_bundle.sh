#!/usr/bin/env bash
set -euo pipefail
cd /home/ot/Students/hs/sailboat-dynamic-routing-v0
test "$(realpath .)" = /home/ot/Students/hs/sailboat-dynamic-routing-v0
run=runs/round3_20261011_2308
test -f "$run/delivery_checks.json"
test -f REPORT_ROUND3_ZH.md
export PYTHONDONTWRITEBYTECODE=1
/home/ot/Students/hs/sailboat-routing-v0/.venv/bin/python scripts/round3_package.py
tar --exclude='*/__pycache__/*' \
  --exclude="$run/train_*/*.pt" --exclude="$run/train_*/*.pth" \
  --exclude="$run/screen/*.pt" --exclude="$run/*.tar.gz" \
  -czf Round3_evidence.tar.gz REPORT_ROUND3_ZH.md HANDOFF.md README.md requirements.lock configs src scripts "$run"
sha256sum DualPolicy_Round3_preview.zip Round3_evidence.tar.gz "$run/selected_checkpoints.tar.gz"
echo complete > "$run/phase.txt"
