"""Offline discovery benchmark contract (issue #717)."""

from pathlib import Path

from scripts.bench_discovery import run

FIXTURE = Path(__file__).parent / "fixtures" / "discovery_cases.json"


def test_discovery_improves_recall_within_bounded_extraction_budget():
    report = run(FIXTURE)
    assert report["discovery_recall"] > report["primary_recall"]
    assert report["discovery_recall"] == 1.0
    assert report["max_extractions_per_case"] <= 2
    assert report["p95_generation_ms"] >= 0
