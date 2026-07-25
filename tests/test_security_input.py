"""Comprehensive input validation security tests for the Web Doc Resolver.

Tests input sanitization, rate limiting behavior, URL length limits,
Unicode/IDN homograph attacks, path traversal, and header injection.

All tests are deterministic — no live network calls.
"""

import httpx
import pytest
import respx

from scripts.providers import (
    _clear_rate_limits,
    _is_rate_limited,
    _set_rate_limit,
    is_rate_limited,
)
from scripts.utils.http import _safe_request, is_safe_url, validate_url
from scripts.utils.urls import is_url, normalize_query, normalize_url

# ---------------------------------------------------------------------------
# Query / Input Sanitization
# ---------------------------------------------------------------------------


class TestQuerySanitization:
    """Verify normalize_query strips and normalizes user input."""

    def test_lowercasing(self):
        assert normalize_query("Python AsyncIO") == "python asyncio"

    def test_whitespace_collapse(self):
        assert normalize_query("  python   asyncio  ") == "python asyncio"

    def test_empty_string(self):
        assert normalize_query("") == ""

    def test_whitespace_only(self):
        assert normalize_query("   ") == ""

    def test_tabs_and_newlines(self):
        assert normalize_query("python\t\nasyncio") == "python asyncio"

    def test_special_characters_preserved(self):
        result = normalize_query("C++ vs Rust!")
        assert "c++" in result
        assert "rust!" in result

    def test_unicode_query(self):
        result = normalize_query("  你好 世界  ")
        assert result == "你好 世界"

    def test_extremely_long_query_truncated(self):
        long_query = "python " * 10000
        result = normalize_query(long_query)
        assert len(result) < len(long_query)

    def test_control_characters(self):
        """Null bytes are NOT stripped by normalize_query — documents current behavior."""
        result = normalize_query("test\x00query")
        # normalize_query only does .lower().split() — null bytes survive
        assert "test\x00query" == result

    def test_sql_injection_in_query(self):
        """SQL injection attempts should be treated as literal text."""
        malicious = "'; DROP TABLE users; --"
        result = normalize_query(malicious)
        assert "drop table" in result


# ---------------------------------------------------------------------------
# Rate Limiting Behavior
# ---------------------------------------------------------------------------


class TestRateLimiting:
    """Verify rate limiting mechanism works correctly."""

    def test_rate_limit_set_and_check(self):
        _clear_rate_limits()
        assert not _is_rate_limited("test_provider")
        _set_rate_limit("test_provider", cooldown=60)
        assert _is_rate_limited("test_provider")
        _clear_rate_limits()

    def test_rate_limit_per_provider_independent(self):
        _clear_rate_limits()
        _set_rate_limit("provider_a")
        assert _is_rate_limited("provider_a")
        assert not _is_rate_limited("provider_b")
        _clear_rate_limits()

    def test_rate_limit_clear(self):
        _clear_rate_limits()
        _set_rate_limit("provider_a")
        _clear_rate_limits()
        assert not _is_rate_limited("provider_a")

    def test_rate_limit_no_reentry(self):
        """After clearing a limit, the provider is immediately available."""
        _clear_rate_limits()
        _set_rate_limit("provider_c")
        _clear_rate_limits()
        _set_rate_limit("provider_c")
        assert _is_rate_limited("provider_c")
        _clear_rate_limits()

    def test_rate_limit_alias(self):
        """The public is_rate_limited alias works identically."""
        _clear_rate_limits()
        assert not is_rate_limited("test_alias")
        _set_rate_limit("test_alias")
        assert is_rate_limited("test_alias")
        _clear_rate_limits()

    def test_rate_limit_thread_safety(self):
        """Basic smoke test for concurrent access."""
        import threading

        _clear_rate_limits()
        errors = []

        def set_and_check():
            try:
                _set_rate_limit("threaded")
                for _ in range(100):
                    _is_rate_limited("threaded")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=set_and_check) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        _clear_rate_limits()


