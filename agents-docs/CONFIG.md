# Configuration Reference

Layered configuration system for `web-doc-resolver` (Python skill + Rust `wdr` CLI).

## Configuration Layers (Priority: High to Low)

1. **CLI flags** — highest priority, override everything
2. **Environment variables** — override config file
3. **`config.toml`** — project-level or user-level file
4. **Built-in defaults** — lowest priority

## Environment Variables

### API Keys

| Variable | Provider | Required |
|----------|----------|----------|
| `EXA_API_KEY` | Exa Search API | Only for `exa` provider |
| `TAVILY_API_KEY` | Tavily Search API | Only for `tavily` provider |
| `MISTRAL_API_KEY` | Mistral OCR API | Only for `mistral` provider |

### Rust CLI (`wdr`) Env Vars

| Variable | Description | Default |
|----------|-------------|--------|
| `WDR_PROVIDERS_ORDER` | Comma-separated cascade order | Built-in default |
| `WDR_SKIP` | Comma-separated providers to skip | (none) |
| `WDR_MIN_CHARS` | Min content chars threshold | `200` |
| `WDR_LOG_LEVEL` | Log level (error/warn/info/debug/trace) | `info` |
| `WDR_LOG_JSON` | Enable JSON structured logs (`1`/`true`) | `false` |
| `WDR_CONFIG` | Path to config.toml | auto-discover |

## config.toml Schema

Default search paths:
1. `./config.toml` (current directory)
2. `~/.config/wdr/config.toml` (user config)
3. `/etc/wdr/config.toml` (system config)

```toml
# config.toml — full example

[resolve]
# Default cascade order (comma-separated)
providers_order = "exa_mcp,llms_txt,direct_fetch,jina,exa,tavily,mistral,duckduckgo"

# Providers to always skip
skip = []

# Minimum chars for a valid result
min_chars = 200

[logging]
# Log level: error | warn | info | debug | trace
level = "info"

# Emit JSON structured logs to stderr
json = false

[providers]
# Per-provider overrides

[providers.jina]
# Jina base URL override (e.g. self-hosted)
base_url = "https://r.jina.ai"

[providers.exa]
# Max results to request
max_results = 5

[providers.tavily]
# Search depth: "basic" | "advanced"
search_depth = "basic"

[providers.mistral]
# Model to use for OCR
model = "mistral-ocr-latest"
```

## Default Values

| Setting | Default |
|---------|---------|
| `providers_order` | `exa_mcp,llms_txt,direct_fetch,jina,exa,tavily,mistral,duckduckgo` |
| `skip` | `[]` |
| `min_chars` | `200` |
| `log.level` | `info` |
| `log.json` | `false` |

## Generating a Default Config

```bash
# Rust CLI
wdr config init
# Writes config.toml to current directory

# View effective (merged) config
wdr config show
```

## Python Skill Config

The Python skill reads only environment variables (no config file).
Pass flags directly on the command line or set env vars before calling:

```bash
export EXA_API_KEY=xxx
export TAVILY_API_KEY=yyy
python scripts/resolve.py "query" --skip mistral
```
