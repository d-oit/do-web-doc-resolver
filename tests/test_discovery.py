"""Offline alternative-source discovery tests (issue #717)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.discovery import DiscoveryInput, discover_alternatives, should_discover
from scripts.discovery_live import fallback_result
from scripts.models import ResolvedResult

FIXTURE = Path(__file__).parent / "fixtures" / "discovery_cases.json"


class _Validation:
    def __init__(self, payload: dict) -> None:
        self.is_valid = bool(payload.get("is_valid"))
        self.final_url = payload.get("final_url")
        self.redirect_chain = payload.get("redirect_chain", [])


def _cases() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]


def _validator(case: dict):
    def validate(url: str) -> _Validation:
        return _Validation(case["validator"].get(url, {"is_valid": False}))

    return validate


def _report(case: dict):
    return discover_alternatives(
        DiscoveryInput(
            primary_url=case["primary_url"],
            final_url=case["final_url"],
            html=case["html"],
            llms_txt=case["llms_txt"],
            search_results=case["search_results"],
            query=case["query"],
        ),
        validator=_validator(case),
    )


@pytest.mark.parametrize("case", _cases(), ids=lambda case: case["name"])
def test_fixture_selects_expected_verified_source(case):
    report = _report(case)
    assert report.selected is not None, case["name"]
    assert report.selected.canonical_url == case["expected_selected"]
    assert report.selected.relationship == case["expected_relationship"]
    assert report.selected.verification_state == "verified"


@pytest.mark.parametrize("case", _cases(), ids=lambda case: case["name"])
def test_every_candidate_carries_provenance_and_verification(case):
    report = _report(case)
    candidates = report.candidates + report.rejected
    assert candidates
    for candidate in candidates:
        assert candidate.strategy
        assert candidate.family
        assert candidate.discovery_provider
        assert candidate.original_url == case["primary_url"]
        assert candidate.canonical_url.startswith("http")
        assert candidate.publisher_domain
        assert candidate.timestamp
        assert candidate.verification_state in {"verified", "unverified", "rejected"}
        assert candidate.reason


@pytest.mark.parametrize("case", _cases(), ids=lambda case: case["name"])
def test_all_four_strategy_families_are_observable(case):
    report = _report(case)
    names = {entry["name"] for entry in report.strategies}
    assert names == {
        "publisher_metadata",
        "official_repository",
        "versioned_docs",
        "search_provider",
    }
    nonzero = {entry["name"] for entry in report.strategies if entry["candidate_count"] > 0}
    assert set(case["expected_nonzero_strategies"]) <= nonzero


def test_duplicate_canonical_urls_are_collapsed():
    case = next(item for item in _cases() if item["name"] == "duplicates")
    report = _report(case)
    assert report.duplicate_count >= case["minimum_duplicates"]
    urls = [candidate.canonical_url for candidate in report.candidates]
    assert len(urls) == len(set(urls))


def test_unofficial_mirror_cannot_outrank_canonical_publisher():
    case = next(item for item in _cases() if item["name"] == "unofficial-mirror")
    report = _report(case)
    canonical_index = next(
        index
        for index, candidate in enumerate(report.candidates)
        if candidate.relationship == "canonical"
    )
    unofficial_index = next(
        index
        for index, candidate in enumerate(report.candidates)
        if candidate.relationship == "unofficial"
    )
    assert canonical_index < unofficial_index


def test_redirect_final_url_is_preferred():
    case = next(item for item in _cases() if item["name"] == "redirect-versioned-host")
    report = _report(case)
    assert report.selected.canonical_url == "https://docs.example.com/stable/api"
    assert report.selected.redirect_chain[-1] == "https://docs.example.com/stable/api"


def test_stale_version_prefers_stable_variant():
    case = next(item for item in _cases() if item["name"] == "stale-version")
    report = _report(case)
    assert report.selected.canonical_url == "https://docs.example.com/docs/stable/guide"


def _fallback_case() -> dict:
    return next(item for item in _cases() if item["name"] == "dead-primary")


def test_fallback_is_bounded_and_returns_discovery_provenance(monkeypatch):
    case = _fallback_case()
    monkeypatch.setenv("DO_WDR_DISCOVERY", "1")
    monkeypatch.setenv("DO_WDR_DISCOVERY_SEARCH", "0")
    extracted: list[str] = []

    def fetch(url: str) -> str | None:
        if url == case["primary_url"]:
            return case["html"]
        return None

    def extract(url: str) -> ResolvedResult | None:
        extracted.append(url)
        return ResolvedResult(
            source="direct_fetch",
            url=url,
            content="# Official reference\n\n" + ("Useful documentation. " * 80),
        )

    result = fallback_result(
        case["primary_url"],
        query=case["query"],
        fetch=fetch,
        search=lambda _query: case["search_results"],
        validator=_validator(case),
        extract=extract,
        max_fetches=1,
    )
    assert result is not None
    assert result["source"].startswith("discovery:")
    assert result["discovered_from"] == case["primary_url"]
    assert result["discovery"]["selected"]["canonical_url"] == case["expected_selected"]
    assert len(extracted) <= 1


@patch("scripts._url_resolve._store_in_semantic_cache", return_value=False)
@patch("scripts._url_resolve._check_semantic_cache", return_value=None)
@patch("scripts._url_resolve.fallback_result")
@patch("scripts._url_resolve.cascade_stream")
def test_url_resolution_runs_discovery_after_primary_failure(
    mock_cascade, mock_fallback, _mock_cache, _mock_store, monkeypatch
):
    from scripts._url_resolve import resolve_url_stream

    monkeypatch.setenv("DO_WDR_DISCOVERY", "1")
    mock_cascade.return_value = iter(
        [{"source": "none", "content": "Failed", "url": "https://docs.example.com/x"}]
    )
    mock_fallback.return_value = {
        "source": "discovery:publisher_metadata",
        "url": "https://docs.example.com/stable/x",
        "content": "Recovered documentation",
        "score": 0.9,
    }
    results = list(resolve_url_stream("https://docs.example.com/x"))
    assert results[-1]["source"].startswith("discovery:")
    mock_fallback.assert_called_once()


@patch("scripts._url_resolve._store_in_semantic_cache", return_value=False)
@patch("scripts._url_resolve._check_semantic_cache", return_value=None)
@patch("scripts._url_resolve.fallback_result")
@patch("scripts._url_resolve.cascade_stream")
def test_url_resolution_skips_discovery_for_high_quality_primary(
    mock_cascade, mock_fallback, _mock_cache, _mock_store, monkeypatch
):
    from scripts._url_resolve import resolve_url_stream

    monkeypatch.setenv("DO_WDR_DISCOVERY", "1")
    mock_cascade.return_value = iter(
        [{"source": "jina", "content": "Good docs", "score": 0.92, "url": "https://x"}]
    )
    results = list(resolve_url_stream("https://docs.example.com/x"))
    assert results[-1]["source"] == "jina"
    mock_fallback.assert_not_called()


def test_should_discover_only_for_failed_or_low_quality_primary(monkeypatch):
    monkeypatch.setenv("DO_WDR_DISCOVERY", "1")
    assert should_discover({"source": "none", "score": 0.0}) is True
    assert should_discover({"source": "jina", "score": 0.4}) is True
    assert should_discover({"source": "jina", "score": 0.9}) is False
    assert should_discover({"source": "jina", "score": 0.9, "semantic_cache_hit": True}) is False
    monkeypatch.setenv("DO_WDR_DISCOVERY", "0")
    assert should_discover({"source": "none", "score": 0.0}) is False
