"""Unit tests for provider implementations with HTTP mocking.

Tests each provider's resolution path, error handling, SSRF blocking,
rate limiting, and malformed response handling using respx for httpx
mocking and unittest.mock for SDK-based providers.
"""

import os
from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest
import respx

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAFE_URL = "https://example.com/docs"
SAFE_QUERY = "python asyncio tutorial"

JINA_MARKDOWN = (
    "# Example Page\n\nThis is a comprehensive page with detailed information "
    "about Python async programming. " * 20
)

SERPER_RESPONSE = {
    "organic": [
        {
            "title": "Async Python Guide",
            "link": "https://example.com/async",
            "snippet": "A comprehensive guide to async Python programming.",
        },
        {
            "title": "Tutorials Point",
            "link": "https://tutorials.example.com/async",
            "snippet": "Learn async Python step by step.",
        },
    ]
}

EXA_MCP_SSE = (
    'data: {"jsonrpc":"2.0","id":1,"result":{"content":[{"text":"'
    + "Exa search results for async Python. " * 30
    + '"}]}}\n'
)

TAVILY_RESPONSE = {
    "results": [
        {"title": "Async Guide", "content": "Comprehensive async Python guide content. " * 15},
        {"title": "Tutorials", "content": "Step by step async tutorial content. " * 15},
    ]
}

EXA_SDK_RESPONSE = MagicMock(
    results=[
        MagicMock(highlight="Exa highlight content. " * 20, text=None),
        MagicMock(highlight=None, text="Exa text fallback content. " * 20),
    ]
)

DDG_SDK_RESPONSE = [
    {"title": "DuckDuckGo Result 1", "body": "DuckDuckGo search body content. " * 10},
    {"title": "DuckDuckGo Result 2", "body": "Another DDG result with info. " * 10},
]

FIRECRAWL_SDK_RESPONSE = MagicMock(
    markdown="# Firecrawl Content\n\nFirecrawl extracted markdown. " * 20
)


# ---------------------------------------------------------------------------
# Jina Provider Tests
# ---------------------------------------------------------------------------


class TestJinaSync:
    """Sync Jina provider tests using respx HTTP mocking."""

    @respx.mock
    def test_successful_resolution(self):
        from scripts.providers.jina import resolve_with_jina

        respx.get(f"https://r.jina.ai/{SAFE_URL}").mock(
            return_value=httpx.Response(200, text=JINA_MARKDOWN)
        )

        result = resolve_with_jina(SAFE_URL)
        assert result is not None
        assert result.source == "jina"
        assert result.url == SAFE_URL
        assert "Example Page" in result.content

    @respx.mock
    def test_content_truncation(self):
        from scripts.providers.jina import resolve_with_jina

        respx.get(f"https://r.jina.ai/{SAFE_URL}").mock(
            return_value=httpx.Response(200, text=JINA_MARKDOWN)
        )

        result = resolve_with_jina(SAFE_URL, max_chars=100)
        assert result is not None
        assert len(result.content) <= 100

    @respx.mock
    def test_rate_limit_response(self):
        from scripts.providers import _is_rate_limited
        from scripts.providers.jina import resolve_with_jina

        respx.get(f"https://r.jina.ai/{SAFE_URL}").mock(
            return_value=httpx.Response(429, text="Rate limited")
        )

        result = resolve_with_jina(SAFE_URL)
        assert result is None
        assert _is_rate_limited("jina")

    @respx.mock
    def test_auth_error_401(self):
        from scripts.providers.jina import resolve_with_jina

        respx.get(f"https://r.jina.ai/{SAFE_URL}").mock(
            return_value=httpx.Response(401, text="Unauthorized")
        )
        assert resolve_with_jina(SAFE_URL) is None

    @respx.mock
    def test_auth_error_403(self):
        from scripts.providers.jina import resolve_with_jina

        respx.get(f"https://r.jina.ai/{SAFE_URL}").mock(
            return_value=httpx.Response(403, text="Forbidden")
        )
        assert resolve_with_jina(SAFE_URL) is None

    @respx.mock
    def test_server_error_500(self):
        from scripts.providers.jina import resolve_with_jina

        respx.get(f"https://r.jina.ai/{SAFE_URL}").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        assert resolve_with_jina(SAFE_URL) is None

    @respx.mock
    def test_server_error_502(self):
        from scripts.providers.jina import resolve_with_jina

        respx.get(f"https://r.jina.ai/{SAFE_URL}").mock(
            return_value=httpx.Response(502, text="Bad Gateway")
        )
        assert resolve_with_jina(SAFE_URL) is None

    @respx.mock
    def test_timeout_error(self):
        from scripts.providers.jina import resolve_with_jina

        respx.get(f"https://r.jina.ai/{SAFE_URL}").mock(
            side_effect=httpx.ReadTimeout("Read timed out")
        )
        assert resolve_with_jina(SAFE_URL) is None

    @respx.mock
    def test_connect_error(self):
        from scripts.providers.jina import resolve_with_jina

        respx.get(f"https://r.jina.ai/{SAFE_URL}").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        assert resolve_with_jina(SAFE_URL) is None

    @respx.mock
    def test_insufficient_content(self):
        from scripts.providers.jina import resolve_with_jina

        respx.get(f"https://r.jina.ai/{SAFE_URL}").mock(
            return_value=httpx.Response(200, text="short")
        )
        assert resolve_with_jina(SAFE_URL) is None

    def test_ssrf_blocked_localhost(self):
        from scripts.providers.jina import resolve_with_jina

        assert resolve_with_jina("http://localhost/secret") is None

    def test_ssrf_blocked_loopback(self):
        from scripts.providers.jina import resolve_with_jina

        assert resolve_with_jina("http://127.0.0.1/secret") is None

    def test_ssrf_blocked_cloud_metadata(self):
        from scripts.providers.jina import resolve_with_jina

        assert resolve_with_jina("http://169.254.169.254/metadata") is None

    def test_ssrf_blocked_private_network(self):
        from scripts.providers.jina import resolve_with_jina

        assert resolve_with_jina("http://10.0.0.1/internal") is None

    def test_ssrf_blocked_ftp_scheme(self):
        from scripts.providers.jina import resolve_with_jina

        assert resolve_with_jina("ftp://example.com/file") is None

    def test_ssrf_blocked_file_scheme(self):
        from scripts.providers.jina import resolve_with_jina

        assert resolve_with_jina("file:///etc/passwd") is None

    @respx.mock
    def test_empty_response(self):
        from scripts.providers.jina import resolve_with_jina

        respx.get(f"https://r.jina.ai/{SAFE_URL}").mock(return_value=httpx.Response(200, text=""))
        assert resolve_with_jina(SAFE_URL) is None


