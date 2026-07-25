"""Extended edge-case tests for utility functions.

Covers HTML parsing, URL normalization, content compaction, cache keys,
and session behavior — focused on scenarios NOT in test_utils.py.
"""

import threading

import pytest

from scripts.utils.cache import _cache_key, _l1_clear
from scripts.utils.html import compact_content, extract_text_from_html
from scripts.utils.urls import normalize_query, normalize_url, score_result

# ─── extract_text_from_html edge cases ──────────────────────────────────────


class TestExtractTextHtmlEntities:
    """HTML entity decoding edge cases."""

    def test_numeric_decimal_entity(self):
        html = "<p>&#65;</p>"
        assert "A" in extract_text_from_html(html)

    def test_numeric_hex_entity(self):
        html = "<p>&#x41;</p>"
        assert "A" in extract_text_from_html(html)

    def test_named_entity_ampersand(self):
        html = "<p>&amp;</p>"
        assert "&" in extract_text_from_html(html)

    def test_named_entity_less_than(self):
        html = "<p>&lt;</p>"
        assert "<" in extract_text_from_html(html)

    def test_named_entity_greater_than(self):
        html = "<p>&gt;</p>"
        assert ">" in extract_text_from_html(html)

    def test_malformed_entity_amp_semicolon(self):
        html = "<p>&;</p>"
        result = extract_text_from_html(html)
        assert "&;" in result or "&" in result

    def test_unknown_entity_name(self):
        html = "<p>&foobarbaz;</p>"
        result = extract_text_from_html(html)
        assert "foobarbaz" in result or "&" in result

    def test_unclosed_ampersand(self):
        html = "<p>test &amp next</p>"
        result = extract_text_from_html(html)
        assert "test" in result

    def test_entity_in_nested_tags(self):
        html = "<div><span>&#72;</span>ello</div>"
        result = extract_text_from_html(html)
        assert "Hello" in result or "H" in result


class TestExtractTextSkipBehavior:
    """Script/style tag skip and nesting behavior."""

    def test_script_content_skipped(self):
        html = "<p>visible</p><script>alert('xss')</script><p>also visible</p>"
        result = extract_text_from_html(html)
        assert "alert" not in result
        assert "visible" in result

    def test_style_content_skipped(self):
        html = "<p>text</p><style>.hidden{display:none}</style>"
        result = extract_text_from_html(html)
        assert "display" not in result
        assert "text" in result

    def test_nested_script_style(self):
        html = "<div><script><style>.x{}</style></script>content</div>"
        result = extract_text_from_html(html)
        assert "content" in result
        assert "x" not in result

    def test_pre_block_preserves_whitespace(self):
        html = "<pre>  indented\ncode block</pre>"
        result = extract_text_from_html(html)
        assert "indented" in result
        assert "code block" in result

    def test_code_inline(self):
        html = "<p>Use <code>print()</code> to output</p>"
        result = extract_text_from_html(html)
        assert "`" in result
        assert "print()" in result

    def test_nested_pre_code(self):
        html = "<pre><code>line1\nline2</code></pre>"
        result = extract_text_from_html(html)
        assert "line1" in result
        assert "line2" in result

    def test_blockquote_preserves_text(self):
        html = "<blockquote><p>quoted text</p></blockquote>"
        result = extract_text_from_html(html)
        assert "quoted text" in result

    def test_hr_separator(self):
        html = "<p>before</p><hr><p>after</p>"
        result = extract_text_from_html(html)
        assert "---" in result
        assert "before" in result
        assert "after" in result

    def test_br_newline(self):
        html = "<p>line1<br>line2</p>"
        result = extract_text_from_html(html)
        assert "line1" in result
        assert "line2" in result


