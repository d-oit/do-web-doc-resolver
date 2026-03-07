---
name: web-doc-resolver
description: Resolve a query or URL into compact, LLM-ready markdown using a low-cost cascade: llms.txt first, Exa highlights first for search, Tavily fallback, Firecrawl last.
license: MIT
compatibility: Python 3.10+, env: EXA_API_KEY, TAVILY_API_KEY, FIRECRAWL_API_KEY
metadata:
  author: Dominik Oswald
  version: "4.0"
  optimized: low-cost cascade, strict-llms-txt, compact-context, deterministic-ranking
allowed-tools: Bash(python:*)
---
Resolve query or URL inputs into compact, high-signal markdown for agents and RAG systems.

## Goals
- Prefer site-provided structured documentation before search
- Minimize duplicate provider calls
- Keep context compact for downstream LLM use
- Return only cleaned, ranked markdown documents
- Never require billing, quota, or usage logic in the skill itself

## Usage
```bash
python scripts/resolve.py "Rust agent frameworks"
python scripts/resolve.py "https://docs.rs/tokio/latest/tokio/"
```

## Output
```json
[
  {
    "url": "https://example.com/docs/page",
    "content_markdown": "# Clean content...",
    "source": "llms_txt_doc|firecrawl|exa_highlights|tavily_search|llms_txt_index",
    "score": 0.87
  }
]
```

## Resolution strategy

### URL input
1. Probe `https://origin/llms.txt`
2. Parse valid markdown file lists from llms.txt
3. Fetch primary linked docs first, then a small number of optional docs
4. If strong markdown docs are found, stop
5. If not, use Firecrawl as the final fallback

### Query input
1. Search with Exa first using compact highlights
2. Keep result count small and use highlights instead of full text for the first pass
3. Only call Tavily if Exa returns too few usable candidates
4. Resolve top candidate URLs through the same URL pipeline
5. Use Firecrawl only when the resolved URLs still do not yield good markdown

## Quality rules
- Normalize markdown before scoring
- Reject obvious error, captcha, access-denied, and not-found pages
- Prefer content in the 200 to 8000 character range
- Reward headings, lists, and code fences
- Penalize HTML-heavy pages and link farms
- Deduplicate by canonical URL and keep the best-scoring version only

## Defaults
```
MAX_CHARS=8000
MIN_CHARS=200
EXA_RESULTS=5
TAVILY_RESULTS=3
OUTPUT_LIMIT=10
```

## CLI options
```bash
python scripts/resolve.py "query or url" \
  --min-chars 200 \
  --max-chars 8000 \
  --exa-results 5 \
  --tavily-results 3 \
  --output-limit 10 \
  --log-level WARNING
```

## Operational behavior
- Exa is the default discovery engine for query inputs
- Tavily is fallback discovery only, not parallel-by-default
- Firecrawl is extraction fallback only
- Provider failures never crash the resolver
- Errors are emitted as JSON, logs go to stderr

## Notes
- llms.txt links are parsed from markdown list items, not filtered by file extension
- Search snippets may be returned when full markdown extraction is unavailable
- The resolver ranks sources deterministically instead of using an uncomputed semantic threshold
- All API keys are **optional** — providers are skipped gracefully when keys are absent
