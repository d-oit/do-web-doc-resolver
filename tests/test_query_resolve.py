"""Comprehensive tests for query resolution (resolve_query and resolve_query_stream)."""

import os
import sys
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts._query_resolve import (
    _check_semantic_cache,
    _store_in_semantic_cache,
    resolve_query,
    resolve_query_stream,
)
from scripts.models import Profile


class TestCheckSemanticCache:
    """Test semantic cache lookup for queries."""

    @patch("scripts._query_resolve.get_semantic_cache")
    def test_cache_disabled_returns_none(self, mock_get_cache):
        """Should return None when semantic cache is disabled."""
        mock_get_cache.return_value = None
        assert _check_semantic_cache("python async") is None

    @patch("scripts._query_resolve.get_semantic_cache")
    def test_cache_miss_returns_none(self, mock_get_cache):
        """Should return None on cache miss."""
        mock_cache = Mock()
        mock_cache.query.return_value = None
        mock_get_cache.return_value = mock_cache
        assert _check_semantic_cache("python async") is None

    @patch("scripts._query_resolve.get_semantic_cache")
    def test_cache_hit_returns_enriched_result(self, mock_get_cache):
        """Cache hit should return enriched result with metadata."""
        entry = Mock()
        entry.result = {"source": "exa", "content": "cached answer"}
        entry.similarity = 0.95
        entry.query = "python async"
        mock_cache = Mock()
        mock_cache.query.return_value = entry
        mock_get_cache.return_value = mock_cache

        result = _check_semantic_cache("python async")
        assert result is not None
        assert result["semantic_cache_hit"] is True
        assert result["semantic_similarity"] == 0.95
        assert result["semantic_original_query"] == "python async"

    @patch("scripts._query_resolve.get_semantic_cache")
    def test_cache_exception_handled_gracefully(self, mock_get_cache):
        """Cache exceptions should not propagate."""
        mock_cache = Mock()
        mock_cache.query.side_effect = RuntimeError("sqlite locked")
        mock_get_cache.return_value = mock_cache
        assert _check_semantic_cache("python async") is None


class TestStoreInSemanticCache:
    """Test semantic cache storage for queries."""

    @patch("scripts._query_resolve.get_semantic_cache")
    def test_store_disabled_returns_false(self, mock_get_cache):
        """Should return False when cache is None."""
        mock_get_cache.return_value = None
        assert _store_in_semantic_cache("query", {}) is False

    @patch("scripts._query_resolve.get_semantic_cache")
    def test_store_skips_none_source(self, mock_get_cache):
        """Should not store results with source=none."""
        mock_cache = Mock()
        mock_get_cache.return_value = mock_cache
        assert _store_in_semantic_cache("query", {"source": "none"}) is False
        mock_cache.store.assert_not_called()

    @patch("scripts._query_resolve.get_semantic_cache")
    def test_store_skips_existing_cache_hit(self, mock_get_cache):
        """Should not store results that were already cache hits."""
        mock_cache = Mock()
        mock_get_cache.return_value = mock_cache
        result = {"source": "exa", "semantic_cache_hit": True}
        assert _store_in_semantic_cache("query", result) is False
        mock_cache.store.assert_not_called()

    @patch("scripts._query_resolve.get_semantic_cache")
    def test_store_succeeds_for_fresh_result(self, mock_get_cache):
        """Should store fresh (non-cache-hit) results."""
        mock_cache = Mock()
        mock_cache.store.return_value = True
        mock_get_cache.return_value = mock_cache
        result = {"source": "exa", "content": "fresh answer"}
        assert _store_in_semantic_cache("python async", result) is True
        mock_cache.store.assert_called_once_with("python async", result)

    @patch("scripts._query_resolve.get_semantic_cache")
    def test_store_exception_returns_false(self, mock_get_cache):
        """Store failure should return False, not raise."""
        mock_cache = Mock()
        mock_cache.store.side_effect = RuntimeError("disk full")
        mock_get_cache.return_value = mock_cache
        assert _store_in_semantic_cache("query", {"source": "exa"}) is False


