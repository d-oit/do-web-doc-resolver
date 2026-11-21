"""Context-aware routing keys and structured outcome semantics (issue #716)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.routing_context import (
    CONTEXT_SCHEMA_VERSION,
    derive_context,
    error_outcome,
    is_query_context_key,
    query_routing_key,
)
from scripts.routing_memory import MEMORY_SCHEMA_VERSION, RoutingMemory

FIXTURES = Path(__file__).parent / "fixtures"


def test_shared_context_fixture_matches_python():
    fixture = json.loads((FIXTURES / "routing_context_cases.json").read_text(encoding="utf-8"))
    assert fixture["schema_version"] == CONTEXT_SCHEMA_VERSION
    for case in fixture["cases"]:
        context = derive_context(case["query"])
        assert context.intent == case["intent"], case["query"]
        assert context.topic == case["topic"], case["query"]
        assert context.language == case["language"], case["query"]
        assert context.platform == case["platform"], case["query"]
        assert context.routing_key() == case["routing_key"], case["query"]


def test_query_keys_are_bounded_and_versioned():
    keys = {query_routing_key(q) for q in ["Python asyncio tutorial", "python asyncio guide"]}
    assert len(keys) == 1, "same query family must share one bucket"
    assert all(key.startswith(f"q:v{CONTEXT_SCHEMA_VERSION}:") for key in keys)
    assert all(is_query_context_key(key) for key in keys)
    # Raw query text never appears in the storage key.
    assert "python asyncio" not in next(iter(keys))


def test_unrelated_families_do_not_share_a_bucket():
    rust = query_routing_key("Rust error handling")
    python = query_routing_key("Python error handling")
    assert rust != python


def test_error_outcome_separates_transport_from_content():
    assert error_outcome(TimeoutError("request timeout")) == "timeout"
    assert error_outcome(RuntimeError("429 rate limit")) == "rate_limited"
    assert error_outcome(ValueError("404 not found")) == "no_result"
    assert error_outcome(RuntimeError("bot challenge")) == "blocked"


def test_blocked_is_not_recorded_as_content_failure():
    memory = RoutingMemory()
    for _ in range(3):
        memory.record_outcome("q:v2:general:rust:rust:none", "exa", "blocked", 100, 0.0)
    stats = memory.get_domain_stats("exa", "q:v2:general:rust:rust:none")
    assert stats is not None
    assert stats["attempts"] == 0
    assert stats["outcome_counts"]["blocked"] == 3
    assert stats["content_attempts"] == 0
    assert stats["transport_failures"] == 3
    assert stats["confidence"] == 0.0


def test_confidence_reaches_full_at_min_evidence():
    key = "q:v2:general:rust:rust:none"
    memory = RoutingMemory(mode="active")
    memory.record_outcome(key, "exa", "success", 100, 0.9)
    assert memory.get_domain_stats("exa", key)["confidence"] == pytest.approx(1 / 3)
    memory.record_outcome(key, "exa", "success", 100, 0.9)
    memory.record_outcome(key, "exa", "success", 100, 0.9)
    assert memory.get_domain_stats("exa", key)["confidence"] == 1.0


def test_legacy_flat_file_migrates_to_versioned_envelope(tmp_path):
    path = tmp_path / "routing_memory.json"
    path.write_text(
        json.dumps({"docs.rs": {"jina": {"success": 3, "failure": 1, "avg_latency_ms": 120}}}),
        encoding="utf-8",
    )
    memory = RoutingMemory(path=path)
    assert memory.schema_version == 1
    stats = memory.get_domain_stats("jina", "docs.rs")
    assert stats["attempts"] == 4
    assert stats["outcome_counts"]["success"] == 3
    assert stats["outcome_counts"]["low_quality"] == 1

    memory.save()
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["version"] == MEMORY_SCHEMA_VERSION
    assert saved["kind"] == "routing_memory"
    assert "docs.rs" in saved["stats"]


def test_newer_schema_is_not_overwritten(tmp_path):
    path = tmp_path / "routing_memory.json"
    original = {"version": 99, "kind": "routing_memory", "stats": {"docs.rs": {}}}
    path.write_text(json.dumps(original), encoding="utf-8")
    memory = RoutingMemory(path=path)
    assert memory.rank("docs.rs", ["a", "b"]) == ["a", "b"]
    memory.save()
    assert json.loads(path.read_text(encoding="utf-8")) == original


def test_shadow_mode_keeps_static_order_but_explains_learning():
    key = "q:v2:documentation:python:python:none"
    providers = ["exa_mcp", "exa", "tavily"]
    memory = RoutingMemory(mode="shadow")
    for _ in range(3):
        memory.record_outcome(key, "exa_mcp", "blocked", 50, 0.0)
        memory.record_outcome(key, "tavily", "success", 100, 0.9)
    assert memory.rank_providers(key, providers) == providers

    explained = memory.explain(key, providers)
    tavily = next(row for row in explained if row["provider"] == "tavily")
    assert tavily["learned_rank"] == 1
    assert tavily["sample_count"] == 3
    assert tavily["confidence"] == 1.0
    assert {"prior", "learned_component", "availability", "blended"} <= tavily.keys()


def test_active_mode_promotes_observed_success_over_blocked_first():
    key = "q:v2:api_reference:rust:rust:none"
    providers = ["exa_mcp", "exa", "tavily"]
    memory = RoutingMemory(mode="active")
    for _ in range(3):
        memory.record_outcome(key, "exa_mcp", "blocked", 50, 0.0)
        memory.record_outcome(key, "exa", "success", 150, 0.85)
        memory.record_outcome(key, "tavily", "success", 100, 0.9)
    ranked = memory.rank_providers(key, providers)
    assert ranked[0] == "tavily"
    assert ranked[-1] == "exa_mcp"


def test_off_mode_keeps_static_order():
    key = "q:v2:general:python:python:none"
    memory = RoutingMemory(mode="off")
    memory.record_outcome(key, "exa", "success", 100, 0.9)
    assert memory.rank_providers(key, ["exa_mcp", "exa"]) == ["exa_mcp", "exa"]
