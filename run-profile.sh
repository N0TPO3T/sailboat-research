#!/bin/bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
test "$ROOT" = /home/ot/Students/hs/yara-env/migration18
if [ "$#" != 3 ] || [ "$2" != check ]; then
  echo "Usage: $0 legacy|yara check work/UNUSED_OUTPUT_DIR" >&2
  exit 2
fi
[[ "$1" == legacy || "$1" == yara ]]
exec 9>"$ROOT/run.lock"
flock -n 9
export PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 TMPDIR="$ROOT/.tmp" MPLCONFIGDIR="$ROOT/.cache/mpl"
cd "$ROOT"
PYTHON=/home/ot/Students/hs/sailboat-routing-v0/.venv/bin/python
if [ ! -f build/libMigrationStep.so ] || [ step.cc -nt build/libMigrationStep.so ]; then
  ../run-yara.sh bash /work/migration18/build.sh
fi
if [ "$1" = legacy ] && [ ! -x build/legacy_probe ]; then
  c++ -O2 -std=c++17 legacy_probe.cc -o build/legacy_probe
fi
exec "$PYTHON" -B profile_check.py "$1" --output "$3"