class TestExtractTextEdgeCases:
    """Other HTML edge cases."""

    def test_empty_html(self):
        assert extract_text_from_html("") == ""

    def test_plain_text_passthrough(self):
        result = extract_text_from_html("just plain text")
        assert "just plain text" in result

    def test_deeply_nested_tags(self):
        html = "<div><div><div><div><p>deep</p></div></div></div></div>"
        result = extract_text_from_html(html)
        assert "deep" in result

    def test_multiple_newlines_collapsed(self):
        html = "<p>a</p><p>b</p><p>c</p>"
        result = extract_text_from_html(html)
        assert "\n\n\n" not in result

    def test_word_joiner_removed(self):
        html = "<p>word\u2060joiner</p>"
        result = extract_text_from_html(html)
        assert "\u2060" not in result

    def test_only_whitespace_content(self):
        html = "<p>   </p>"
        result = extract_text_from_html(html)
        assert result.strip() == ""

    def test_table_content_extracted(self):
        html = "<table><tr><td>cell1</td><td>cell2</td></tr></table>"
        result = extract_text_from_html(html)
        assert "cell1" in result
        assert "cell2" in result


# ─── normalize_url edge cases ───────────────────────────────────────────────


class TestNormalizeUrlEdgeCases:
    """URL normalization edge cases NOT covered in test_utils.py."""

    def test_strips_trailing_slash_path(self):
        result = normalize_url("https://example.com/docs/")
        assert result == "https://example.com/docs"

    def test_keeps_root_trailing_slash(self):
        result = normalize_url("https://example.com/")
        assert result.endswith("/")

    def test_strips_empty_fragment(self):
        result = normalize_url("https://example.com/page#")
        assert "#" not in result or result.endswith("#") is False

    def test_keeps_non_empty_fragment(self):
        result = normalize_url("https://example.com/page#section")
        assert "section" in result

    def test_strips_default_port_http(self):
        result = normalize_url("http://example.com:80/path")
        assert ":80" not in result

    def test_strips_default_port_https(self):
        result = normalize_url("https://example.com:443/path")
        assert ":443" not in result

    def test_keeps_non_default_port(self):
        result = normalize_url("https://example.com:8080/path")
        assert ":8080" in result

    def test_lowercases_scheme(self):
        result = normalize_url("HTTPS://Example.COM/Path")
        assert result.startswith("https://")

    def test_lowercases_netloc(self):
        result = normalize_url("https://EXAMPLE.COM/Path")
        assert "example.com" in result

    def test_strips_tracking_params(self):
        result = normalize_url("https://example.com/page?utm_source=test&keep=this")
        assert "utm_source" not in result
        assert "keep=this" in result

    def test_strips_all_utm_params(self):
        url = "https://example.com/page?utm_source=a&utm_medium=b&utm_campaign=c"
        result = normalize_url(url)
        assert "utm_" not in result

    def test_strips_social_tracking_params(self):
        url = "https://example.com/page?fbclid=abc&gclid=def"
        result = normalize_url(url)
        assert "fbclid" not in result
        assert "gclid" not in result

    def test_preserves_non_tracking_params(self):
        result = normalize_url("https://example.com/page?lang=en&page=2")
        assert "lang=en" in result
        assert "page=2" in result

    def test_empty_query_preserved(self):
        result = normalize_url("https://example.com/page")
        assert "?" not in result

    def test_encoded_characters_preserved(self):
        result = normalize_url("https://example.com/path%20with%20spaces")
        assert "path%20with%20spaces" in result

    def test_complex_url_normalization(self):
        url = "https://EXAMPLE.COM:443/Docs/?utm_source=twitter&q=test#intro"
        result = normalize_url(url)
        assert result.startswith("https://")
        assert ":443" not in result
        assert "utm_source" not in result
        assert "q=test" in result


# ─── compact_content extended edge cases ─────────────────────────────────────


