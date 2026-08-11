"""do-web-doc-resolver: Resolve URLs and queries into LLM-ready markdown."""

from scripts.resolve import resolve, resolve_url, resolve_query

__version__ = "0.1.0"
__all__ = ["resolve", "resolve_url", "resolve_query"]
