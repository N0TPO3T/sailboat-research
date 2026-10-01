"""Canonical SailBoatRL environment and algorithm package."""

from gymnasium.envs.registration import register, registry


_ENV_SPECS = {
    "sailboat-s14-nowind": "sailboat_rl.envs:Sailboat_nowind_last",
    "sailboat-s14-wind": "sailboat_rl.envs:Sailboat_wind_last",
}


def register_envs() -> None:
    """Register the canonical environments without modifying Gymnasium itself."""
    for env_id, entry_point in _ENV_SPECS.items():
        if env_id not in registry:
            register(id=env_id, entry_point=entry_point, max_episode_steps=3000)


register_envs()