class TestJinaAsync:
    """Async Jina provider tests using respx HTTP mocking."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_successful_resolution(self):
        from scripts.providers.jina import resolve_with_jina_async

        respx.get(f"https://r.jina.ai/{SAFE_URL}").mock(
            return_value=httpx.Response(200, text=JINA_MARKDOWN)
        )

        result = await resolve_with_jina_async(SAFE_URL)
        assert result is not None
        assert result.source == "jina"
        assert result.url == SAFE_URL
        assert "Example Page" in result.content

    @respx.mock
    @pytest.mark.asyncio
    async def test_rate_limit_response(self):
        from scripts.providers import _is_rate_limited
        from scripts.providers.jina import resolve_with_jina_async

        respx.get(f"https://r.jina.ai/{SAFE_URL}").mock(
            return_value=httpx.Response(429, text="Rate limited")
        )

        result = await resolve_with_jina_async(SAFE_URL)
        assert result is None
        assert _is_rate_limited("jina")

    @respx.mock
    @pytest.mark.asyncio
    async def test_auth_error(self):
        from scripts.providers.jina import resolve_with_jina_async

        respx.get(f"https://r.jina.ai/{SAFE_URL}").mock(
            return_value=httpx.Response(401, text="Unauthorized")
        )
        assert await resolve_with_jina_async(SAFE_URL) is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_server_error(self):
        from scripts.providers.jina import resolve_with_jina_async

        respx.get(f"https://r.jina.ai/{SAFE_URL}").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        assert await resolve_with_jina_async(SAFE_URL) is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_timeout(self):
        from scripts.providers.jina import resolve_with_jina_async

        respx.get(f"https://r.jina.ai/{SAFE_URL}").mock(side_effect=httpx.ReadTimeout("timeout"))
        assert await resolve_with_jina_async(SAFE_URL) is None

    @pytest.mark.asyncio
    async def test_ssrf_blocked(self):
        from scripts.providers.jina import resolve_with_jina_async

        result = await resolve_with_jina_async("http://169.254.169.254/metadata")
        assert result is None


# ---------------------------------------------------------------------------
# Serper Provider Tests
# ---------------------------------------------------------------------------


class TestSerperSync:
    """Sync Serper provider tests using respx HTTP mocking."""

    @respx.mock
    @patch.dict(os.environ, {"SERPER_API_KEY": "test-serper-key"})
    def test_successful_resolution(self):
        from scripts.providers.serper import resolve_with_serper

        respx.post("https://google.serper.dev/search").mock(
            return_value=httpx.Response(200, json=SERPER_RESPONSE)
        )

        result = resolve_with_serper(SAFE_QUERY)
        assert result is not None
        assert result.source == "serper"
        assert result.query == SAFE_QUERY
        assert "Async Python Guide" in result.content

    @respx.mock
    @patch.dict(os.environ, {"SERPER_API_KEY": "test-serper-key"})
    def test_content_truncation(self):
        from scripts.providers.serper import resolve_with_serper

        respx.post("https://google.serper.dev/search").mock(
            return_value=httpx.Response(200, json=SERPER_RESPONSE)
        )

        result = resolve_with_serper(SAFE_QUERY, max_chars=50)
        assert result is not None
        assert len(result.content) <= 50

    @respx.mock
    @patch.dict(os.environ, {"SERPER_API_KEY": "test-serper-key"})
    def test_rate_limit_429(self):
        from scripts.providers import _is_rate_limited
        from scripts.providers.serper import resolve_with_serper

        respx.post("https://google.serper.dev/search").mock(
            return_value=httpx.Response(429, text="Rate limited")
        )

        result = resolve_with_serper(SAFE_QUERY)
        assert result is None
        assert _is_rate_limited("serper")

    @respx.mock
    @patch.dict(os.environ, {"SERPER_API_KEY": "test-serper-key"})
    def test_auth_error_401(self):
        from scripts.providers.serper import resolve_with_serper

        respx.post("https://google.serper.dev/search").mock(
            return_value=httpx.Response(401, text="Unauthorized")
        )
        assert resolve_with_serper(SAFE_QUERY) is None

    @respx.mock
    @patch.dict(os.environ, {"SERPER_API_KEY": "test-serper-key"})
    def test_auth_error_403(self):
        from scripts.providers.serper import resolve_with_serper

        respx.post("https://google.serper.dev/search").mock(
            return_value=httpx.Response(403, text="Forbidden")
        )
        assert resolve_with_serper(SAFE_QUERY) is None

    @respx.mock
    @patch.dict(os.environ, {"SERPER_API_KEY": "test-serper-key"})
    def test_server_error_500(self):
        from scripts.providers.serper import resolve_with_serper

        respx.post("https://google.serper.dev/search").mock(
            return_value=httpx.Response(500, text="Server Error")
        )
        assert resolve_with_serper(SAFE_QUERY) is None

    @respx.mock
    @patch.dict(os.environ, {"SERPER_API_KEY": "test-serper-key"})
    def test_timeout(self):
        from scripts.providers.serper import resolve_with_serper

        respx.post("https://google.serper.dev/search").mock(
            side_effect=httpx.ReadTimeout("timeout")
        )
        assert resolve_with_serper(SAFE_QUERY) is None

    @patch.dict(os.environ, {}, clear=True)
    def test_no_api_key(self):
        from scripts.providers.serper import resolve_with_serper

        assert resolve_with_serper(SAFE_QUERY) is None

    @respx.mock
    @patch.dict(os.environ, {"SERPER_API_KEY": "test-serper-key"})
    def test_empty_organic_results(self):
        from scripts.providers.serper import resolve_with_serper

        respx.post("https://google.serper.dev/search").mock(
            return_value=httpx.Response(200, json={"organic": []})
        )
        assert resolve_with_serper(SAFE_QUERY) is None

    @respx.mock
    @patch.dict(os.environ, {"SERPER_API_KEY": "test-serper-key"})
    def test_no_usable_snippets(self):
        from scripts.providers.serper import resolve_with_serper

        respx.post("https://google.serper.dev/search").mock(
            return_value=httpx.Response(
                200, json={"organic": [{"title": "", "link": "", "snippet": ""}]}
            )
        )
        assert resolve_with_serper(SAFE_QUERY) is None


class TestSerperAsync:
    """Async Serper provider tests using respx HTTP mocking."""

    @respx.mock
    @patch.dict(os.environ, {"SERPER_API_KEY": "test-serper-key"})
    @pytest.mark.asyncio
    async def test_successful_resolution(self):
        from scripts.providers.serper import resolve_with_serper_async

        respx.post("https://google.serper.dev/search").mock(
            return_value=httpx.Response(200, json=SERPER_RESPONSE)
        )

        result = await resolve_with_serper_async(SAFE_QUERY)
        assert result is not None
        assert result.source == "serper"
        assert "Async Python Guide" in result.content

    @respx.mock
    @patch.dict(os.environ, {"SERPER_API_KEY": "test-serper-key"})
    @pytest.mark.asyncio
    async def test_rate_limit_429(self):
        from scripts.providers import _is_rate_limited
        from scripts.providers.serper import resolve_with_serper_async

        respx.post("https://google.serper.dev/search").mock(
            return_value=httpx.Response(429, text="Rate limited")
        )

        result = await resolve_with_serper_async(SAFE_QUERY)
        assert result is None
        assert _is_rate_limited("serper")

    @respx.mock
    @patch.dict(os.environ, {"SERPER_API_KEY": "test-serper-key"})
    @pytest.mark.asyncio
    async def test_timeout(self):
        from scripts.providers.serper import resolve_with_serper_async

        respx.post("https://google.serper.dev/search").mock(
            side_effect=httpx.ReadTimeout("timeout")
        )
        assert await resolve_with_serper_async(SAFE_QUERY) is None


# ---------------------------------------------------------------------------
# Exa MCP Provider Tests
# ---------------------------------------------------------------------------


class TestExaMcpSync:
    """Sync Exa MCP provider tests using respx HTTP mocking."""

    @respx.mock
    def test_successful_resolution(self):
        from scripts.providers.exa import resolve_with_exa_mcp

        respx.post("https://mcp.exa.ai/mcp").mock(
            return_value=httpx.Response(200, text=EXA_MCP_SSE)
        )

        result = resolve_with_exa_mcp(SAFE_QUERY)
        assert result is not None
        assert result.source == "exa_mcp"
        assert result.query == SAFE_QUERY

    @respx.mock
    def test_content_truncation(self):
        from scripts.providers.exa import resolve_with_exa_mcp

        respx.post("https://mcp.exa.ai/mcp").mock(
            return_value=httpx.Response(200, text=EXA_MCP_SSE)
        )

        result = resolve_with_exa_mcp(SAFE_QUERY, max_chars=50)
        assert result is not None
        assert len(result.content) <= 50

    @respx.mock
    def test_http_error(self):
        from scripts.providers.exa import resolve_with_exa_mcp

        respx.post("https://mcp.exa.ai/mcp").mock(
            return_value=httpx.Response(500, text="Server Error")
        )
        assert resolve_with_exa_mcp(SAFE_QUERY) is None

    @respx.mock
    def test_timeout(self):
        from scripts.providers.exa import resolve_with_exa_mcp

        respx.post("https://mcp.exa.ai/mcp").mock(side_effect=httpx.ReadTimeout("timeout"))
        assert resolve_with_exa_mcp(SAFE_QUERY) is None

    @respx.mock
    def test_connect_error(self):
        from scripts.providers.exa import resolve_with_exa_mcp

        respx.post("https://mcp.exa.ai/mcp").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        assert resolve_with_exa_mcp(SAFE_QUERY) is None

    @respx.mock
    def test_no_sse_data(self):
        from scripts.providers.exa import resolve_with_exa_mcp

        respx.post("https://mcp.exa.ai/mcp").mock(
            return_value=httpx.Response(200, text="plain text without sse\n")
        )
        assert resolve_with_exa_mcp(SAFE_QUERY) is None

    @respx.mock
    def test_empty_sse_content(self):
        from scripts.providers.exa import resolve_with_exa_mcp

        empty_sse = 'data: {"jsonrpc":"2.0","id":1,"result":{"content":[{"text":""}]}}\n'
        respx.post("https://mcp.exa.ai/mcp").mock(return_value=httpx.Response(200, text=empty_sse))
        assert resolve_with_exa_mcp(SAFE_QUERY) is None

    @respx.mock
    def test_malformed_json_in_sse(self):
        from scripts.providers.exa import resolve_with_exa_mcp

        bad_sse = "data: {not valid json}\n"
        respx.post("https://mcp.exa.ai/mcp").mock(return_value=httpx.Response(200, text=bad_sse))
        assert resolve_with_exa_mcp(SAFE_QUERY) is None


class TestExaMcpAsync:
    """Async Exa MCP provider tests using respx HTTP mocking."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_successful_resolution(self):
        from scripts.providers.exa import resolve_with_exa_mcp_async

        respx.post("https://mcp.exa.ai/mcp").mock(
            return_value=httpx.Response(200, text=EXA_MCP_SSE)
        )

        result = await resolve_with_exa_mcp_async(SAFE_QUERY)
        assert result is not None
        assert result.source == "exa_mcp"

    @respx.mock
    @pytest.mark.asyncio
    async def test_timeout(self):
        from scripts.providers.exa import resolve_with_exa_mcp_async

        respx.post("https://mcp.exa.ai/mcp").mock(side_effect=httpx.ReadTimeout("timeout"))
        assert await resolve_with_exa_mcp_async(SAFE_QUERY) is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_http_error(self):
        from scripts.providers.exa import resolve_with_exa_mcp_async

        respx.post("https://mcp.exa.ai/mcp").mock(
            return_value=httpx.Response(429, text="Rate limited")
        )
        assert await resolve_with_exa_mcp_async(SAFE_QUERY) is None


