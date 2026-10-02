"""Synthetic field determinism and recorded-trajectory metric contracts."""
import math
import pickle
import random
import unittest

import numpy as np

from sailboat_routing.metrics import (
    METHODS, posthoc_tack_events, segment_circle_clearance, summarize_paired,
)
from sailboat_routing.planner import CircleObstacle
from sailboat_routing.wind_fields import SyntheticWindField


class WindFieldTests(unittest.TestCase):
    def test_query_order_count_and_path_do_not_change_field(self):
        queries = [((0, 0), 0), ((120, -50), 0.25), ((120, -50), 99.7),
                   ((-400, 280), 300), ((0, 0), 2400)]
        for profile in ("stable", "slow", "fast"):
            field = SyntheticWindField(7, 3.1, profile)
            expected = [field.sample(*q) for q in queries]
            for q in reversed(queries):
                for _ in range(8):
                    field.sample(*q)
            # Extra samples along a different route, including same physical time.
            for x in range(50):
                field.sample((x * 30, -x * 17), 99.7)
            duplicate = SyntheticWindField(7, 3.1, profile)
            self.assertEqual(expected, [field.sample(*q) for q in queries])
            self.assertEqual(expected, [duplicate.sample(*q) for q in queries])

    def test_change_onsets_activate_real_smooth_variation(self):
        self.assertEqual(SyntheticWindField(5, 0.4).change_onsets, ())
        for profile in ("slow", "fast"):
            field = SyntheticWindField(5, 0.4, profile)
            self.assertEqual(field.change_onsets, (100,))
            base = field.sample((0, 0), 0)
            for xy in ((0, 0), (450, -80)):
                self.assertEqual(field.sample(xy, 99), base)
                self.assertEqual(field.sample(xy, 100), base)
                nearby = field.sample(xy, 100.0001)
                self.assertLess(abs(nearby[0] - base[0]), 1e-8)
                self.assertLess(abs(nearby[1] - base[1]), 1e-8)
                self.assertNotEqual(field.sample(xy, 130), base)

    def test_global_numpy_and_python_random_states_are_untouched(self):
        before = (pickle.dumps(np.random.get_state()), random.getstate())
        field = SyntheticWindField(912, -2, "fast", horizon=12.4)
        for t in (0, 1.2, 12.4):
            field.sample((1200, -60), t)
        self.assertEqual(before, (pickle.dumps(np.random.get_state()), random.getstate()))

    def test_fixed_field_and_fractional_time_continuity_across_wrap(self):
        stable = SyntheticWindField(1, math.pi + 0.1)
        self.assertAlmostEqual(stable.sample((0, 0), 0)[1], -math.pi + 0.1)
        self.assertEqual(stable.sample((0, 0), 0), stable.sample((8000, -9), 1300.5))
        self.assertTrue(stable.diagnostics()["fixed_wind"])
        fast = SyntheticWindField(2, math.pi, "fast", horizon=3.4)
        self.assertFalse(fast.diagnostics()["fixed_wind"])
        self.assertNotEqual(fast.sample((0, 0), 1), fast.sample((900, 900), 1))
        for t in (0.5, 1.0, 3.0):
            before, after = fast.sample((80, 15), t - 1e-6), fast.sample((80, 15), t + 1e-6)
            self.assertLess(abs(before[0] - after[0]), 1e-5)
            self.assertLess(abs((before[1] - after[1] + math.pi) % (2 * math.pi) - math.pi), 1e-5)
        fast.sample((0, 0), 3.4)
        with self.assertRaises(ValueError):
            fast.sample((0, 0), 3.4001)


