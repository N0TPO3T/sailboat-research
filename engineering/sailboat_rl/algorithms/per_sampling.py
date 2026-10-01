import torch


PER_BACKENDS = ("legacy", "optimized")


def validate_per_backend(backend: str) -> str:
    if backend not in PER_BACKENDS:
        raise ValueError(f"Unknown PER backend {backend!r}; expected one of {PER_BACKENDS}")
    return backend


def optimized_priority_distribution(
    priorities: torch.Tensor,
    epsilon: float,
    alpha: float,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Return unnormalized PER weights and their sum on the priority device."""
    scaled = (priorities.flatten() + epsilon).pow(alpha)
    total = scaled.sum()
    if not bool(torch.isfinite(scaled).all().item()) or not bool(torch.isfinite(total).item()) or total.item() <= 0:
        scaled = torch.ones_like(scaled)
        total = scaled.sum()
    return scaled, total


def optimized_sample(
    priorities: torch.Tensor,
    size: int,
    batch_size: int,
    epsilon: float,
    alpha: float,
    beta: float,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Sample independent PER indices with replacement using a device-side CDF."""
    scaled, total = optimized_priority_distribution(priorities[:size], epsilon, alpha)
    cumulative = torch.cumsum(scaled, dim=0)
    actual_batch_size = min(batch_size, size)
    targets = torch.rand(actual_batch_size, device=priorities.device) * total
    indices = torch.searchsorted(cumulative, targets, right=True).clamp_max_(size - 1)

    selected_probs = (scaled[indices] / total).view(-1, 1)
    weights = (size * selected_probs).pow(-beta)
    weights = weights / weights.max()
    return indices, weights
