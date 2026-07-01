"""
Evaluation tests for the VisualResolver skill.
"""

import os
import sys

# Add the parent directory to sys.path to allow imports from visual_resolver
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from visual_resolver import HAS_DEPS, VisualResolver


class TestVisualResolver:
    """Tests for VisualResolver interface and availability."""

    def test_is_available_type(self):
        """is_available() should return a boolean."""
        resolver = VisualResolver()
        assert isinstance(resolver.is_available(), bool)

    def test_is_available_consistent_with_imports(self):
        """is_available() should match the HAS_DEPS constant."""
        resolver = VisualResolver()
        assert resolver.is_available() == HAS_DEPS

    def test_resolve_returns_none_when_unavailable(self):
        """resolve() should return None if dependencies are missing."""
        if not HAS_DEPS:
            resolver = VisualResolver()
            result = resolver.resolve("https://example.com", "test query")
            assert result is None

    def test_resolve_return_type_or_none(self):
        """resolve() should return None (for now) or a ResolvedResult."""
        resolver = VisualResolver()
        result = resolver.resolve("https://example.com", "test query")

        if result is not None:
            # Check for expected attributes if a result is returned
            assert hasattr(result, "source")
            assert hasattr(result, "content")
            assert hasattr(result, "score")
            assert result.source == "visual_clip"

    def test_threshold_initialization(self):
        """VisualResolver should accept a custom threshold."""
        resolver = VisualResolver(threshold=0.5)
        assert resolver.threshold == 0.5
