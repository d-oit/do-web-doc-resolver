"""
Scrim provider: optional local JavaScript-rendering backend.

Scrim (https://github.com/strelov1/scrim) is a minimal MIT-licensed headless
browser (no layout, no paint) that executes page JavaScript and extracts
text/markdown. This adapter keeps it strictly opt-in:

- Disabled unless DO_WDR_SCRIM_ENABLED=1.
- Not part of any default cascade; routing must only include "scrim" after a
  documented benchmark decision (see agents-docs/SCRIM_EVALUATION.md).
- The binary is located via SCRIM_BIN or PATH; when missing, the provider
  returns a structured skipped result (None + logged reason), never raises.
- All arguments are passed as an argv array (no shell interpolation), with a
  strict timeout and output-size cap.
- The URL is SSRF-checked (is_safe_url) before invocation; Scrim's own
  subresource fetches are NOT covered by that check, which is one reason the
  provider stays disabled by default (see evaluation doc, security section).
"""

import asyncio
import logging
import os
import shutil
import subprocess
from functools import lru_cache

from scripts.constants import MAX_CHARS, MIN_CHARS
from scripts.models import ResolvedResult
from scripts.utils import _get_from_cache, _save_to_cache, is_safe_url

logger = logging.getLogger(__name__)

SCRIM_TIMEOUT_SECONDS = int(os.getenv("SCRIM_TIMEOUT", "30"))
SCRIM_MAX_OUTPUT_BYTES = int(os.getenv("SCRIM_MAX_OUTPUT_BYTES", str(5 * 1024 * 1024)))


def scrim_enabled() -> bool:
    """Scrim is opt-in: the adapter is inert unless explicitly enabled."""
    return os.getenv("DO_WDR_SCRIM_ENABLED", "0") == "1"


@lru_cache(maxsize=1)
def _scrim_binary() -> str | None:
    candidate = os.getenv("SCRIM_BIN")
    if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
        return candidate
    return shutil.which("scrim")


@lru_cache(maxsize=1)
def scrim_version() -> str | None:
    """Reported Scrim version, or None when the binary is missing/unusable."""
    binary = _scrim_binary()
    if not binary:
        return None
    try:
        result = subprocess.run(
            [binary, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as e:
        logger.warning("Scrim version probe failed: %s: %s", type(e).__name__, e)
        return None
    version = (result.stdout or "").strip()
    return version or None


class ScrimNotInstalled(RuntimeError):
    """Raised internally when the Scrim binary is unavailable."""


def _run_scrim(url: str) -> str:
    binary = _scrim_binary()
    if not binary:
        raise ScrimNotInstalled("scrim binary not found (set SCRIM_BIN or install scrim)")

    argv = [binary, "fetch", url, "--dump", "markdown"]
    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            timeout=SCRIM_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"scrim timed out after {SCRIM_TIMEOUT_SECONDS}s") from e

    if result.returncode != 0:
        stderr = (result.stderr or b"").decode("utf-8", "replace")[:500]
        raise RuntimeError(f"scrim exited {result.returncode}: {stderr}")

    if len(result.stdout) > SCRIM_MAX_OUTPUT_BYTES:
        raise RuntimeError(f"scrim output exceeds size limit ({SCRIM_MAX_OUTPUT_BYTES} bytes)")

    return result.stdout.decode("utf-8", "replace")


def resolve_with_scrim(url: str, max_chars: int = MAX_CHARS) -> ResolvedResult | None:
    """Resolve a URL through a local Scrim render (opt-in)."""
    if not scrim_enabled():
        logger.debug("Scrim disabled (set DO_WDR_SCRIM_ENABLED=1 to opt in)")
        return None

    if not is_safe_url(url):
        logger.warning("SSRF blocked: %s", url)
        return None

    cached = _get_from_cache(url, "scrim")
    if cached:
        return ResolvedResult(**cached)

    import time

    start = time.monotonic()
    try:
        output = _run_scrim(url)
    except ScrimNotInstalled as e:
        logger.warning("Scrim skipped: not_installed (%s)", e)
        return None
    except (OSError, RuntimeError, subprocess.SubprocessError) as e:
        logger.warning("Scrim resolution failed: %s: %s", type(e).__name__, e)
        return None
    elapsed_ms = int((time.monotonic() - start) * 1000)

    content = output.strip()
    if len(content) < MIN_CHARS:
        logger.warning("Scrim returned insufficient content (%s chars) for %s", len(content), url)
        return None

    result = ResolvedResult(
        source="scrim",
        content=content[:max_chars],
        url=url,
        metadata={
            "scrim_version": scrim_version(),
            "elapsed_ms": elapsed_ms,
            "renderer": "scrim-local",
        },
    )
    _save_to_cache(url, "scrim", result.to_dict())
    return result


async def resolve_with_scrim_async(url: str, max_chars: int = MAX_CHARS) -> ResolvedResult | None:
    """Async wrapper running the Scrim subprocess off the event loop."""
    from scripts.utils.thread_pool import get_shared_pool

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(get_shared_pool(), resolve_with_scrim, url, max_chars)
