"""Tests for the async provider cascade (`scripts/_cascade_async.py`).

These cover the launch policy (free tier before paid), the quality gate, and
latency-budget enforcement. The module previously had no direct tests, so
regressions in paid-spend behaviour and deadline handling were invisible.
"""

import asyncio
from dataclasses import dataclass

import pytest

from scripts._cascade_async import cascade_stream_async
from scripts.models import ProviderType, ResolvedResult
from scripts.routing import ResolutionBudget


@dataclass
class _FakeBreakers:
    """Minimal CircuitBreakerRegistry stand-in."""

    failures: dict = None
    opened: set = None

    def __post_init__(self):
        self.failures = {}
        self.opened = set()

    def is_open(self, name: str) -> bool:
        return name in self.opened

    def record_failure(self, name: str) -> None:
        self.failures[name] = self.failures.get(name, 0) + 1

    def record_success(self, name: str) -> None:
        self.failures.pop(name, None)


class _FakeMemory:
    def __init__(self):
        self.records = []

    def record(self, *args, **kwargs) -> None:
        self.records.append((args, kwargs))


@dataclass
class _FakeMetrics:
    """Stand-in for ResolveMetrics; `asdict()` requires a dataclass."""

    quality_gate: dict | None = None
    providers: list | None = None

    def __post_init__(self):
        self.providers = []

    def record_provider(self, provider, latency, success) -> None:
        self.providers.append((provider, latency, success))


@pytest.fixture
def free_provider():
    """A free provider returning content good enough to clear the gate."""

    def make(source="jina", content=None, delay=0.0):
        if content is None:
            content = (
                "# Title\n\n" + ("Useful documentation paragraph. " * 60) + "\n\n[x](http://a)\n"
            )

        async def run():
            if delay:
                await asyncio.sleep(delay)
            return ResolvedResult(source=source, url="https://example.com", content=content)

        return ProviderType.FREE, run

    return make


def _budget(**overrides):
    defaults = {
        "max_provider_attempts": 6,
        "max_paid_attempts": 2,
        "max_total_latency_ms": 12_000,
        "min_free_quality_to_skip_paid": 0.70,
        "allow_paid": True,
    }
    defaults.update(overrides)
    return ResolutionBudget(**defaults)


async def _drain(gen):
    return [item async for item in gen]


def test_paid_provider_not_launched_when_free_clears_gate(monkeypatch):
    """A2 regression: paid providers must not fire if a free result passes."""
    launched: list[str] = []

    def paid():
        launched.append("paid")
        raise AssertionError("paid provider should not have been launched")

    async def good_free():
        return ResolvedResult(
            source="jina",
            url="https://example.com",
            content="# T\n\n" + ("Great prose about the subject. " * 80) + "\n\n[x](http://a)\n",
        )

    cascade_map = {
        "jina": (ProviderType.JINA, good_free),
        "tavily": (ProviderType.TAVILY, paid),
    }

    results = asyncio.run(
        _drain(
            cascade_stream_async(
                target="https://example.com",
                cascade_map=cascade_map,
                eligible=["jina", "tavily"],
                budget=_budget(),
                metrics=_FakeMetrics(),
                routing_memory=_FakeMemory(),
                circuit_breakers=_FakeBreakers(),
                semantic_cache_store=lambda *a: False,
                routing_key="example.com",
            )
        )
    )

    assert launched == [], "paid provider ran despite free quality gate"
    assert results[0]["source"] == "jina"


def test_paid_launched_when_free_tier_fails(monkeypatch):
    """Paid escalation still happens when the free tier yields nothing usable."""
    launched: list[str] = []

    async def failing_free():
        return None

    async def paid_ok():
        launched.append("paid")
        return ResolvedResult(
            source="tavily",
            url="https://example.com",
            content="# T\n\n" + ("Excellent paid result content. " * 60) + "\n\n[x](http://a)\n",
        )

    cascade_map = {
        "jina": (ProviderType.JINA, failing_free),
        "tavily": (ProviderType.TAVILY, paid_ok),
    }

    results = asyncio.run(
        _drain(
            cascade_stream_async(
                target="https://example.com",
                cascade_map=cascade_map,
                eligible=["jina", "tavily"],
                budget=_budget(),
                metrics=_FakeMetrics(),
                routing_memory=_FakeMemory(),
                circuit_breakers=_FakeBreakers(),
                semantic_cache_store=lambda *a: False,
                routing_key="example.com",
            )
        )
    )

    assert launched == ["paid"]
    assert results[0]["source"] == "tavily"


