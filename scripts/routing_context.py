"""Stable, explainable routing context derived from a search query.

The resolver must not store every raw query as a routing-memory key. This
module maps a query to a bounded feature tuple (intent, topic, language,
platform) and serializes it as a versioned key. The same feature rules are
implemented in ``cli/src/routing_context.rs``; shared fixtures keep the two
runtimes aligned.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

CONTEXT_SCHEMA_VERSION = 2

_INTENTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "troubleshooting",
        (
            "error",
            "exception",
            "traceback",
            "crash",
            "broken",
            "debug",
            "troubleshoot",
            "not working",
            "does not work",
            "fix",
            "issue",
        ),
    ),
    (
        "release",
        (
            "release",
            "changelog",
            "change log",
            "version",
            "upgrade",
            "migration",
            "deprecated",
            "breaking",
            "whats new",
            "what's new",
        ),
    ),
    (
        "package",
        (
            "install",
            "installation",
            "package",
            "crate",
            "dependency",
            "sdk",
            "download",
            "cargo add",
            "pip install",
            "npm install",
            "gem",
        ),
    ),
    (
        "api_reference",
        (
            "api",
            "reference",
            "signature",
            "method",
            "function",
            "class",
            "endpoint",
            "struct",
            "trait",
            "parameter",
            "argument",
        ),
    ),
    (
        "comparison",
        ("vs", "versus", "compare", "comparison", "difference", "alternative", "alternatives"),
    ),
    (
        "documentation",
        (
            "docs",
            "documentation",
            "guide",
            "tutorial",
            "how to",
            "example",
            "usage",
            "learn",
            "quickstart",
            "manual",
        ),
    ),
)

# First matching alias in query order wins; this bounds cardinality instead of
# storing the raw query.
_TOPIC_ALIASES: dict[str, str] = {
    "rust": "rust",
    "cargo": "rust",
    "crates": "rust",
    "crates.io": "rust",
    "docs.rs": "rust",
    "tokio": "rust",
    "serde": "rust",
    "axum": "rust",
    "python": "python",
    "pip": "python",
    "pypi": "python",
    "django": "django",
    "flask": "flask",
    "fastapi": "fastapi",
    "pandas": "pandas",
    "numpy": "numpy",
    "node": "nodejs",
    "nodejs": "nodejs",
    "npm": "nodejs",
    "express": "nodejs",
    "typescript": "typescript",
    "javascript": "javascript",
    "deno": "deno",
    "bun": "bun",
    "react": "react",
    "reactjs": "react",
    "next.js": "nextjs",
    "nextjs": "nextjs",
    "vue": "vue",
    "angular": "angular",
    "svelte": "svelte",
    "go": "go",
    "golang": "go",
    "java": "java",
    "spring": "spring",
    "kotlin": "kotlin",
    "dotnet": "dotnet",
    "csharp": "dotnet",
    "c#": "dotnet",
    "php": "php",
    "ruby": "ruby",
    "rails": "rails",
    "swift": "swift",
    "android": "android",
    "ios": "ios",
    "kubernetes": "kubernetes",
    "k8s": "kubernetes",
    "docker": "docker",
    "terraform": "terraform",
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "mysql": "mysql",
    "sqlite": "sqlite",
    "redis": "redis",
    "mongodb": "mongodb",
    "aws": "aws",
    "amazon": "aws",
    "azure": "azure",
    "gcp": "gcp",
    "linux": "linux",
    "git": "git",
    "github": "github",
    "graphql": "graphql",
    "grpc": "grpc",
    "openai": "llm",
    "anthropic": "llm",
    "langchain": "llm",
    "llm": "llm",
}

_LANGUAGE_BY_TOPIC: dict[str, str] = {
    "rust": "rust",
    "python": "python",
    "django": "python",
    "flask": "python",
    "fastapi": "python",
    "pandas": "python",
    "numpy": "python",
    "nodejs": "javascript",
    "javascript": "javascript",
    "deno": "javascript",
    "bun": "javascript",
    "typescript": "typescript",
    "react": "typescript",
    "nextjs": "typescript",
    "vue": "typescript",
    "angular": "typescript",
    "svelte": "typescript",
    "go": "go",
    "java": "java",
    "spring": "java",
    "kotlin": "kotlin",
    "dotnet": "csharp",
    "php": "php",
    "ruby": "ruby",
    "rails": "ruby",
    "swift": "swift",
    "android": "kotlin",
    "ios": "swift",
}

_PLATFORM_HINTS: tuple[tuple[str, str], ...] = (
    ("stack overflow", "stackoverflow"),
    ("stackoverflow", "stackoverflow"),
    ("github", "github"),
    ("gitlab", "gitlab"),
    ("docs.rs", "docsrs"),
    ("docsrs", "docsrs"),
    ("read the docs", "readthedocs"),
    ("readthedocs", "readthedocs"),
    ("pypi", "pypi"),
    ("pip ", "pypi"),
    ("crates.io", "cratesio"),
    ("cratesio", "cratesio"),
    ("npmjs", "npm"),
    ("npm ", "npm"),
)

_NORMALIZE_RE = re.compile(r"[^a-z0-9+#.]+")
_TOKEN_RE = re.compile(r"[a-z0-9+#.]+")


@dataclass(frozen=True)
class QueryContext:
    """Bounded routing features for one search query."""

    intent: str
    topic: str
    language: str
    platform: str
    schema_version: int = CONTEXT_SCHEMA_VERSION

    def routing_key(self) -> str:
        return (
            f"q:v{self.schema_version}:{self.intent}:{self.topic}:"
            f"{self.language}:{self.platform}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "intent": self.intent,
            "topic": self.topic,
            "language": self.language,
            "platform": self.platform,
            "routing_key": self.routing_key(),
        }


def normalize_query_text(query: str) -> str:
    """Lowercase and collapse separators without dropping ``+``/``#`` tokens."""
    return " ".join(_NORMALIZE_RE.sub(" ", (query or "").lower()).split())


