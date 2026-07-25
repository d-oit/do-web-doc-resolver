"""Extended tests for data models: serialization, scoring, providers, and metrics."""

import pytest

from scripts.models import (
    ErrorType,
    Profile,
    ProviderMetric,
    ProviderType,
    ResolvedResult,
    ResolveMetrics,
    ValidationResult,
)

# ─── ValidationResult ────────────────────────────────────────────────────────


class TestValidationResult:
    """ValidationResult dataclass validation."""

    def test_minimal_construction(self):
        vr = ValidationResult(is_valid=True)
        assert vr.is_valid is True
        assert vr.status_code is None
        assert vr.error is None
        assert vr.redirect_chain == []

    def test_full_construction(self):
        vr = ValidationResult(
            is_valid=False,
            status_code=404,
            content_type="text/html",
            final_url="https://example.com/final",
            error="Not Found",
            redirect_chain=["https://example.com/old", "https://example.com/final"],
        )
        assert vr.status_code == 404
        assert vr.final_url == "https://example.com/final"
        assert len(vr.redirect_chain) == 2

    def test_is_valid_false_with_error(self):
        vr = ValidationResult(is_valid=False, error="timeout")
        assert vr.is_valid is False
        assert vr.error == "timeout"


# ─── ResolvedResult ──────────────────────────────────────────────────────────


class TestResolvedResultSerialization:
    """ResolvedResult.to_dict() and roundtrip behavior."""

    def test_to_dict_minimal(self):
        r = ResolvedResult(source="test", content="hello")
        d = r.to_dict()
        assert d["source"] == "test"
        assert d["content"] == "hello"
        assert d["url"] is None
        assert d["query"] is None
        assert d["score"] == 0.0

    def test_to_dict_full(self):
        r = ResolvedResult(
            source="jina",
            content="# Title\nContent here",
            url="https://example.com",
            query="python tutorial",
            score=0.85,
            validated_links=["https://example.com/a", "https://example.com/b"],
            metadata={"status_code": 200, "cleaned": True},
        )
        d = r.to_dict()
        assert d["source"] == "jina"
        assert d["url"] == "https://example.com"
        assert d["score"] == 0.85
        assert len(d["validated_links"]) == 2
        assert d["metadata"]["status_code"] == 200

    def test_to_dict_with_metrics(self):
        metrics = ResolveMetrics(total_latency_ms=500)
        r = ResolvedResult(source="test", content="data", metrics=metrics)
        d = r.to_dict()
        assert d["metrics"]["total_latency_ms"] == 500

    def test_to_dict_empty_metadata(self):
        r = ResolvedResult(source="test", content="data")
        d = r.to_dict()
        assert d["metadata"] == {}
        assert d["validated_links"] == []


# ─── ProviderType ────────────────────────────────────────────────────────────


class TestProviderType:
    """ProviderType is_paid/is_fast for all providers."""

    def test_paid_providers(self):
        paid = {p for p in ProviderType if p.is_paid()}
        expected = {
            ProviderType.EXA,
            ProviderType.TAVILY,
            ProviderType.SERPER,
            ProviderType.FIRECRAWL,
            ProviderType.MISTRAL_WEBSEARCH,
            ProviderType.MISTRAL_BROWSER,
            ProviderType.VISUAL_CLIP,
        }
        assert paid == expected

    def test_fast_providers(self):
        fast = {p for p in ProviderType if p.is_fast()}
        expected = {
            ProviderType.EXA_MCP,
            ProviderType.DUCKDUCKGO,
            ProviderType.LLMS_TXT,
            ProviderType.JINA,
            ProviderType.DIRECT_FETCH,
        }
        assert fast == expected

    def test_free_providers(self):
        free = {p for p in ProviderType if not p.is_paid()}
        assert ProviderType.DIRECT_FETCH in free
        assert ProviderType.LLMS_TXT in free
        assert ProviderType.EXA_MCP in free
        assert ProviderType.DUCKDUCKGO in free
        assert ProviderType.FIRECRAWL not in free

    def test_non_fast_providers(self):
        non_fast = {p for p in ProviderType if not p.is_fast()}
        assert ProviderType.FIRECRAWL in non_fast
        assert ProviderType.EXA in non_fast
        assert ProviderType.TAVILY in non_fast

    def test_all_providers_have_value(self):
        for p in ProviderType:
            assert isinstance(p.value, str)
            assert len(p.value) > 0

    def test_provider_values_unique(self):
        values = [p.value for p in ProviderType]
        assert len(values) == len(set(values))


# ─── Profile ─────────────────────────────────────────────────────────────────


class TestProfile:
    """Profile max_hops and provider filtering."""

    def test_free_max_hops(self):
        assert Profile.FREE.max_hops() == 3

    def test_fast_max_hops(self):
        assert Profile.FAST.max_hops() == 2

    def test_balanced_max_hops(self):
        assert Profile.BALANCED.max_hops() == 6

    def test_quality_max_hops(self):
        assert Profile.QUALITY.max_hops() == 8

    def test_free_disallows_paid_providers(self):
        assert Profile.FREE.is_provider_allowed(ProviderType.FIRECRAWL) is False
        assert Profile.FREE.is_provider_allowed(ProviderType.EXA) is False

    def test_free_allows_free_providers(self):
        assert Profile.FREE.is_provider_allowed(ProviderType.DIRECT_FETCH) is True
        assert Profile.FREE.is_provider_allowed(ProviderType.LLMS_TXT) is True

    def test_fast_allows_only_fast_providers(self):
        assert Profile.FAST.is_provider_allowed(ProviderType.EXA_MCP) is True
        assert Profile.FAST.is_provider_allowed(ProviderType.DIRECT_FETCH) is True
        assert Profile.FAST.is_provider_allowed(ProviderType.FIRECRAWL) is False
        assert Profile.FAST.is_provider_allowed(ProviderType.EXA) is False

    def test_balanced_allows_all(self):
        assert Profile.BALANCED.is_provider_allowed(ProviderType.FIRECRAWL) is True
        assert Profile.BALANCED.is_provider_allowed(ProviderType.DIRECT_FETCH) is True

    def test_quality_allows_all(self):
        assert Profile.QUALITY.is_provider_allowed(ProviderType.FIRECRAWL) is True
        assert Profile.QUALITY.is_provider_allowed(ProviderType.DIRECT_FETCH) is True


