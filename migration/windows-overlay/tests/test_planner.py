"""Static-map and information-boundary checks; no simulated performance claims."""
from dataclasses import replace
import math
import pickle
import random
import unittest

import numpy as np

from sailboat_routing.planner import (
    CircleObstacle, LocalWaypointPlanner, LocalWindEstimate, NoLocalTargetError,
    NoRouteError, PlannerConfig, PlannerInput, StaticMap, distance,
)


class StaticMapTests(unittest.TestCase):
    def test_astar_routes_around_circle_and_simplifies_grid_nodes(self):
        chart = StaticMap((0, 1200, -400, 400), (CircleObstacle((600, 0), 100, 40),), 25)
        path = chart.route((0, 0), (1200, 0))
        self.assertEqual(path[0], (0, 0))
        self.assertEqual(path[-1], (1200, 0))
        self.assertGreater(len(path), 2)
        self.assertTrue(all(chart.segment_clear(a, b) for a, b in zip(path, path[1:])))
        self.assertTrue(all(not chart.segment_clear(path[i], path[i + 2])
                            for i in range(len(path) - 2)))
        self.assertGreater(sum(distance(a, b) for a, b in zip(path, path[1:])), 1200)

    def test_entity_and_buffer_gap_are_distinct(self):
        obstacles = tuple(CircleObstacle((500, y), 100, 49) for y in (-150, 150))
        chart = StaticMap((0, 1000, -20, 20), obstacles, 10)
        self.assertTrue(chart.segment_clear((0, 0), (1000, 0)))
        blocked = replace(chart, obstacles=tuple(replace(o, safety_buffer=50) for o in obstacles))
        self.assertFalse(blocked.segment_clear((0, 0), (1000, 0)))
        with self.assertRaises(NoRouteError):
            blocked.route((0, 0), (1000, 0))
        self.assertEqual(obstacles[0].entity_radius, 100)

    def test_outside_bounds_and_no_connected_route_are_explicit(self):
        chart = StaticMap((0, 1000, -100, 100), (CircleObstacle((500, 0), 120),), 25)
        self.assertFalse(chart.segment_clear((-1, 0), (100, 0)))
        with self.assertRaises(NoRouteError):
            chart.route((0, 0), (1000, 0))
        with self.assertRaises(NoRouteError):
            chart.route((-1, 0), (100, 0))