def test_latency_budget_cancels_slow_providers():
    """A2 regression: max_total_latency_ms must actually bound the cascade."""

    async def slow_free():
        await asyncio.sleep(5)
        return ResolvedResult(source="jina", url="https://example.com", content="late")

    cascade_map = {"jina": (ProviderType.JINA, slow_free)}

    results = asyncio.run(
        _drain(
            cascade_stream_async(
                target="https://example.com",
                cascade_map=cascade_map,
                eligible=["jina"],
                budget=_budget(max_total_latency_ms=150),
                metrics=_FakeMetrics(),
                routing_memory=_FakeMemory(),
                circuit_breakers=_FakeBreakers(),
                semantic_cache_store=lambda *a: False,
                routing_key="example.com",
            )
        )
    )

    assert results[-1]["source"] == "none"
    assert "Failed" in results[-1]["content"]


def test_no_eligible_providers_reports_failure():
    results = asyncio.run(
        _drain(
            cascade_stream_async(
                target="https://example.com",
                cascade_map={},
                eligible=[],
                budget=_budget(),
                metrics=_FakeMetrics(),
                routing_memory=_FakeMemory(),
                circuit_breakers=_FakeBreakers(),
                semantic_cache_store=lambda *a: False,
                routing_key="example.com",
            )
        )
    )

    assert results[0]["source"] == "none"
    assert "No providers available" in results[0]["error"]


def test_provider_exception_records_circuit_failure():
    breakers = _FakeBreakers()

    async def boom():
        raise RuntimeError("provider exploded")

    cascade_map = {"jina": (ProviderType.JINA, boom)}

    results = asyncio.run(
        _drain(
            cascade_stream_async(
                target="https://example.com",
                cascade_map=cascade_map,
                eligible=["jina"],
                budget=_budget(),
                metrics=_FakeMetrics(),
                routing_memory=_FakeMemory(),
                circuit_breakers=breakers,
                semantic_cache_store=lambda *a: False,
                routing_key="example.com",
            )
        )
    )

    assert breakers.failures.get("jina") == 1
    assert results[0]["source"] == "none"


def test_paid_only_plan_launches_paid_immediately():
    """When nothing free is eligible, the paid tier must still run."""
    launched: list[str] = []

    async def paid_only():
        launched.append("paid")
        return ResolvedResult(
            source="tavily",
            url="https://example.com",
            content="# T\n\n" + ("Only paid source available here. " * 60) + "\n\n[x](http://a)\n",
        )

    results = asyncio.run(
        _drain(
            cascade_stream_async(
                target="https://example.com",
                cascade_map={"tavily": (ProviderType.TAVILY, paid_only)},
                eligible=["tavily"],
                budget=_budget(),
                metrics=_FakeMetrics(),
                routing_memory=_FakeMemory(),
                circuit_breakers=_FakeBreakers(),
                semantic_cache_store=lambda *a: False,
                routing_key="example.com",
            )
        )
    )

    assert launched == ["paid"]
    assert results[0]["source"] == "tavily"


def test_skipped_providers_are_not_launched():
    launched: list[str] = []

    async def free():
        launched.append("free")
        return None

    cascade_map = {"jina": (ProviderType.JINA, free)}

    asyncio.run(
        _drain(
            cascade_stream_async(
                target="https://example.com",
                cascade_map=cascade_map,
                eligible=["jina"],
                budget=_budget(),
                metrics=_FakeMetrics(),
                routing_memory=_FakeMemory(),
                circuit_breakers=_FakeBreakers(),
                semantic_cache_store=lambda *a: False,
                routing_key="example.com",
                skip_providers={"jina"},
            )
        )
    )

    assert launched == []


def test_open_circuit_breaker_skips_provider():
    breakers = _FakeBreakers()
    breakers.opened.add("jina")

    async def free():  # pragma: no cover - must never run
        raise AssertionError("open breaker should prevent launch")

    cascade_map = {"jina": (ProviderType.JINA, free)}

    results = asyncio.run(
        _drain(
            cascade_stream_async(
                target="https://example.com",
                cascade_map=cascade_map,
                eligible=["jina"],
                budget=_budget(),
                metrics=_FakeMetrics(),
                routing_memory=_FakeMemory(),
                circuit_breakers=breakers,
                semantic_cache_store=lambda *a: False,
                routing_key="example.com",
            )
        )
    )

    assert results[0]["source"] == "none"
