#!/bin/bash
set -e
cd /work/migration18/build
python3 /work/migration18/generate_sail_plugin.py
cmake ..
make -j2