class LocalPlannerTests(unittest.TestCase):
    def setUp(self):
        self.chart = StaticMap((-1000, 6000, -1500, 1500))
        self.visible = PlannerInput((0, 0), 0.0, None, ((0, 0), (1000, 0)), 0.0)

    def planner(self, mode="geometry_only", **settings):
        return LocalWaypointPlanner(self.chart, PlannerConfig(**settings), mode)

    def test_invalid_estimate_falls_back_to_identical_geometry_policy(self):
        geometry, estimated = self.planner(), self.planner("estimated_local")
        current = None
        for time in (0, 10, 30, 60):
            visible = replace(self.visible, current_goal_xy=current, simulation_time=time)
            expected = geometry.plan(visible)
            actual = estimated.plan(replace(visible, wind=LocalWindEstimate(math.nan, False)))
            self.assertEqual(actual, expected)
            current = expected.target_xy

    def test_none_and_geometry_mode_ignore_wind(self):
        self.assertEqual(self.planner().plan(self.visible),
                         self.planner("estimated_local").plan(self.visible))
        self.assertEqual(self.planner().plan(self.visible), self.planner().plan(
            replace(self.visible, wind=LocalWindEstimate(math.pi, True))))

    def test_unrestricted_environment_payload_cannot_enter_formal_api(self):
        with self.assertRaises(TypeError):
            self.planner("estimated_local").plan({
                "position_xy": (0, 0), "wind_grid": [0, 1], "seed": 11, "future": 0.5})
        with self.assertRaises(TypeError):
            PlannerInput((0, 0), 0.0, None, ((0, 0), (1000, 0)), 0.0,
                         environment=object())

    def test_blowing_toward_convention_and_upwind_remains_candidate(self):
        tailwind = self.planner("oracle_local").plan(replace(
            self.visible, wind=LocalWindEstimate(0, True)))
        upwind = self.planner("oracle_local").plan(replace(
            self.visible, wind=LocalWindEstimate(math.pi, True)))
        tail = next(s for s in tailwind.candidates if distance(s.target_xy, (500, 0)) < 1e-6)
        head = next(s for s in upwind.candidates if distance(s.target_xy, (500, 0)) < 1e-6)
        self.assertAlmostEqual(tail.local_wind_penalty, 0)
        self.assertAlmostEqual(head.local_wind_penalty, 150)
        self.assertGreater(len(upwind.candidates), 0)  # Upwind is not hard-excluded.
        estimated = self.planner("estimated_local").plan(replace(
            self.visible, wind=LocalWindEstimate(math.pi, True)))
        self.assertEqual(estimated, upwind)

    def test_current_target_holding_replanning_and_hysteresis(self):
        planner = self.planner("oracle_local", wind_weight=10, smoothing=1)
        current = (500, 0)
        v = replace(self.visible, current_goal_xy=current, wind=LocalWindEstimate(math.pi, True))
        first = planner.plan(v)
        self.assertEqual(first.target_xy, current)
        self.assertEqual(first.reason, "minimum_hold")
        self.assertIn(current, [s.target_xy for s in first.candidates])
        periodic = planner.plan(replace(v, simulation_time=5))
        self.assertEqual(periodic.reason, "replan_period")
        held = planner.plan(replace(v, simulation_time=20))
        self.assertEqual(held.reason, "minimum_hold")
        switched = planner.plan(replace(v, simulation_time=40))
        self.assertNotEqual(switched.target_xy, current)
        cautious = self.planner("oracle_local", wind_weight=10, smoothing=1,
                                improvement_threshold=1e9, minimum_hold_time=0)
        retained = cautious.plan(v)
        self.assertEqual(retained.target_xy, current)
        self.assertEqual(retained.reason, "hysteresis")

    def test_all_new_targets_are_nominal_500_not_distant_final(self):
        for final_distance in (1000, 3000, 5000):
            decision = self.planner().plan(replace(self.visible, route=((0, 0), (final_distance, 0))))
            for score in decision.candidates:
                self.assertAlmostEqual(distance(self.visible.position_xy, score.target_xy), 500)
            self.assertNotEqual(decision.target_xy, (final_distance, 0))

    def test_final_nearby_is_not_overshot_and_arrived_target_can_change(self):
        visible = replace(self.visible, position_xy=(950, 0), current_goal_xy=(960, 0))
        decision = self.planner().plan(visible)
        self.assertEqual(decision.target_xy, (1000, 0))
        arrived = self.planner().plan(replace(visible, position_xy=(1000, 0), current_goal_xy=(1000, 0)))
        self.assertEqual(arrived.target_xy, (1000, 0))

    def test_bounded_candidate_infeasibility_is_not_hidden(self):
        chart = StaticMap((0, 200, 0, 1000), (CircleObstacle((100, 200), 40, 10),), 10)
        path = chart.route((100, 0), (100, 1000))
        with self.assertRaises(NoLocalTargetError):
            LocalWaypointPlanner(chart).plan(PlannerInput((100, 0), 0, None, path, 0))

    def test_states_are_independent_and_rng_is_not_consumed(self):
        before_py, before_np = random.getstate(), pickle.dumps(np.random.get_state())
        first, untouched = self.planner(), self.planner()
        goal = first.plan(self.visible).target_xy
        first.plan(replace(self.visible, current_goal_xy=goal, simulation_time=50))
        self.assertEqual(untouched.plan(self.visible), self.planner().plan(self.visible))
        self.planner(lateral_angles_rad=(-0.5, -0.25, 0.25, 0.5)).plan(self.visible)
        self.assertEqual(before_py, random.getstate())
        self.assertEqual(before_np, pickle.dumps(np.random.get_state()))


if __name__ == "__main__":
    unittest.main()
