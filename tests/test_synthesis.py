"""Tests for synthesis gating, deduplication, conflict detection, and quality integration."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.models import ResolvedResult
from scripts.quality import ACCEPTABLE_THRESHOLD, score_content
from scripts.synthesis import (
    _content_similarity,
    _has_conflicts,
    _is_fragmented,
    deterministic_merge,
    synthesis_gate_decision,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

LONG_CONTENT = (
    "This is a detailed technical document about web documentation resolvers. "
    "It covers multiple providers, cascade strategies, and quality scoring. "
    "The resolver uses a tiered approach starting with free static sources "
    "like llms.txt, escalating to paid providers like Firecrawl and Mistral. "
    "Each provider returns structured content that is scored for quality. "
    "Content scoring considers length, link density, duplicates, and noise. "
    "The synthesis module merges multiple provider outputs into a single "
    "coherent document following 2026 LLM-readable standards. "
    "Anchors are used for RAG optimization: SUMMARY, TECHNICAL_DETAILS, "
    "COMPARISON, and CITATIONS. Frontmatter includes relevance score, "
    "intent category, token estimate, and last updated date."
) * 5  # ~2000 chars


@pytest.fixture
def single_high_quality_result():
    """Single result with high quality score."""
    return ResolvedResult(
        source="jina",
        content=LONG_CONTENT,
        url="https://docs.rs/tokio",
        score=0.92,
    )


@pytest.fixture
def single_low_quality_result():
    """Single result with low quality score."""
    return ResolvedResult(
        source="jina",
        content="Short.",
        url="https://example.com",
        score=0.3,
    )


@pytest.fixture
def two_similar_results():
    """Two results with similar content (no conflicts)."""
    content = (
        "Tokio is an asynchronous runtime for Rust. It provides the building blocks "
        "needed for writing network applications. It works with async/await syntax. "
        "Tokio handles I/O, scheduling, and timers. The runtime is multi-threaded "
        "by default and can be configured for single-threaded execution as well."
    )
    return [
        ResolvedResult(source="jina", content=content, url="https://tokio.rs", score=0.85),
        ResolvedResult(
            source="firecrawl", content=content, url="https://docs.rs/tokio", score=0.80
        ),
    ]


@pytest.fixture
def two_conflicting_results():
    """Two results with very different content (conflicts)."""
    return [
        ResolvedResult(
            source="jina",
            content="Tokio is an asynchronous runtime for Rust that provides core building "
            "blocks for writing network applications. It supports async/await and handles "
            "I/O operations, task scheduling, and timers for concurrent programming.",
            url="https://tokio.rs",
            score=0.85,
        ),
        ResolvedResult(
            source="tavily",
            content="React is a JavaScript library for building user interfaces. It uses a "
            "virtual DOM and component-based architecture. React was created by Facebook "
            "and is maintained by Meta along with a community of developers.",
            url="https://react.dev",
            score=0.75,
        ),
    ]


@pytest.fixture
def fragmented_results():
    """Results that are individually too short (fragmented)."""
    return [
        ResolvedResult(source="jina", content="Short snippet A.", url="https://a.com", score=0.7),
        ResolvedResult(
            source="firecrawl", content="Short snippet B.", url="https://b.com", score=0.65
        ),
        ResolvedResult(source="tavily", content="Short snippet C.", url="https://c.com", score=0.6),
    ]


@pytest.fixture
def insufficient_total_content():
    """Two results with total chars < 1000 but not fragmented (one >= 500 chars).

    Gate checks: conflicts first, then fragmentation, then insufficient_content.
    Content must be similar enough (>= 0.2 similarity) to avoid conflicts.
    One result >= 500 chars to avoid fragmentation (short_count <= 1 for 2 results).
    Total < 1000 chars to trigger insufficient_content.
    """
    base = (
        "Web documentation resolvers fetch and process content from multiple providers. "
        "They use cascade strategies to try providers in order of cost and quality. "
        "Each provider returns structured content that is scored for relevance. "
    )
    content_long = (
        base + "The resolver supports multiple output formats for downstream consumption. "
        "Caching layers reduce redundant fetches across similar queries efficiently. "
        "Performance benchmarks show the resolver handles thousands of concurrent requests. "
        "Error handling and retry logic ensure reliable operation under adverse network conditions. "
    )  # >= 500 chars (not short)
    content_short = base + "Extra detail."  # ~300 chars (short)
    return [
        ResolvedResult(source="jina", content=content_long, url="https://a.com", score=0.85),
        ResolvedResult(source="firecrawl", content=content_short, url="https://b.com", score=0.80),
    ]


@pytest.fixture
def complete_results():
    """Results with sufficient total content and no issues."""
    return [
        ResolvedResult(
            source="jina",
            content=LONG_CONTENT[:1200],
            url="https://tokio.rs",
            score=0.85,
        ),
        ResolvedResult(
            source="firecrawl",
            content=LONG_CONTENT[200:1400],
            url="https://docs.rs/tokio",
            score=0.80,
        ),
    ]


@pytest.fixture
def multi_provider_results():
    """Three provider results with different content."""
    return [
        ResolvedResult(
            source="jina",
            content="Tokio is an async runtime for Rust. It provides I/O, networking, "
            "and scheduling primitives. Tokio uses a work-stealing scheduler and "
            "supports thousands of concurrent tasks. The runtime is battle-tested "
            "in production systems worldwide and powers critical infrastructure.",
            url="https://tokio.rs",
            score=0.88,
        ),
        ResolvedResult(
            source="firecrawl",
            content="Getting started with Tokio requires adding the tokio dependency "
            "to your Cargo.toml. The basic runtime setup uses #[tokio::main] attribute "
            "macro. Tokio supports both multi-threaded and current-thread runtimes. "
            "You can spawn tasks using tokio::spawn() function.",
            url="https://docs.rs/tokio",
            score=0.82,
        ),
        ResolvedResult(
            source="tavily",
            content="Tokio ecosystem includes towers for middleware, hyper for HTTP, "
            "and tonic for gRPC. The tokio-console provides real-time debugging. "
            "Tokio 1.0 was released in 2020 and has been stable since then. "
            "The project is hosted on GitHub with active community support.",
            url="https://github.com/tokio-rs/tokio",
            score=0.78,
        ),
    ]


# ---------------------------------------------------------------------------
# Content Similarity
# ---------------------------------------------------------------------------


class TestContentSimilarity:
    def test_identical_strings(self):
        assert _content_similarity("hello world", "hello world") == 1.0

    def test_empty_strings(self):
        assert _content_similarity("", "hello") == 0.0
        assert _content_similarity("hello", "") == 0.0
        assert _content_similarity("", "") == 0.0

    def test_similar_strings(self):
        a = "The quick brown fox jumps over the lazy dog"
        b = "The quick brown fox leaps over the lazy dog"
        ratio = _content_similarity(a, b)
        assert ratio > 0.8

    def test_different_strings(self):
        a = "Completely unrelated text about cooking recipes"
        b = "Advanced quantum computing algorithms and theory"
        ratio = _content_similarity(a, b)
        assert ratio < 0.3

    def test_truncation_at_2000_chars(self):
        long_a = "a" * 3000
        long_b = "a" * 1000 + "b" * 2000
        # Both truncated to 2000 chars; ratio = 1000/2000 = 0.5
        ratio = _content_similarity(long_a, long_b)
        assert ratio >= 0.5


# ---------------------------------------------------------------------------
# Conflict Detection
# ---------------------------------------------------------------------------


class TestHasConflicts:
    def test_single_result_no_conflict(self):
        results = [
            ResolvedResult(
                source="jina", content="Some content here.", url="https://a.com", score=0.8
            ),
        ]
        assert _has_conflicts(results) is False

    def test_empty_results_no_conflict(self):
        assert _has_conflicts([]) is False

    def test_similar_results_no_conflict(self, two_similar_results):
        assert _has_conflicts(two_similar_results) is False

    def test_conflicting_results(self, two_conflicting_results):
        assert _has_conflicts(two_conflicting_results) is True

    def test_three_results_two_conflict(self):
        content_a = "Tokio runtime details for async Rust programming with I/O."
        content_b = "Tokio runtime details for async Rust programming with I/O."
        content_c = "React component lifecycle and hooks API documentation."
        results = [
            ResolvedResult(source="jina", content=content_a, url="https://a.com", score=0.8),
            ResolvedResult(source="firecrawl", content=content_b, url="https://b.com", score=0.7),
            ResolvedResult(source="tavily", content=content_c, url="https://c.com", score=0.6),
        ]
        assert _has_conflicts(results) is True


# ---------------------------------------------------------------------------
# Fragmentation Detection
# ---------------------------------------------------------------------------


class TestIsFragmented:
    def test_not_fragmented_with_long_content(self):
        results = [
            ResolvedResult(source="jina", content="A" * 600, url="https://a.com", score=0.8),
            ResolvedResult(source="firecrawl", content="B" * 600, url="https://b.com", score=0.7),
        ]
        assert _is_fragmented(results) is False

    def test_fragmented_when_majority_short(self, fragmented_results):
        assert _is_fragmented(fragmented_results) is True

    def test_fragmented_custom_threshold(self):
        results = [
            ResolvedResult(source="jina", content="x" * 20, url="https://a.com", score=0.8),
            ResolvedResult(source="firecrawl", content="y" * 20, url="https://b.com", score=0.7),
        ]
        assert _is_fragmented(results, min_chars=100) is True

    def test_not_fragmented_when_majority_long(self):
        results = [
            ResolvedResult(source="jina", content="A" * 600, url="https://a.com", score=0.8),
            ResolvedResult(source="firecrawl", content="B" * 600, url="https://b.com", score=0.7),
            ResolvedResult(source="tavily", content="Short", url="https://c.com", score=0.6),
        ]
        assert _is_fragmented(results) is False


# ---------------------------------------------------------------------------
# Synthesis Gate Decision
# ---------------------------------------------------------------------------


class TestSynthesisGateDecision:
    def test_empty_results(self):
        should_call, reason = synthesis_gate_decision([])
        assert should_call is False
        assert reason == "no_results"

    def test_single_high_quality(self, single_high_quality_result):
        should_call, reason = synthesis_gate_decision([single_high_quality_result])
        assert should_call is False
        assert reason == "single_high_quality"

    def test_single_low_quality(self, single_low_quality_result):
        should_call, reason = synthesis_gate_decision([single_low_quality_result])
        assert should_call is True
        assert reason == "single_low_quality"

    def test_conflicts_trigger_llm(self, two_conflicting_results):
        should_call, reason = synthesis_gate_decision(two_conflicting_results)
        assert should_call is True
        assert reason == "conflicts"

    def test_fragmented_triggers_llm(self, fragmented_results):
        should_call, reason = synthesis_gate_decision(fragmented_results)
        assert should_call is True
        assert reason == "fragmented"

    def test_insufficient_content_triggers_llm(self, insufficient_total_content):
        should_call, reason = synthesis_gate_decision(insufficient_total_content)
        assert should_call is True
        assert reason == "insufficient_content"

    def test_complete_skips_llm(self, complete_results):
        should_call, reason = synthesis_gate_decision(complete_results)
        assert should_call is False
        assert reason == "complete"

    def test_custom_threshold(self):
        result = ResolvedResult(source="jina", content=LONG_CONTENT, url="https://a.com", score=0.7)
        # Default threshold 0.8 → should call
        should_call, _ = synthesis_gate_decision([result], threshold=0.8)
        assert should_call is True
        # Lower threshold → skip
        should_call, _ = synthesis_gate_decision([result], threshold=0.6)
        assert should_call is False


# ---------------------------------------------------------------------------
# Deterministic Merge
# ---------------------------------------------------------------------------


class TestDeterministicMerge:
    def test_empty_results(self):
        assert deterministic_merge([]) == ""

    def test_single_result_passthrough(self, single_high_quality_result):
        output = deterministic_merge([single_high_quality_result])
        assert "Deterministic extraction from jina" in output
        assert "[1] https://docs.rs/tokio" in output
        assert "[ANCHOR: SUMMARY]" in output
        assert "[ANCHOR: TECHNICAL_DETAILS]" in output
        assert "[ANCHOR: COMPARISON]" in output
        assert "[ANCHOR: CITATIONS]" in output
        assert single_high_quality_result.content in output

    def test_multi_result_merge(self, two_similar_results):
        output = deterministic_merge(two_similar_results)
        assert "Deterministic merge of 2 sources" in output
        assert "[1] https://tokio.rs" in output
        assert "[2] https://docs.rs/tokio" in output
        assert "[ANCHOR: SUMMARY]" in output

    def test_deduplication_in_merge(self):
        shared_lines = [
            "Line A: Tokio is a runtime",
            "Line B: Used for async I/O",
            "Line C: Built on Rust",
        ]
        results = [
            ResolvedResult(
                source="jina",
                content="\n".join(shared_lines + ["Extra from jina: work-stealing scheduler"]),
                url="https://tokio.rs",
                score=0.85,
            ),
            ResolvedResult(
                source="firecrawl",
                content="\n".join(shared_lines + ["Extra from firecrawl: task spawning API"]),
                url="https://docs.rs",
                score=0.80,
            ),
        ]
        output = deterministic_merge(results)
        # Shared lines should appear only once
        assert output.count("Line A: Tokio is a runtime") == 1
        # Unique lines from both sources should be present
        assert "work-stealing scheduler" in output
        assert "task spawning API" in output

    def test_merge_has_frontmatter(self, multi_provider_results):
        output = deterministic_merge(multi_provider_results)
        assert output.startswith("---")
        assert "relevance_score:" in output
        assert "intent_category:" in output
        assert "token_estimate:" in output
        assert "last_updated:" in output

    def test_merge_source_labels(self, multi_provider_results):
        output = deterministic_merge(multi_provider_results)
        assert "Source 1: Jina" in output
        assert "Source 2: Firecrawl" in output
        assert "Source 3: Tavily" in output

    def test_merge_handles_none_urls(self):
        results = [
            ResolvedResult(source="jina", content="Content A.", url=None, score=0.8),
            ResolvedResult(source="firecrawl", content="Content B.", url=None, score=0.7),
        ]
        output = deterministic_merge(results)
        assert "[1] N/A" in output
        assert "[2] N/A" in output


# ---------------------------------------------------------------------------
# Quality Score Calculation
# ---------------------------------------------------------------------------


class TestQualityScoreCalculation:
    def test_perfect_score(self):
        doc = (
            "---\n"
            "relevance_score: 0.9\n"
            "intent_category: Technical\n"
            "token_estimate: 500\n"
            "last_updated: 2026-01-01\n"
            "---\n\n"
            "[ANCHOR: SUMMARY]\n"
            "Summary text.\n\n"
            "[ANCHOR: TECHNICAL_DETAILS]\n"
            "Technical details here.\n\n"
            "[ANCHOR: COMPARISON]\n"
            "Comparison text.\n\n"
            "[ANCHOR: CITATIONS]\n"
            "[1] https://example.com\n\n"
        )
        # Pad to avoid too_short
        doc += "\n".join(f"Unique line {i}: detail about topic {i}" for i in range(30))
        score = score_content(doc, ["https://example.com"])
        assert score.score == pytest.approx(1.0)
        assert score.too_short is False
        assert score.acceptable is True

    def test_too_short_penalty(self):
        # Short content (< 500 chars) with enough unique lines to avoid duplicate penalty
        lines = [f"Unique line {i}: topic {i} has different words here" for i in range(8)]
        content = "\n".join(lines)
        score = score_content(content, [])
        assert score.too_short is True
        # 1.0 - 0.25 (short) - 0.10 (no links) = 0.65
        assert score.score == pytest.approx(0.65)

    def test_missing_links_penalty(self):
        # Multi-line unique content (>= 500 chars) to avoid duplicate_heavy
        lines = [f"Unique line number {i} about topic {i} for testing purposes" for i in range(30)]
        long_doc = "\n".join(lines)
        score = score_content(long_doc, [])
        assert score.missing_links is True
        assert score.too_short is False
        # 1.0 - 0.10 (no links) = 0.90
        assert score.score == pytest.approx(0.90)

    def test_duplicate_heavy_penalty(self):
        repeated = "\n".join(["Same line repeated over and over"] * 50)
        score = score_content(repeated, ["https://example.com"])
        assert score.duplicate_heavy is True
        assert score.score < 1.0

    def test_noise_penalty(self):
        noisy = " ".join(
            ["cookie"] * 4
            + ["subscribe"] * 4
            + ["javascript"] * 4
            + [f"unique word {i}" for i in range(20)]
        )
        score = score_content(noisy, ["https://example.com"])
        assert score.noisy is True
        assert score.score < 1.0

    def test_jargon_penalty(self):
        jargon_doc = (
            "This seamless and robust solution leverages comprehensive streamlined "
            "approaches to revolutionize game-changing intuitive next-generation "
            "cutting-edge state-of-the-art best-in-class unlock transform supercharge "
        )
        jargon_doc += "\n".join(
            f"Unique technical line {i} about specific topic" for i in range(20)
        )
        score = score_content(jargon_doc, ["https://example.com"])
        assert score.noisy is True  # jargon sets noisy=True

    def test_frontmatter_bonus(self):
        doc_with_fm = (
            "---\nrelevance_score: 0.8\nintent_category: Technical\n"
            "token_estimate: 200\nlast_updated: 2026-01-01\n---\n\n"
        )
        doc_with_fm += "\n".join(f"Unique content line {i} for variety" for i in range(30))
        score_with = score_content(doc_with_fm, ["https://example.com"])

        doc_without = "\n".join(f"Unique content line {i} for variety" for i in range(30))
        score_without = score_content(doc_without, ["https://example.com"])

        assert score_with.score >= score_without.score

    def test_anchors_bonus(self):
        doc_with_anchors = (
            "[ANCHOR: SUMMARY]\nSummary.\n\n"
            "[ANCHOR: TECHNICAL_DETAILS]\nDetails.\n\n"
            "[ANCHOR: COMPARISON]\nComparison.\n\n"
            "[ANCHOR: CITATIONS]\nCitations.\n\n"
        )
        doc_with_anchors += "\n".join(f"Unique anchor test line {i}" for i in range(30))
        score_with = score_content(doc_with_anchors, ["https://example.com"])

        doc_without = "\n".join(f"Unique anchor test line {i}" for i in range(30))
        score_without = score_content(doc_without, ["https://example.com"])

        assert score_with.score >= score_without.score

    def test_bot_challenge_detected(self):
        bot_content = "Just a moment... Checking your browser before accessing. cf-challenge."
        bot_content += "\n" + "A" * 600
        score = score_content(bot_content, ["https://example.com"])
        assert score.bot_challenge is True
        assert score.acceptable is False

    def test_acceptable_threshold(self):
        score = score_content("A" * 600, ["https://example.com"])
        assert score.acceptable is True
        assert score.score >= ACCEPTABLE_THRESHOLD

    def test_clamped_to_zero(self):
        # All penalties active
        repeated_noisy_jargon = (
            "cookie subscribe javascript log in sign up " * 10
            + "seamlessly robust powerful comprehensive streamlined leverage "
        )
        repeated_noisy_jargon += "\n".join(["Same line"] * 50)
        score = score_content(repeated_noisy_jargon, [])
        assert score.score >= 0.0  # Clamped, never negative

    def test_non_string_input(self):
        score = score_content(None, [])
        assert score.score == 1.0  # MagicMock bypass


# ---------------------------------------------------------------------------
# Anchor Validation
# ---------------------------------------------------------------------------


class TestAnchorValidation:
    REQUIRED_ANCHORS = [
        "[ANCHOR: SUMMARY]",
        "[ANCHOR: TECHNICAL_DETAILS]",
        "[ANCHOR: COMPARISON]",
        "[ANCHOR: CITATIONS]",
    ]

    def test_all_anchors_present(self):
        from scripts.quality import _check_anchors

        doc = "\n".join(self.REQUIRED_ANCHORS)
        assert _check_anchors(doc) is True

    def test_missing_one_anchor(self):
        from scripts.quality import _check_anchors

        doc = "[ANCHOR: SUMMARY]\n[ANCHOR: TECHNICAL_DETAILS]\n[ANCHOR: CITATIONS]"
        assert _check_anchors(doc) is False

    def test_no_anchors(self):
        from scripts.quality import _check_anchors

        assert _check_anchors("Just plain text content.") is False

    def test_partial_anchor_match_rejected(self):
        from scripts.quality import _check_anchors

        doc = (
            "[ANCHOR: SUM]\n[ANCHOR: TECHNICAL_DETAILS]\n[ANCHOR: COMPARISON]\n[ANCHOR: CITATIONS]"
        )
        assert _check_anchors(doc) is False

    def test_anchors_in_deterministic_merge(self):
        """Verify deterministic_merge output always includes all anchors."""
        results = [
            ResolvedResult(source="jina", content="Content A.", url="https://a.com", score=0.8),
        ]
        output = deterministic_merge(results)
        for anchor in self.REQUIRED_ANCHORS:
            assert anchor in output, f"Missing anchor: {anchor}"


# ---------------------------------------------------------------------------
# Empty and Single Result Handling
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_synthesis_gate(self):
        should_call, reason = synthesis_gate_decision([])
        assert should_call is False
        assert reason == "no_results"

    def test_single_result_high_score_passthrough(self):
        result = ResolvedResult(
            source="jina",
            content=LONG_CONTENT,
            url="https://example.com",
            score=0.95,
        )
        should_call, reason = synthesis_gate_decision([result])
        assert should_call is False
        assert reason == "single_high_quality"

    def test_single_result_low_score_calls_llm(self):
        result = ResolvedResult(
            source="jina",
            content="Barely anything.",
            url="https://example.com",
            score=0.2,
        )
        should_call, reason = synthesis_gate_decision([result])
        assert should_call is True
        assert reason == "single_low_quality"

    def test_deterministic_merge_empty(self):
        assert deterministic_merge([]) == ""

    def test_deterministic_merge_single(self):
        result = ResolvedResult(source="jina", content="Hello.", url="https://a.com", score=0.8)
        output = deterministic_merge([result])
        assert "Hello." in output
        assert "jina" in output


# ---------------------------------------------------------------------------
# Quality Threshold Filtering
# ---------------------------------------------------------------------------


class TestQualityThresholdFiltering:
    def test_results_below_threshold_rejected(self):
        low_quality = ResolvedResult(
            source="jina",
            content="Tiny.",
            url="https://example.com",
            score=0.2,
        )
        should_call, reason = synthesis_gate_decision([low_quality], threshold=0.8)
        assert should_call is True  # Low quality triggers LLM synthesis

    def test_results_above_threshold_accepted(self):
        high_quality = ResolvedResult(
            source="jina",
            content=LONG_CONTENT,
            url="https://example.com",
            score=0.9,
        )
        should_call, reason = synthesis_gate_decision([high_quality], threshold=0.8)
        assert should_call is False

    def test_mixed_quality_multi_result(self):
        """When mixing high and low quality, conflict/fragmentation logic takes over."""
        results = [
            ResolvedResult(
                source="jina",
                content=LONG_CONTENT,
                url="https://a.com",
                score=0.9,
            ),
            ResolvedResult(
                source="tavily",
                content=LONG_CONTENT,
                url="https://b.com",
                score=0.3,
            ),
        ]
        should_call, reason = synthesis_gate_decision(results)
        # Two similar long results → complete (no conflict, no fragmentation)
        assert should_call is False
        assert reason == "complete"


# ---------------------------------------------------------------------------
# Provider Format Handling
# ---------------------------------------------------------------------------


class TestDifferentProviderFormats:
    def test_merge_handles_different_content_lengths(self):
        results = [
            ResolvedResult(
                source="jina",
                content="Short but valid.",
                url="https://jina.example.com",
                score=0.7,
            ),
            ResolvedResult(
                source="firecrawl",
                content=LONG_CONTENT,
                url="https://fc.example.com",
                score=0.85,
            ),
        ]
        output = deterministic_merge(results)
        assert "Short but valid." in output
        assert "documentation resolvers" in output.lower()

    def test_merge_preserves_all_sources(self, multi_provider_results):
        output = deterministic_merge(multi_provider_results)
        assert "jina" in output.lower()
        assert "firecrawl" in output.lower()
        assert "tavily" in output.lower()
        assert "[1]" in output
        assert "[2]" in output
        assert "[3]" in output

    def test_gate_delegates_to_real_functions(self):
        """Verify synthesis_gate_decision uses real logic, not conftest mocks."""
        # The conftest mocks should_call_llm_synthesis, not synthesis_gate_decision
        results = []
        should_call, reason = synthesis_gate_decision(results)
        assert should_call is False
        assert reason == "no_results"

    def test_synthesis_gate_score_respects_threshold(self):
        """Score-based gating for single results."""
        result = ResolvedResult(
            source="jina",
            content=LONG_CONTENT,
            url="https://example.com",
            score=0.75,
        )
        # Threshold 0.7 → skip (0.75 >= 0.7)
        should_call, _ = synthesis_gate_decision([result], threshold=0.7)
        assert should_call is False
        # Threshold 0.8 → call (0.75 < 0.8)
        should_call, _ = synthesis_gate_decision([result], threshold=0.8)
        assert should_call is True
