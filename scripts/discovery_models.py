"""Data models shared by the pure and live discovery paths."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

DISCOVERY_SCHEMA_VERSION = 2


@dataclass
class DiscoveryCandidate:
    url: str
    canonical_url: str
    strategy: str
    family: str
    discovery_provider: str
    original_url: str
    publisher_domain: str
    relationship: str
    reason: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    verification_state: str = "unverified"
    redirect_chain: list[str] = field(default_factory=list)
    title: str | None = None
    content_hash: str | None = None
    scores: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DiscoveryInput:
    primary_url: str
    final_url: str | None = None
    html: str = ""
    llms_txt: str | None = None
    search_results: list[dict[str, Any]] = field(default_factory=list)
    query: str | None = None
    redirect_chain: list[str] = field(default_factory=list)


@dataclass
class DiscoveryReport:
    primary_url: str
    candidates: list[DiscoveryCandidate]
    rejected: list[DiscoveryCandidate]
    strategies: list[dict[str, Any]]
    duplicate_count: int
    selected: DiscoveryCandidate | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": DISCOVERY_SCHEMA_VERSION,
            "primary_url": self.primary_url,
            "selected": self.selected.to_dict() if self.selected else None,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "rejected": [candidate.to_dict() for candidate in self.rejected],
            "strategies": self.strategies,
            "duplicate_count": self.duplicate_count,
        }


__all__ = [
    "DISCOVERY_SCHEMA_VERSION",
    "DiscoveryCandidate",
    "DiscoveryInput",
    "DiscoveryReport",
]
