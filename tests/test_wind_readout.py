"""Deterministic math tests only: no environment, capture or real-wind experiment."""
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from sailboat_routing.wind_readout import (
    CausalWindFilter, Episode, FEATURE_SCHEMA, RidgeWindReadout, circular_metrics,
    evaluate_episodes, load_episode, local_to_world, predict_episode, split_episodes,
    world_to_local, wrap_angle,
)

SOURCE = {"actor_sha256": "a" * 64, "normalizer_sha256": "b" * 64, "feature_schema": FEATURE_SCHEMA}


def episode(eid="a", scenario="a", n=12):
    t = np.arange(n, dtype=float)
    return Episode(eid, scenario, dict(SOURCE), np.zeros((n, 2)), np.zeros(n), t, t.copy(),
                   t.copy(), np.zeros(n), np.arange(n), np.zeros(n, dtype=bool), np.zeros(n, dtype=bool))


def save_episode(path, ep, **overrides):
    metadata = {"schema_version": 1, "episode_id": ep.episode_id, "scenario_id": ep.scenario_id,
                "source_identity": ep.source_identity, "feature_timing": "decision_pre_action"}
    fields = {k: getattr(ep, k) for k in ("features", "labels_local_rad", "decision_time", "labels_time",
              "observed_through_time", "frame_angle", "history_count", "goal_switch", "wind_change")}
    fields["metadata_json"] = np.array(json.dumps(metadata))
    fields.update(overrides)
    np.savez(path, **fields)


