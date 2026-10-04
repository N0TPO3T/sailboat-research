import math
import unittest
from dataclasses import replace
from sailboat_routing.planner import StaticMap,CircleObstacle,PlannerInput
from sailboat_routing.r2_planner import RelayPlanner
from sailboat_routing.r5_planner import TangentSupervisor,TangentConfig,tangent_headings
from sailboat_routing.metrics import segment_circle_clearance


def test_source_tangent_has_analytic_margin():
    p=(0.,0.);o=CircleObstacle((300.,0.),50.,60.)
    for a in tangent_headings(p,o,12.).values():
        q=(500*math.cos(a),500*math.sin(a))
        assert abs(segment_circle_clearance(p,q,(o,))['safety_m']-12.)<1e-8


def test_normal_mode_matches_relay_without_obstacles():
    chart=StaticMap((-2000,2000,-2000,2000),(),25)
    cfg=TangentConfig(margin=160,handoff=100,trigger_clearance=80)
    baseline=RelayPlanner(chart,cfg);method=TangentSupervisor(chart,cfg)
    current=None
    for t,x in [(0,0),(10,40),(100,420),(110,460)]:
        v=PlannerInput((x,0),0,current,((0,0),(1000,0)),t)
        a=baseline.plan(v);b=method.plan(v)
        assert a.target_xy==b.target_xy
        current=a.target_xy


def test_other_obstacle_filters_unsafe_tangent():
    chart=StaticMap((-1200,1800,-1200,1200),
        (CircleObstacle((150,0),50,60),CircleObstacle((0,-250),20,60)),25)
    cfg=TangentConfig(margin=160,handoff=100,trigger_clearance=80,
                      entry_clearance=80,exit_clearance=120,tangent_buffer=50)
    v=PlannerInput((0,0),0,None,chart.route((0,0),(1000,0)),0)
    method=TangentSupervisor(chart,cfg);q=method.plan(v).target_xy
    event=next(x for x in reversed(method.log) if x['event']=='target')
    lower=next(x for x in event['candidates'] if x['target'][1]<0)
    assert not lower['segment_valid']
    assert q[1]>0 and chart.segment_clear(v.position_xy,q)
    assert chart.route(q,(1000,0))


def test_position_hold_is_distinct_from_moving_heading_reference():
    chart=StaticMap((-1200,1800,-1200,1200),(CircleObstacle((150,0),50,60),),25)
    cfg=TangentConfig(margin=160,handoff=100,trigger_clearance=80,
                      entry_clearance=80,exit_clearance=120,tangent_buffer=50)
    v=PlannerInput((0,0),0,None,chart.route((0,0),(1000,0)),0)
    moving=TangentSupervisor(chart,cfg);fixed=TangentSupervisor(chart,replace(cfg,hold_position=True))
    q=moving.plan(v).target_xy;assert fixed.plan(v).target_xy==q
    later=replace(v,position_xy=(1,0),current_goal_xy=q,simulation_time=10)
    assert fixed.plan(later).target_xy==q
    assert math.dist(moving.plan(later).target_xy,q)>0.1


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(unittest.FunctionTestCase(value)
                              for name,value in sorted(globals().items())
                              if name.startswith('test_') and callable(value))


if __name__=='__main__':
    unittest.main()
