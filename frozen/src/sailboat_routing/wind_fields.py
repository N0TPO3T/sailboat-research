"""Environment-private, continuous synthetic wind; no planning-grid dependency."""
from dataclasses import asdict, dataclass
import math
import random


@dataclass(frozen=True, slots=True)
class WindProfile:
    direction_amplitude_rad: float
    speed_fraction: float
    temporal_period_s: float
    spatial_wavelength_m: float
    perturbation_period_s: float
    perturbation_amplitude_rad: float
    transition_duration_s: float


PROFILES = {
    "stable": WindProfile(0.0, 0.0, 1200.0, 2000.0, 120.0, 0.0, 60.0),
    "slow": WindProfile(math.radians(25), 0.12, 1800.0, 2400.0, 180.0, math.radians(3), 60.0),
    "fast": WindProfile(math.radians(45), 0.20, 480.0, 1200.0, 60.0, math.radians(6), 30.0),
}


class SyntheticWindField:
    """Pure (world x metres, world y metres, physical seconds) -> local wind.

    A private RNG chooses phases and independent coarse perturbation knots once.
    Smoothstep interpolates those knots, then the resulting perturbation is
    precomputed at integer seconds and linearly interpolated for fractional time.
    Sampling never advances an RNG. Profiles are bounded, analytic spatial waves,
    not a reconstructed weather map. Stable means exactly fixed speed/direction.
    Varying profiles start with base wind, then smoothly activate the waves at
    change_onsets[0]. Onsets are environment/offline metadata, never planner input.
    """

    def __init__(self, seed, base_direction_rad, profile="stable", horizon=2400,
                 base_speed=8.0):
        if profile not in PROFILES:
            raise ValueError("profile must be stable, slow, or fast")
        if not all(math.isfinite(v) for v in (base_direction_rad, horizon, base_speed)):
            raise ValueError("Wind parameters must be finite")
        if horizon <= 0 or base_speed <= 0:
            raise ValueError("horizon and base_speed must be positive")
        self.seed = seed
        self.base_direction_rad = float(base_direction_rad)
        self.profile = profile
        self.horizon = float(horizon)
        self.base_speed = float(base_speed)
        self.parameters = PROFILES[profile]
        self.change_onsets = () if profile == "stable" else (int(min(100, horizon / 4)),)
        rng = random.Random(seed)
        self._phases = tuple(rng.uniform(-math.pi, math.pi) for _ in range(3))
        period = self.parameters.perturbation_period_s
        knots = tuple(rng.uniform(-1, 1) for _ in range(math.ceil(horizon / period) + 2))
        perturbations = []
        for second in range(math.ceil(horizon) + 1):
            index = int(second / period)
            fraction = second / period - index
            smooth = fraction * fraction * (3 - 2 * fraction)
            perturbations.append(knots[index] * (1 - smooth) + knots[index + 1] * smooth)
        self._perturbations = tuple(perturbations)

    def sample(self, xy, time_s):
        """Return (m/s, world blowing-TOWARD angle radians in [-pi, pi))."""
        x, y = map(float, xy)
        if not all(math.isfinite(v) for v in (x, y, time_s)):
            raise ValueError("Wind query must be finite")
        if not 0 <= time_s <= self.horizon:
            raise ValueError("Wind query time is outside the predeclared horizon")
        p = self.parameters
        second = math.floor(time_s)
        fraction = time_s - second
        perturbation = self._perturbations[second]
        if fraction:
            perturbation += fraction * (self._perturbations[second + 1] - perturbation)
        temporal = 2 * math.pi * time_s / p.temporal_period_s
        spatial = 2 * math.pi / p.spatial_wavelength_m
        wave = (0.65 * math.sin(temporal + spatial * (0.8 * x + 0.6 * y) + self._phases[0])
                + 0.35 * math.sin(0.53 * temporal + spatial * (-0.6 * x + 0.8 * y) + self._phases[1]))
        activation = 0.0
        if self.change_onsets:
            onset = self.change_onsets[0]
            duration = min(p.transition_duration_s, self.horizon - onset)
            progress = max(0.0, min(1.0, (time_s - onset) / duration))
            activation = progress * progress * (3 - 2 * progress)
        angle = (self.base_direction_rad + activation * (
            p.direction_amplitude_rad * wave + p.perturbation_amplitude_rad * perturbation))
        speed = self.base_speed * (1 + activation * p.speed_fraction * math.sin(
            0.73 * temporal + spatial * (0.6 * x - 0.8 * y) + self._phases[2]))
        return speed, (angle + math.pi) % (2 * math.pi) - math.pi

    def diagnostics(self):
        """Environment/offline metadata only; NEVER pass this or self to planner."""
        return {"kind": "synthetic", "seed": self.seed, "profile": self.profile,
                "fixed_wind": self.profile == "stable",
                "spatially_varying": self.profile != "stable",
                "temporally_varying": self.profile != "stable",
                "change_onsets": self.change_onsets,
                "base_speed_m_s": self.base_speed,
                "base_direction_toward_world_rad": self.base_direction_rad,
                "horizon_s": self.horizon, "parameters": asdict(self.parameters)}
