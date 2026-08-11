# Performance Optimization (Condensed Status)

## Original Overview

10 performance optimizations organized by effort level: quick wins (Phase 1),
medium effort (Phase 2), high effort (Phase 3).

## Status

> Status refreshed 2026-08-11; prior file said "~1/10 done" but most items are
> now shipped or partially shipped. See CHANGELOG v0.3.9 and the code
> references below.

## What's Done

- **Opt 1: Reuse ThreadPoolExecutor** (Phase 1): ✅ Shipped — `scripts/utils/thread_pool.py`
  (`get_shared_pool()`), consumed by duckduckgo.py:34, exa.py:92, firecrawl.py:43,
  mistral.py:70/124, tavily.py:35 via `loop.run_in_executor`.
- **Opt 2: Eliminate busy-polling** (Phase 1): ⚠️ Verify — `timeout=0.01` no longer
  present in `scripts/resolve.py` (file still exists). Re-check for remaining
  tight-poll loops before closing.
- **Opt 3: HTTP/2 + keep-alive** (Phase 1): ✅ Shipped — shared `get_session()`
  (sync, `utils/http.py`) used by exa.py:141, jina.py:74, serper.py:96; async
  `get_async_client()` (`utils/async_http.py`). Rust `shared_client.rs` shares a
  single `reqwest::Client`.
- **Opt 4: L1 in-memory cache** (Phase 1): ⚠️ Partial — `functools.lru_cache`
  used for DNS bucketing (`utils/http.py:75`, `utils/async_http.py:62`); no
  general content `TTLCache` layer. Two-tier cache (semantic + disk) remains.
- **Opt 5: Content compaction optimization** (Phase 1): ✅ PR #325 merged
  (`optimize compact_content`).
- **Opt 6: Early quality exit** (Phase 1): ⚠️ Verify — check `scripts/quality.py`
  for early-exit in the recent refactor before closing.
- **Opt 7: Shared reqwest Client** (Phase 2): ✅ Shipped — `cli/src/providers/shared_client.rs`
  `SHARED_CLIENT: OnceLock<Client>` + `get_client()`; used by all Rust providers.
- **Opt 8: Async-aware locks** (Phase 2): ⚠️ Partial — `tokio::sync::Mutex` in
  `rate_limiter.rs`; `std::sync::Mutex` still used in `semantic_cache/*` and
  `thread_pool.py`. Migration depends on async consolidation (ADR-014).
- **Opt 9: True parallel provider launch** (Phase 3): ⚠️ Partial — `asyncio.gather`
  in `utils/http.py:248` / `async_http.py:232`; `_cascade.py` still bridges
  sync→async with a 1-worker pool.
- **Opt 10: Request coalescing** (Phase 3): ✅ Shipped — `scripts/utils/cache.py`
  `coalesce_request` + `_inflight_requests` dedupes in-flight concurrent calls.

## What Remains

- Close/verify Opt 2 and Opt 6 (status flags above).
- Opt 4 (general content TTL cache) and Opt 8 (full async lock migration) are
  the only clearly-open items; Opt 9 needs a dedicated async-cascade sprint.
- Phases 2-3 depend on async migration (ADR-014).

## References

- [ADR-014](014-architecture-and-parity.md) — Async/await migration dependency
- [scripts/resolve.py](../scripts/resolve.py) — Busy-polling locations
- [scripts/utils.py](../scripts/utils.py) — Compaction + session code
- [scripts/utils/thread_pool.py](../scripts/utils/thread_pool.py) — shared executor
- [scripts/utils/cache.py](../scripts/utils/cache.py) — request coalescing