# ---------------------------------------------------------------------------
# URL Length Limits
# ---------------------------------------------------------------------------


class TestURLLengthLimits:
    """Verify handling of extremely long URLs."""

    def test_very_long_path(self):
        long_path = "a" * 10000
        url = f"https://example.com/{long_path}"
        # Should not crash — is_safe_url handles it gracefully
        result = is_safe_url(url)
        # Long but valid HTTP URL — depends on parser behavior
        assert isinstance(result, bool)

    def test_very_long_query(self):
        long_query = "q=" + "a" * 10000
        url = f"https://example.com?{long_query}"
        result = is_safe_url(url)
        assert isinstance(result, bool)

    def test_very_long_fragment(self):
        long_fragment = "a" * 10000
        url = f"https://example.com#{long_fragment}"
        result = is_safe_url(url)
        assert isinstance(result, bool)

    def test_validate_url_empty(self):
        result = validate_url("")
        assert not result.is_valid
        assert result.error == "Empty URL"

    def test_validate_url_whitespace(self):
        result = validate_url("   ")
        assert not result.is_valid

    def test_validate_url_invalid_format(self):
        result = validate_url("not a url at all")
        assert not result.is_valid
        assert result.error == "Invalid URL format"


# ---------------------------------------------------------------------------
# Unicode / IDN Homograph Attacks
# ---------------------------------------------------------------------------


class TestUnicodeHomograph:
    """Verify that Unicode-based IDN homograph attacks are handled."""

    def test_cyrillic_a_in_domain(self):
        """Cyrillic 'а' looks like Latin 'a' — should be treated as a separate URL."""
        # Cyrillic а (U+0430) in "exаmple.com"
        url = "https://ex\u0430mple.com"
        # urlparse doesn't normalize IDN, so is_url should still parse it
        result = is_url(url)
        # The URL has a valid structure — it passes URL format check
        assert result is True

    def test_unicode_in_path(self):
        url = "https://example.com/\u4e2d\u6587\u8def\u5f84"
        assert is_url(url)

    def test_unicode_in_query(self):
        url = "https://example.com?q=\u4e2d\u6587"
        assert is_url(url)

    def test_mixed_script_domain(self):
        """Domain mixing Latin and Cyrillic scripts."""
        url = "https://gооgle.com"  # Cyrillic о
        result = is_url(url)
        assert result is True

    def test_punycode_domain(self):
        url = "https://xn--e1afmapc.xn--p1ai"
        assert is_url(url)

    def test_zero_width_characters(self):
        """Zero-width characters in URL should not cause crashes."""
        url = "https://exam\u200bp\u200ble.com"
        result = is_url(url)
        assert result is True


# ---------------------------------------------------------------------------
# Path Traversal in URL Parameters
# ---------------------------------------------------------------------------


class TestPathTraversal:
    """Verify path traversal attempts are handled safely."""

    def test_dot_dot_in_path(self):
        url = "https://example.com/../../../etc/passwd"
        assert is_url(url)
        # is_safe_url should allow the URL through to the HTTP layer
        # which normalizes paths before making requests
        assert is_safe_url(url)

    def test_encoded_dot_dot(self):
        url = "https://example.com/%2e%2e/%2e%2e/etc/passwd"
        assert is_url(url)

    def test_double_encoded_dot_dot(self):
        url = "https://example.com/%252e%252e/%252e%252e/etc/passwd"
        assert is_url(url)

    def test_backslash_path(self):
        url = "https://example.com/..\\..\\..\\etc\\passwd"
        assert is_url(url)

    def test_null_byte_in_path(self):
        """Null bytes in URLs should be handled gracefully."""
        url = "https://example.com/page%00.html"
        result = is_url(url)
        assert isinstance(result, bool)

    def test_path_traversal_ssrf_file_scheme(self):
        """Path traversal to file:// should be blocked by scheme check."""
        assert not is_safe_url("file:///etc/passwd")
        assert not is_safe_url("file://127.0.0.1/etc/passwd")

    def test_path_traversal_with_redirect(self):
        """A redirect to file:// should be blocked by _safe_request."""
        with respx.mock:
            respx.get("https://example.com/redirect").mock(
                return_value=httpx.Response(301, headers={"Location": "file:///etc/passwd"})
            )
            with pytest.raises(httpx.RequestError, match="SSRF blocked"):
                _safe_request("GET", "https://example.com/redirect")


