"""Query-relevance blending in the quality scorer (Plan 22 B3).

The scorer used to be relevance-blind: a pristine page about the wrong topic
scored as high as an on-topic one, so the paid-skip gate could short-circuit
on content that did not answer the query. `score_content` now accepts an
optional query and applies a proportional discount for missing terms.

Also covers Plan 22 B13: the provider content floor (`constants.MIN_CHARS`)
and the scorer's `too_short` threshold are one value, so a provider can no
longer accept content the scorer is guaranteed to reject.
"""

import pytest

from scripts import constants
from scripts.quality import RELEVANCE_WEIGHT, THRESHOLD_MIN_CHARS, score_content


def _build_body(sentences: list[str], paragraphs: int = 12) -> str:
    """Return a long, duplicate-free body (unique numbered lines)."""
    lines = []
    for i, sentence in enumerate(sentences * paragraphs):
        lines.append(f"{sentence} Section {i}.")
    return "\n".join(lines)


ASYNCIO_BODY = _build_body(["Use the Python asyncio event loop to run coroutines and tasks."])
KUBERNETES_BODY = _build_body(["Kubernetes schedules pods across cluster nodes and services."])


def test_bodies_are_long_and_not_duplicate_heavy():
    # Guards the fixtures: a change to the duplicate heuristic must not turn
    # these comparisons into accidental duplicate-penalty tests.
    for body in (ASYNCIO_BODY, KUBERNETES_BODY):
        assert len(body) >= THRESHOLD_MIN_CHARS
        assert score_content(body).duplicate_heavy is False


def test_irrelevant_content_scores_lower_than_relevant():
    query = "python asyncio"

    relevant = score_content(ASYNCIO_BODY, query=query)
    irrelevant = score_content(KUBERNETES_BODY, query=query)

    assert relevant.relevance == 1.0
    assert irrelevant.relevance == 0.0
    assert irrelevant.score < relevant.score
    # Proportional discount, not a flat penalty.
    assert irrelevant.score == pytest.approx(relevant.score * (1 - RELEVANCE_WEIGHT))


def test_irrelevant_content_fails_the_acceptance_gate():
    assert score_content(KUBERNETES_BODY, query="python asyncio").acceptable is False
    assert score_content(ASYNCIO_BODY, query="python asyncio").acceptable is True


def test_partial_overlap_sits_between_the_extremes():
    query = "python kubernetes"

    relevant = score_content(ASYNCIO_BODY, query="python asyncio")
    partial = score_content(ASYNCIO_BODY, query=query)
    irrelevant = score_content(KUBERNETES_BODY, query="python asyncio")

    assert partial.relevance == pytest.approx(0.5)
    assert irrelevant.score < partial.score < relevant.score


def test_no_query_leaves_the_heuristic_score_untouched():
    baseline = score_content(ASYNCIO_BODY)
    with_none = score_content(ASYNCIO_BODY, query=None)

    assert baseline.score == with_none.score
    assert baseline.relevance == 1.0
    assert with_none.relevance == 1.0


def test_query_without_usable_terms_disables_the_blend():
    baseline = score_content(ASYNCIO_BODY)

    for query in ("to be or", "a of in", ""):
        scored = score_content(KUBERNETES_BODY, query=query)
        assert scored.relevance == 1.0
        assert scored.score == score_content(KUBERNETES_BODY).score
        assert baseline.score == score_content(ASYNCIO_BODY).score


def test_relevance_is_case_insensitive():
    scored = score_content(ASYNCIO_BODY, query="PYTHON Asyncio")

    assert scored.relevance == 1.0


def test_min_chars_matches_quality_threshold():
    assert THRESHOLD_MIN_CHARS == constants.MIN_CHARS == 500


def test_provider_floor_content_is_scored_too_short():
    # Content between the old 200-char provider floor and the 500-char quality
    # gate used to be accepted by providers and then always scored too short.
    body = "word " * 45  # 225 chars
    assert len(body) < constants.MIN_CHARS

    scored = score_content(body)

    assert scored.too_short is True
    assert scored.acceptable is False
