#!/usr/bin/env bash
set -e
export PYTHONPATH=/work/docker/wheels/pip-24.3.1-py3-none-any.whl
python3 -m pip install --no-index --find-links=/work/docker/wheels --target=/work/python --ignore-installed 'torch==1.13.1+cpu' 'stable-baselines3==2.3.2' 'gymnasium==0.29.1' 'numpy==1.24.4' 'scipy==1.10.1' 'pandas==2.0.3' 'matplotlib==3.7.5' 'simple-pid==2.0.1' 'importlib-metadata==8.5.0' 'importlib-resources==6.4.5'
cp /work/docker/sitecustomize.py /work/python/sitecustomize.py
export PYTHONPATH=/work/python
python3 -c 'import torch,gymnasium,stable_baselines3,rospy; print(torch.__version__,gymnasium.__version__,stable_baselines3.__version__)'
