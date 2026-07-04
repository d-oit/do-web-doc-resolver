# tests/test_fetch_tier.py

from scripts.constants import PROVIDER_TIERS
from scripts.models import FetchTier


def test_free_providers_have_lower_tier_than_paid():
    assert PROVIDER_TIERS["direct_fetch"] < PROVIDER_TIERS["jina"]
    assert PROVIDER_TIERS["llms_txt"] < PROVIDER_TIERS["mistral_browser"]
    assert PROVIDER_TIERS["direct_fetch"] < PROVIDER_TIERS["mistral_browser"]

def test_sort_eligible_by_tier():
    eligible = ["mistral_browser", "jina", "direct_fetch", "llms_txt"]
    sorted_eligible = sorted(eligible, key=lambda p: PROVIDER_TIERS.get(p, FetchTier.PAID_BROWSER).value)
    assert sorted_eligible[0] == "llms_txt"
    assert sorted_eligible[1] == "direct_fetch"
    assert sorted_eligible[-1] == "mistral_browser"

def test_stealth_tier_position():
    assert PROVIDER_TIERS["stealth"] > PROVIDER_TIERS["firecrawl"]
    assert PROVIDER_TIERS["stealth"] < PROVIDER_TIERS["mistral_browser"]

def test_all_cascade_providers_have_tiers():
    # Sync cascade providers
    sync_providers = ["llms_txt", "jina", "firecrawl", "direct_fetch", "mistral_browser", "visual_clip", "duckduckgo", "stealth"]
    for p in sync_providers:
        assert p in PROVIDER_TIERS, f"Provider {p} missing from PROVIDER_TIERS"