# ---------------------------------------------------------------------------
# Tavily Provider Tests (SDK mock — patch at source module)
# ---------------------------------------------------------------------------


class TestTavilySync:
    """Sync Tavily provider tests using SDK mocking."""

    @patch.dict(os.environ, {"TAVILY_API_KEY": "test-tavily-key"})
    @patch("tavily.TavilyClient")
    def test_successful_resolution(self, mock_tavily_cls):
        from scripts.providers.tavily import resolve_with_tavily

        mock_client = Mock()
        mock_client.search.return_value = TAVILY_RESPONSE
        mock_tavily_cls.return_value = mock_client

        result = resolve_with_tavily(SAFE_QUERY)
        assert result is not None
        assert result.source == "tavily"
        assert result.query == SAFE_QUERY
        assert "Async Guide" in result.content

    @patch.dict(os.environ, {"TAVILY_API_KEY": "test-tavily-key"})
    @patch("tavily.TavilyClient")
    def test_content_truncation(self, mock_tavily_cls):
        from scripts.providers.tavily import resolve_with_tavily

        mock_client = Mock()
        mock_client.search.return_value = TAVILY_RESPONSE
        mock_tavily_cls.return_value = mock_client

        result = resolve_with_tavily(SAFE_QUERY, max_chars=50)
        assert result is not None
        assert len(result.content) <= 50

    @patch.dict(os.environ, {"TAVILY_API_KEY": "test-tavily-key"})
    @patch("tavily.TavilyClient")
    def test_empty_results(self, mock_tavily_cls):
        from scripts.providers.tavily import resolve_with_tavily

        mock_client = Mock()
        mock_client.search.return_value = {"results": []}
        mock_tavily_cls.return_value = mock_client

        assert resolve_with_tavily(SAFE_QUERY) is None

    @patch.dict(os.environ, {"TAVILY_API_KEY": "test-tavily-key"})
    @patch("tavily.TavilyClient")
    def test_none_response(self, mock_tavily_cls):
        from scripts.providers.tavily import resolve_with_tavily

        mock_client = Mock()
        mock_client.search.return_value = None
        mock_tavily_cls.return_value = mock_client

        assert resolve_with_tavily(SAFE_QUERY) is None

    @patch.dict(os.environ, {}, clear=True)
    def test_no_api_key(self):
        from scripts.providers.tavily import resolve_with_tavily

        assert resolve_with_tavily(SAFE_QUERY) is None

    @patch.dict(os.environ, {"TAVILY_API_KEY": "test-tavily-key"})
    @patch("tavily.TavilyClient")
    def test_auth_error_401(self, mock_tavily_cls):
        from scripts.providers.tavily import resolve_with_tavily

        error = Exception("Unauthorized")
        error.status_code = 401
        mock_client = Mock()
        mock_client.search.side_effect = error
        mock_tavily_cls.return_value = mock_client

        assert resolve_with_tavily(SAFE_QUERY) is None

    @patch.dict(os.environ, {"TAVILY_API_KEY": "test-tavily-key"})
    @patch("tavily.TavilyClient")
    def test_rate_limit_429(self, mock_tavily_cls):
        from scripts.providers import _is_rate_limited
        from scripts.providers.tavily import resolve_with_tavily

        error = Exception("Rate limited")
        error.status_code = 429
        mock_client = Mock()
        mock_client.search.side_effect = error
        mock_tavily_cls.return_value = mock_client

        result = resolve_with_tavily(SAFE_QUERY)
        assert result is None
        assert _is_rate_limited("tavily")

    @patch.dict(os.environ, {"TAVILY_API_KEY": "test-tavily-key"})
    @patch("tavily.TavilyClient")
    def test_generic_error(self, mock_tavily_cls):
        from scripts.providers.tavily import resolve_with_tavily

        mock_client = Mock()
        mock_client.search.side_effect = RuntimeError("Network error")
        mock_tavily_cls.return_value = mock_client

        assert resolve_with_tavily(SAFE_QUERY) is None