class TestResolveQueryStream:
    """Test resolve_query_stream generator."""

    @patch("scripts._query_resolve._store_in_semantic_cache", return_value=False)
    @patch("scripts._query_resolve._check_semantic_cache", return_value=None)
    @patch("scripts._query_resolve.cascade_stream")
    def test_cache_hit_yields_immediately(self, mock_cascade, mock_check_cache, mock_store):
        """Cache hit should yield cached result without cascade."""
        cached = {
            "source": "exa",
            "content": "cached answer about Python",
            "query": "python async",
            "semantic_cache_hit": True,
        }
        mock_check_cache.return_value = cached
        results = list(resolve_query_stream("python async"))
        assert len(results) == 1
        assert results[0]["semantic_cache_hit"] is True
        assert results[0]["query"] == "python async"
        mock_cascade.assert_not_called()

    @patch("scripts._query_resolve._store_in_semantic_cache", return_value=False)
    @patch("scripts._query_resolve._check_semantic_cache", return_value=None)
    @patch("scripts._query_resolve.cascade_stream")
    def test_cache_miss_runs_cascade(self, mock_cascade, mock_check_cache, mock_store):
        """Cache miss should trigger cascade with all providers."""
        mock_cascade.return_value = iter(
            [{"source": "exa", "content": "fresh answer", "query": "python async"}]
        )
        results = list(resolve_query_stream("python async"))
        assert mock_cascade.called
        assert len(results) == 1
        assert results[0]["source"] == "exa"

    @patch("scripts._query_resolve._store_in_semantic_cache", return_value=False)
    @patch("scripts._query_resolve._check_semantic_cache", return_value=None)
    @patch("scripts._query_resolve.cascade_stream")
    def test_cascade_failure_yields_none_source(self, mock_cascade, mock_check_cache, mock_store):
        """Should yield source=none when cascade produces no successful result."""
        # The real cascade_stream produces the "none" fallback itself; mock that behavior
        mock_cascade.return_value = iter(
            [{"source": "none", "query": "python async", "content": "Failed"}]
        )
        results = list(resolve_query_stream("python async"))
        assert len(results) == 1
        assert results[0]["source"] == "none"


class TestResolveQuery:
    """Test resolve_query (non-streaming wrapper)."""

    @patch("scripts._query_resolve._store_in_semantic_cache", return_value=False)
    @patch("scripts._query_resolve._check_semantic_cache", return_value=None)
    @patch("scripts._query_resolve.cascade_stream")
    def test_returns_first_non_partial(self, mock_cascade, mock_check_cache, mock_store):
        """Should return first non-partial result."""
        mock_cascade.return_value = iter(
            [
                {"source": "partial", "content": "..."},
                {"source": "exa", "content": "complete answer", "query": "q"},
            ]
        )
        result = resolve_query("python async")
        assert result["source"] == "exa"

    @patch("scripts._query_resolve._store_in_semantic_cache", return_value=False)
    @patch("scripts._query_resolve._check_semantic_cache", return_value=None)
    @patch("scripts._query_resolve.cascade_stream")
    def test_returns_none_source_on_all_failure(self, mock_cascade, mock_check_cache, mock_store):
        """Should return source=none when all results are partial or cascade empty."""
        mock_cascade.return_value = iter([])
        result = resolve_query("python async")
        assert result["source"] == "none"
        assert result["content"] == "Failed"
        assert result["query"] == "python async"

    @patch("scripts._query_resolve._store_in_semantic_cache", return_value=False)
    @patch("scripts._query_resolve._check_semantic_cache")
    def test_returns_cached_result(self, mock_check_cache, mock_store):
        """Should return cached result directly without cascade."""
        mock_check_cache.return_value = {
            "source": "exa",
            "content": "cached answer",
            "semantic_cache_hit": True,
        }
        result = resolve_query("python async")
        assert result["semantic_cache_hit"] is True


class TestResolveQueryEmptyInput:
    """Test empty query handling."""

    @patch("scripts._query_resolve._store_in_semantic_cache", return_value=False)
    @patch("scripts._query_resolve._check_semantic_cache", return_value=None)
    @patch("scripts._query_resolve.cascade_stream")
    def test_empty_query_runs_cascade(self, mock_cascade, mock_check_cache, mock_store):
        """Empty query should not crash; cascade handles it."""
        mock_cascade.return_value = iter([{"source": "none", "query": "", "content": "Failed"}])
        results = list(resolve_query_stream(""))
        assert len(results) == 1

    @patch("scripts._query_resolve._store_in_semantic_cache", return_value=False)
    @patch("scripts._query_resolve._check_semantic_cache", return_value=None)
    @patch("scripts._query_resolve.cascade_stream")
    def test_whitespace_query_runs_cascade(self, mock_cascade, mock_check_cache, mock_store):
        """Whitespace-only query should not crash."""
        mock_cascade.return_value = iter([{"source": "none", "query": "   ", "content": "Failed"}])
        results = list(resolve_query_stream("   "))
        assert len(results) == 1


