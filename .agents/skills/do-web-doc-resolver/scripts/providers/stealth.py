"""Stealth fetch provider — placeholder for anti-bot escalation tier.

TODO: Implement using playwright-stealth or curl-impersonate.
Returns ``None`` so the cascade skips it cleanly. Returning an empty
``ResolvedResult`` here would be truthy: the cascade would score it 0.0 and
write a negative-cache "thin_content" entry that suppresses the STEALTH tier
slot for the whole TTL.
"""

import logging

from scripts.models import ResolvedResult

logger = logging.getLogger(__name__)


def resolve_with_stealth(url: str, max_chars: int) -> ResolvedResult | None:
    """Stealth browser fetch (anti-bot bypass).

    Returns ``None`` until a concrete implementation is chosen; the cascade
    treats ``None`` as a provider miss and moves on to the next tier.
    """
    logger.debug(
        "Stealth provider not yet implemented — skipping %s "
        "(candidates: playwright-stealth, curl-impersonate, camoufox)",
        url,
    )
    return None
