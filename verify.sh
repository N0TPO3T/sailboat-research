#!/bin/bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
test "$ROOT" = /home/ot/Students/hs/yara-env/migration18
exec 9>"$ROOT/run.lock"
flock -n 9 || { echo "Migration task already running"; exit 1; }
export MIGRATION18_LOCK_HELD=1
export PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR="$ROOT/.cache/mpl" XDG_CACHE_HOME="$ROOT/.cache" TMPDIR="$ROOT/.tmp"
mkdir -p "$MPLCONFIGDIR"
cd "$ROOT"
test ! -L output
mkdir -p archives
if [ -d output ]; then mv output "archives/output-$(date -u +%Y%m%dT%H%M%S)-$$"; fi
mkdir output
"$ROOT/../run-yara.sh" bash /work/migration18/build.sh > output/build.log 2>&1
"$ROOT/run.sh" --stage all > output/validation.log 2>&1
"$ROOT/run.sh" --stage capture > output/camera_checks.log 2>&1
PY=/home/ot/Students/hs/sailboat-routing-v0/.venv/bin/python
"$PY" "$ROOT/edge_checks.py" > output/edges.log 2>&1
"$PY" "$ROOT/audit.py" > output/audit.log 2>&1
"$PY" "$ROOT/plots.py" > output/summary.log 2>&1
"$PY" "$ROOT/generate_report.py"
"$PY" "$ROOT/index_artifacts.py"
echo "Validation complete: $ROOT/output"