class TestTavilyAsync:
    """Async Tavily provider tests using SDK mocking."""

    @patch.dict(os.environ, {"TAVILY_API_KEY": "test-tavily-key"})
    @patch("tavily.TavilyClient")
    @pytest.mark.asyncio
    async def test_successful_resolution(self, mock_tavily_cls):
        from scripts.providers.tavily import resolve_with_tavily_async

        mock_client = Mock()
        mock_client.search.return_value = TAVILY_RESPONSE
        mock_tavily_cls.return_value = mock_client

        result = await resolve_with_tavily_async(SAFE_QUERY)
        assert result is not None
        assert result.source == "tavily"

    @patch.dict(os.environ, {"TAVILY_API_KEY": "test-tavily-key"})
    @patch("tavily.TavilyClient")
    @pytest.mark.asyncio
    async def test_rate_limit_429(self, mock_tavily_cls):
        from scripts.providers import _is_rate_limited
        from scripts.providers.tavily import resolve_with_tavily_async

        error = Exception("Rate limited")
        error.status_code = 429
        mock_client = Mock()
        mock_client.search.side_effect = error
        mock_tavily_cls.return_value = mock_client

        result = await resolve_with_tavily_async(SAFE_QUERY)
        assert result is None
        assert _is_rate_limited("tavily")


