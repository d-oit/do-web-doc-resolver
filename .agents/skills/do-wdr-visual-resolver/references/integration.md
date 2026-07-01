# Integration Guide: Visual Resolver

To integrate `VisualResolver` into the `do-wdr` cascade, follow these steps:

## 1. Update `scripts/models.py`

Add `VISUAL_CLIP` to the `ProviderType` enum.

```python
class ProviderType(Enum):
    # ... existing ...
    OCR = "ocr"
    VISUAL_CLIP = "visual_clip"  # <-- Add this

    def is_paid(self) -> bool:
        return self in (
            # ...
            ProviderType.MISTRAL_BROWSER,
            ProviderType.VISUAL_CLIP, # <-- Consider it paid due to GPU/Compute costs
        )
```

## 2. Update `scripts/providers_impl.py`

Export the `resolve_with_visual_clip` function.

```python
from .visual_resolver import VisualResolver

_visual_resolver = VisualResolver()

def resolve_with_visual_clip(url: str, query: str, max_chars: int) -> ResolvedResult | None:
    if not _visual_resolver.is_available():
        return None
    return _visual_resolver.resolve(url, query)
```

## 3. Wire into `scripts/_url_resolve.py`

Add `visual_clip` to the cascade map in `resolve_url_stream`.

```python
    cascade_map: dict[str, tuple[ProviderType, Any]] = {
        # ...
        "mistral_browser": (
            ProviderType.MISTRAL_BROWSER,
            lambda: resolve_with_mistral_browser(url, max_chars),
        ),
        "visual_clip": (
            ProviderType.VISUAL_CLIP,
            lambda: resolve_with_visual_clip(url, query, max_chars),
        ),
        "duckduckgo": (ProviderType.DUCKDUCKGO, lambda: resolve_with_duckduckgo(url, max_chars)),
    }
```

> **Note**: Since `visual_clip` requires a `query`, ensure `resolve_url_stream` receives it or can access it from the session.