def _tokens(normalized: str) -> list[str]:
    return _TOKEN_RE.findall(normalized)


def classify_intent(query: str) -> str:
    normalized = normalize_query_text(query)
    padded = f" {normalized} "
    for intent, signals in _INTENTS:
        if any(f" {signal} " in padded for signal in signals):
            return intent
    return "general"


def detect_topic(normalized: str) -> str:
    for token in _tokens(normalized):
        topic = _TOPIC_ALIASES.get(token)
        if topic:
            return topic
    return "general"


def detect_platform(normalized: str) -> str:
    padded = f" {normalized} "
    for hint, platform in _PLATFORM_HINTS:
        if hint in padded:
            return platform
    return "none"


def derive_context(query: str) -> QueryContext:
    normalized = normalize_query_text(query)
    intent = classify_intent(normalized)
    topic = detect_topic(normalized)
    language = _LANGUAGE_BY_TOPIC.get(topic, "na")
    platform = detect_platform(normalized)
    return QueryContext(intent=intent, topic=topic, language=language, platform=platform)


def query_routing_key(query: str) -> str:
    """Return the versioned, low-cardinality memory key for a search query."""
    return derive_context(query).routing_key()


def is_query_context_key(key: str) -> bool:
    return key.startswith("q:v")


def routing_key_for(target: str, *, is_url: bool) -> str:
    """URL/domain keys stay flat; only search queries get feature keys."""
    if not is_url:
        return query_routing_key(target)
    from scripts.routing import extract_domain

    return extract_domain(target) or "any"


def error_outcome(error: Exception) -> str:
    """Map an exception to an attempt outcome without conflating transport with content."""
    from scripts.models import ErrorType
    from scripts.utils import _detect_error_type

    return {
        ErrorType.RATE_LIMIT: "rate_limited",
        ErrorType.AUTH_ERROR: "auth_error",
        ErrorType.QUOTA_EXHAUSTED: "rate_limited",
        ErrorType.NETWORK_ERROR: "transport_error",
        ErrorType.NOT_FOUND: "no_result",
        ErrorType.INVALID_URL: "blocked",
        ErrorType.TIMEOUT: "timeout",
        ErrorType.INVALID_RESPONSE: "server_error",
        ErrorType.SSRF_BLOCKED: "blocked",
        ErrorType.CONTENT_TOO_LARGE: "server_error",
        ErrorType.BOT_CHALLENGE: "blocked",
        ErrorType.UNKNOWN: "unknown",
    }.get(_detect_error_type(error), "unknown")


__all__ = [
    "CONTEXT_SCHEMA_VERSION",
    "QueryContext",
    "classify_intent",
    "derive_context",
    "detect_platform",
    "detect_topic",
    "error_outcome",
    "is_query_context_key",
    "normalize_query_text",
    "query_routing_key",
    "routing_key_for",
]