# ---------------------------------------------------------------------------
# Exa SDK Provider Tests (patch at source module)
# ---------------------------------------------------------------------------


class TestExaSync:
    """Sync Exa provider tests using SDK mocking."""

    @patch.dict(os.environ, {"EXA_API_KEY": "test-exa-key"})
    @patch("exa_py.Exa")
    def test_successful_resolution(self, mock_exa_cls):
        from scripts.providers.exa import resolve_with_exa

        mock_client = Mock()
        mock_client.search_and_contents.return_value = EXA_SDK_RESPONSE
        mock_exa_cls.return_value = mock_client

        result = resolve_with_exa(SAFE_QUERY)
        assert result is not None
        assert result.source == "exa"
        assert result.query == SAFE_QUERY

    @patch.dict(os.environ, {"EXA_API_KEY": "test-exa-key"})
    @patch("exa_py.Exa")
    def test_empty_results(self, mock_exa_cls):
        from scripts.providers.exa import resolve_with_exa

        mock_client = Mock()
        mock_response = MagicMock(results=[])
        mock_client.search_and_contents.return_value = mock_response
        mock_exa_cls.return_value = mock_client

        assert resolve_with_exa(SAFE_QUERY) is None

    @patch.dict(os.environ, {"EXA_API_KEY": "test-exa-key"})
    @patch("exa_py.Exa")
    def test_auth_error_401(self, mock_exa_cls):
        from scripts.providers.exa import resolve_with_exa

        error = Exception("Unauthorized")
        error.status_code = 401
        mock_client = Mock()
        mock_client.search_and_contents.side_effect = error
        mock_exa_cls.return_value = mock_client

        assert resolve_with_exa(SAFE_QUERY) is None

    @patch.dict(os.environ, {"EXA_API_KEY": "test-exa-key"})
    @patch("exa_py.Exa")
    def test_rate_limit_429(self, mock_exa_cls):
        from scripts.providers import _is_rate_limited
        from scripts.providers.exa import resolve_with_exa

        error = Exception("Rate limited")
        error.status_code = 429
        mock_client = Mock()
        mock_client.search_and_contents.side_effect = error
        mock_exa_cls.return_value = mock_client

        result = resolve_with_exa(SAFE_QUERY)
        assert result is None
        assert _is_rate_limited("exa")

    @patch.dict(os.environ, {}, clear=True)
    def test_no_api_key(self):
        from scripts.providers.exa import resolve_with_exa

        assert resolve_with_exa(SAFE_QUERY) is None


