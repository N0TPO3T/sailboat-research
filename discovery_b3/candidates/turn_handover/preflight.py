"""Admission checks only. No scientific pilot or controller-performance claim."""
import os
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.dont_write_bytecode = True
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
os.environ['MPLCONFIGDIR'] = str(ROOT / 'cache')
sys.path.insert(0, str(ROOT / 'vendor'))
import hashlib
import json
import platform
import numpy as np
from python_vehicle_simulator.vehicles.otter import otter
from python_vehicle_simulator.lib.gnc import attitudeEuler


def force_bounds(v):
    return v.k_neg * v.n_min * abs(v.n_min), v.k_pos * v.n_max**2


def shaft_to_force(v, n):
    n = np.clip(np.asarray(n, dtype=float), v.n_min, v.n_max)
    return np.where(n >= 0, v.k_pos, v.k_neg) * n * np.abs(n)


def force_to_shaft(v, f):
    """Physical asymmetric inverse, common prerequisite for every controller."""
    f = np.clip(np.asarray(f, dtype=float), *force_bounds(v))
    return np.sign(f) * np.sqrt(np.abs(f) / np.where(f >= 0, v.k_pos, v.k_neg))


def forces_to_wrench(v, f):
    return np.array([f[0] + f[1], -v.l1 * f[0] - v.l2 * f[1]])


def yaw_priority_allocation(v, surge, yaw):
    """Exact feasible static allocation: prioritize clipped yaw, then surge.

    Units: surge N, yaw N m. This is a mature allocation baseline, not a new method.
    Only valid for the verified symmetric opposite lever arms of this vehicle.
    """
    assert np.isclose(v.l1, -v.l2) and v.l1 < 0
    arm = -v.l1
    lo, hi = force_bounds(v)
    difference = np.clip(yaw / arm, lo-hi, hi-lo)
    feasible_surge_lo = 2*lo + abs(difference)
    feasible_surge_hi = 2*hi - abs(difference)
    feasible_surge = np.clip(surge, feasible_surge_lo, feasible_surge_hi)
    f = np.array([(feasible_surge+difference)/2, (feasible_surge-difference)/2])
    return force_to_shaft(v, f), forces_to_wrench(v, f)


def integrate(v, command, duration=1.0, dt=0.01):
    """Unmodified upstream six-DOF dynamics and Euler kinematics."""
    eta = np.zeros(6)
    nu = np.zeros(6)
    actual = np.zeros(2)
    command = np.clip(np.asarray(command, float), v.n_min, v.n_max)
    for _ in range(round(duration/dt)):
        nu, actual = v.dynamics(eta, nu, actual, command, dt)
        eta = attitudeEuler(eta, nu, dt)
        assert np.isfinite(np.r_[eta, nu, actual]).all()
    return {'eta': eta.tolist(), 'nu': nu.tolist(), 'shaft_actual': actual.tolist()}


def main():
    v = otter()
    lo, hi = force_bounds(v)
    values = np.linspace(lo, hi, 101)
    error = float(np.max(abs(shaft_to_force(v, force_to_shaft(v, values))-values)))
    assert error < 1e-10
    assert np.allclose(shaft_to_force(v, force_to_shaft(v, [lo-100, hi+100])), [lo, hi])
    for surge in [-500, 0, 120, 500]:
        for yaw in [-500, -10, 0, 10, 500]:
            command, achieved = yaw_priority_allocation(v, surge, yaw)
            assert np.all(command >= v.n_min-1e-9) and np.all(command <= v.n_max+1e-9)
            assert np.allclose(achieved, forces_to_wrench(v, shaft_to_force(v, command)))
            assert abs(achieved[1]) <= (-v.l1)*(hi-lo)+1e-9
    forward = integrate(otter(), [50, 50])
    reverse = integrate(otter(), [-50, -50])
    turn_left = integrate(otter(), [50, 0])
    turn_right = integrate(otter(), [0, 50])
    assert forward['nu'][0] > 0 and reverse['nu'][0] < 0
    assert turn_left['nu'][5] > 0 and turn_right['nu'][5] < 0
    assert abs(turn_left['nu'][5]+turn_right['nu'][5]) < 1e-8
    manifest = {}
    for p in sorted((ROOT/'vendor').rglob('*')):
        if p.is_file():
            manifest[str(p.relative_to(ROOT)).replace('\\','/')] = {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size}
    receipt = {'status':'pass','scope':'admission only; not a scientific pilot', 'python':sys.executable,
        'python_version':platform.python_version(),'numpy':np.__version__,
        'upstream_commit':(ROOT/'upstream_commit.txt').read_text().strip(),
        'upstream_files':manifest,'mapping_roundtrip_max_error_N':error,
        'per_propeller_force_bounds_N':[lo,hi], 'allocation_test_count':20,
        'sign_checks':{'forward':forward,'reverse':reverse,'left_only':turn_left,'right_only':turn_right},
        'integration_dt_s':0.01,'each_sign_check_duration_s':1.0,
        'gpu_used':False,'controller_tasks_run':0}
    (ROOT/'preflight_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps({'status':'pass','force_bounds_N':[lo,hi],'roundtrip_error_N':error,'upstream_commit':receipt['upstream_commit']}))

if __name__ == '__main__':
    main()