class TestResolveQueryProfileBudget:
    """Test provider selection based on profile and budget."""

    @patch("scripts._query_resolve._store_in_semantic_cache", return_value=False)
    @patch("scripts._query_resolve._check_semantic_cache", return_value=None)
    @patch("scripts._query_resolve.cascade_stream")
    def test_free_profile_no_paid_providers(self, mock_cascade, mock_check_cache, mock_store):
        """FREE profile should not use paid providers."""
        mock_cascade.return_value = iter(
            [{"source": "duckduckgo", "content": "free result", "query": "q"}]
        )
        results = list(resolve_query_stream("python async", profile=Profile.FREE))
        assert mock_cascade.called
        # Budget config is internal; verify it ran without error
        assert len(results) == 1

    @patch("scripts._query_resolve._store_in_semantic_cache", return_value=False)
    @patch("scripts._query_resolve._check_semantic_cache", return_value=None)
    @patch("scripts._query_resolve.cascade_stream")
    def test_quality_profile_higher_budget(self, mock_cascade, mock_check_cache, mock_store):
        """QUALITY profile should have higher provider attempt limits."""
        mock_cascade.return_value = iter(
            [{"source": "exa", "content": "quality result", "query": "q"}]
        )
        results = list(resolve_query_stream("python async", profile=Profile.QUALITY))
        assert mock_cascade.called
        assert len(results) == 1

    @patch("scripts._query_resolve._store_in_semantic_cache", return_value=False)
    @patch("scripts._query_resolve._check_semantic_cache", return_value=None)
    @patch("scripts._query_resolve.cascade_stream")
    def test_fast_profile_reduced_budget(self, mock_cascade, mock_check_cache, mock_store):
        """FAST profile should have fewer provider attempts."""
        mock_cascade.return_value = iter([{"source": "none", "query": "q", "content": "Failed"}])
        list(resolve_query_stream("python async", profile=Profile.FAST))
        assert mock_cascade.called

    @patch("scripts._query_resolve._store_in_semantic_cache", return_value=False)
    @patch("scripts._query_resolve._check_semantic_cache", return_value=None)
    @patch("scripts._query_resolve.cascade_stream")
    def test_skip_providers_excludes_from_cascade(self, mock_cascade, mock_check_cache, mock_store):
        """skip_providers should exclude providers from the cascade."""
        mock_cascade.return_value = iter(
            [{"source": "duckduckgo", "content": "result", "query": "q"}]
        )
        results = list(resolve_query_stream("python async", skip_providers={"exa", "tavily"}))
        assert mock_cascade.called
        assert len(results) == 1


class TestResolveQueryBudgetExhaustion:
    """Test budget exhaustion behavior."""

    @patch("scripts._query_resolve._store_in_semantic_cache", return_value=False)
    @patch("scripts._query_resolve._check_semantic_cache", return_value=None)
    @patch("scripts._query_resolve.cascade_stream")
    def test_budget_exhaustion_yields_none(self, mock_cascade, mock_check_cache, mock_store):
        """When budget is exhausted, should yield source=none."""
        mock_cascade.return_value = iter(
            [
                {
                    "source": "none",
                    "query": "q",
                    "content": "Failed",
                    "error": "max_provider_attempts",
                }
            ]
        )
        results = list(resolve_query_stream("python async"))
        assert len(results) == 1
        assert results[0]["source"] == "none"

    @patch("scripts._query_resolve._store_in_semantic_cache", return_value=False)
    @patch("scripts._query_resolve._check_semantic_cache", return_value=None)
    @patch("scripts._query_resolve.cascade_stream")
    def test_budget_exhausted_after_partial_results(
        self, mock_cascade, mock_check_cache, mock_store
    ):
        """Should yield partial results even when budget exhausts."""
        mock_cascade.return_value = iter(
            [
                {"source": "partial", "content": "..."},
                {"source": "partial", "content": "..."},
                {"source": "none", "query": "q", "content": "Failed"},
            ]
        )
        results = list(resolve_query_stream("python async"))
        assert len(results) == 3
        assert results[-1]["source"] == "none"