# ---------------------------------------------------------------------------
# DuckDuckGo Provider Tests (SDK mock — patch at source module)
# ---------------------------------------------------------------------------


class TestDuckDuckGoSync:
    """Sync DuckDuckGo provider tests using SDK mocking."""

    @patch("ddgs.DDGS")
    def test_successful_resolution(self, mock_ddgs_cls):
        from scripts.providers.duckduckgo import resolve_with_duckduckgo

        mock_context = MagicMock()
        mock_context.__enter__ = Mock(return_value=mock_context)
        mock_context.__exit__ = Mock(return_value=False)
        mock_context.text.return_value = DDG_SDK_RESPONSE
        mock_ddgs_cls.return_value = mock_context

        result = resolve_with_duckduckgo(SAFE_QUERY)
        assert result is not None
        assert result.source == "duckduckgo"
        assert result.query == SAFE_QUERY
        assert "DuckDuckGo Result 1" in result.content

    @patch("ddgs.DDGS")
    def test_empty_results(self, mock_ddgs_cls):
        from scripts.providers.duckduckgo import resolve_with_duckduckgo

        mock_context = MagicMock()
        mock_context.__enter__ = Mock(return_value=mock_context)
        mock_context.__exit__ = Mock(return_value=False)
        mock_context.text.return_value = []
        mock_ddgs_cls.return_value = mock_context

        assert resolve_with_duckduckgo(SAFE_QUERY) is None

    @patch("ddgs.DDGS")
    def test_network_error(self, mock_ddgs_cls):
        from scripts.providers.duckduckgo import resolve_with_duckduckgo

        mock_ddgs_cls.side_effect = RuntimeError("Network error")

        assert resolve_with_duckduckgo(SAFE_QUERY) is None

    @patch("ddgs.DDGS")
    def test_content_truncation(self, mock_ddgs_cls):
        from scripts.providers.duckduckgo import resolve_with_duckduckgo

        mock_context = MagicMock()
        mock_context.__enter__ = Mock(return_value=mock_context)
        mock_context.__exit__ = Mock(return_value=False)
        mock_context.text.return_value = DDG_SDK_RESPONSE
        mock_ddgs_cls.return_value = mock_context

        result = resolve_with_duckduckgo(SAFE_QUERY, max_chars=50)
        assert result is not None
        assert len(result.content) <= 50


