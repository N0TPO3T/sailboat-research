#!/bin/bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
test "$ROOT" = /home/ot/Students/hs/yara-env/migration18
# This branch defaults to the source-defined origin18D verification.
if [ "$#" = 0 ]; then exec "$ROOT/run-origin18d.sh" verify; fi
if [ "${MIGRATION18_LOCK_HELD:-0}" != 1 ]; then
  exec flock -n "$ROOT/run.lock" env MIGRATION18_LOCK_HELD=1 "$0" "$@"
fi
export PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 TMPDIR="$ROOT/.tmp"
if [ ! -f "$ROOT/build/libMigrationStep.so" ] || [ "$ROOT/step.cc" -nt "$ROOT/build/libMigrationStep.so" ]; then
  mkdir -p "$ROOT/build"
  "$ROOT/../run-yara.sh" bash /work/migration18/build.sh
fi
exec /home/ot/Students/hs/sailboat-routing-v0/.venv/bin/python "$ROOT/validate.py" "$@"
