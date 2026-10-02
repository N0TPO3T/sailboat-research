"""Offline sin/cos ridge fitting and label-free causal wind-direction inference."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Mapping, Sequence

import numpy as np

MODEL_VERSION = 1
SOURCE_KEYS = {"actor_sha256", "normalizer_sha256", "feature_schema"}
FEATURE_SCHEMA = "frozen_obs14+lstm_ln256_pre_action_v1"
EPISODE_KEYS = {"metadata_json", "features", "labels_local_rad", "decision_time",
                "labels_time", "observed_through_time", "frame_angle", "history_count",
                "goal_switch", "wind_change"}
METADATA_KEYS = {"schema_version", "episode_id", "scenario_id", "source_identity", "feature_timing"}


def wrap_angle(angle):
    return np.arctan2(np.sin(angle), np.cos(angle))


def local_to_world(direction, frame_angle):
    return wrap_angle(np.asarray(direction) + np.asarray(frame_angle))


def world_to_local(direction, frame_angle):
    return wrap_angle(np.asarray(direction) - np.asarray(frame_angle))


def _source(identity: Mapping) -> dict:
    if not isinstance(identity, dict) or set(identity) != SOURCE_KEYS:
        raise ValueError("source_identity must contain exactly actor_sha256, normalizer_sha256, feature_schema")
    for key in ("actor_sha256", "normalizer_sha256"):
        if not isinstance(identity[key], str) or not re.fullmatch(r"[0-9a-f]{64}", identity[key]):
            raise ValueError(f"{key} must be a lowercase SHA256 digest")
    if identity["feature_schema"] != FEATURE_SCHEMA:
        raise ValueError("unsupported frozen feature schema")
    return dict(identity)


def _features(features, dimension=None):
    x = np.asarray(features, dtype=np.float64)
    if x.ndim != 2 or x.shape[0] == 0 or x.shape[1] == 0 or not np.isfinite(x).all():
        raise ValueError("features must be a nonempty finite N-by-D matrix")
    if dimension is not None and x.shape[1] != dimension:
        raise ValueError(f"expected feature dimension {dimension}, got {x.shape[1]}")
    return x


@dataclass(frozen=True)
class Episode:
    episode_id: str
    scenario_id: str
    source_identity: dict
    features: np.ndarray
    labels_local_rad: np.ndarray
    decision_time: np.ndarray
    labels_time: np.ndarray
    observed_through_time: np.ndarray
    frame_angle: np.ndarray
    history_count: np.ndarray
    goal_switch: np.ndarray
    wind_change: np.ndarray


def load_episode(path, *, dimension=270) -> Episode:
    """Load an explicitly attested pre-action capture; never infer causality from names."""
    with np.load(path, allow_pickle=False) as data:
        if set(data.files) != EPISODE_KEYS:
            raise ValueError(f"episode fields must be exactly {sorted(EPISODE_KEYS)}")
        metadata = json.loads(str(data["metadata_json"].item()))
        if set(metadata) != METADATA_KEYS or metadata["schema_version"] != 1:
            raise ValueError("unsupported episode metadata schema")
        if metadata["feature_timing"] != "decision_pre_action":
            raise ValueError("feature provenance must explicitly attest decision_pre_action")
        for key in ("episode_id", "scenario_id"):
            if not isinstance(metadata[key], str) or not metadata[key]:
                raise ValueError(f"{key} must be a nonempty string")
        source = _source(metadata["source_identity"])
        x = _features(data["features"], dimension)
        arrays = {}
        for key in EPISODE_KEYS - {"metadata_json", "features"}:
            value = np.array(data[key], copy=True)
            if value.shape != (len(x),) or not np.isfinite(value).all():
                raise ValueError(f"{key} must be a finite N-vector")
            arrays[key] = value
        for key in ("goal_switch", "wind_change"):
            if arrays[key].dtype != np.bool_:
                raise ValueError(f"{key} must have boolean dtype")
        h = arrays["history_count"]
        if not np.issubdtype(h.dtype, np.integer) or np.any(h < 0):
            raise ValueError("history_count must contain nonnegative integers")
        t = arrays["decision_time"]
        if np.any(np.diff(t) <= 0) or not np.array_equal(t, arrays["labels_time"]):
            raise ValueError("decision_time must increase strictly and equal labels_time exactly")
        if np.any(arrays["observed_through_time"] > t):
            raise ValueError("future observation timestamp is forbidden")
        return Episode(metadata["episode_id"], metadata["scenario_id"], source, x, **arrays)


def split_episodes(episodes: Sequence[Episode], manifest: Mapping) -> dict[str, list[Episode]]:
    """Apply predeclared whole-episode IDs; reject scenario and episode leakage."""
    if set(manifest) != {"schema_version", "splits"} or manifest["schema_version"] != 1:
        raise ValueError("unsupported split manifest schema")
    splits = manifest["splits"]
    if not isinstance(splits, dict) or set(splits) != {"train", "validation", "test"}:
        raise ValueError("manifest requires exactly train, validation, test")
    lookup = {}
    identity = None
    for episode in episodes:
        if episode.episode_id in lookup:
            raise ValueError("duplicate episode ID in input")
        lookup[episode.episode_id] = episode
        if identity is None:
            identity = episode.source_identity
        if episode.source_identity != identity:
            raise ValueError("mixed frozen source identities")
    result, used, scenarios = {}, set(), {}
    for name in ("train", "validation", "test"):
        ids = splits[name]
        if not isinstance(ids, list) or not ids or any(not isinstance(i, str) for i in ids):
            raise ValueError(f"{name} requires a nonempty episode ID list")
        result[name] = []
        for eid in ids:
            if eid in used:
                raise ValueError("episode appears more than once or across splits")
            if eid not in lookup:
                raise ValueError(f"missing episode: {eid}")
            episode = lookup[eid]
            if episode.scenario_id in scenarios and scenarios[episode.scenario_id] != name:
                raise ValueError("scenario appears across splits")
            scenarios[episode.scenario_id] = name
            used.add(eid)
            result[name].append(episode)
    if used != set(lookup):
        raise ValueError("every supplied episode must be assigned by the manifest")
    return result


@dataclass(frozen=True)
class RidgeWindReadout:
    mean: np.ndarray
    scale: np.ndarray
    coefficients: np.ndarray
    intercept: np.ndarray
    alpha: float
    source_identity: dict

    @property
    def dimension(self):
        return len(self.mean)

    @classmethod
    def fit(cls, features, labels_local_rad, *, alpha, source_identity):
        x = _features(features)
        labels = np.asarray(labels_local_rad, dtype=np.float64)
        if labels.shape != (len(x),) or not np.isfinite(labels).all():
            raise ValueError("labels_local_rad must be a finite N-vector")
        if not np.isfinite(alpha) or alpha <= 0:
            raise ValueError("alpha must be finite and positive")
        mean, scale = x.mean(axis=0), x.std(axis=0)
        scale[scale == 0] = 1.0
        z = (x - mean) / scale
        y = np.column_stack((np.sin(labels), np.cos(labels)))
        intercept = y.mean(axis=0)
        # Centering removes the intercept from the penalty; dual solve avoids D^3 for N<D.
        centered = y - intercept
        if len(x) < x.shape[1]:
            coefficients = z.T @ np.linalg.solve(z @ z.T + alpha * np.eye(len(x)), centered)
        else:
            coefficients = np.linalg.solve(z.T @ z + alpha * np.eye(x.shape[1]), z.T @ centered)
        return cls(mean, scale, coefficients, intercept, float(alpha), _source(source_identity))

    def predict_vectors(self, features):
        """Return sin/cos vectors. Norm is NOT a calibrated confidence score."""
        x = _features(features, self.dimension)
        return ((x - self.mean) / self.scale) @ self.coefficients + self.intercept

    def save(self, path):
        path = Path(path)
        with path.open("xb") as file:
            np.savez(file, version=np.array(MODEL_VERSION), dimension=np.array(self.dimension),
                     mean=self.mean, scale=self.scale, coefficients=self.coefficients,
                     intercept=self.intercept, alpha=np.array(self.alpha),
                     source_identity_json=np.array(json.dumps(self.source_identity, sort_keys=True)))

    @classmethod
    def load(cls, path, *, expected_source_identity=None, expected_dimension=None):
        fields = {"version", "dimension", "mean", "scale", "coefficients", "intercept", "alpha", "source_identity_json"}
        with np.load(path, allow_pickle=False) as data:
            if set(data.files) != fields or data["version"].item() != MODEL_VERSION:
                raise ValueError("unsupported model schema/version")
            d = data["dimension"].item()
            if not isinstance(d, int) or d <= 0 or (expected_dimension is not None and d != expected_dimension):
                raise ValueError("model feature dimension mismatch")
            arrays = {k: np.array(data[k], dtype=np.float64, copy=True)
                      for k in ("mean", "scale", "coefficients", "intercept")}
            shapes = {"mean": (d,), "scale": (d,), "coefficients": (d, 2), "intercept": (2,)}
            if any(arrays[k].shape != shapes[k] or not np.isfinite(arrays[k]).all() for k in arrays):
                raise ValueError("invalid model arrays")
            if np.any(arrays["scale"] <= 0):
                raise ValueError("model scales must be positive")
            alpha = float(data["alpha"].item())
            if not np.isfinite(alpha) or alpha <= 0:
                raise ValueError("invalid model alpha")
            source = _source(json.loads(str(data["source_identity_json"].item())))
            if expected_source_identity is not None and source != _source(expected_source_identity):
                raise ValueError("frozen source identity mismatch")
            return cls(**arrays, alpha=alpha, source_identity=source)


@dataclass(frozen=True)
class WindEstimate:
    local_rad: float
    world_rad: float
    valid: bool
    vector_norm: float


class CausalWindFilter:
    """One episode's world-frame circular EMA; no labels, environment or wind queries."""
    def __init__(self, model: RidgeWindReadout, *, warmup=10, min_norm=1e-6, ema_weight=0.25):
        if not isinstance(warmup, int) or warmup < 0:
            raise ValueError("warmup must be a nonnegative integer")
        if not np.isfinite(min_norm) or min_norm <= 0:
            raise ValueError("min_norm must be positive")
        if not np.isfinite(ema_weight) or not 0 < ema_weight <= 1:
            raise ValueError("ema_weight must be in (0,1]")
        self.model, self.warmup, self.min_norm, self.ema_weight = model, warmup, min_norm, ema_weight
        self._world_vector = None

    def update(self, features, *, frame_angle, history_count) -> WindEstimate:
        if not np.isfinite(frame_angle) or not isinstance(history_count, (int, np.integer)) or history_count < 0:
            raise ValueError("invalid frame_angle/history_count")
        vector = self.model.predict_vectors(np.asarray(features)[None, :])[0]
        norm = float(np.linalg.norm(vector))
        if history_count < self.warmup or norm < self.min_norm:
            return WindEstimate(float("nan"), float("nan"), False, norm)
        angle = float(local_to_world(np.arctan2(vector[0], vector[1]), frame_angle))
        unit = np.array([np.sin(angle), np.cos(angle)])
        candidate = unit if self._world_vector is None else (1 - self.ema_weight) * self._world_vector + self.ema_weight * unit
        if np.linalg.norm(candidate) < self.min_norm:
            # Opposite vectors cancel; do not invent a direction or corrupt the last state.
            return WindEstimate(float("nan"), float("nan"), False, norm)
        self._world_vector = candidate
        world = float(np.arctan2(candidate[0], candidate[1]))
        return WindEstimate(float(world_to_local(world, frame_angle)), world, True, norm)