class TestDuckDuckGoAsync:
    """Async DuckDuckGo provider tests using SDK mocking."""

    @patch("ddgs.DDGS")
    @pytest.mark.asyncio
    async def test_successful_resolution(self, mock_ddgs_cls):
        from scripts.providers.duckduckgo import resolve_with_duckduckgo_async

        mock_context = MagicMock()
        mock_context.__enter__ = Mock(return_value=mock_context)
        mock_context.__exit__ = Mock(return_value=False)
        mock_context.text.return_value = DDG_SDK_RESPONSE
        mock_ddgs_cls.return_value = mock_context

        result = await resolve_with_duckduckgo_async(SAFE_QUERY)
        assert result is not None
        assert result.source == "duckduckgo"

    @patch("ddgs.DDGS")
    @pytest.mark.asyncio
    async def test_empty_results(self, mock_ddgs_cls):
        from scripts.providers.duckduckgo import resolve_with_duckduckgo_async

        mock_context = MagicMock()
        mock_context.__enter__ = Mock(return_value=mock_context)
        mock_context.__exit__ = Mock(return_value=False)
        mock_context.text.return_value = []
        mock_ddgs_cls.return_value = mock_context

        assert await resolve_with_duckduckgo_async(SAFE_QUERY) is None


# ---------------------------------------------------------------------------
# Firecrawl Provider Tests (SDK mock — patch at source module)
# ---------------------------------------------------------------------------