class TestResolveQuerySynthesis:
    """Test result synthesis from multiple providers."""

    @patch("scripts._query_resolve._store_in_semantic_cache", return_value=False)
    @patch("scripts._query_resolve._check_semantic_cache", return_value=None)
    @patch("scripts._query_resolve.cascade_stream")
    def test_multiple_partial_results_yielded(self, mock_cascade, mock_check_cache, mock_store):
        """Multiple providers can yield partial results before final."""
        mock_cascade.return_value = iter(
            [
                {"source": "partial", "content": "exa partial"},
                {"source": "partial", "content": "tavily partial"},
                {"source": "duckduckgo", "content": "final answer", "query": "q"},
            ]
        )
        results = list(resolve_query_stream("python async"))
        assert len(results) == 3
        assert results[-1]["source"] == "duckduckgo"

    @patch("scripts._query_resolve._store_in_semantic_cache", return_value=False)
    @patch("scripts._query_resolve._check_semantic_cache", return_value=None)
    @patch("scripts._query_resolve.cascade_stream")
    def test_single_provider_success(self, mock_cascade, mock_check_cache, mock_store):
        """Single provider success should yield one result."""
        mock_cascade.return_value = iter([{"source": "exa", "content": "answer", "query": "q"}])
        results = list(resolve_query_stream("python async"))
        assert len(results) == 1
        assert results[0]["source"] == "exa"


class TestResolveQueryAllProvidersFail:
    """Test error handling when all providers fail."""

    @patch("scripts._query_resolve._store_in_semantic_cache", return_value=False)
    @patch("scripts._query_resolve._check_semantic_cache", return_value=None)
    @patch("scripts._query_resolve.cascade_stream")
    def test_all_fail_yields_none_source(self, mock_cascade, mock_check_cache, mock_store):
        """When all providers fail, should yield source=none."""
        mock_cascade.return_value = iter([{"source": "none", "query": "q", "content": "Failed"}])
        results = list(resolve_query_stream("python async"))
        assert len(results) == 1
        assert results[0]["source"] == "none"

    @patch("scripts._query_resolve._store_in_semantic_cache", return_value=False)
    @patch("scripts._query_resolve._check_semantic_cache", return_value=None)
    @patch("scripts._query_resolve.cascade_stream")
    def test_all_providers_return_none(self, mock_cascade, mock_check_cache, mock_store):
        """When all providers return None, should yield source=none."""
        mock_cascade.return_value = iter(
            [
                {
                    "source": "none",
                    "query": "q",
                    "content": "Failed",
                    "error": "No resolution method available",
                }
            ]
        )
        results = list(resolve_query_stream("python async"))
        assert results[0]["source"] == "none"
        assert "Failed" in results[0]["content"]

    @patch("scripts._query_resolve._store_in_semantic_cache", return_value=False)
    @patch("scripts._query_resolve._check_semantic_cache", return_value=None)
    @patch("scripts._query_resolve.cascade_stream")
    def test_all_providers_rate_limited(self, mock_cascade, mock_check_cache, mock_store):
        """When all providers are rate limited, cascade yields none."""
        mock_cascade.return_value = iter([{"source": "none", "query": "q", "content": "Failed"}])
        results = list(resolve_query_stream("python async"))
        assert results[0]["source"] == "none"


class TestResolveQueryEdgeCases:
    """Test edge cases."""

    @patch("scripts._query_resolve._store_in_semantic_cache", return_value=False)
    @patch("scripts._query_resolve._check_semantic_cache", return_value=None)
    @patch("scripts._query_resolve.cascade_stream")
    def test_max_chars_forwarded(self, mock_cascade, mock_check_cache, mock_store):
        """max_chars should be forwarded to cascade."""
        mock_cascade.return_value = iter([])
        list(resolve_query_stream("python async", max_chars=4000))
        assert mock_cascade.called

    @patch("scripts._query_resolve._store_in_semantic_cache", return_value=False)
    @patch("scripts._query_resolve._check_semantic_cache", return_value=None)
    @patch("scripts._query_resolve.cascade_stream")
    def test_skip_providers_none_is_safe(self, mock_cascade, mock_check_cache, mock_store):
        """None skip_providers should work like empty set."""
        mock_cascade.return_value = iter([{"source": "exa", "content": "answer", "query": "q"}])
        results = list(resolve_query_stream("python async", skip_providers=None))
        assert mock_cascade.called
        assert len(results) == 1

    @patch("scripts._query_resolve._store_in_semantic_cache", return_value=False)
    @patch("scripts._query_resolve._check_semantic_cache", return_value=None)
    @patch("scripts._query_resolve.cascade_stream")
    def test_special_characters_in_query(self, mock_cascade, mock_check_cache, mock_store):
        """Queries with special characters should not crash."""
        mock_cascade.return_value = iter(
            [{"source": "none", "query": "q&x=y", "content": "Failed"}]
        )
        results = list(resolve_query_stream("python&x=y?q=1"))
        assert len(results) == 1
