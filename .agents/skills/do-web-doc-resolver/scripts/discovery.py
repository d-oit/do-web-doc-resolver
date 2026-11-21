"""Bounded alternative-source discovery for failed or low-quality URLs.

Discovery generates candidates from independent strategy families, keeps
provenance, validates redirects before extraction, deduplicates by canonical
URL, and ranks canonical publisher sources above unofficial mirrors.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from collections.abc import Callable
from typing import Any
from urllib.parse import urljoin, urlparse

from scripts.discovery_models import (
    DISCOVERY_SCHEMA_VERSION,
    DiscoveryCandidate,
    DiscoveryInput,
    DiscoveryReport,
)
from scripts.utils.urls import normalize_url

logger = logging.getLogger(__name__)

DEFAULT_MAX_CANDIDATES = 8
DEFAULT_MAX_FETCHES = 2
DEFAULT_BUDGET_MS = 6000

RELATIONSHIP_TIER = {
    "canonical": 4,
    "same-publisher": 3,
    "official-repository": 2,
    "unofficial": 1,
}

_LINK_RE = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
_CANONICAL_RE = re.compile(
    r"""<link[^>]+rel\s*=\s*["'][^"']*canonical[^"']*["'][^>]+href\s*=\s*["']([^"']+)["']""",
    re.IGNORECASE,
)
_ALTERNATE_RE = re.compile(
    r"""<link[^>]+rel\s*=\s*["'][^"']*alternate[^"']*["'][^>]+href\s*=\s*["']([^"']+)["']""",
    re.IGNORECASE,
)
_OG_URL_RE = re.compile(
    r"""<meta[^>]+property\s*=\s*["']og:url["'][^>]+content\s*=\s*["']([^"']+)["']""",
    re.IGNORECASE,
)
_MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\((https?://[^)\s]+)")
_REGISTRY_RE = re.compile(
    r"https?://(?:www\.)?(?:github\.com|gitlab\.com|crates\.io|pypi\.org|npmjs\.com)/[^\s\"'<>]+",
    re.IGNORECASE,
)
_VERSION_SEGMENT_RE = re.compile(r"^(?:v)?\d+(?:\.\d+)+(?:\.\d+)?$", re.IGNORECASE)
_VERSION_WORDS = frozenset({"latest", "stable", "current", "next", "v2", "v3"})
_SEARCH_STOPWORDS = frozenset(
    {"the", "and", "for", "with", "from", "docs", "documentation", "guide", "reference", "api"}
)

Validator = Callable[[str], Any]


def _domain(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""


def _same_publisher(left: str, right: str) -> bool:
    a, b = _domain(left), _domain(right)
    if not a or not b:
        return False
    return a == b or a.endswith(f".{b}") or b.endswith(f".{a}")


def _canonical(url: str) -> str:
    try:
        return normalize_url(urljoin("https://placeholder.invalid/", url))
    except ValueError:
        return url


def _absolute(base: str, url: str) -> str:
    return urljoin(base, url.strip())


def _relationship(url: str, primary_url: str, final_url: str | None) -> str:
    if _canonical(url) == _canonical(primary_url):
        return "canonical"
    if final_url and _canonical(url) == _canonical(final_url):
        return "canonical"
    if _same_publisher(url, primary_url) or (final_url and _same_publisher(url, final_url)):
        return "same-publisher"
    host = _domain(url)
    if host in {"github.com", "gitlab.com"} or host.endswith(".github.com"):
        return "official-repository"
    if host in {"crates.io", "pypi.org", "npmjs.com"}:
        return "official-repository"
    return "unofficial"


def _candidate(
    inp: DiscoveryInput,
    url: str,
    *,
    strategy: str,
    family: str,
    discovery_provider: str,
    reason: str,
    title: str | None = None,
    content_hash: str | None = None,
) -> DiscoveryCandidate | None:
    if not url or url.startswith(("javascript:", "data:", "mailto:")):
        return None
    absolute = _absolute(inp.primary_url, url)
    parsed = urlparse(absolute)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return None
    canonical = _canonical(absolute)
    return DiscoveryCandidate(
        url=absolute,
        canonical_url=canonical,
        strategy=strategy,
        family=family,
        discovery_provider=discovery_provider,
        original_url=inp.primary_url,
        publisher_domain=_domain(absolute),
        relationship=_relationship(absolute, inp.primary_url, inp.final_url),
        reason=reason,
        title=title,
        content_hash=content_hash,
    )


def _publisher_metadata(inp: DiscoveryInput) -> list[DiscoveryCandidate]:
    candidates: list[DiscoveryCandidate] = []
    html = inp.html or ""
    for regex, reason in (
        (_CANONICAL_RE, "canonical link"),
        (_ALTERNATE_RE, "alternate link"),
        (_OG_URL_RE, "og:url"),
    ):
        for match in regex.findall(html):
            candidate = _candidate(
                inp,
                match,
                strategy="publisher_metadata",
                family="publisher_metadata",
                discovery_provider="page-html",
                reason=reason,
            )
            if candidate:
                candidates.append(candidate)
    for match in _LINK_RE.findall(html):
        lowered = match.lower()
        if lowered.endswith(("llms.txt", "sitemap.xml", "feed.xml", "atom.xml", "rss.xml")):
            candidate = _candidate(
                inp,
                match,
                strategy="publisher_metadata",
                family="publisher_metadata",
                discovery_provider="page-html",
                reason="publisher metadata link",
            )
            if candidate:
                candidates.append(candidate)
    for match in _MARKDOWN_LINK_RE.findall(inp.llms_txt or ""):
        candidate = _candidate(
            inp,
            match,
            strategy="publisher_metadata",
            family="publisher_metadata",
            discovery_provider="llms.txt",
            reason="llms.txt link",
        )
        if candidate:
            candidates.append(candidate)
    return candidates


def _official_repository(inp: DiscoveryInput) -> list[DiscoveryCandidate]:
    candidates: list[DiscoveryCandidate] = []
    text = f"{inp.html or ''}\n{inp.llms_txt or ''}"
    for match in _REGISTRY_RE.findall(text):
        candidate = _candidate(
            inp,
            match.rstrip(".,);"),
            strategy="official_repository",
            family="official_repository",
            discovery_provider="page-html",
            reason="official repository or registry link",
        )
        if candidate:
            candidate.relationship = "official-repository"
            candidates.append(candidate)
    return candidates


def _versioned_docs(inp: DiscoveryInput) -> list[DiscoveryCandidate]:
    candidates: list[DiscoveryCandidate] = []
    source = inp.final_url or inp.primary_url
    parsed = urlparse(source)
    segments = [segment for segment in parsed.path.split("/") if segment]
    for index, segment in enumerate(segments):
        if not (_VERSION_SEGMENT_RE.match(segment) or segment.lower() in _VERSION_WORDS):
            continue
        for replacement, freshness in (("stable", 1.0), ("latest", 0.98), (None, 0.6)):
            replaced = list(segments)
            if replacement is None:
                replaced.pop(index)
            else:
                replaced[index] = replacement
            path = "/" + "/".join(replaced)
            candidate = _candidate(
                inp,
                path,
                strategy="versioned_docs",
                family="versioned_docs",
                discovery_provider="url-path",
                reason=f"versioned documentation variant ({replacement or 'unversioned'})",
            )
            if candidate:
                candidate.scores["freshness"] = freshness
                if replacement in ("stable", "latest"):
                    candidate.relationship = "canonical"
                candidates.append(candidate)
    if inp.final_url and _canonical(inp.final_url) != _canonical(inp.primary_url):
        candidate = _candidate(
            inp,
            inp.final_url,
            strategy="versioned_docs",
            family="versioned_docs",
            discovery_provider="redirect",
            reason="redirect final URL",
        )
        if candidate:
            candidate.relationship = "canonical"
            candidate.redirect_chain = list(inp.redirect_chain)
            candidate.scores["freshness"] = 0.9
            candidates.append(candidate)
    return candidates


def _search_provider(inp: DiscoveryInput) -> list[DiscoveryCandidate]:
    candidates: list[DiscoveryCandidate] = []
    for result in inp.search_results:
        url = result.get("url") or result.get("href")
        if not url:
            continue
        candidate = _candidate(
            inp,
            str(url),
            strategy="search_provider",
            family="search_provider",
            discovery_provider=str(result.get("provider", "search")),
            reason="normalized product/version/error query",
            title=result.get("title"),
        )
        if candidate:
            candidates.append(candidate)
    return candidates


_STRATEGIES = (
    ("publisher_metadata", "publisher_metadata", _publisher_metadata),
    ("official_repository", "official_repository", _official_repository),
    ("versioned_docs", "versioned_docs", _versioned_docs),
    ("search_provider", "search_provider", _search_provider),
)


def _registry_rank(url: str) -> int:
    """Prefer source repositories over package registries when scores tie."""
    host = _domain(url)
    if host in {"github.com", "gitlab.com"} or host.endswith(".github.com"):
        return 2
    if host in {"crates.io", "pypi.org", "npmjs.com"}:
        return 1
    return 0


def _query_terms(query: str | None) -> set[str]:
    if not query:
        return set()
    return {
        token
        for token in re.findall(r"[a-z0-9]{3,}", query.lower())
        if token not in _SEARCH_STOPWORDS
    }


def _score_candidate(
    candidate: DiscoveryCandidate, terms: set[str], inp: DiscoveryInput
) -> dict[str, float]:
    haystack = f"{candidate.url} {candidate.title or ''}".lower()
    relevance = sum(1 for term in terms if term in haystack) / len(terms) if terms else 0.5
    authority = {
        "canonical": 1.0,
        "same-publisher": 0.85,
        "official-repository": 0.75,
        "unofficial": 0.25,
    }[candidate.relationship]
    structural = {
        "llms.txt": 1.0,
        "redirect": 0.9,
        "page-html": 0.75,
        "url-path": 0.65,
        "search": 0.45,
    }.get(candidate.discovery_provider, 0.5)
    freshness = candidate.scores.get("freshness", 0.7)
    if "freshness" not in candidate.scores:
        segments = [segment for segment in urlparse(candidate.url).path.split("/") if segment]
        if any(_VERSION_SEGMENT_RE.match(segment) for segment in segments):
            freshness = 0.3
    extraction = candidate.scores.get("extraction_quality", 0.5)
    overall = (
        0.35 * authority
        + 0.25 * relevance
        + 0.15 * freshness
        + 0.15 * structural
        + 0.10 * extraction
    )
    return {
        "relevance": round(relevance, 4),
        "freshness": round(freshness, 4),
        "structural_completeness": round(structural, 4),
        "authority": round(authority, 4),
        "extraction_quality": round(extraction, 4),
        "overall": round(overall, 4),
    }


def _verify(candidate: DiscoveryCandidate, validator: Validator | None) -> None:
    if validator is None:
        return
    try:
        result = validator(candidate.url)
    except Exception as error:  # noqa: BLE001 - validation must never crash discovery
        candidate.verification_state = "rejected"
        candidate.reason = f"{candidate.reason}; validation error: {error}"
        return
    if isinstance(result, dict):
        valid = bool(result.get("is_valid", False))
        final_url = result.get("final_url")
        chain = result.get("redirect_chain", [])
    else:
        valid = bool(getattr(result, "is_valid", False))
        final_url = getattr(result, "final_url", None)
        chain = getattr(result, "redirect_chain", [])
    if not valid:
        candidate.verification_state = "rejected"
        candidate.reason = f"{candidate.reason}; URL validation failed"
        return
    candidate.verification_state = "verified"
    if final_url:
        candidate.canonical_url = _canonical(str(final_url))
        candidate.publisher_domain = _domain(str(final_url))
        derived = _relationship(str(final_url), candidate.original_url, None)
        if RELATIONSHIP_TIER[derived] > RELATIONSHIP_TIER[candidate.relationship]:
            candidate.relationship = derived
    candidate.redirect_chain = [str(item) for item in (chain or [])]


def discover_alternatives(
    inp: DiscoveryInput,
    *,
    validator: Validator | None = None,
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
) -> DiscoveryReport:
    """Generate, verify, deduplicate, and rank alternatives from all strategies."""
    generated: list[DiscoveryCandidate] = []
    strategy_report: list[dict[str, Any]] = []
    for name, family, strategy in _STRATEGIES:
        produced = strategy(inp)
        generated.extend(produced)
        strategy_report.append(
            {
                "name": name,
                "family": family,
                "candidate_count": len(produced),
                "observable": True,
            }
        )

    terms = _query_terms(inp.query)
    deduplicated: dict[str, DiscoveryCandidate] = {}
    duplicate_count = 0
    for candidate in generated:
        key = candidate.canonical_url
        existing = deduplicated.get(key)
        if existing is not None:
            duplicate_count += 1
            if RELATIONSHIP_TIER[candidate.relationship] > RELATIONSHIP_TIER[existing.relationship]:
                deduplicated[key] = candidate
            continue
        deduplicated[key] = candidate

    accepted: list[DiscoveryCandidate] = []
    rejected: list[DiscoveryCandidate] = []
    seen_content: set[str] = set()
    for candidate in deduplicated.values():
        if candidate.content_hash and candidate.content_hash in seen_content:
            duplicate_count += 1
            continue
        if candidate.content_hash:
            seen_content.add(candidate.content_hash)
        _verify(candidate, validator)
        candidate.scores.update(_score_candidate(candidate, terms, inp))
        if candidate.verification_state == "rejected":
            rejected.append(candidate)
        else:
            accepted.append(candidate)

    # Relationship tier comes first: an unverified canonical publisher must not
    # be silently outranked by a verified unofficial mirror.
    accepted.sort(
        key=lambda candidate: (
            RELATIONSHIP_TIER[candidate.relationship],
            candidate.verification_state == "verified",
            candidate.scores["overall"],
            _registry_rank(candidate.url),
        ),
        reverse=True,
    )
    accepted = accepted[:max_candidates]
    selected = next(
        (
            candidate
            for candidate in accepted
            if candidate.verification_state == "verified" and candidate.relationship != "unofficial"
        ),
        None,
    )
    return DiscoveryReport(
        primary_url=inp.primary_url,
        candidates=accepted,
        rejected=rejected,
        strategies=strategy_report,
        duplicate_count=duplicate_count,
        selected=selected,
    )


def content_identity(text: str) -> str:
    """Stable content hash used to deduplicate identical extracted pages."""
    return hashlib.sha256((text or "").strip().encode("utf-8")).hexdigest()


def discovery_enabled() -> bool:
    return os.getenv("DO_WDR_DISCOVERY", "1") != "0"


def should_discover(result: dict[str, Any], threshold: float = 0.65) -> bool:
    """Only failed or low-quality primaries pay for alternative discovery."""
    if not discovery_enabled():
        return False
    if result.get("semantic_cache_hit") or result.get("discovery"):
        return False
    return result.get("source") == "none" or float(result.get("score") or 0.0) < threshold


__all__ = [
    "DEFAULT_BUDGET_MS",
    "DEFAULT_MAX_CANDIDATES",
    "DEFAULT_MAX_FETCHES",
    "DISCOVERY_SCHEMA_VERSION",
    "DiscoveryCandidate",
    "DiscoveryInput",
    "DiscoveryReport",
    "content_identity",
    "discover_alternatives",
    "discovery_enabled",
    "should_discover",
]
