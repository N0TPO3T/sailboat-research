#!/usr/bin/env bash
set -eu
cd /home/ot/Students/hs/sailboat-track-b/discovery_b2/candidates/acoustic_update
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=""
export TMPDIR="$PWD/tmp" MPLCONFIGDIR="$PWD/cache" XDG_CACHE_HOME="$PWD/cache"
timeout 3600 /home/ot/Students/hs/sailboat-routing-v0/.venv/bin/python -u pilot_stable.py --input input/xdat.Full.csv --out stable_results_reproduce
