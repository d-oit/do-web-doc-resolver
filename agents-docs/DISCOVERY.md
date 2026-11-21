# Alternative-Source Discovery

Discovery is a bounded fallback, not part of the successful-primary path. It
runs only when the primary URL fails or its content score is below the
acceptance threshold. A successful primary pays no discovery cost.

## Strategy families

| Family | Input | Candidate examples |
|---|---|---|
| `publisher_metadata` | page HTML, `llms.txt` | canonical/alternate/`og:url`, sitemap, feed, `llms.txt` links |
| `official_repository` | HTML and `llms.txt` | GitHub/GitLab, crates.io, PyPI, npm package pages |
| `versioned_docs` | URL path and redirect chain | `/docs/stable/`, `/docs/latest/`, unversioned path, redirect final URL |
| `search_provider` | normalized search results | product/version/error-term queries from an injected provider |

All four families are always reported, including zero-candidate families, so a
missing strategy is visible rather than silent.

## Provenance and verification

Every candidate carries:

- `strategy`, `family`, and `discovery_provider`;
- `original_url`, `canonical_url`, `publisher_domain`;
- `relationship`: `canonical`, `same-publisher`, `official-repository`, or
  `unofficial`;
- `timestamp`, `reason`, `redirect_chain`;
- `verification_state`: `verified`, `unverified`, or `rejected`;
- separate `relevance`, `freshness`, `structural_completeness`, `authority`, and
  `extraction_quality` scores plus `overall`.

Validation runs before extraction and follows redirects. Deduplication is by
canonical URL first, then by content identity when an extractor provides a
content hash. A canonical publisher source is ordered before a verified
unofficial mirror; the mirror can still be returned as an alternative, but not
silently as the answer.

## Ranking and budgets

```text
overall = 0.35 * authority
        + 0.25 * relevance
        + 0.15 * freshness
        + 0.15 * structural_completeness
        + 0.10 * extraction_quality
```

- Default candidate cap: 8.
- Default extraction cap: 2 candidates per fallback.
- Default fallback budget: 6000 ms.
- Versioned docs prefer `stable` over `latest` deterministically; numeric
  version paths lose freshness unless a newer variant is found.
- `DO_WDR_DISCOVERY=0` disables the fallback entirely.
- `DO_WDR_DISCOVERY_SEARCH=0` disables the live search strategy.

## Runtime split

Python splits the pure core (`scripts/discovery.py` and
`scripts/discovery_models.py`) from the live path
(`scripts/discovery_live.py`, which owns HTTP fetching, validation, extraction,
and the URL-cascade integration). Rust (`cli/src/discovery.rs` and
`cli/src/discovery_strategies.rs`) owns the same pure candidate-generation,
provenance, verification, deduplication, and ranking contract for parity tests
and future integration.

This is a deliberate staged rollout: the Rust CLI does not yet execute the live
discovery phase. Do not add a second unsafe extraction path; the Python live
path already enforces `_safe_request` redirect-by-redirect SSRF validation and
bounded fetch limits.

## Fixtures and benchmark

Shared fixture: `tests/fixtures/discovery_cases.json`.

```bash
python -m pytest tests/test_discovery.py tests/test_discovery_bench.py
python scripts/bench_discovery.py --json
```

Current offline result:

| Metric | Primary only | Discovery |
|---|---|---|
| Recall | 0.375 | 1.000 |
| Mean selected quality | n/a | 0.81 |
| Median candidate generation | n/a | < 1 ms |
| Extraction cap | n/a | 2 per case |

The benchmark is deterministic apart from wall-clock generation timing and is
not a claim for every live source. It proves the bounded fallback recovers the
fixture corpus without increasing cost for a successful primary.
