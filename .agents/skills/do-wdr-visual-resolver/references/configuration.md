# Configuration Guide: Visual Resolver

The visual resolver is configured via the `[visual]` section in `config.toml`.

## `config.toml`

```toml
[visual]
enabled = true
threshold = 0.25
device = "auto"    # "cpu", "cuda", or "auto"
model = "ViT-B/32"
timeout = 30       # Playwright screenshot timeout in seconds
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `VISUAL_RESOLVER_THRESHOLD` | Override similarity threshold (0.0-1.0) |
| `VISUAL_RESOLVER_DEVICE`    | Force device (cpu/cuda) |
| `PLAYWRIGHT_HEADLESS`       | Set to `false` for debugging (default: `true`) |
