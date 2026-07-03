"""
Tests for Visual CLIP provider integration.
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.models import Profile, ProviderType


class TestVisualClipIntegration:
    """Test the integration of visual_clip provider in the cascade."""

    @patch.dict(os.environ, {"MISTRAL_API_KEY": "test_key"})
    @patch("scripts.providers.visual_clip.get_visual_resolver")
    @patch("scripts.routing.plan_provider_order", return_value=["visual_clip"])
    @patch("scripts._url_resolve.get_semantic_cache", return_value=None)
    def test_visual_clip_in_sync_cascade(self, mock_cache, mock_plan, mock_get_resolver):
        """Test that visual_clip is called in the sync cascade when others are skipped."""
        # Setup mock resolver
        mock_resolver = mock_get_resolver.return_value
        mock_resolver.is_available.return_value = True

        from scripts.visual_resolver import ProviderResult

        mock_resolver.resolve.return_value = ProviderResult(
            content="Visual content from the page that is long enough to pass the quality gate and contains enough information to be useful for the user. "
            * 10,
            score=0.9,
            provider="visual_clip",
            metadata={"clip_score": 0.9},
        )

        # Import resolve here to pick up the patch
        from scripts.resolve import resolve_url

        # Execute resolution
        url = "https://example.com/image-heavy"
        query = "find the chart"
        result = resolve_url(url, query=query, profile=Profile.BALANCED)

        # Verify visual_clip was called
        assert result["source"] == "visual_clip"
        assert "Visual content" in result["content"]
        mock_resolver.resolve.assert_called_once_with(url, query)

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test_key"})
    @patch("scripts.providers.visual_clip.get_visual_resolver")
    @patch("scripts.routing.plan_provider_order", return_value=["visual_clip"])
    @patch("scripts._url_resolve_async.get_semantic_cache", return_value=None)
    def test_visual_clip_in_async_cascade(self, mock_cache, mock_plan, mock_get_resolver):
        """Test that visual_clip is called in the async cascade when others are skipped."""
        # Setup mock resolver
        mock_resolver = mock_get_resolver.return_value
        mock_resolver.is_available.return_value = True

        from scripts.visual_resolver import ProviderResult

        # Mock async resolve
        mock_resolver.resolve_async = AsyncMock(
            return_value=ProviderResult(
                content="Async visual content from the page that is long enough to pass the quality gate and contains enough information to be useful for the user. "
                * 10,
                score=0.95,
                provider="visual_clip",
                metadata={"clip_score": 0.95},
            )
        )

        # Import resolve here to pick up the patch
        from scripts.resolve import resolve_url_async

        # Execute resolution
        url = "https://example.com/async-image"
        query = "describe the image"

        result = asyncio.run(resolve_url_async(url, query=query, profile=Profile.BALANCED))

        # Verify visual_clip was called
        assert result["source"] == "visual_clip"
        assert "Async visual content" in result["content"]
        mock_resolver.resolve_async.assert_called_once_with(url, query)

    def test_provider_type_enum(self):
        """Verify VISUAL_CLIP is in ProviderType and correctly configured."""
        assert ProviderType.VISUAL_CLIP.value == "visual_clip"
        assert ProviderType.VISUAL_CLIP.is_paid()
        assert not ProviderType.VISUAL_CLIP.is_fast()

    @patch.dict(os.environ, {}, clear=True)
    @patch("scripts.providers.visual_clip.VisualResolver")
    def test_visual_clip_skipped_without_api_key(self, mock_resolver_class):
        """Test that visual_clip is skipped when no API key is present."""
        from scripts.providers.visual_clip import resolve_with_visual_clip

        result = resolve_with_visual_clip("https://example.com")
        assert result is None
        mock_resolver_class.assert_not_called()

    @patch.dict(os.environ, {"MISTRAL_API_KEY": "test_key"})
    @patch("scripts.providers.visual_clip.get_visual_resolver")
    def test_resolve_direct_visual_clip(self, mock_get_resolver):
        """Test resolve_direct with visual_clip."""
        from scripts.resolve import resolve_direct

        mock_resolver = mock_get_resolver.return_value
        mock_resolver.is_available.return_value = True

        from scripts.visual_resolver import ProviderResult

        mock_resolver.resolve.return_value = ProviderResult(
            content="Direct visual content from the page that is long enough to pass the quality gate.",
            score=0.8,
            provider="visual_clip",
        )

        result = resolve_direct("https://example.com", ProviderType.VISUAL_CLIP)
        assert result["source"] == "visual_clip"
        assert "Direct visual content" in result["content"]