class WindReadoutTests(unittest.TestCase):
    def test_circular_boundary_and_empty(self):
        metric = circular_metrics([np.pi - .01], [-np.pi + .01])
        self.assertAlmostEqual(metric["mae_deg"], .02 * 180 / np.pi)
        self.assertAlmostEqual(metric["p90_deg"], metric["mae_deg"])
        empty = circular_metrics([np.nan], [0.], [False])
        self.assertEqual(empty["status"], "empty")
        self.assertIsNone(empty["mae_deg"])

    def test_low_sample_closed_form_and_unpenalized_intercept(self):
        x = np.array([[1., 5., -1., 2.], [3., 5., 1., 8.]])
        labels = np.array([-.5, .8])
        model = RidgeWindReadout.fit(x, labels, alpha=.7, source_identity=SOURCE)
        scale = np.array([1., 1., 1., 3.])
        np.testing.assert_array_equal(model.mean, [2., 5., 0., 5.])
        np.testing.assert_array_equal(model.scale, scale)
        z = (x - x.mean(axis=0)) / scale
        y = np.column_stack([np.sin(labels), np.cos(labels)])
        expected = np.linalg.solve(z.T @ z + .7 * np.eye(4), z.T @ (y - y.mean(axis=0)))
        np.testing.assert_allclose(model.coefficients, expected, atol=1e-14)
        np.testing.assert_allclose(model.intercept, y.mean(axis=0))
        one = RidgeWindReadout.fit([[999., 4.]], [.7], alpha=10., source_identity=SOURCE)
        np.testing.assert_allclose(one.predict_vectors([[999., 4.]]), [[np.sin(.7), np.cos(.7)]])

    def test_standardization_uses_only_training_episode(self):
        a, b, c = episode("train"), episode("val", "b"), episode("test", "c")
        a.features[:, 0] = np.arange(12)
        b.features[:] = 1e9
        c.features[:] = -1e9
        split = split_episodes([a, b, c], {"schema_version": 1, "splits": {
            "train": ["train"], "validation": ["val"], "test": ["test"]}})
        model = RidgeWindReadout.fit(split["train"][0].features, a.labels_local_rad, alpha=1., source_identity=SOURCE)
        np.testing.assert_allclose(model.mean, [5.5, 0.])
        np.testing.assert_allclose(model.scale, [np.std(np.arange(12)), 1.])
        before = model.mean.copy()
        model.predict_vectors(b.features)
        np.testing.assert_array_equal(model.mean, before)

    def test_split_episode_and_scenario_leaks_rejected(self):
        manifest = {"schema_version": 1, "splits": {"train": ["a"], "validation": ["b"], "test": ["c"]}}
        with self.assertRaisesRegex(ValueError, "scenario"):
            split_episodes([episode("a", "same"), episode("b", "same"), episode("c", "c")], manifest)
        manifest["splits"]["validation"] = ["a"]
        with self.assertRaisesRegex(ValueError, "episode"):
            split_episodes([episode("a"), episode("b", "b"), episode("c", "c")], manifest)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            split_episodes([episode(), episode()], manifest)

    def test_future_and_misaligned_timestamps_rejected(self):
        ep = episode()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ep.npz"
            future = ep.decision_time.copy()
            future[3] += .01
            save_episode(path, ep, observed_through_time=future)
            with self.assertRaisesRegex(ValueError, "future"):
                load_episode(path, dimension=2)
            save_episode(path, ep, labels_time=ep.labels_time + 1.)
            with self.assertRaisesRegex(ValueError, "labels_time"):
                load_episode(path, dimension=2)
            metadata = {"schema_version": 1, "episode_id": "a", "scenario_id": "a",
                        "source_identity": SOURCE, "feature_timing": "post_action"}
            save_episode(path, ep, metadata_json=np.array(json.dumps(metadata)))
            with self.assertRaisesRegex(ValueError, "pre_action"):
                load_episode(path, dimension=2)
            save_episode(path, ep, wind_query=np.zeros(12))
            with self.assertRaisesRegex(ValueError, "fields"):
                load_episode(path, dimension=2)

    def test_warmup_and_vector_degeneracy(self):
        model = RidgeWindReadout.fit([[0.], [0.]], [0., np.pi], alpha=1., source_identity=SOURCE)
        result = CausalWindFilter(model).update([0.], frame_angle=0., history_count=10)
        self.assertFalse(result.valid)
        self.assertLess(result.vector_norm, 1e-6)
        good = RidgeWindReadout.fit([[0.]], [.4], alpha=1., source_identity=SOURCE)
        state = CausalWindFilter(good)
        self.assertFalse(state.update([0.], frame_angle=0., history_count=9).valid)
        self.assertTrue(state.update([0.], frame_angle=0., history_count=10).valid)

    def test_world_frame_ema_survives_rotating_goal(self):
        # Exact identity map from local sin/cos features to sin/cos outputs.
        model = RidgeWindReadout(np.zeros(2), np.ones(2), np.eye(2), np.zeros(2), 1., dict(SOURCE))
        state = CausalWindFilter(model, warmup=0, ema_weight=.25)
        world = np.pi - .02
        for frame in [0., np.pi / 2, -np.pi + .01, .1]:
            local = world_to_local(world, frame)
            estimate = state.update([np.sin(local), np.cos(local)], frame_angle=frame, history_count=0)
            self.assertTrue(estimate.valid)
            self.assertAlmostEqual(float(wrap_angle(estimate.world_rad - world)), 0., places=12)
            self.assertAlmostEqual(float(wrap_angle(estimate.local_rad - local)), 0., places=12)
            self.assertAlmostEqual(float(wrap_angle(local_to_world(local, frame) - world)), 0., places=12)

    def test_causal_prefix_invariance_and_circular_ema(self):
        model = RidgeWindReadout(np.zeros(2), np.ones(2), np.eye(2), np.zeros(2), 1., dict(SOURCE))
        def run(angles):
            state = CausalWindFilter(model, warmup=0, ema_weight=.5)
            return [state.update([np.sin(a), np.cos(a)], frame_angle=0., history_count=i) for i, a in enumerate(angles)]
        prefix = [np.pi - .02, -np.pi + .02]
        a, b = run(prefix), run(prefix + [0., 1., 2.])
        self.assertEqual(a, b[:2])
        self.assertLess(abs(float(wrap_angle(a[1].world_rad - np.pi))), 1e-12)
        cancellation = run([0., np.pi])
        self.assertFalse(cancellation[1].valid)

    def test_save_load_and_dimension_identity_guards(self):
        model = RidgeWindReadout.fit([[1., 2.], [3., 2.]], [-.4, .7], alpha=.1, source_identity=SOURCE)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "model.npz"
            model.save(path)
            loaded = RidgeWindReadout.load(path, expected_dimension=2, expected_source_identity=SOURCE)
            np.testing.assert_array_equal(model.predict_vectors([[2., 2.]]), loaded.predict_vectors([[2., 2.]]))
            with self.assertRaises(FileExistsError):
                model.save(path)
            with self.assertRaisesRegex(ValueError, "dimension"):
                RidgeWindReadout.load(path, expected_dimension=270)
            with self.assertRaisesRegex(ValueError, "dimension"):
                loaded.predict_vectors([[1., 2., 3.]])
            with self.assertRaisesRegex(ValueError, "identity"):
                RidgeWindReadout.load(path, expected_source_identity={**SOURCE, "actor_sha256": "c" * 64})

    def test_marked_event_response_windows_do_not_cross_episodes(self):
        model = RidgeWindReadout.fit([[0., 0.]], [0.], alpha=1., source_identity=SOURCE)
        first, second = episode(n=3), episode("b", "b", n=3)
        first.goal_switch[-1] = True
        first.wind_change[1] = True
        first.labels_local_rad[:] = [0., .1, .2]
        second.labels_local_rad[:] = 1.
        metrics = evaluate_episodes(model, [first, second], warmup=0, window_steps=2)
        self.assertEqual(metrics["goal_switch_window"]["count"], 1)
        self.assertAlmostEqual(metrics["goal_switch_window"]["mae_deg"], .2 * 180 / np.pi)
        self.assertEqual(metrics["wind_change_response_window"]["count"], 2)
        self.assertAlmostEqual(metrics["wind_change_response_window"]["mae_deg"], .15 * 180 / np.pi)
        empty = evaluate_episodes(model, [second], warmup=0)
        self.assertEqual(empty["goal_switch_window"]["status"], "empty")


if __name__ == "__main__":
    unittest.main()