# ─── ErrorType ───────────────────────────────────────────────────────────────


class TestErrorType:
    """ErrorType enum completeness and values."""

    def test_all_error_types(self):
        expected = {
            "rate_limit",
            "auth_error",
            "quota_exhausted",
            "network_error",
            "not_found",
            "invalid_url",
            "timeout",
            "invalid_response",
            "ssrf_blocked",
            "content_too_large",
            "bot_challenge",
            "unknown",
        }
        actual = {e.value for e in ErrorType}
        assert actual == expected

    def test_error_type_count(self):
        assert len(ErrorType) == 12


# ─── ResolveMetrics ──────────────────────────────────────────────────────────


class TestResolveMetrics:
    """ResolveMetrics record_provider and aggregation."""

    def test_initial_state(self):
        m = ResolveMetrics()
        assert m.total_latency_ms == 0
        assert m.provider_metrics == []
        assert m.paid_usage is False
        assert m.cache_hit is False

    def test_record_free_provider(self):
        m = ResolveMetrics()
        m.record_provider(ProviderType.DIRECT_FETCH, 150, success=True)
        assert m.total_latency_ms == 150
        assert len(m.provider_metrics) == 1
        assert m.provider_metrics[0].provider == "direct_fetch"
        assert m.provider_metrics[0].paid is False
        assert m.paid_usage is False

    def test_record_paid_provider_success(self):
        m = ResolveMetrics()
        m.record_provider(ProviderType.FIRECRAWL, 300, success=True)
        assert m.total_latency_ms == 300
        assert m.provider_metrics[0].paid is True
        assert m.paid_usage is True

    def test_record_paid_provider_failure(self):
        m = ResolveMetrics()
        m.record_provider(ProviderType.FIRECRAWL, 300, success=False)
        assert m.paid_usage is False  # Only set on success

    def test_multiple_providers_cumulative_latency(self):
        m = ResolveMetrics()
        m.record_provider(ProviderType.DIRECT_FETCH, 100, success=True)
        m.record_provider(ProviderType.JINA, 200, success=True)
        m.record_provider(ProviderType.FIRECRAWL, 300, success=False)
        assert m.total_latency_ms == 600
        assert len(m.provider_metrics) == 3

    def test_paid_usage_stays_true_once_set(self):
        m = ResolveMetrics()
        m.record_provider(ProviderType.EXA, 100, success=True)
        assert m.paid_usage is True
        m.record_provider(ProviderType.DIRECT_FETCH, 50, success=True)
        assert m.paid_usage is True

    def test_to_dict_via_result(self):
        m = ResolveMetrics(cascade_depth=3)
        m.record_provider(ProviderType.JINA, 250, success=True)
        r = ResolvedResult(source="test", content="data", metrics=m)
        d = r.to_dict()
        assert d["metrics"]["total_latency_ms"] == 250
        assert d["metrics"]["cascade_depth"] == 3
        assert len(d["metrics"]["provider_metrics"]) == 1


# ─── ProviderMetric ──────────────────────────────────────────────────────────


class TestProviderMetric:
    """ProviderMetric dataclass."""

    def test_construction(self):
        pm = ProviderMetric(provider="jina", latency_ms=120, success=True, paid=True)
        assert pm.provider == "jina"
        assert pm.latency_ms == 120
        assert pm.success is True
        assert pm.paid is True

    def test_failure_metric(self):
        pm = ProviderMetric(provider="firecrawl", latency_ms=0, success=False, paid=True)
        assert pm.success is False


# ─── score_result integration ────────────────────────────────────────────────


class TestScoreResultIntegration:
    """score_result with various URL/content combos."""

    def test_none_url_zero_words(self):
        from scripts.utils.urls import score_result

        s = score_result(None, "")
        assert s == pytest.approx(0.3, abs=0.01)

    def test_io_domain_bonus(self):
        from scripts.utils.urls import score_result

        s = score_result("https://docs.rs/tokio", "word " * 600)
        assert s >= 0.7

    def test_org_domain_bonus(self):
        from scripts.utils.urls import score_result

        s = score_result("https://w3.org/spec", "word " * 600)
        assert s >= 0.7

    def test_score_never_exceeds_one(self):
        from scripts.utils.urls import score_result

        s = score_result("https://github.com/x/y", "word " * 1000)
        assert s <= 1.0

    def test_score_never_below_zero(self):
        from scripts.utils.urls import score_result

        s = score_result("https://example.com", "")
        assert s >= 0.0

    def test_empty_url_empty_content(self):
        from scripts.utils.urls import score_result

        s = score_result("", "")
        assert s == pytest.approx(0.3, abs=0.01)
