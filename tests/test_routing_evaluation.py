"""Deterministic, held-out routing evaluation (issue #716)."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.evaluate_routing import cold_start_and_low_sample, evaluate

FIXTURE = Path(__file__).parent / "fixtures" / "routing_eval.json"


def _load() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_learned_route_does_not_regress_fixture_recall():
    report = evaluate(_load())
    assert report["learned_success_rate"] >= report["static_success_rate"]
    assert report["learned_success_rate"] == 1.0


def test_cold_start_and_low_sample_are_conservative():
    report = cold_start_and_low_sample(_load())
    assert report["cold_start_preserves_static_order"] is True
    assert report["one_observation_preserves_static_first"] is True


def test_blocked_and_quality_failure_are_reported_separately():
    report = evaluate(_load())
    rows = {row["case"]: row for row in report["rows"]}
    rust = rows["rust-api-reference"]["provider_attempts"]["exa_mcp"]
    assert rust["blocked"] == 3
    assert rust["low_quality"] == 0
    python = rows["python-docs"]["provider_attempts"]["exa"]
    assert python["low_quality"] == 3
    assert python["blocked"] == 0
