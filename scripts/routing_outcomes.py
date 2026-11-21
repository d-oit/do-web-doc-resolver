"""Structured provider-attempt outcomes for routing memory.

A transport failure (blocked, rate-limited, timeout, auth, server error) is not
evidence that a provider returns bad content. The router therefore keeps
content outcomes and transport outcomes separate and exposes both in its
ranking explanation.
"""

from __future__ import annotations

import time
from enum import StrEnum
from typing import Any

MIN_EVIDENCE = 3
CONTENT_OUTCOMES = frozenset({"success", "low_quality"})
TRANSPORT_OUTCOMES = frozenset(
    {
        "blocked",
        "rate_limited",
        "timeout",
        "auth_error",
        "server_error",
        "transport_error",
    }
)
KNOWN_OUTCOMES = CONTENT_OUTCOMES | TRANSPORT_OUTCOMES | {"no_result", "unknown"}


class Outcome(StrEnum):
    SUCCESS = "success"
    LOW_QUALITY = "low_quality"
    NO_RESULT = "no_result"
    BLOCKED = "blocked"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    AUTH_ERROR = "auth_error"
    SERVER_ERROR = "server_error"
    TRANSPORT_ERROR = "transport_error"
    UNKNOWN = "unknown"


DEFAULT_OUTCOME_COUNTS: dict[str, int] = {outcome.value: 0 for outcome in Outcome}

DEFAULT_PROVIDER_STATS: dict[str, Any] = {
    "success": 0,
    "failure": 0,
    "outcomes": dict(DEFAULT_OUTCOME_COUNTS),
    "contributed": 0,
    "avg_latency_ms": 0.0,
    "avg_quality": 0.0,
    "last_attempted": None,
}


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_stats(raw: Any) -> dict[str, Any]:
    """Return a defensively filled stats entry for legacy or partial data."""
    stats: dict[str, Any] = {
        "success": 0,
        "failure": 0,
        "outcomes": dict(DEFAULT_OUTCOME_COUNTS),
        "contributed": 0,
        "avg_latency_ms": 0.0,
        "avg_quality": 0.0,
        "last_attempted": None,
    }
    if not isinstance(raw, dict):
        return stats

    stats["success"] = max(0, _as_int(raw.get("success")))
    stats["failure"] = max(0, _as_int(raw.get("failure")))
    stats["contributed"] = max(0, _as_int(raw.get("contributed")))
    stats["avg_latency_ms"] = max(0.0, _as_float(raw.get("avg_latency_ms")))
    stats["avg_quality"] = min(1.0, max(0.0, _as_float(raw.get("avg_quality"))))
    last = raw.get("last_attempted")
    stats["last_attempted"] = _as_float(last) if last is not None else None

    raw_outcomes = raw.get("outcomes")
    if isinstance(raw_outcomes, dict):
        for name in DEFAULT_OUTCOME_COUNTS:
            stats["outcomes"][name] = max(0, _as_int(raw_outcomes.get(name)))
        if sum(stats["outcomes"].values()) == 0 and (stats["success"] or stats["failure"]):
            stats["outcomes"]["success"] = stats["success"]
            stats["outcomes"]["low_quality"] = stats["failure"]
    else:
        # Legacy flat entries only had success/failure. Preserve their evidence
        # as content outcomes rather than inventing transport failures.
        stats["outcomes"]["success"] = stats["success"]
        stats["outcomes"]["low_quality"] = stats["failure"]
    return stats


def migrate_document(raw: Any) -> tuple[dict[str, dict[str, dict[str, Any]]], int, bool]:
    """Load a versioned envelope or migrate the legacy flat mapping.

    Returns ``(stats, source_version, supported)``. An unsupported newer version
    is not rewritten: callers must disable persistence instead of destroying
    data written by a newer resolver.
    """
    if not isinstance(raw, dict):
        return {}, 0, True

    source_version = 1
    supported = True
    if "version" in raw:
        source_version = _as_int(raw.get("version"), 0)
        if source_version > 2:
            return {}, source_version, False
        data = raw.get("stats") or raw.get("domain_stats") or {}
    else:
        data = raw

    if not isinstance(data, dict):
        return {}, source_version, True

    migrated: dict[str, dict[str, dict[str, Any]]] = {}
    for domain, providers in data.items():
        if not isinstance(providers, dict):
            continue
        migrated[str(domain)] = {
            str(provider): normalize_stats(stats) for provider, stats in providers.items()
        }
    return migrated, source_version, supported