class TestCompactContentExtended:
    """Content compaction edge cases beyond what test_utils.py covers."""

    def test_all_whitespace_lines(self):
        content = "  \n\t\n  \n"
        result = compact_content(content, 1000)
        assert result.strip() == ""

    def test_many_unique_lines(self):
        lines = [f"unique line {i}" for i in range(1000)]
        content = "\n".join(lines)
        result = compact_content(content, 50000)
        result_lines = [line for line in result.splitlines() if line]
        assert len(result_lines) == 1000

    def test_interleaved_duplicates(self):
        content = "a\nb\na\nc\nb\nd\na"
        result = compact_content(content, 1000)
        lines = [line for line in result.splitlines() if line]
        assert lines == ["a", "b", "c", "d"]

    def test_single_line(self):
        result = compact_content("hello world", 100)
        assert result == "hello world"

    def test_single_line_truncated(self):
        result = compact_content("a very long line", 5)
        assert len(result) == 5

    def test_blank_lines_preserved_even_with_truncation(self):
        content = "a\n\n\nb"
        result = compact_content(content, 10)
        lines = result.splitlines()
        assert "" in lines

    def test_content_exactly_at_max_chars(self):
        content = "a" * 100
        result = compact_content(content, 100)
        assert len(result) == 100

    def test_content_one_over_max_chars(self):
        content = "a" * 101
        result = compact_content(content, 100)
        assert len(result) == 100

    def test_mixed_long_and_short_lines(self):
        content = "short\n" + "x" * 5000 + "\nshort again"
        result = compact_content(content, 100)
        assert "short" in result

    def test_duplicate_after_trim_same_as_original(self):
        content = "  hello  \nhello\n"
        result = compact_content(content, 1000)
        lines = [line for line in result.splitlines() if line]
        assert lines.count("hello") == 1


# ─── cache key generation ───────────────────────────────────────────────────


class TestCacheKeyConsistency:
    """Cache key generation: determinism, normalization, source separation."""

    def test_same_url_same_key(self):
        k1 = _cache_key("https://example.com/page", "direct_fetch")
        k2 = _cache_key("https://example.com/page", "direct_fetch")
        assert k1 == k2

    def test_same_query_same_key(self):
        k1 = _cache_key("python tutorial", "exa")
        k2 = _cache_key("python tutorial", "exa")
        assert k1 == k2

    def test_different_source_different_key(self):
        k1 = _cache_key("https://example.com", "direct_fetch")
        k2 = _cache_key("https://example.com", "jina")
        assert k1 != k2

    def test_url_normalized_key(self):
        # Tracking params should be stripped before hashing
        k1 = _cache_key("https://example.com/page?utm_source=tw", "direct_fetch")
        k2 = _cache_key("https://example.com/page", "direct_fetch")
        assert k1 == k2

    def test_query_normalized_key(self):
        # Case and whitespace normalization should produce same key
        k1 = _cache_key("Python  Tutorial", "exa")
        k2 = _cache_key("python tutorial", "exa")
        assert k1 == k2

    def test_key_is_hex_sha256(self):
        key = _cache_key("test", "source")
        assert len(key) == 64  # SHA-256 hex digest length
        int(key, 16)  # Should not raise — valid hex

    def test_url_trailing_slash_normalized(self):
        k1 = _cache_key("https://example.com/path/", "direct_fetch")
        k2 = _cache_key("https://example.com/path", "direct_fetch")
        assert k1 == k2

    def test_empty_query_same_key(self):
        k1 = _cache_key("", "exa")
        k2 = _cache_key("", "exa")
        assert k1 == k2

    def test_empty_source_affects_key(self):
        k1 = _cache_key("test", "source_a")
        k2 = _cache_key("test", "source_b")
        assert k1 != k2


# ─── normalize_query extended ────────────────────────────────────────────────


class TestNormalizeQueryExtended:
    """Additional query normalization edge cases."""

    def test_mixed_case_preserves_words(self):
        result = normalize_query("Python TUTORIAL Guide")
        assert result == "python tutorial guide"

    def test_special_characters_preserved(self):
        result = normalize_query("c++ programming")
        assert "c++" in result

    def test_unicode_preserved(self):
        result = normalize_query("日本語テスト")
        assert "日本語テスト" in result

    def test_multiple_tabs_and_spaces(self):
        result = normalize_query("python\t\ttutorial   guide")
        assert result == "python tutorial guide"

    def test_leading_trailing_mixed_whitespace(self):
        result = normalize_query("\t\n  hello world  \n\t")
        assert result == "hello world"


