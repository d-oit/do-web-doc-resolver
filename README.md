# web-doc-resolver

<p align="center">
  <a href="https://pypi.org/project/web-doc-resolver/"><img src="https://img.shields.io/pypi/v/web-doc-resolver?color=blue" alt="PyPI"></a>
  <a href="https://pypi.org/project/web-doc-resolver/"><img src="https://img.shields.io/pypi/pyversions/web-doc-resolver" alt="Python"></a>
  <a href="https://github.com/d-oit/web-doc-resolver/blob/main/LICENSE"><img src="https://img.shields.io/pypi/l/web-doc-resolver" alt="License"></a>
  <a href="https://github.com/d-oit/web-doc-resolver/actions/workflows/ci.yml"><img src="https://github.com/d-oit/web-doc-resolver/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
</p>

Resolve queries or URLs into compact, LLM-ready markdown using an intelligent, low-cost cascade.

## Why This Project?

Building AI agents that need to fetch web content? This library handles the complexity of web scraping and search so you can focus on your application. It automatically tries multiple providers in order of cost-efficiency, falling back gracefully when services are unavailable.

**Works without any API keys** — uses free providers (Exa MCP, DuckDuckGo, Jina Reader) by default.

## Installation

```bash
pip install web-doc-resolver
```

Or install with all dependencies:

```bash
pip install web-doc-resolver[all]
```

### Prebuilt Binary

```bash
# Linux
curl -L https://github.com/d-oit/web-doc-resolver/releases/latest/download/wdr-linux-x86_64 -o wdr && chmod +x wdr

# macOS (Apple Silicon)
curl -L https://github.com/d-oit/web-doc-resolver/releases/latest/download/wdr-macos-aarch64 -o wdr && chmod +x wdr

# Windows (PowerShell)
Invoke-WebRequest -Uri "https://github.com/d-oit/web-doc-resolver/releases/latest/download/wdr-windows-x86_64.exe" -OutFile wdr.exe
```

## Quick Start

```python
from scripts.resolve import resolve

# Resolve a URL to markdown
result = resolve("https://docs.example.com")
print(result)

# Resolve a query to search results
result = resolve("python async best practices")
print(result)
```

## How It Works

The resolver automatically detects whether the input is a URL or a query, then runs through a cascade of providers:

| Input Type | Cascade Order |
|------------|---------------|
| **URL** | llms.txt → Jina Reader → Firecrawl → Direct fetch → Mistral → DuckDuckGo |
| **Query** | Exa MCP → Exa SDK → Tavily → DuckDuckGo → Mistral |

Free providers are tried first. Paid providers are skipped if their API keys aren't configured.

## API Keys

All API keys are **optional**. The resolver works with zero keys using free providers.

| Variable | Provider | Notes |
|----------|----------|-------|
| `EXA_API_KEY` | Exa SDK | Optional — Exa MCP is free and tried first |
| `TAVILY_API_KEY` | Tavily | Optional — comprehensive search |
| `FIRECRAWL_API_KEY` | Firecrawl | Optional — deep extraction |
| `MISTRAL_API_KEY` | Mistral | Optional — AI-powered fallback |

```bash
export EXA_API_KEY="your-key"
export TAVILY_API_KEY="your-key"
export FIRECRAWL_API_KEY="your-key"
export MISTRAL_API_KEY="your-key"
```

## Advanced Usage

### Skip Specific Providers

```python
result = resolve("query", skip_providers={"exa_mcp", "exa"})
```

### Use a Specific Provider

```python
from scripts.resolve import resolve_direct, ProviderType

result = resolve_direct("https://example.com", ProviderType.JINA)
result = resolve_direct("python tutorials", ProviderType.EXA_MCP)
```

### Custom Provider Order

```python
from scripts.resolve import resolve_with_order, ProviderType

result = resolve_with_order(
    "https://example.com",
    [ProviderType.LLMS_TXT, ProviderType.JINA, ProviderType.DIRECT_FETCH]
)
```

### Command Line

```bash
# URL to markdown
python -m scripts.resolve "https://example.com"

# Query to search results
python -m scripts.resolve "python async tutorials"

# With options
python -m scripts.resolve "query" --max-chars 8000 --json

# Skip providers
python -m scripts.resolve "query" --skip exa_mcp --skip exa
```

## Features

- **Multi-layer caching** — URL, query, and provider-level semantic cache
- **Parallel probes** — Concurrent fast-path checks for lower latency
- **Content compaction** — Boilerplate removal and deduplication
- **Telemetry** — Per-provider latency and cost tracking
- **Link validation** — Async HTTP status checks for returned links
- **Document OCR** — PDF/DOCX support via Docling, images via OCR
- **Execution profiles** — `free`, `balanced`, `fast`, and `quality` modes

## Testing

```bash
# Unit tests (no API keys required)
python -m pytest tests/ -v -m "not live"

# Live integration tests (requires API keys)
python -m pytest tests/ -m live -v

# With coverage
python -m pytest --cov=scripts tests/
```

## Web UI

A Next.js 15 PWA deployed on Vercel at [web-doc-resolver.vercel.app](https://web-doc-resolver.vercel.app).

### Local Development

```bash
cd web
pnpm install
pnpm dev          # http://localhost:3000
```

### Vercel Deployment

```bash
vercel login
vercel link
vercel pull --yes --environment=production
vercel build --prod
vercel deploy --prebuilt --prod --yes
```

### Debugging

```bash
vercel logs <deployment-url>       # build/runtime logs
vercel logs --level error          # errors only
vercel inspect <url> --logs        # build logs
```

## Project Structure

```
web-doc-resolver/
├── README.md              # This file
├── SKILL.md               # agentskills.io skill definition
├── AGENTS.md              # Developer documentation
├── pyproject.toml         # Python package configuration
├── cli/                   # Rust CLI (wdr binary)
│   └── ui/                # Design system (CSS tokens + components)
├── web/                   # Next.js web UI (Vercel)
│   ├── app/               # App Router pages
│   └── public/            # Static assets + PWA manifest
├── scripts/               # Python source code
│   └── resolve.py         # Main resolver
├── tests/                 # Test suite
└── agents-docs/           # Detailed reference docs
```

## Related Documentation

- [SKILL.md](SKILL.md) — Agent skill specification
- [AGENTS.md](AGENTS.md) — Developer guide
- [agents-docs/CASCADE.md](agents-docs/CASCADE.md) — Full cascade logic
- [agents-docs/PROVIDERS.md](agents-docs/PROVIDERS.md) — Provider details

## License

MIT License — see [LICENSE](LICENSE) file.

## Contributing

Contributions are welcome. Please ensure tests pass and follow the code style guidelines in [AGENTS.md](AGENTS.md).

## Support

- Report bugs: [GitHub Issues](https://github.com/d-oit/web-doc-resolver/issues)
- Security issues: See [SECURITY.md](SECURITY.md)