class TrajectoryMetricsTests(unittest.TestCase):
    def test_segment_entity_and_buffer_clearance_and_degenerate_point(self):
        obstacles = (CircleObstacle((0, 0), 2, 1.5),)
        self.assertEqual(segment_circle_clearance((-5, 3), (5, 3), obstacles),
                         {"entity_m": 1.0, "safety_m": -0.5})
        self.assertEqual(segment_circle_clearance((0, 0), (0, 0), obstacles),
                         {"entity_m": -2.0, "safety_m": -3.5})
        self.assertEqual(segment_circle_clearance((-5, 2), (5, 2), obstacles)["entity_m"], 0)
        self.assertEqual(segment_circle_clearance((0, 0), (1, 0), ()),
                         {"entity_m": math.inf, "safety_m": math.inf})

    def test_boat_tack_and_pure_wind_side_change_are_distinct(self):
        radians = math.radians
        times = [0, 1, 2, 3, 4]
        headings = [radians(v) for v in (-35, -8, 0, 8, 35)]
        boat = posthoc_tack_events(times, headings, [math.pi] * 5)
        wind = posthoc_tack_events(times, [radians(-35)] * 5,
                                  [math.pi + radians(v) for v in (0, -27, -35, -43, -70)])
        self.assertEqual((boat["tack_count"], boat["wind_side_change_count"]), (1, 0))
        self.assertEqual((wind["tack_count"], wind["wind_side_change_count"]), (0, 1))
        self.assertEqual(boat["events"][0]["start_time_s"], 0)
        self.assertEqual(boat["events"][0]["end_time_s"], 4)

    def test_angle_wrap_downwind_and_hysteresis_do_not_create_false_tacks(self):
        r = math.radians
        # Heading crosses +/-pi while actual upwind is pi (wind blows toward 0).
        wrapped = posthoc_tack_events([0, 1, 2], [r(145), r(179), r(-145)], [0] * 3)
        self.assertEqual(wrapped["tack_count"], 1)
        downwind = posthoc_tack_events([0, 1, 2], [r(145), r(179), r(-145)], [math.pi] * 3)
        self.assertEqual(downwind["events"], [])
        jitter = posthoc_tack_events(range(7), [r(v) for v in (-30, -2, 2, -2, 2, -2, -30)],
                                    [math.pi] * 7)
        self.assertEqual(jitter["events"], [])
        small = posthoc_tack_events([0, 1], [r(-11), r(11)], [math.pi] * 2,
                                   min_heading_change_rad=r(30))
        self.assertEqual(small["tack_count"], 0)

    def test_mixed_wind_dominated_crossing_is_not_counted_as_boat_tack(self):
        r = math.radians
        result = posthoc_tack_events([0, 1, 2], [r(-40), r(-25), r(-10)],
                                    [math.pi, math.pi - r(30), math.pi - r(60)])
        self.assertEqual((result["tack_count"], result["wind_side_change_count"]), (0, 1))


class PairedSummaryTests(unittest.TestCase):
    @staticmethod
    def row(scene, method, success, value=10):
        return {"scene_id": scene, "method": method, "success": success,
                "time_s": value, "path_length_m": value * 3,
                "min_safety_clearance_m": value / 2,
                "actuator_variation_rad": value / 10,
                "target_changes": 2, "tack_count": 1, "wall_seconds": value / 100}

    def test_success_all_scenes_efficiency_only_common_success(self):
        rows = [self.row("common", m, True, 10 + i) for i, m in enumerate(METHODS)]
        rows += [self.row("common2", m, True, 30 + i) for i, m in enumerate(METHODS)]
        rows += [self.row("partial", m, m != "estimated_local", 900) for m in METHODS]
        # Failure metrics are not required to produce success-rate denominators.
        rows += [{"scene_id": "all_fail", "method": m, "success": False} for m in METHODS]
        summary = summarize_paired(rows)
        self.assertEqual(summary["scene_count"], 4)
        self.assertEqual(summary["common_success_scene_ids"], ["common", "common2"])
        self.assertEqual(summary["common_success_count"], 2)
        for i, m in enumerate(METHODS):
            stats = summary["methods"][m]
            self.assertEqual(stats["efficiency_sample_count"], 2)
            self.assertEqual(stats["efficiency_mean"]["time_s"], 20 + i)
            self.assertEqual(stats["success_rate"], (2 if m == "estimated_local" else 3) / 4)

    def test_zero_common_success_and_empty_are_explicit_none(self):
        rows = [{"scene_id": "failed", "method": m, "success": False} for m in METHODS]
        result = summarize_paired(rows)
        self.assertEqual(result["common_success_count"], 0)
        for stats in result["methods"].values():
            self.assertEqual(stats["success_rate"], 0)
            self.assertIsNone(stats["efficiency_mean"])
        for stats in summarize_paired([])["methods"].values():
            self.assertIsNone(stats["success_rate"])
            self.assertIsNone(stats["efficiency_mean"])

    def test_incomplete_and_duplicate_pairs_do_not_silently_change_denominator(self):
        rows = [self.row("s", m, True) for m in METHODS]
        with self.assertRaises(ValueError):
            summarize_paired(rows[:-1])
        with self.assertRaises(ValueError):
            summarize_paired(rows + [rows[0]])


if __name__ == "__main__":
    unittest.main()
