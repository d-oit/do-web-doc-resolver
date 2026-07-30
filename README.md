<div align="center">

<img src="assets/do-web-doc-resolver-banner.png" alt="do-web-doc-resolver logo" width="320"/>

# do-web-doc-resolver

**Resolve queries or URLs into compact, LLM-ready Markdown**
An intelligent cascade routing engine across free, direct, paid, and browser-based providers.

[![CI](https://github.com/d-oit/do-web-doc-resolver/actions/workflows/ci.yml/badge.svg)](https://github.com/d-oit/do-web-doc-resolver/actions)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![Rust](https://img.shields.io/badge/rust-stable-f74c00?logo=rust&logoColor=white)](https://www.rust-lang.org/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js)](https://nextjs.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-06b6d4.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[Live Demo](https://web-eight-ivory-29.vercel.app) · [Documentation](docs/) · [Report Bug](https://github.com/d-oit/do-web-doc-resolver/issues) · [Request Feature](https://github.com/d-oit/do-web-doc-resolver/issues)

</div>

---

## What the Tool Does

The web doc resolver translates complex web URLs or text search queries into clean, deduplicated, and token-efficient Markdown. This Markdown is structured for direct injection into Large Language Model (LLM) context windows or Retrieval-Augmented Generation (RAG) pipelines. It uses local semantic caching, heuristic quality scoring, circuit breakers, and per-domain routing memory to find the most efficient provider for any request.

---

## Installation

### Python Library and CLI

Install the Python core dependencies. Python 3.11 or higher is required.

```bash
git clone https://github.com/d-oit/do-web-doc-resolver.git
cd do-web-doc-resolver
pip install -r requirements.txt
```

### Rust CLI (`do-wdr`)

Build the high-performance compiled binary.

```bash
cd cli
cargo build --release
# Built binary is located at cli/target/release/do-wdr
```

### Web UI (Next.js)

Install the web interface dependencies.

```bash
cd web
npm install --legacy-peer-deps
```

---

## How to Run

### Python Library

```python
from scripts.resolve import resolve

# Resolve a URL
result = resolve("https://docs.python.org/3/library/json.html")
print(result["content"])

# Resolve a search query
result = resolve("Python json module documentation")
print(result["content"])
```

### Python CLI

```bash
# Resolve a search query
python -m scripts.cli "Python subprocess"

# Resolve a URL
python -m scripts.cli "https://example.com"
```

### Rust CLI

```bash
# Resolve a URL or query
./cli/target/release/do-wdr resolve "https://docs.example.com"
./cli/target/release/do-wdr resolve "how to parse json in rust"
```

### Web UI

Start the development server:

```bash
cd web
npm run dev
# Open http://localhost:3000 in your browser
```

---

## The Cascade

The resolver organizes providers into an escalation-based cascade, attempting free or low-cost static methods before falling back to heavier or paid scrapers and headless browser sessions.

### Query Resolution Cascade

1. **Semantic Cache**: Fast local SQLite + `sqlite-vec` vector lookup of similar previous queries.
2. **Exa MCP**: Desktop/local model-context-protocol search integration.
3. **Exa SDK**: Web search with highlights.
4. **Tavily**: Broad web search engine.
5. **Serper**: Google search API.
6. **DuckDuckGo**: Free HTML search fallback.
7. **Mistral Websearch**: LLM-augmented search routing.

### URL Resolution Cascade

1. **Semantic Cache**: Fast similarity lookup of previously cached page content.
2. **Document/Image parsers**: Local extraction of specialized extensions (Docling for `.pdf`/`.docx`/`.pptx`, OCR for `.png`/`.jpg`/`.jpeg`).
3. **llms.txt**: Reads static `.txt` files directly if published at the target domain root or path.
4. **Jina Reader**: Light markdown extraction API.
5. **Firecrawl**: Deep cloud content rendering API.
6. **Direct Fetch**: Local HTTP client utilizing `trafilatura` and `readability-lxml` parsing.
7. **Mistral Browser**: Headless JS-enabled browser rendering.
8. **Visual CLIP**: Multi-modal vision-based target validation.
9. **DuckDuckGo**: Domain-level search.
10. **Stealth**: anti-bot bypass tier.

---

## Environment Variables Required

All environment variables are optional. The tool defaults to free local direct fetching or cached results if no keys are set.

| Variable | Provider / Component | Purpose |
|---|---|---|
| `EXA_API_KEY` | Exa SDK | Activates Exa web search |
| `TAVILY_API_KEY` | Tavily Search | Activates Tavily web search |
| `SERPER_API_KEY` | Serper | Activates Google search fallback |
| `FIRECRAWL_API_KEY` | Firecrawl | Activates cloud JS rendering |
| `MISTRAL_API_KEY` | Mistral AI | Activates Mistral Search and Mistral Browser |
| `DO_WDR_SEMANTIC_CACHE` | Semantic Cache | Set to `0` to disable the SQLite semantic cache |
| `DO_WDR_CACHE_THRESHOLD` | Semantic Cache | Minimum similarity score (default `0.85`) |
| `DO_WDR_CACHE_MAX_ENTRIES`| Semantic Cache | Max entries before LRU eviction (default `10000`) |

---

## How to Run Tests

### Python Test Suite

Run the unit and integration tests (excluding live external API calls):

```bash
PYTHONPATH=. python -m pytest tests/ -v -m "not live"
```

### Rust CLI Test Suite

Run the native CLI tests:

```bash
cd cli && cargo test
```

### Web UI Test Suite

Run the Playwright E2E browser tests:

```bash
cd web
npx playwright test --project=desktop
```