class TestFirecrawlSync:
    """Sync Firecrawl provider tests using SDK mocking."""

    @patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test-fc-key"})
    @patch("firecrawl.Firecrawl")
    def test_successful_resolution(self, mock_fc_cls):
        from scripts.providers.firecrawl import resolve_with_firecrawl

        mock_app = Mock()
        mock_app.scrape.return_value = FIRECRAWL_SDK_RESPONSE
        mock_fc_cls.return_value = mock_app

        result = resolve_with_firecrawl(SAFE_URL)
        assert result is not None
        assert result.source == "firecrawl"
        assert result.url == SAFE_URL
        assert "Firecrawl Content" in result.content

    @patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test-fc-key"})
    @patch("firecrawl.Firecrawl")
    def test_content_truncation(self, mock_fc_cls):
        from scripts.providers.firecrawl import resolve_with_firecrawl

        mock_app = Mock()
        mock_app.scrape.return_value = FIRECRAWL_SDK_RESPONSE
        mock_fc_cls.return_value = mock_app

        result = resolve_with_firecrawl(SAFE_URL, max_chars=50)
        assert result is not None
        assert len(result.content) <= 50

    @patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test-fc-key"})
    @patch("firecrawl.Firecrawl")
    def test_auth_error_401(self, mock_fc_cls):
        from scripts.providers.firecrawl import resolve_with_firecrawl

        error = Exception("Unauthorized")
        error.status_code = 401
        mock_app = Mock()
        mock_app.scrape.side_effect = error
        mock_fc_cls.return_value = mock_app

        assert resolve_with_firecrawl(SAFE_URL) is None

    @patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test-fc-key"})
    @patch("firecrawl.Firecrawl")
    def test_rate_limit_429(self, mock_fc_cls):
        from scripts.providers import _is_rate_limited
        from scripts.providers.firecrawl import resolve_with_firecrawl

        error = Exception("Rate limited")
        error.status_code = 429
        mock_app = Mock()
        mock_app.scrape.side_effect = error
        mock_fc_cls.return_value = mock_app

        result = resolve_with_firecrawl(SAFE_URL)
        assert result is None
        assert _is_rate_limited("firecrawl")

    @patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test-fc-key"})
    @patch("firecrawl.Firecrawl")
    def test_no_markdown(self, mock_fc_cls):
        from scripts.providers.firecrawl import resolve_with_firecrawl

        mock_app = Mock()
        mock_app.scrape.return_value = Mock(spec=[])
        mock_fc_cls.return_value = mock_app

        assert resolve_with_firecrawl(SAFE_URL) is None

    @patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test-fc-key"})
    @patch("firecrawl.Firecrawl")
    def test_empty_markdown(self, mock_fc_cls):
        from scripts.providers.firecrawl import resolve_with_firecrawl

        mock_app = Mock()
        mock_app.scrape.return_value = Mock(markdown="")
        mock_fc_cls.return_value = mock_app

        assert resolve_with_firecrawl(SAFE_URL) is None

    @patch.dict(os.environ, {}, clear=True)
    def test_no_api_key(self):
        from scripts.providers.firecrawl import resolve_with_firecrawl

        assert resolve_with_firecrawl(SAFE_URL) is None

    def test_ssrf_blocked_localhost(self):
        from scripts.providers.firecrawl import resolve_with_firecrawl

        assert resolve_with_firecrawl("http://localhost/secret") is None

    def test_ssrf_blocked_loopback(self):
        from scripts.providers.firecrawl import resolve_with_firecrawl

        assert resolve_with_firecrawl("http://127.0.0.1/secret") is None

    def test_ssrf_blocked_cloud_metadata(self):
        from scripts.providers.firecrawl import resolve_with_firecrawl

        assert resolve_with_firecrawl("http://169.254.169.254/metadata") is None

    def test_ssrf_blocked_ftp_scheme(self):
        from scripts.providers.firecrawl import resolve_with_firecrawl

        assert resolve_with_firecrawl("ftp://example.com/file") is None

    def test_ssrf_blocked_private_network(self):
        from scripts.providers.firecrawl import resolve_with_firecrawl

        assert resolve_with_firecrawl("http://10.0.0.1/internal") is None


class TestFirecrawlAsync:
    """Async Firecrawl provider tests using SDK mocking."""

    @patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test-fc-key"})
    @patch("firecrawl.Firecrawl")
    @pytest.mark.asyncio
    async def test_successful_resolution(self, mock_fc_cls):
        from scripts.providers.firecrawl import resolve_with_firecrawl_async

        mock_app = Mock()
        mock_app.scrape.return_value = FIRECRAWL_SDK_RESPONSE
        mock_fc_cls.return_value = mock_app

        result = await resolve_with_firecrawl_async(SAFE_URL)
        assert result is not None
        assert result.source == "firecrawl"

    @pytest.mark.asyncio
    async def test_ssrf_blocked(self):
        from scripts.providers.firecrawl import resolve_with_firecrawl_async

        result = await resolve_with_firecrawl_async("http://169.254.169.254/metadata")
        assert result is None


# ---------------------------------------------------------------------------
# Rate Limit Unit Tests
# ---------------------------------------------------------------------------


class TestRateLimiting:
    """Tests for the rate limiting mechanism itself."""

    def test_rate_limit_set_and_check(self):
        from scripts.providers import _clear_rate_limits, _is_rate_limited, _set_rate_limit

        _clear_rate_limits()
        assert not _is_rate_limited("test_provider")

        _set_rate_limit("test_provider", cooldown=60)
        assert _is_rate_limited("test_provider")

        _clear_rate_limits()
        assert not _is_rate_limited("test_provider")

    def test_rate_limit_per_provider(self):
        from scripts.providers import _clear_rate_limits, _is_rate_limited, _set_rate_limit

        _clear_rate_limits()
        _set_rate_limit("provider_a")
        assert _is_rate_limited("provider_a")
        assert not _is_rate_limited("provider_b")
        _clear_rate_limits()

    def test_is_rate_limited_alias(self):
        from scripts.providers import _clear_rate_limits, _set_rate_limit, is_rate_limited

        _clear_rate_limits()
        assert not is_rate_limited("test_provider")
        _set_rate_limit("test_provider")
        assert is_rate_limited("test_provider")
        _clear_rate_limits()
