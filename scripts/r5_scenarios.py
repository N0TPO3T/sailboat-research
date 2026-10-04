"""R5 prespecified geometric risk strata; no outcome-dependent selection."""
import copy
import math
import random


def risk_scenes(base, seed, clearances=(80., 160., 280.), repeats=1):
    """Start at origin under unchanged reset; vary obstacles, not physical state.

    3 clearances x 3 bearings x 2 wind profiles = 18 per repeat.
    Bearing135 is a rear-obstacle control. Outcomes never enter generation.
    """
    rng=random.Random(seed); result=[]
    for repeat in range(repeats):
        for clearance in clearances:
            for bearing in (-45., 0., 135.):
                for profile in ('stable','fast'):
                    i=len(result); radius=rng.uniform(55.,75.)
                    offset=rng.uniform(-5.,5.); angle=math.radians(bearing+offset)
                    c_actual=clearance+rng.uniform(-8.,8.)
                    d=radius+60.+c_actual
                    obstacle=dict(center_xy=[d*math.cos(angle),d*math.sin(angle)],
                                  entity_radius=radius,safety_buffer=60.)
                    scene=dict(id=f'risk{seed}_{i:03d}_c{int(clearance)}_b{int(bearing)}_{profile}_1000',
                               seed=seed*100+i, profile=profile,
                               base_direction_degrees=rng.choice([0,60,120,180,240,300])+rng.uniform(-12,12),
                               goal=[1000.,0.],map='generated',distance_m=1000,
                               layout='risk_single',split='development',evaluation_family='risk',
                               initial_clearance_stratum_m=clearance,
                               initial_clearance_actual_m=c_actual,
                               obstacle_bearing_stratum_deg=bearing,
                               obstacle_bearing_actual_deg=bearing+offset,repeat=repeat)
                    suite=copy.deepcopy(base)
                    suite.update(purpose='R5 prespecified geometric risk strata; not natural failure frequency',
                                 maps={'generated':[obstacle]},world_bounds=[-2600,2600,-2600,2600],
                                 world_radius_limit_m=3000,task_time_limit_s=1800,
                                 goal_radius_m=10,comparison_scenarios=[scene],capture_scenarios=[])
                    result.append((scene,suite))
    return result