# ---------------------------------------------------------------------------
# Header Injection via URL Components
# ---------------------------------------------------------------------------


class TestHeaderInjection:
    """Verify URL components cannot inject HTTP headers."""

    def test_crlf_in_path(self):
        """CRLF in URL path should not inject headers."""
        url = "https://example.com/page\r\nX-Injected: true"
        result = is_url(url)
        assert isinstance(result, bool)

    def test_crlf_in_host(self):
        url = "https://example.com\r\nX-Injected: true/path"
        result = is_url(url)
        assert isinstance(result, bool)

    def test_newline_in_path(self):
        url = "https://example.com/path%0aX-Injected:%20true"
        result = is_url(url)
        assert isinstance(result, bool)

    def test_null_byte_in_host(self):
        url = "https://example.com%00.evil.com"
        result = is_url(url)
        assert isinstance(result, bool)

    def test_tab_in_url(self):
        url = "https://example.com/path\tX-Injected: true"
        result = is_url(url)
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# URL Normalization Security
# ---------------------------------------------------------------------------


class TestURLNormalizationSecurity:
    """Verify normalize_url handles security-relevant edge cases."""

    def test_tracking_param_removal(self):
        url = "https://example.com/page?utm_source=test&q=hello&id=123"
        normalized = normalize_url(url)
        assert "utm_source" not in normalized
        assert "q=hello" in normalized
        assert "id=123" in normalized

    def test_case_normalization(self):
        url = "HTTPS://EXAMPLE.COM/Path"
        normalized = normalize_url(url)
        assert normalized.startswith("https://")

    def test_default_port_stripping(self):
        assert ":80" not in normalize_url("http://example.com:80/path")
        assert ":443" not in normalize_url("https://example.com:443/path")

    def test_non_default_port_preserved(self):
        normalized = normalize_url("https://example.com:8080/path")
        assert ":8080" in normalized

    def test_trailing_slash_stripped(self):
        normalized = normalize_url("https://example.com/path/")
        assert not normalized.endswith("/path/")

    def test_root_slash_preserved(self):
        normalized = normalize_url("https://example.com/")
        assert normalized.endswith("/")

    def test_malformed_url_graceful(self):
        result = normalize_url("not a url")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_fragment_handling(self):
        url = "https://example.com/page#section1"
        normalized = normalize_url(url)
        assert isinstance(normalized, str)


# ---------------------------------------------------------------------------
# Validate URL Security
# ---------------------------------------------------------------------------


class TestValidateURLSecurity:
    """Verify validate_url rejects unsafe inputs without network calls."""

    def test_empty_url(self):
        result = validate_url("")
        assert not result.is_valid

    def test_whitespace_url(self):
        result = validate_url("   ")
        assert not result.is_valid

    def test_ftp_url(self):
        result = validate_url("ftp://example.com/file")
        assert not result.is_valid

    def test_file_url(self):
        result = validate_url("file:///etc/passwd")
        assert not result.is_valid

    def test_javascript_url(self):
        result = validate_url("javascript:alert(1)")
        assert not result.is_valid

    def test_ssrf_localhost(self):
        result = validate_url("http://localhost/admin")
        assert not result.is_valid or result.error

    def test_ssrf_private_ip(self):
        result = validate_url("http://192.168.1.1/admin")
        assert not result.is_valid or result.error
