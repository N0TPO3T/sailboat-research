#!/bin/bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
test "$ROOT" = /home/ot/Students/hs/yara-env/migration18
[[ "${1:-}" = check || "${1:-}" = verify ]]
exec 9>"$ROOT/run.lock"
flock -n 9
export PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 TMPDIR="$ROOT/.tmp" MPLCONFIGDIR="$ROOT/.cache/mpl"
cd "$ROOT"
OUT="work/${MIGRATION18_RUN:-native_benchmark_$(date -u +%Y%m%dT%H%M%SZ)}"
test ! -e "$OUT"
PYTHON=/home/ot/Students/hs/sailboat-routing-v0/.venv/bin/python
../run-yara.sh bash /work/migration18/build.sh
"$PYTHON" -B native_benchmark.py check --output "$OUT/check"
if [ "$1" = verify ]; then
 "$PYTHON" -B native6dof_policy.py --output "$OUT/policy" --config config_yara_transfer.json --gate "$OUT/check/result.json"
 "$PYTHON" -B native_benchmark.py plots --output "$OUT/policy" --gate "$OUT/check/result.json"
fi
echo "RESULTS $ROOT/$OUT"
