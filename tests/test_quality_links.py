"""Tests for link detection in content quality scoring.

The cascades call `score_content(content)` without a link list, so the scorer
has to infer links from the markdown itself. Getting this wrong made every
result take a flat missing-links penalty.
"""

from scripts.quality import extract_links, score_content


def test_extract_markdown_links():
    markdown = "See [the docs](https://example.com/docs) and [more](https://example.org)."

    links = extract_links(markdown)

    assert len(links) == 2
    assert any("example.com/docs" in link for link in links)


def test_extract_angle_bracket_links():
    assert extract_links("Visit <https://example.com/page> today") != []


def test_extract_links_from_non_markdown_returns_empty():
    assert extract_links("plain text with no links at all") == []
    assert extract_links("") == []


def test_content_with_links_is_not_penalised():
    body = "Useful documentation prose. " * 40
    without = score_content(body + "\n[ref](https://example.com/a)")
    with_explicit_empty = score_content(body, links=[])

    # No links at all -> penalty applies.
    assert without.missing_links is False
    assert with_explicit_empty.missing_links is True

    baseline = score_content(body)
    assert baseline.missing_links is True
    assert baseline.score < without.score


def test_explicit_links_argument_wins():
    body = "Useful documentation prose. " * 40

    assert score_content(body, links=["https://example.com"]).missing_links is False
    assert score_content(body, links=[]).missing_links is True


def test_non_string_input_is_handled():
    result = score_content(None)  # type: ignore[arg-type]

    assert result.too_short is True
    assert result.acceptable is False
