"""Live, bounded discovery fallback (kept separate from the pure core)."""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

from scripts.discovery import (
    DEFAULT_BUDGET_MS,
    DEFAULT_MAX_FETCHES,
    DiscoveryInput,
    content_identity,
    discover_alternatives,
    discovery_enabled,
)

logger = logging.getLogger(__name__)

Fetch = Callable[[str], str | None]
Search = Callable[[str], list[dict[str, Any]]]
Validator = Callable[[str], Any]


def search_urls(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Live search helper; isolated so offline tests never import the network path."""
    try:
        from ddgs import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=limit))
        return [
            {
                "url": result.get("href") or result.get("url"),
                "title": result.get("title"),
                "snippet": result.get("body"),
                "provider": "duckduckgo",
            }
            for result in results
            if result.get("href") or result.get("url")
        ]
    except Exception as error:  # noqa: BLE001 - search is optional discovery input
        logger.debug("Discovery search failed: %s", error)
        return []


def fallback_result(
    primary_url: str,
    *,
    query: str | None = None,
    max_chars: int = 8000,
    fetch: Fetch | None = None,
    search: Search | None = None,
    validator: Validator | None = None,
    extract: Callable[[str], Any] | None = None,
    max_fetches: int = DEFAULT_MAX_FETCHES,
    budget_ms: int = DEFAULT_BUDGET_MS,
) -> dict[str, Any] | None:
    """Live bounded discovery fallback. Returns a resolved result dict or None."""
    if not discovery_enabled():
        return None
    if fetch is None or validator is None:
        from scripts.utils import _safe_request, get_session, validate_url

        def _default_fetch(url: str) -> str | None:
            try:
                response = _safe_request("GET", url, session=get_session(), timeout=4)
                if response.status_code >= 400:
                    return None
                return response.text[:262144]
            except Exception as error:  # noqa: BLE001 - discovery is best-effort
                logger.debug("Discovery fetch failed for %s: %s", url, error)
                return None

        fetch = fetch or _default_fetch
        validator = validator or validate_url
    if search is None and os.getenv("DO_WDR_DISCOVERY_SEARCH", "1") != "0":
        search = search_urls

    start = time.monotonic()
    html = fetch(primary_url) or ""
    llms_txt = None
    parsed = urlparse(primary_url)
    if parsed.scheme and parsed.netloc:
        llms_txt = fetch(f"{parsed.scheme}://{parsed.netloc}/llms.txt")
    search_results = (search(query or primary_url) if search else None) or []
    report = discover_alternatives(
        DiscoveryInput(
            primary_url=primary_url,
            html=html,
            llms_txt=llms_txt,
            search_results=search_results,
            query=query,
        ),
        validator=validator,
    )

    from scripts.quality import score_content
    from scripts.utils import fetch_url_content

    if extract is None:
        extract = lambda candidate_url: fetch_url_content(  # noqa: E731
            candidate_url, max_chars=max_chars
        )
    best: tuple[float, dict[str, Any]] | None = None
    seen_content: set[str] = set()
    for candidate in [item for item in report.candidates if item.verification_state == "verified"][
        :max_fetches
    ]:
        if (time.monotonic() - start) * 1000 >= budget_ms:
            break
        resolved = extract(candidate.canonical_url)
        if resolved is None:
            continue
        identity = content_identity(resolved.content)
        if identity in seen_content:
            continue
        seen_content.add(identity)
        quality = score_content(resolved.content, query=query)
        if best is None or quality.score > best[0]:
            payload = resolved.to_dict()
            payload["source"] = f"discovery:{candidate.strategy}"
            payload["score"] = quality.score
            payload["discovery"] = report.to_dict()
            payload["discovered_from"] = primary_url
            best = (quality.score, payload)
    return best[1] if best else None


__all__ = ["Fetch", "Search", "Validator", "fallback_result", "search_urls"]
