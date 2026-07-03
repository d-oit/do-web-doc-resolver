"""Tests for content cleaning utilities."""

from scripts.utils.content_clean import _strip_html_tags, clean_content

NAV_HEAVY_HTML = """
<html><head><title>Docs</title></head><body>
<nav>Home About Contact</nav>
<header>Logo Brand</header>
<main>
  <h1>API Reference</h1>
  <p>The <code>resolve_url</code> function accepts a URL and returns resolved content.</p>
  <p>It supports multiple providers including jina, firecrawl, and direct fetch.</p>
</main>
<footer>Cookie Policy Privacy Terms</footer>
</body></html>
"""


class TestCleanContent:
    def test_removes_nav_and_footer(self):
        result = clean_content(NAV_HEAVY_HTML, url="https://example.com/docs")
        assert "API Reference" in result
        assert "Cookie Policy" not in result

    def test_respects_max_chars(self):
        result = clean_content(NAV_HEAVY_HTML, max_chars=50)
        assert len(result) <= 50

    def test_returns_string_on_empty_input(self):
        result = clean_content("", url="")
        assert isinstance(result, str)
        assert result == ""

    def test_returns_string_on_whitespace_input(self):
        result = clean_content("   ", url="")
        assert isinstance(result, str)
        assert result == ""

    def test_preserves_main_content(self):
        html = """
        <html><body>
        <nav>Sidebar</nav>
        <article>
            <h1>Getting Started</h1>
            <p>Install the package with pip install mypackage.</p>
            <p>Then import it in your code.</p>
        </article>
        <aside>Ads</aside>
        </body></html>
        """
        result = clean_content(html, url="https://example.com/guide")
        assert "Getting Started" in result
        assert "pip install" in result


class TestStripHtmlTags:
    def test_strips_simple_tags(self):
        html = "<p>Hello <b>world</b></p>"
        result = _strip_html_tags(html)
        assert result == "Hello world"
        assert "<" not in result

    def test_strips_nested_tags(self):
        html = "<div><span>foo</span> <em>bar</em></div>"
        result = _strip_html_tags(html)
        assert "foo" in result
        assert "bar" in result
        assert "<" not in result

    def test_handles_empty_string(self):
        result = _strip_html_tags("")
        assert result == ""
