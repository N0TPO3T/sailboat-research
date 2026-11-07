#!/bin/bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
test "$ROOT" = /home/ot/Students/hs/yara-env/migration18
exec 9>"$ROOT/run.lock"
flock -n 9
export PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 TMPDIR="$ROOT/.tmp" MPLCONFIGDIR="$ROOT/.cache/mpl"
if [ ! -f "$ROOT/build/libMigrationStep.so" ] || [ "$ROOT/step.cc" -nt "$ROOT/build/libMigrationStep.so" ]; then
  mkdir -p "$ROOT/build"
  "$ROOT/../run-yara.sh" bash /work/migration18/build.sh
fi
exec /home/ot/Students/hs/sailboat-routing-v0/.venv/bin/python "$ROOT/signed_test.py" "${1:-response}"