# ─── score_result edge cases ─────────────────────────────────────────────────


class TestScoreResultEdgeCases:
    """Score result boundary values and edge cases."""

    def test_none_url_zero_content(self):
        score = score_result(None, "")
        assert 0.0 <= score <= 1.0

    def test_empty_content(self):
        score = score_result("https://example.com", "")
        assert 0.0 <= score <= 1.0

    def test_short_content_penalty(self):
        score = score_result("https://example.com", "few words")
        assert score < 0.5

    def test_medium_content_neutral(self):
        content = " ".join(["word"] * 200)
        score = score_result("https://example.com", content)
        assert score == pytest.approx(0.5, abs=0.01)

    def test_long_content_bonus(self):
        content = " ".join(["word"] * 600)
        score = score_result("https://example.com", content)
        assert score > 0.5

    def test_edu_domain_bonus(self):
        content = " ".join(["word"] * 600)
        score = score_result("https://university.edu/page", content)
        assert score >= 0.7

    def test_gov_domain_bonus(self):
        content = " ".join(["word"] * 600)
        score = score_result("https://agency.gov/page", content)
        assert score >= 0.7

    def test_github_bonus(self):
        content = " ".join(["word"] * 600)
        score = score_result("https://github.com/user/repo", content)
        assert score >= 0.7

    def test_stackoverflow_bonus(self):
        content = " ".join(["word"] * 600)
        score = score_result("https://stackoverflow.com/q/123", content)
        assert score >= 0.7

    def test_score_clamped_at_zero(self):
        score = score_result("https://random-site.com", "x")
        assert score >= 0.0

    def test_score_clamped_at_one(self):
        content = " ".join(["word"] * 600)
        score = score_result("https://github.com/user/repo", content)
        assert score <= 1.0

    def test_exactly_500_words_no_bonus(self):
        content = " ".join(["word"] * 500)
        score_500 = score_result("https://example.com", content)
        content501 = " ".join(["word"] * 501)
        score_501 = score_result("https://example.com", content501)
        assert score_501 > score_500

    def test_exactly_49_words_penalty(self):
        content = " ".join(["word"] * 49)
        score_49 = score_result("https://example.com", content)
        content50 = " ".join(["word"] * 50)
        score_50 = score_result("https://example.com", content50)
        assert score_49 < score_50


# ─── L1 cache (in-memory) edge cases ─────────────────────────────────────────


class TestL1CacheEdgeCases:
    """L1 in-memory cache TTL and eviction behavior."""

    def setup_method(self):
        _l1_clear()

    def test_get_miss(self):
        from scripts.utils.cache import _l1_get

        assert _l1_get("nonexistent") is None

    def test_set_and_get(self):
        from scripts.utils.cache import _l1_get, _l1_set

        _l1_set("key1", {"data": "value"}, ttl=300)
        assert _l1_get("key1") == {"data": "value"}

    def test_expired_entry_returns_none(self):
        from scripts.utils.cache import _l1_get, _l1_set

        _l1_set("key1", "value", ttl=-1)
        # Negative TTL sets expire_time in the past — already expired on get
        assert _l1_get("key1") is None

    def test_clear_empties_cache(self):
        from scripts.utils.cache import _l1_clear, _l1_get, _l1_set

        _l1_set("key1", "value")
        _l1_clear()
        assert _l1_get("key1") is None

    def test_overwrite_same_key(self):
        from scripts.utils.cache import _l1_get, _l1_set

        _l1_set("key1", "first", ttl=300)
        _l1_set("key1", "second", ttl=300)
        assert _l1_get("key1") == "second"

    def test_thread_safety_concurrent_writes(self):
        from scripts.utils.cache import _l1_get, _l1_set

        errors = []

        def writer(key, value):
            try:
                for i in range(100):
                    _l1_set(f"{key}_{i}", f"value_{i}", ttl=300)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(f"t{t}", t)) for t in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        # Verify some keys exist
        assert _l1_get("t0_0") is not None
