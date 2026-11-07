#!/bin/bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
test "$ROOT" = /home/ot/Students/hs/yara-env/migration18
exec 9>"$ROOT/run.lock"
flock -n 9
export PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 TMPDIR="$ROOT/.tmp" MPLCONFIGDIR="$ROOT/.cache/mpl"
cd "$ROOT"
PYTHON=/home/ot/Students/hs/sailboat-routing-v0/.venv/bin/python
RUN="${MIGRATION18_RUN:-legacy4dof_20261108}"
[[ "$RUN" == legacy4dof_* && "$RUN" != */* ]]
mkdir -p "$RUN" "$ROOT/build"
if [ "${1:-response}" = verify ]; then
  test ! -e "$RUN/kernel_gate.json"
  "$PYTHON" export_legacy.py
  c++ -O2 -std=c++17 legacy_probe.cc -o build/legacy_probe
  ../run-yara.sh bash /work/migration18/build.sh > "$RUN/build.log" 2>&1
  for stage in kernel response reset wind policy; do
    "$PYTHON" legacy_validate.py "$stage" > "$RUN/$stage.log" 2>&1
  done
  "$PYTHON" legacy_analysis.py > "$RUN/analysis.log" 2>&1
  "$PYTHON" legacy_validate.py capture > "$RUN/capture.log" 2>&1
elif [ "${1:-response}" = control ]; then
  exec "$PYTHON" native_control_check.py
else
  exec "$PYTHON" legacy_validate.py "${1:-response}"
fi