def predict_episode(model, episode, *, warmup=10, min_norm=1e-6, ema_weight=0.25):
    if model.source_identity != episode.source_identity:
        raise ValueError("frozen source identity mismatch")
    state = CausalWindFilter(model, warmup=warmup, min_norm=min_norm, ema_weight=ema_weight)
    return [state.update(x, frame_angle=float(frame), history_count=int(history))
            for x, frame, history in zip(episode.features, episode.frame_angle, episode.history_count)]


def circular_metrics(predicted_rad, labels_rad, valid=None):
    prediction, labels = np.asarray(predicted_rad), np.asarray(labels_rad)
    if prediction.ndim != 1 or labels.shape != prediction.shape:
        raise ValueError("metrics require matching one-dimensional angle arrays")
    mask = np.ones(prediction.shape, dtype=bool) if valid is None else np.asarray(valid, dtype=bool)
    if mask.shape != prediction.shape or not np.isfinite(labels).all() or not np.isfinite(prediction[mask]).all():
        raise ValueError("invalid metrics inputs")
    errors = np.abs(wrap_angle(prediction[mask] - labels[mask])) * 180 / np.pi
    return {"status": "ok" if len(errors) else "empty", "count": int(len(errors)),
            "total_count": int(len(prediction)), "mae_deg": float(errors.mean()) if len(errors) else None,
            "p90_deg": float(np.percentile(errors, 90)) if len(errors) else None}


