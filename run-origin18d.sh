#!/bin/bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
test "$ROOT" = /home/ot/Students/hs/yara-env/migration18
[[ "${1:-verify}" == verify ]]
exec 9>"$ROOT/run.lock"
flock -n 9
export PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 TMPDIR="$ROOT/.tmp" MPLCONFIGDIR="$ROOT/.cache/mpl"
export MIGRATION18_RUN="${MIGRATION18_RUN:-legacy4dof_origin18d_$(date -u +%Y%m%dT%H%M%SZ)}"
[[ "$MIGRATION18_RUN" == legacy4dof_* && "$MIGRATION18_RUN" != */* ]]
cd "$ROOT"
test ! -e "$MIGRATION18_RUN"
mkdir "$MIGRATION18_RUN"
PYTHON=/home/ot/Students/hs/sailboat-routing-v0/.venv/bin/python
"$PYTHON" -B origin18d_audit.py preflight > "$MIGRATION18_RUN/preflight.log" 2>&1
../run-yara.sh bash /work/migration18/build.sh > "$MIGRATION18_RUN/build.log" 2>&1
c++ -O2 -std=c++17 legacy_probe.cc -o build/legacy_probe
for stage in kernel response reset wind; do
 "$PYTHON" -B legacy_validate.py "$stage" > "$MIGRATION18_RUN/$stage.log" 2>&1
done
"$PYTHON" -B origin18d_audit.py wind_kernel > "$MIGRATION18_RUN/wind_kernel.log" 2>&1
"$PYTHON" -B legacy_validate.py policy > "$MIGRATION18_RUN/policy.log" 2>&1
"$PYTHON" -B origin18d_audit.py postflight > "$MIGRATION18_RUN/postflight.log" 2>&1
"$PYTHON" -B origin18d_audit.py plots > "$MIGRATION18_RUN/analysis.log" 2>&1
"$PYTHON" -B legacy_validate.py capture > "$MIGRATION18_RUN/capture.log" 2>&1
printf '%s\n' "$ROOT/$MIGRATION18_RUN/acceptance.json"
