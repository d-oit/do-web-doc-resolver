"""
Per-domain and query-context routing memory for the Web Doc Resolver.
"""

from __future__ import annotations

import json
import logging
import math
import os
import threading
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, cast

from scripts._routing_utils import DEFAULT_PROVIDER_STATS, compute_p75_latency
from scripts.routing_context import is_query_context_key
from scripts.routing_outcomes import (
    CONTENT_OUTCOMES,
    MIN_EVIDENCE,
    TRANSPORT_OUTCOMES,
    confidence,
    content_attempts,
    merge_stats,
    migrate_document,
    normalize_stats,
    outcome_counts,
    record_stats,
)

LEGACY_QUERY_KEY = "query"
GENERAL_QUERY_KEY = "q:v2:general:general:na:none"

logger = logging.getLogger(__name__)
SCORE_BASE = 0.5
RECENCY_DECAY_DAYS = 7.0
SCORE_SCALE = 1000.0
SAVE_INTERVAL_SECONDS = 5.0
MEMORY_SCHEMA_VERSION = 2

ROUTING_MODES = frozenset({"off", "shadow", "active"})
DEFAULT_QUERY_ROUTING_MODE = "shadow"


def _default_stats() -> dict[str, Any]:
    return normalize_stats(DEFAULT_PROVIDER_STATS)


