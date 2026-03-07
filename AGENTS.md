# Agent Instructions

This repository contains the **web-doc-resolver** Agent Skill — a low-cost cascade resolver that fetches and resolves web documentation into compact, LLM-ready markdown.

## Repository Structure

```
web-doc-resolver/
├── SKILL.md              # Agent skill definition (agentskills.io format)
├── AGENTS.md             # This file - project-level context
├── README.md             # Human-readable project documentation
├── scripts/
│   └── resolve.py        # Main resolver script (async Python)
├── tests/
│   └── test_resolve.py   # Basic unit tests
├── .github/workflows/
│   └── ci.yml            # CI/CD pipeline (lint, test, sample)
├── .gitignore            # Python gitignore
└── LICENSE               # MIT license
```

## How It Works

The resolver uses a **cascade strategy** to minimize API calls and token usage:

1. **For URLs**: Probes `llms.txt` first → falls back to Firecrawl if needed
2. **For queries**: Uses Exa highlights first → Tavily fallback → Firecrawl last

This approach:
- Prioritizes site-provided structured docs (llms.txt)
- Uses Exa highlights for token-efficient search
- Calls Tavily only when Exa returns insufficient results
- Scrapes with Firecrawl only as final fallback

## Running the Script

### Prerequisites

- Python 3.10+
- Install dependency: `pip install aiohttp`

### Basic Usage

```bash
# Resolve a query
python scripts/resolve.py "Rust agent frameworks"

# Resolve a URL
python scripts/resolve.py "https://docs.rs/tokio/latest/tokio/"

# With custom options
python scripts/resolve.py "query" \
  --min-chars 200 \
  --max-chars 8000 \
  --exa-results 5 \
  --tavily-results 3 \
  --output-limit 10 \
  --log-level INFO
```

### Output

Returns JSON array:
```json
[
  {
    "url": "https://example.com/docs",
    "content_markdown": "# Documentation...",
    "source": "llms_txt_doc|exa_highlights|tavily_search|firecrawl",
    "score": 0.87
  }
]
```

## API Keys (All Optional)

Set environment variables for provider access:

```bash
export EXA_API_KEY="your-key"        # For Exa search
export TAVILY_API_KEY="your-key"     # For Tavily fallback
export FIRECRAWL_API_KEY="your-key"  # For Firecrawl scraping
```

**Important**: All API keys are optional. The script runs without them and provides placeholder results.

## Testing

```bash
# Run unit tests
python -m pytest tests/

# Run with coverage
python -m pytest --cov=scripts --cov-report=term tests/
```

## Development

### Code Style

- Format with `black`
- Lint with `ruff`
- Type check with `mypy`

### CI/CD

GitHub Actions runs on every push:
- **Lint**: ruff, black, mypy
- **Test**: pytest on Python 3.10, 3.11, 3.12
- **Sample**: Demonstrates script runs without API keys

## Cascade Strategy Details

### Why This Order?

1. **llms.txt first**: Sites provide structured markdown indices — use them before search
2. **Exa highlights**: Token-efficient for agentic workflows (vs full text)
3. **Tavily fallback**: Richer content increases cost — use only when needed
4. **Firecrawl last**: Scraping is slowest and most expensive — final resort only

### Quality Ranking

Results scored by:
- Source priority (llms_txt_doc: 1.00, firecrawl: 0.86, exa: 0.78, tavily: 0.72)
- Markdown quality (headings, lists, code fences)
- Content length (200-8000 chars preferred)
- Low HTML-to-text ratio

## Troubleshooting

### Missing aiohttp
```
pip install aiohttp
```

### API Key Errors
All keys are optional — script degrades gracefully without them.

### Empty Results
Check:
1. Input is valid URL or query
2. Log level: `--log-level DEBUG` for details
3. API keys if using providers

## Related Files

- `SKILL.md`: Full agent skill specification
- `README.md`: Human-readable overview
- `scripts/resolve.py`: Implementation source code
