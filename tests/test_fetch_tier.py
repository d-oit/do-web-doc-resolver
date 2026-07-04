# tests/test_fetch_tier.py

from scripts.constants import PROVIDER_TIERS
from scripts.models import FetchTier


def test_fetch_tier_values_are_ascending():
    assert FetchTier.FREE_STATIC.value < FetchTier.FREE_DIRECT.value
    assert FetchTier.FREE_DIRECT.value < FetchTier.FREE_SEARCH.value
    assert FetchTier.FREE_SEARCH.value < FetchTier.PAID_LITE.value
    assert FetchTier.PAID_LITE.value < FetchTier.PAID_BROWSER.value


def test_provider_tiers_cover_cascade_providers():
    cascade_providers = [
        "llms_txt",
        "jina",
        "firecrawl",
        "direct_fetch",
        "mistral_browser",
        "duckduckgo",
    ]
    for p in cascade_providers:
        assert p in PROVIDER_TIERS, f"{p} missing from PROVIDER_TIERS"


def test_free_tiers_are_cheaper_than_paid():
    assert PROVIDER_TIERS["llms_txt"] < PROVIDER_TIERS["jina"]
    assert PROVIDER_TIERS["direct_fetch"] < PROVIDER_TIERS["mistral_browser"]


def test_sort_eligible_by_tier():
    eligible = ["mistral_browser", "jina", "direct_fetch", "llms_txt"]
    sorted_eligible = sorted(
        eligible, key=lambda p: int(PROVIDER_TIERS.get(p, FetchTier.PAID_BROWSER))
    )
    assert sorted_eligible[0] == "llms_txt"
    assert sorted_eligible[1] == "direct_fetch"
    assert sorted_eligible[-1] == "mistral_browser"


def test_stealth_tier_position():
    assert PROVIDER_TIERS["stealth"] > PROVIDER_TIERS["firecrawl"]
    assert PROVIDER_TIERS["stealth"] < PROVIDER_TIERS["mistral_browser"]


def test_all_cascade_providers_have_tiers():
    sync_providers = [
        "llms_txt",
        "jina",
        "firecrawl",
        "direct_fetch",
        "mistral_browser",
        "visual_clip",
        "duckduckgo",
        "stealth",
    ]
    for p in sync_providers:
        assert p in PROVIDER_TIERS, f"Provider {p} missing from PROVIDER_TIERS"
