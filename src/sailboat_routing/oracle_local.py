"""Diagnostic-only current wind tap; never passed to the formal planner."""
import math
from .planner import LocalWindEstimate


class CurrentLocalWindOracle:
    """Read the dynamics' CURRENT local direction, with no position/time query API.

    The simulation supervisor owns this object. Only the returned angle/validity
    record may enter an oracle_local planner. No wind speed, seed, field object or
    callback is exposed by that record. This is not available to estimated_local.
    """
    def __init__(self, physics):
        self._physics = physics

    def sample_current(self) -> LocalWindEstimate:
        if self._physics.raw is None:
            raise RuntimeError("Physics must be initialized before reading its current local wind")
        angle = float(self._physics.modules.globals.w_change_d)
        if not math.isfinite(angle):
            return LocalWindEstimate(math.nan, False)
        return LocalWindEstimate(math.atan2(math.sin(angle), math.cos(angle)), True)
