import pytest
from unittest.mock import MagicMock, patch
from scripts.quality import is_bot_challenge, score_content
from scripts.utils.fetch import fetch_url_content
from scripts.models import ErrorType, ProviderType
from scripts.utils import _detect_error_type

CF_CHALLENGE_HTML = """
<html><head><title>Just a moment...</title></head>
<body>Checking your browser before accessing the site.
<div id="cf-content">cf_chl_opt.chl_params...</div>
</body></html>
"""

NORMAL_HTML = "<html><body><h1>Documentation</h1><p>This is the API docs.</p></body></html>"

def test_detects_cloudflare_challenge():
    assert is_bot_challenge(CF_CHALLENGE_HTML) is True

def test_does_not_flag_normal_content():
    assert is_bot_challenge(NORMAL_HTML) is False

def test_score_content_sets_bot_challenge_flag():
    qs = score_content(CF_CHALLENGE_HTML)
    assert hasattr(qs, "bot_challenge")
    assert qs.bot_challenge is True
    assert qs.acceptable is False

def test_score_content_no_bot_challenge_on_normal():
    qs = score_content(NORMAL_HTML * 10)  # ensure not too_short
    assert hasattr(qs, "bot_challenge")
    assert qs.bot_challenge is False

def test_detect_error_type_bot_challenge():
    exc = ValueError("bot_challenge detected")
    assert _detect_error_type(exc) == ErrorType.BOT_CHALLENGE

    exc2 = ValueError("Cloudflare ray id")
    assert _detect_error_type(exc2) == ErrorType.BOT_CHALLENGE

def test_fetch_url_content_raises_on_bot_challenge():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = CF_CHALLENGE_HTML

    # Force the local imports in fetch_url_content to return our mocks
    with patch("scripts.utils.fetch.validate_url") as mock_validate, \
         patch("scripts.utils.fetch._safe_request") as mock_safe, \
         patch("scripts.utils.fetch.get_session") as mock_sess:

        # When scripts.utils.__init__ is imported, it re-exports these.
        # But fetch_url_content does: from scripts.utils import ...
        # This from-import happens INSIDE the function.

        mock_validate.return_value.is_valid = True
        mock_validate.return_value.final_url = "https://example.com"
        mock_safe.return_value = mock_response

        # We need to make sure that when fetch_url_content executes 'from scripts.utils import ...'
        # it gets our mocks.

        with patch("scripts.utils.validate_url", mock_validate), \
             patch("scripts.utils._safe_request", mock_safe), \
             patch("scripts.utils.get_session", mock_sess):
                with pytest.raises(ValueError, match="Bot challenge detected"):
                    fetch_url_content("https://example.com")

def test_fetch_url_content_raises_on_403_bot_challenge():
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.text = "Access Denied. checking your browser..."

    with patch("scripts.utils.validate_url") as mock_validate, \
         patch("scripts.utils._safe_request") as mock_safe, \
         patch("scripts.utils.get_session") as mock_sess:
        mock_validate.return_value.is_valid = True
        mock_safe.return_value = mock_response

        with patch("scripts.utils.validate_url", mock_validate), \
             patch("scripts.utils._safe_request", mock_safe), \
             patch("scripts.utils.get_session", mock_sess):
                with pytest.raises(ValueError, match="Bot challenge detected"):
                    fetch_url_content("https://example.com")

def test_should_skip_from_bot_challenge_cache():
    from scripts.cache_negative import should_skip_from_bot_challenge_cache
    cache = {"direct_fetch": {"example.com"}}
    assert should_skip_from_bot_challenge_cache("direct_fetch", "https://example.com/docs", cache) is True
    assert should_skip_from_bot_challenge_cache("direct_fetch", "https://other.com", cache) is False
    assert should_skip_from_bot_challenge_cache("jina", "https://example.com", cache) is False
