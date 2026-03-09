<!-- skill: web-doc-resolver v1.2.0 -->
<!-- source: https://github.com/d-oit/web-doc-resolver/tree/v1.2.0 -->

# Agent Instructions

This repository contains the **web-doc-resolver** Agent Skill — a low-cost cascade resolver that fetches and resolves web documentation into compact, LLM-ready markdown.

## Setup (run once)

```bash
# No-install run via uvx (recommended)
uvx web-doc-resolver --help

# Or install directly
pip install -r requirements.txt

# Setup git hooks (validates skill symlink on commit)
./scripts/setup-hooks.sh
```

## Skill Symlink Validation

The skill definition in `.blackbox/skills/web-doc-resolver/SKILL.md` must always point to the root `SKILL.md` file. This is validated:

- **On every commit** via pre-commit hook
- **In CI** via `validate-symlink` job
- **Manually** via `python scripts/validate_skill_symlink.py`

If the symlink is broken or points to the wrong location, commits and CI will fail.

## Repository Structure

```
web-doc-resolver/
├── SKILL.md              # Agent skill definition (agentskills.io format)
├── AGENTS.md             # This file - project-level context
├── README.md             # Human-readable project documentation
├── .mcp.json             # MCP server config for Claude Code / OpenCode
├── scripts/
│   └── resolve.py        # Main resolver script (async Python)
├── references/
│   └── CASCADE.md        # Full cascade fallback decision tree
├── tests/
│   └── test_resolve.py   # Comprehensive unit tests
├── .github/workflows/
│   ├── ci.yml            # CI/CD pipeline (lint, test, sample)
│   └── release.yml       # Tag-based release + changelog automation
├── .gitignore            # Python gitignore
└── LICENSE               # MIT license
```

## How It Works

The resolver uses a **cascade strategy** to minimize API calls and token usage:

1. **For URLs**: Probes `llms.txt` first → falls back to Firecrawl → Direct fetch → Mistral fallback
2. **For queries**: Uses **Exa MCP (FREE)** first → Exa SDK → Tavily → DuckDuckGo (free) → Mistral fallback

This approach:
- **Exa MCP is now primary**: Free search via Model Context Protocol (no API key!)
- Prioritizes site-provided structured docs (llms.txt)
- Uses Exa highlights for token-efficient search
- Calls Tavily only when Exa returns insufficient results
- Falls back to DuckDuckGo (completely free, no API key needed)
- Uses Mistral as final AI-powered fallback

## Running the Script

### Prerequisites

- Python 3.10+
- Install dependencies: `pip install -r requirements.txt`

### Basic Usage

```bash
# Resolve a query (uses Exa MCP - FREE!)
python scripts/resolve.py "Rust agent frameworks"

# Resolve a URL
python scripts/resolve.py "https://docs.rs/tokio/latest/tokio/"

# With options
python scripts/resolve.py "query" --max-chars 8000 --log-level INFO --json
```

### Skip Specific Providers

```bash
# Skip Exa MCP to test fallbacks
python scripts/resolve.py "query" --skip exa_mcp --skip exa

# Use only Mistral
python scripts/resolve.py "query" --skip exa_mcp --skip exa --skip tavily --skip duckduckgo

# Use only DuckDuckGo
python scripts/resolve.py "query" --skip exa_mcp --skip exa --skip tavily --skip mistral
```

## Environment Variables (all optional)

| Variable | Provider | Notes |
|---|---|---|
| `EXA_API_KEY` | Exa SDK | Optional - Exa MCP is free and used first |
| `TAVILY_API_KEY` | Tavily | Optional - comprehensive search |
| `FIRECRAWL_API_KEY` | Firecrawl | Optional - deep extraction |
| `MISTRAL_API_KEY` | Mistral | Optional - AI-powered fallback |

**Note**: Exa MCP and DuckDuckGo are always available as free fallbacks (no API key required).

## Versioning

This is an [agentskills.io](https://agentskills.io) Agent Skill. Versions are Git tags.