def record_stats(
    stats: dict[str, Any],
    *,
    outcome: str,
    latency_ms: int,
    quality_score: float,
    contributed: bool,
) -> None:
    """Update one stats entry in place."""
    name = outcome if outcome in KNOWN_OUTCOMES else "unknown"
    outcomes = stats.setdefault("outcomes", dict(DEFAULT_OUTCOME_COUNTS))
    outcomes[name] = _as_int(outcomes.get(name)) + 1

    total_attempts = sum(max(0, _as_int(v)) for v in outcomes.values())
    previous_attempts = max(0, total_attempts - 1)
    avg_latency = _as_float(stats.get("avg_latency_ms"))
    stats["avg_latency_ms"] = ((avg_latency * previous_attempts) + max(0, int(latency_ms))) / max(
        total_attempts, 1
    )
    stats["last_attempted"] = time.time()

    if name == "success":
        stats["success"] = _as_int(stats.get("success")) + 1
    elif name == "low_quality":
        stats["failure"] = _as_int(stats.get("failure")) + 1

    if name in CONTENT_OUTCOMES:
        content_attempts = _as_int(stats.get("success")) + _as_int(stats.get("failure"))
        previous_content = max(0, content_attempts - 1)
        avg_quality = _as_float(stats.get("avg_quality"))
        stats["avg_quality"] = min(
            1.0,
            max(
                0.0,
                ((avg_quality * previous_content) + max(0.0, min(1.0, quality_score)))
                / max(content_attempts, 1),
            ),
        )
    if contributed:
        stats["contributed"] = _as_int(stats.get("contributed")) + 1


def merge_stats(target: dict[str, Any], source: dict[str, Any]) -> None:
    """Merge a legacy aggregate bucket into a context bucket."""
    target_total = sum(outcome_counts(target).values())
    source_total = sum(outcome_counts(source).values())
    target["success"] = _as_int(target.get("success")) + _as_int(source.get("success"))
    target["failure"] = _as_int(target.get("failure")) + _as_int(source.get("failure"))
    target["contributed"] = _as_int(target.get("contributed")) + _as_int(source.get("contributed"))
    merged_outcomes = outcome_counts(target)
    for name, value in outcome_counts(source).items():
        merged_outcomes[name] += value
    target["outcomes"] = merged_outcomes
    total = target_total + source_total
    if total:
        target["avg_latency_ms"] = (
            _as_float(target.get("avg_latency_ms")) * target_total
            + _as_float(source.get("avg_latency_ms")) * source_total
        ) / total
        target["avg_quality"] = (
            _as_float(target.get("avg_quality")) * target_total
            + _as_float(source.get("avg_quality")) * source_total
        ) / total
    last_values = [
        value
        for value in (target.get("last_attempted"), source.get("last_attempted"))
        if value is not None
    ]
    target["last_attempted"] = max(last_values) if last_values else None


def outcome_counts(stats: dict[str, Any]) -> dict[str, int]:
    raw = stats.get("outcomes")
    if not isinstance(raw, dict):
        return {
            **DEFAULT_OUTCOME_COUNTS,
            "success": _as_int(stats.get("success")),
            "low_quality": _as_int(stats.get("failure")),
        }
    return {name: max(0, _as_int(raw.get(name))) for name in DEFAULT_OUTCOME_COUNTS}


def content_attempts(stats: dict[str, Any]) -> int:
    return _as_int(stats.get("success")) + _as_int(stats.get("failure"))


def confidence(stats: dict[str, Any]) -> float:
    return min(1.0, content_attempts(stats) / MIN_EVIDENCE)


__all__ = [
    "CONTENT_OUTCOMES",
    "DEFAULT_OUTCOME_COUNTS",
    "DEFAULT_PROVIDER_STATS",
    "KNOWN_OUTCOMES",
    "MIN_EVIDENCE",
    "Outcome",
    "TRANSPORT_OUTCOMES",
    "confidence",
    "content_attempts",
    "merge_stats",
    "migrate_document",
    "normalize_stats",
    "outcome_counts",
    "record_stats",
]
