"""Tests for ReadonlyResolverProtocol."""

from scripts.models import ReadonlyResolverProtocol, ResolvedResult


def test_protocol_docstring_has_contract():
    """Protocol docstring explicitly lists MUST / MUST NOT constraints."""
    assert "MUST" in ReadonlyResolverProtocol.__doc__
    assert "MUST NOT" in ReadonlyResolverProtocol.__doc__


def test_resolved_result_satisfies_protocol():
    """A correctly-typed callable satisfies the protocol at runtime."""

    def mock_resolver(url: str, max_chars: int) -> ResolvedResult | None:
        return ResolvedResult(source="test", content="hello", url=url)

    assert isinstance(mock_resolver, ReadonlyResolverProtocol)


def test_lambda_satisfies_protocol():
    """A lambda with correct signature satisfies the protocol."""

    def resolver(url, max_chars):  # noqa: E731
        return ResolvedResult(source="test", content="ok", url=url)

    assert isinstance(resolver, ReadonlyResolverProtocol)


def test_protocol_in_all():
    """ReadonlyResolverProtocol is exported in __all__."""
    from scripts.models import __all__

    assert "ReadonlyResolverProtocol" in __all__