def evaluate_episodes(model, episodes, *, warmup=10, min_norm=1e-6, ema_weight=0.25, window_steps=10):
    """Aggregate frame-weighted errors; event windows include event step + next W-1 steps."""
    if not isinstance(window_steps, int) or window_steps <= 0:
        raise ValueError("window_steps must be positive")
    predictions, labels, validity, switches, changes = [], [], [], [], []
    for episode in episodes:
        estimates = predict_episode(model, episode, warmup=warmup, min_norm=min_norm, ema_weight=ema_weight)
        predictions.extend(e.local_rad for e in estimates)
        labels.extend(episode.labels_local_rad)
        validity.extend(e.valid for e in estimates)
        for flags, target in ((episode.goal_switch, switches), (episode.wind_change, changes)):
            mask = np.zeros(len(flags), dtype=bool)
            for i in np.flatnonzero(flags):
                mask[i:min(i + window_steps, len(flags))] = True
            target.extend(mask)
    valid = np.asarray(validity, dtype=bool)
    return {"overall": circular_metrics(predictions, labels, valid),
            "goal_switch_window": circular_metrics(predictions, labels, valid & np.asarray(switches, dtype=bool)),
            "wind_change_response_window": circular_metrics(predictions, labels, valid & np.asarray(changes, dtype=bool)),
            "window_steps": window_steps, "norm_semantics": "degeneracy_only_not_confidence"}
