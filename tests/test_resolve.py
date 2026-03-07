"""Basic tests for resolve.py"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.resolve import is_url, resolve_url, resolve_query


def test_is_url():
    """Test URL detection."""
    assert is_url("https://example.com") == True
    assert is_url("http://example.com/path") == True
    assert is_url("not a url") == False
    assert is_url("just some text") == False


def test_resolve_url():
    """Test URL resolution returns expected structure."""
    result = resolve_url("https://example.com")
    assert "url" in result
    assert "content_markdown" in result
    assert "source" in result
    assert "score" in result
    assert result["url"] == "https://example.com"


def test_resolve_query():
    """Test query resolution returns expected structure."""
    results = resolve_query("test query")
    assert isinstance(results, list)
    assert len(results) > 0
    assert "url" in results[0]
    assert "content_markdown" in results[0]
    assert "source" in results[0]
    assert "score" in results[0]
