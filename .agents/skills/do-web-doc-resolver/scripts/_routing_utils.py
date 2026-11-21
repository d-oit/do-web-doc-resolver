import logging

from scripts.routing_outcomes import DEFAULT_PROVIDER_STATS

logger = logging.getLogger(__name__)


def compute_p75_latency(avg_latency_ms: float, default: int = 3000) -> int:
    if avg_latency_ms == 0:
        return default
    return int(avg_latency_ms * 1.5)


__all__ = ["DEFAULT_PROVIDER_STATS", "compute_p75_latency", "logger"]