class RoutingMemory:
    """Thread-safe routing statistics with versioned persistence.

    Domain keys keep their historical active ranking. Query keys use the
    context-aware ranking and default to ``shadow``: outcomes are recorded and
    explainable, but the static provider order is preserved until the operator
    opts into ``DO_WDR_ROUTING_MODE=active``.
    """

    def __init__(self, path: str | os.PathLike[str] | None = None, mode: str | None = None) -> None:
        self.domain_stats: dict[str, dict[str, dict[str, Any]]] = defaultdict(
            lambda: defaultdict(_default_stats)
        )
        self._lock = threading.RLock()
        self._path = Path(path) if path is not None else None
        self._last_save = 0.0
        self._persistence_unsupported = False
        self._loaded_schema_version = MEMORY_SCHEMA_VERSION
        configured = (
            mode or os.getenv("DO_WDR_ROUTING_MODE") or DEFAULT_QUERY_ROUTING_MODE
        ).lower()
        self.mode = configured if configured in ROUTING_MODES else DEFAULT_QUERY_ROUTING_MODE
        if self._path is not None:
            self._load_from_disk()

    @property
    def schema_version(self) -> int:
        return self._loaded_schema_version

    # --- Persistence -------------------------------------------------------

    def _load_from_disk(self) -> None:
        if self._path is None or not self._path.exists():
            return
        try:
            with self._path.open("r", encoding="utf-8") as fh:
                raw = json.load(fh)
            stats, source_version, supported = migrate_document(raw)
            self._loaded_schema_version = source_version
            if not supported:
                self._persistence_unsupported = True
                logger.warning(
                    "Routing memory at %s uses schema %s, newer than supported %s; "
                    "persistence disabled to avoid destroying data",
                    self._path,
                    source_version,
                    MEMORY_SCHEMA_VERSION,
                )
                return
            for domain, providers in stats.items():
                for provider, provider_stats in providers.items():
                    self.domain_stats[domain][provider] = provider_stats
            legacy = self.domain_stats.pop(LEGACY_QUERY_KEY, None)
            if legacy:
                for provider, legacy_stats in legacy.items():
                    current = self.domain_stats[GENERAL_QUERY_KEY][provider]
                    if current == normalize_stats(DEFAULT_PROVIDER_STATS):
                        self.domain_stats[GENERAL_QUERY_KEY][provider] = legacy_stats
                    else:
                        merge_stats(current, legacy_stats)
            logger.debug(
                "Loaded routing memory from %s (schema %s -> %s)",
                self._path,
                source_version,
                MEMORY_SCHEMA_VERSION,
            )
        except (OSError, ValueError, TypeError) as e:
            logger.warning("Failed to load routing memory from %s: %s", self._path, e)

    def _save_to_disk_unlocked(self) -> None:
        if self._path is None or self._persistence_unsupported:
            return
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            data = {d: dict(ps) for d, ps in self.domain_stats.items()}
            document = {
                "version": MEMORY_SCHEMA_VERSION,
                "kind": "routing_memory",
                "stats": data,
            }
            tmp = self._path.with_suffix(self._path.suffix + ".tmp")
            with tmp.open("w", encoding="utf-8") as fh:
                json.dump(document, fh, sort_keys=True)
            tmp.replace(self._path)
            self._last_save = time.time()
            self._loaded_schema_version = MEMORY_SCHEMA_VERSION
        except OSError as e:
            logger.warning("Failed to save routing memory to %s: %s", self._path, e)

    def save(self) -> None:
        """Flush routing memory to disk (no-op when no path is configured)."""
        with self._lock:
            self._save_to_disk_unlocked()

    def record(
        self,
        domain: str,
        provider: str,
        success: bool,
        latency_ms: int,
        quality_score: float,
        *,
        outcome: str | None = None,
        contributed: bool = False,
    ) -> None:
        """Record an attempt.

        The legacy boolean form remains supported; it maps to ``success`` or
        ``low_quality``. Explicit transport outcomes do not increment the
        content failure counter.
        """
        resolved = outcome or ("success" if success else "low_quality")
        if resolved not in CONTENT_OUTCOMES and resolved not in TRANSPORT_OUTCOMES:
            resolved = "unknown" if resolved != "no_result" else "no_result"
        with self._lock:
            stats = self.domain_stats[domain][provider]
            record_stats(
                stats,
                outcome=resolved,
                latency_ms=latency_ms,
                quality_score=quality_score,
                contributed=contributed,
            )
            if self._path is not None and time.time() - self._last_save >= SAVE_INTERVAL_SECONDS:
                self._save_to_disk_unlocked()

    def record_outcome(
        self,
        key: str,
        provider: str,
        outcome: str,
        latency_ms: int,
        quality_score: float,
        *,
        contributed: bool = False,
    ) -> None:
        self.record(
            key,
            provider,
            outcome == "success",
            latency_ms,
            quality_score,
            outcome=outcome,
            contributed=contributed,
        )

    def get_domain_stats(self, provider: str, domain: str) -> dict[str, Any] | None:
        with self._lock:
            domain_dict = self.domain_stats.get(domain)
            if not domain_dict:
                return None
            stats = domain_dict.get(provider)
            if not stats:
                return None

            s = cast(int, stats.get("success", 0))
            f = cast(int, stats.get("failure", 0))
            attempts = s + f
            counts = outcome_counts(stats)
            if attempts == 0 and sum(counts.values()) == 0:
                return None

            success_rate = float(s) / max(attempts, 1)
            days_since_last = 0.0
            last = cast(float | None, stats.get("last_attempted"))
            if last:
                days_since_last = (time.time() - last) / 86400.0

            total_attempts = sum(counts.values())
            transport_failures = sum(counts.get(name, 0) for name in TRANSPORT_OUTCOMES)
            return {
                "attempts": attempts,
                "total_attempts": total_attempts,
                "success_rate": success_rate,
                "avg_latency_ms": stats.get("avg_latency_ms", 0.0),
                "avg_quality": stats.get("avg_quality", 0.5),
                "days_since_last": days_since_last,
                "confidence": confidence(stats),
                "content_attempts": content_attempts(stats),
                "outcome_counts": counts,
                "transport_failures": transport_failures,
                "contributed": int(stats.get("contributed", 0) or 0),
            }

    def _score_stats(self, stats: dict[str, Any]) -> float:
        success = cast(int, stats.get("success", 0))
        failure = cast(int, stats.get("failure", 0))
        attempts = success + failure
        if attempts == 0:
            return SCORE_BASE

        success_rate = float(success) / max(attempts, 1)
        days_since_last = 0.0
        last = cast(float | None, stats.get("last_attempted"))
        if last:
            days_since_last = (time.time() - last) / 86400.0

        avg_quality = float(stats.get("avg_quality", SCORE_BASE) or SCORE_BASE)
        quality_factor = SCORE_BASE + SCORE_BASE * avg_quality
        recency = math.exp(-days_since_last / RECENCY_DECAY_DAYS)
        latency = float(stats.get("avg_latency_ms", 0.0) or 0.0)
        return (success_rate * quality_factor * recency) * SCORE_SCALE / max(latency, 1.0)

    def _query_score(self, stats: dict[str, Any]) -> float:
        """Content quality score with an explicit availability discount."""
        base = self._score_stats(stats)
        counts = outcome_counts(stats)
        total = sum(counts.values())
        transport = sum(counts.get(name, 0) for name in TRANSPORT_OUTCOMES)
        availability = 1.0 if total == 0 else max(0.5, 1.0 - (transport / total))
        return base * availability

    def _rank_legacy(self, domain: str, providers: list[str]) -> list[str]:
        scores = {}
        for p in providers:
            stats = self.domain_stats.get(domain, {}).get(p)
            scores[p] = self._score_stats(stats) if stats else SCORE_BASE
            if stats:
                logger.debug("Provider score: key=%s provider=%s score=%.4f", domain, p, scores[p])
        return sorted(providers, key=lambda p: scores[p], reverse=True)

    def _query_breakdown(self, key: str, providers: list[str]) -> dict[str, dict[str, float]]:
        """Blend learned content evidence with the static order and availability.

        ``confidence`` reaches 1.0 only after ``MIN_EVIDENCE`` content attempts,
        so one or two observations move a route modestly rather than replacing
        the whole plan. Transport-only failures reduce availability without
        changing the content success rate.
        """
        base = list(providers)
        raw: dict[str, float] = {}
        for provider in base:
            stats = self.domain_stats.get(key, {}).get(provider)
            raw[provider] = self._query_score(stats) if stats and content_attempts(stats) else 0.0
        gated = {
            provider: (self.domain_stats.get(key, {}).get(provider) is not None)
            and content_attempts(self.domain_stats[key][provider]) >= MIN_EVIDENCE
            for provider in base
        }
        max_raw = max((raw[p] for p in base if gated[p]), default=0.0)
        n = len(base)
        breakdown: dict[str, dict[str, float]] = {}
        for index, provider in enumerate(base):
            stats = self.domain_stats.get(key, {}).get(provider)
            counts = outcome_counts(stats) if stats else {}
            total = sum(counts.values())
            transport = sum(counts.get(name, 0) for name in TRANSPORT_OUTCOMES)
            availability = 1.0 if total == 0 else max(0.0, 1.0 - (transport / total))
            conf = confidence(stats) if stats else 0.0
            # Minimum-evidence gate: below MIN_EVIDENCE content attempts the
            # static prior wins outright, so one or two observations cannot
            # materially promote or demote a route.
            weight = 1.0 if gated[provider] else 0.0
            # The static prior is deliberately small: cold-start order is
            # preserved, but any fully observed success outranks an unobserved
            # provider and a fully observed quality failure does not.
            prior = 0.3 * (1.0 - (index / n)) if n else 0.3
            learned_component = (raw[provider] / max_raw) if max_raw and weight else 0.0
            blended = (
                weight * learned_component + (1.0 - weight) * prior - (1.0 - availability) * 0.5
            )
            breakdown[provider] = {
                "prior": prior,
                "learned_component": learned_component,
                "confidence": conf,
                "evidence_gate": weight,
                "availability": availability,
                "blended": blended,
            }
        return breakdown

    def _rank_query(self, key: str, providers: list[str]) -> list[str]:
        breakdown = self._query_breakdown(key, providers)
        return sorted(
            providers,
            key=lambda provider: (-breakdown[provider]["blended"], providers.index(provider)),
        )

    def rank_providers(
        self, domain: str, providers: list[str], mode: str | None = None
    ) -> list[str]:
        with self._lock:
            effective = (mode or self.mode).lower()
            if effective not in ROUTING_MODES:
                effective = self.mode
            if effective == "off":
                return list(providers)
            if is_query_context_key(domain):
                if effective == "shadow":
                    return list(providers)
                return self._rank_query(domain, providers)
            # Domain/URL routing keeps its historical active behavior.
            if effective == "shadow" and mode is not None:
                return list(providers)
            return self._rank_legacy(domain, providers)

    def rank(self, domain: str, providers: list[str]) -> list[str]:
        """Backward compatibility for rank method."""
        return self.rank_providers(domain, providers)

    def explain(self, domain: str, providers: list[str]) -> list[dict[str, Any]]:
        """Expose the score breakdown and sample support behind a route."""
        with self._lock:
            active = self.rank_providers(domain, providers, mode="active")
            learned_rank = {provider: index + 1 for index, provider in enumerate(active)}
            breakdown = (
                self._query_breakdown(domain, providers) if is_query_context_key(domain) else {}
            )
            rows: list[dict[str, Any]] = []
            for static_rank, provider in enumerate(providers, start=1):
                stats = self.domain_stats.get(domain, {}).get(provider)
                extra = breakdown.get(provider, {})
                if stats is None:
                    rows.append(
                        {
                            "provider": provider,
                            "static_rank": static_rank,
                            "learned_rank": learned_rank[provider],
                            "sample_count": 0,
                            "total_attempts": 0,
                            "confidence": 0.0,
                            "score": SCORE_BASE,
                            "success_rate": None,
                            "avg_quality": None,
                            "avg_latency_ms": None,
                            "outcomes": {},
                            "transport_failures": 0,
                            "contributed": 0,
                            **extra,
                        }
                    )
                    continue
                counts = outcome_counts(stats)
                success = cast(int, stats.get("success", 0))
                failure = cast(int, stats.get("failure", 0))
                rows.append(
                    {
                        "provider": provider,
                        "static_rank": static_rank,
                        "learned_rank": learned_rank[provider],
                        "sample_count": success + failure,
                        "total_attempts": sum(counts.values()),
                        "confidence": confidence(stats),
                        "score": (
                            self._query_score(stats)
                            if is_query_context_key(domain)
                            else self._score_stats(stats)
                        ),
                        "success_rate": (
                            (success / (success + failure)) if success + failure else None
                        ),
                        "avg_quality": stats.get("avg_quality"),
                        "avg_latency_ms": stats.get("avg_latency_ms"),
                        "outcomes": counts,
                        "transport_failures": sum(
                            counts.get(name, 0) for name in TRANSPORT_OUTCOMES
                        ),
                        "contributed": int(stats.get("contributed", 0) or 0),
                        **extra,
                    }
                )
            return rows

    def get_p75_latency(self, domain: str, provider: str, default: int = 3000) -> int:
        with self._lock:
            domain_dict = self.domain_stats.get(domain)
            if not domain_dict:
                return default
            stats = domain_dict.get(provider)
            if not stats:
                return default
            return compute_p75_latency(cast(float, stats.get("avg_latency_ms", 0.0)), default)

    def clear(self) -> None:
        with self._lock:
            self.domain_stats.clear()


__all__ = [
    "DEFAULT_QUERY_ROUTING_MODE",
    "MEMORY_SCHEMA_VERSION",
    "MIN_EVIDENCE",
    "ROUTING_MODES",
    "RoutingMemory",
]
