# Plan 22 — Full-Repo Improvement Sweep (2026-10-02)

> Source: four parallel deep-dive analyses (Python core, Rust CLI, Web UI, Tests/CI)
> run on `main` @ `76b1b5c` after v0.3.10.
> Target landing: `plans/22-codebase-improvement-2026-10.md` + `plans/README.md` row.

## Goal

Close every gap surfaced by the 2026-10 analysis: correctness bugs, security
hardening, cross-runtime parity, feature gaps, DRY consolidation, file-size
violations, and CI enforcement. Items verified by direct inspection are marked
**[V]**.

## Wave A — P0 Correctness & Security

| ID | Area | File(s) | Issue | Action |
|----|------|---------|-------|--------|
| A1 | Skill | `scripts/sync_skill.py:28-40` | `SYNC_FILES` stale — mirrored skill imports `_query_resolve`, `_url_resolve`, `_url_resolve_async`, `providers` pkg, `semantic_cache` that don't exist in mirror; standalone skill unusable | Add missing modules + `providers/` package to SYNC_FILES; add mirror-import smoke test |
| A2 | Py-async | `scripts/_cascade_async.py:52-95` | Async cascade launches ALL eligible providers (free+paid) in parallel; sync quality-gate/cost control bypassed; `asyncio.wait` has no timeout so latency budgets never enforced | Staggered hedged launch: free tier first, paid only when `min_free_quality_to_skip_paid` unmet; add `max_total_latency_ms` timeout |
| A3 | Web | `web/app/page.tsx:322` **[V]** | Reads `data.quality_score` but API returns `quality` object (`route.ts:288,294`); score always null | `setQualityScore(data.quality?.score ?? null)` |
| A4 | Web | `web/middleware.ts:20` + `web/app/api/resolve/route.ts:209` | Rate limit counted twice → effective 15/min not 30/min | Count in one layer only (keep middleware) |
| A5 | Web | `web/app/api/ui-state/route.ts:24-33`, `web/lib/ui-state.ts:153-162` | API keys synced unthrottled every keystroke; stored plaintext server-side keyed by `sha256(IP+UA)`; unauthenticated GET exposes keys to shared-NAT users | Keep keys localStorage-only; drop server key sync; debounce persistence |
| A6 | Web | `web/app/api/cache/route.ts:8-11`, `web/app/api/records/route.ts:35-38` | Unauthenticated, unrate-limited DELETE endpoints wipe server state | Require session token or remove endpoints |
| A7 | Rust | `cli/src/output.rs:31-39` | `JsonOutput::error()` takes `_msg` and discards it; JSON consumers never see the error | Add `error: Option<String>` field and render it |
| A8 | Rust | `cli/src/config/mod.rs:399-403` | `merge_bool` only overrides on `true` — TOML can never disable `semantic_cache`/`prewarm`/`synthesis` | Presence-tracking merge (`Option<bool>` + serde default) |
| A9 | Rust | `cli/src/bias_scorer.rs:29,34,46` | `domain.contains(site)` — `github.com.evil.example` earns dev-domain trust bonus | Exact-host / public-suffix match |
| A10 | Py | `scripts/routing_memory.py:101-106` **[V]** | `_dirty is False or ...` → `_save_to_disk_unlocked()` resets `_dirty`, so every `record()` writes JSON to disk; 5s throttle never throttles; hot-path disk churn | Save on interval only: `time.time() - self._last_save >= SAVE_INTERVAL_SECONDS` |
| A11 | Py | `scripts/providers/stealth.py:1-31` **[V]** | TODO stub returns truthy empty `ResolvedResult` (not None) → cascade scores it 0.0 and writes negative-cache entry suppressing the tier slot | Return `None` or remove from `PROVIDER_TIERS`/cascade maps until implemented |
| A12 | Rust | `cli/src/providers/shared_client.rs:16` | AGENTS.md advertises `DEFAULT_MAX_RETRIES=3` but the Rust HTTP client has zero retries; the doc comment claims "retry configuration" that does not exist | Add bounded retry/backoff middleware or fix the comment (parity gap, see F9) |

A12 deferred to Wave F9 with the Python retry work so both runtimes land together.

## Wave B — P1 High-Impact Fixes

| ID | Area | File(s) | Issue | Action |
|----|------|---------|-------|--------|
| B1 | Py | `scripts/_url_resolve_async.py:56`, `_cascade_async.py:142-192` | Blocking semantic-cache/embedding work on event loop (sentence-transformers encode stalls all tasks; matches SEMANTIC_HEALTH_ISSUE.md) | Wrap in `asyncio.to_thread()`; background model preload |
| B2 | Py | `scripts/_cascade.py:113`, `_cascade_async.py:117` vs `quality.py:152,179` | `score_content()` called without `links` → `missing_links` always True → every result takes -0.10 penalty; quality gates effectively +0.10 | Extract markdown links inside `score_content` when `links is None` |
| B3 | Py | `scripts/quality.py:171` | No query-relevance signal; pristine-but-irrelevant content scores high | Add `query: str \| None` param; blend embedding/term-overlap relevance |
| B4 | Rust | `cli/src/resolver/mod.rs:77-79`, `startup.rs:27-30` | Routing memory / negative cache / circuit breakers process-local — memory never accumulates, prewarm always early-returns (dead), breakers reset per run | Persist to `.do-wdr_cache` state file |
| B5 | Rust | `cli/src/resolver/mod.rs:210-220` | Synthesis error aborts command; deterministic-merge fallback only on missing key, not on Mistral failure | Fall back on `Err` too |
| B6 | Rust | `cli/src/providers/llms_txt.rs:65-69` | Port dropped when building `scheme://host/llms.txt` | Include port from parsed URL |
| B7 | Rust | `cli/src/link_validator.rs:38` | HEAD-only probing drops valid links on 405/501 sites | Retry with GET or `Range: bytes=0-0` |
| B8 | Rust | `cli/src/compaction.rs:60-68` | Fast path compares bytes to `max_chars`, slow path truncates chars | Unify on chars |
| B9 | Rust | `cli/src/resolver/url.rs:56-59` | `url.ends_with(".pdf")` misses `.PDF`, `file.pdf?v=2` | Case-insensitive match on path component |
| B10 | Web | `web/app/page.tsx:381-389` | History load re-runs query; provider outage clobbers stored result while stale result stays visible | Show stored result; make re-run explicit |
| B11 | Web | `web/app/page.tsx:222` vs `web/lib/resolvers/index.ts:35` | Client `startsWith("http")` vs server regex — mode label can disagree with execution | Share one `isUrl` util |
| B12 | Web | `web/app/components/History.tsx:201` | `>+${n}` renders literal `+$` | Fix template |
| B13 | Py | `scripts/constants.py:48` vs `quality.py:21` | `MIN_CHARS=200` (Jina gate) vs `THRESHOLD_MIN_CHARS=500` (quality) — 300-char results pass then always fail | Align thresholds |
| B14 | Py | `scripts/providers/*` (all except blocks) | Providers swallow error causes; cascade/negative-cache can't distinguish no-key vs transient vs bot-challenge | Typed `ProviderResult`/error return |

**Wave A + early Wave B items: DONE.** Verified per-item below.

| ID | Change | Verification |
|----|--------|--------------|
| A1 | `sync_skill.py` now syncs `_cascade*`, `_query_resolve`, `_url_resolve*`, `_routing_utils`, `semantic_cache`, `cli`, `visual_resolver`, and the whole `providers/` package; standalone skill imports resolve | `python -m scripts.resolve` import check in the skill dir ✅ |
| A2 | Free tier launches first; paid escalates only when the free tier fails the gate; `max_total_latency_ms` enforced as a deadline | `tests/test_cascade_async.py` (8 tests) ✅ |
| A3 | `page.tsx` reads `data.quality?.score` | typecheck + web unit tests ✅ |
| A4 | Duplicate `checkRateLimit` removed from `app/api/resolve/route.ts`; middleware is the single gate | `tests/api/resolve-rate-limit.test.ts` rewritten against middleware ✅ |
| A5 | `apiKeys` stripped in `/api/ui-state` POST **and** GET, and never sent from the client | `tests/api/ui-state-route.test.ts` new case ✅ |
| A6 | DELETE on `/api/cache` and `/api/records` requires the `ui-session` cookie; records POST gains zod validation with size caps | `tests/api/records-route.test.ts` (new, 7 tests) ✅ |
| A7 | `JsonOutput::error()` now surfaces the message in an `error` field | `cargo test` ✅ |
| A8 | Presence-tracked TOML booleans (`ExplicitBools`) so `enabled = false` overrides a `true` default; `SemanticCacheConfig` fields gained serde defaults so partial tables parse | 2 new `config::tests` cases + `cargo test` ✅ |
| A9 | `bias_scorer` uses exact-host/subdomain matching instead of substring | 3 new `bias_scorer` tests ✅ |
| A10 | `RoutingMemory.record()` writes to disk on the interval only | full pytest ✅ |
| A11 | `resolve_with_stealth` returns `None` instead of a truthy empty result | full pytest ✅ |
| B1 | Semantic-cache check and stores moved off the event loop via `asyncio.to_thread` | full pytest ✅ |
| B2 | `score_content` infers markdown links when none are passed, removing the systematic -0.10 penalty | `tests/test_quality_links.py` (new, 6 tests) ✅ |

`cargo fmt` and `cargo clippy --all-targets -D warnings` clean. One pre-existing
failure remains and is unrelated to this work: `semantic_cache::tests::
test_database_failure` (verified failing on pristine `HEAD` in the same
container). Rust was verified in `rust:1.90` because no host toolchain exists.

## Wave C — Feature Additions

| ID | Area | Feature | Notes |
|----|------|---------|-------|
| C1 | Py | **New keyless query providers** — Brave Search (2k/mo free), Wikipedia/CirrusSearch (no key), Mojeek or SearxNG JSON, Google CSE (100/day) | De-risks DDG/Serper instability (ISSUES.md recurring); follow zero-arg-lambda pattern; register in web constants too |
| C2 | Web | **Streaming cascade UX** — SSE/NDJSON per-provider events ("Trying Tavily… 1.2s ✗"), progressive render in deep-research mode | Replaces 60s blocking POST + "Fetching…" |
| C3 | Web | **Structured API response + provider trace** — return `{results, trace, budget, cache_hit}`; stop regex-parsing markdown client-side (`lib/results.ts`) | Route already collects trace via `getProviderSummary()`/`budget.getState()` then discards |
| C4 | Web | **`/api/providers` single source of truth** — serve ids/labels/free-paid/profiles/key-status; derive UI | Provider lists hardcoded in 7 places (constants.ts, routing.ts, resolvers/index.ts, route.ts ×2, key-status, settings, help) |
| C5 | Web | **Real persistence** — Vercel KV/Upstash for history, cache, rate-limit, ui-state (all in-memory Maps; history broken in prod) | Comment at `app/api/history/route.ts:3` already promises this |
| C6 | Web | **Export/share** — .md/.json download, copy-as-JSON, permalink `?q=&profile=&providers=` | Trivial on existing state |
| C7 | Web | **Theme toggle** — `UIState.theme` already round-trips but never read; `layout.tsx:34` hardcodes dark; dark-mode Playwright project exists but never runs | Read theme; honor `prefers-color-scheme` |
| C8 | Web | **Cost estimate display** — map provider → est. cost/request; budget already tracks `paidAttempts` | MetadataBar |
| C9 | Web | **Provider comparison view** — side-by-side cards per provider w/ overlap stats (deep-research currently concatenates) | `extractNormalizedUrls` exists |
| C10 | Rust | **Shell completions** — `clap_complete` + `completions <shell>` subcommand | ~40 lines |
| C11 | Rust | **Distinct exit codes** — map `ResolverError` taxonomy: NotFound→2, RateLimit→3, Quota→4, Auth→5 | Error enum already has variants |
| C12 | Rust | **`cache clear` / `cache drop <key>`** — `SemanticCache::remove` exists, just expose | |
| C13 | Rust | **Streaming/progress events** — NDJSON `{"event":"provider_start",...}` or `--progress` stderr lines | `RoutingDecision` vec has the data |
| C14 | Rust | **stdin input** — `do-wdr resolve -` | |
| C15 | Rust | **Release profile** — `lto="thin"`, `codegen-units=1`, `strip="symbols"`; startup-time win on cache-hit fast path | |
| C16 | Rust | **Parallel `resolve_aggregated`** — race top 2-3 free providers with JoinSet, first acceptable wins | Currently sequential |
| C17 | Web/Rust | **Markdown rendering** — `react-markdown@^10` declared but never imported; render raw view as markdown or drop dep | |
| C18 | Web | **History upgrades** — export JSON/CSV, clear-all, pagination, restore quality/maxChars on load | |
| C19 | Web | **PWA completion** — manifest references nonexistent `/icon-192.png`/`/icon-512.png`; add icons + SW or delete manifest | |
| C20 | Web | **AbortController + Cancel button** during up-to-60s resolves | |

## Wave D — Architecture & DRY

| ID | Area | File(s) | Action |
|----|------|---------|--------|
| D1 | Py | `_cascade.py` / `_cascade_async.py` / `_query_resolve.py:25-61` / `_url_resolve.py:41-77` / `_url_resolve_async.py:167-203` | Consolidate 3× copy-pasted semantic-cache helpers into `semantic_cache.py` single `check()`/`store()`; `resolve.py:75-87` double-computes embeddings on miss |
| D2 | Py | `providers/jina.py`, `serper.py`, `exa.py`, `tavily.py`, `firecrawl.py`, `mistral.py` | Each duplicates sync+async bodies verbatim; extract shared core taking a client factory (~halves each file) |
| D3 | Py | `utils/http.py:76-153` vs `utils/async_http.py:62-137` | Dedupe `is_safe_url`/`_normalize_host`/`_getaddrinfo_cached` (~80 lines each); async `is_safe_url` is pure-sync |
| D4 | Py | `_url_resolve.py:178-197` vs `_url_resolve_async.py:129-148` | Dedupe verbatim `_url_result_builder` |
| D5 | Py | `_url_resolve_async.py:79-105` | Async parity: add `llms_txt`, wire `docling`/`ocr` async file-type shortcuts, add `resolve_query_stream_async`, store final best-free result in semantic cache (sync misses it), port `EXCELLENT_QUALITY_THRESHOLD` early-exit, enforce budget mid-flight |
| D6 | Py | `providers/tavily.py:80`, `exa.py:98,194`, `firecrawl.py:40,90`, `mistral.py:182,260` | Cache SDK clients per API key (thread-safe) instead of per-call construction |
| D7 | Py | `utils/fetch.py:20-25` | Drop HEAD pre-flight in `fetch_url_content` (double round-trip; `response.url` suffices) |
| D8 | Py | `utils/cache.py:124-129`, `32-70`, `105-108` | Remove `_get_cache_proxy` (per-op import of `scripts.resolve`; never assigned) and dead `coalesce_request` (or wire it in for thundering-herd) |
| D9 | Py | `utils/async_http.py:28,31-51` | Actually acquire `_client_lock` (AsyncClient leak race) |
| D10 | Py | `semantic_cache.py:174-179, 350-368, 315-322` | Add TTL/max-age invalidation (timestamp stored, never read); fix similarity-dedup JSON key-ordering |
| D11 | Py | `visual_resolver.py:193-208` | Batch frame encoding (`encode` accepts a list) |
| D12 | Py | `models.py:35-51`, `utils/urls.py:118-137`, `cache_negative.py:58-71`, `constants.py:12-13,73`, `resolve.py:90-129` | Remove dead code: `Profile.is_provider_allowed`/`max_hops`, `score_result`, `should_skip_from_bot_challenge_cache` (cache never populated), `ENABLE_SEMANTIC_CACHE`, empty TYPE_CHECKING, re-export bloat; fix `found_final` unreachable branch (`_cascade.py:92,161`) |
| D13 | Py | `doc_validator.py:336-343`, `_routing_utils.py` | Remove `fix_rust_architecture` stub (always returns 0); fold 17-line `_routing_utils` into `routing_memory` |
| D14 | Py | `scripts/cli.py:35-50,74-82` | Dedupe async/sync dispatch if/elif chain |
| D15 | Rust | `cli/src/resolver/url.rs` (532) + `resolver/query/mod.rs` (504) | Extract shared cascade engine (param'd over async attempt fn) — kills ~300 duplicated lines, fixes 2 file-size violations, removes subtle drift (min_free_quality override) |
| D16 | Rust | `cli/src/providers/direct_fetch.rs` (612) | Move `decode_entities` + `strip_html`/`StriperState` to `providers/html_strip.rs` |
| D17 | Rust | `cli/src/semantic_cache/ops.rs` (521) | Split `normalize_text`/`encode_query` into own module |
| D18 | Rust | `cli/src/types.rs:189-199`, `output.rs:50-76`, `semantic_cache/mod.rs:31-42`, `routing.rs:9,59` | Remove dead code: `is_fast()`, `TextOutput`, `CacheEntry`, `PreflightResult.confidence`, `PlannedProvider.skip_reason` |
| D19 | Rust | `resolver/mod.rs:33` + `synthesis.rs:24` | Unify duplicate link-regex statics |
| D20 | Rust | `cli/Cargo.toml` | Drop unused deps: `sha2`, dev `mockall`, clap `env` feature, `futures` (JoinSet), `once_cell` (LazyLock); trim tokio features; `#[command(version)]` instead of hardcoded "0.3.10" (`cli.rs:11`) |
| D21 | Rust | `providers/serper.rs:47-82`, `.do_wdr_state.toml` | Move CWD-relative state to `$XDG_STATE_HOME/do-wdr/`; wrap `save_credits` sync IO in `spawn_blocking` |
| D22 | Rust | `main.rs:197,202` | Config loaded twice per invocation |
| D23 | Rust | `url.rs:337`, `query/mod.rs:330`, `output.rs:9-16` | `validate_links` blocks response on up to 10 HEADs but `validated_links` isn't in JSON output — make opt-in (`--validate-links`) or expose |
| D24 | Rust | `main.rs:156-161` | `--metrics-json` before content on stdout breaks parsing — send to stderr or `--metrics-file` |
| D25 | Rust | `url.rs:233-244` | Skips recorded as `success:false, latency:0` skew failure-rate metrics — record as skip |
| D26 | Rust | `providers/mistral_websearch.rs:122-128` | Fabricated pseudo-URL treated as real source by bias/caching — mark synthetic |
| D27 | Rust | `providers/docling.rs:29,42`, `ocr.rs` | `is_available()` hardcoded true burns attempts when tools missing — actually probe |
| D28 | Rust | stray `cli/text` artifact | Delete (accidental `> text` redirect) |
| D29 | Web | `web/app/page.tsx` (514 — **violates 500 limit**) | Decompose god component: extract reducer/context + hooks (prewarm, history, keys); MainContent takes ~30 props incl. unused setters |
| D30 | Web | `lib/results.ts:45-47` | Remove `nextjs.org` special case from generic canonicalizer |
| D31 | Web | `lib/records.ts:149-182` | Browser `fetch("/api/history")` inside server lib — split client/server modules |
| D32 | Web | `page.tsx:155-167` | Full result markdown written to localStorage on every query keystroke — debounce |
| D33 | Web | `app/api/history/route.ts:27-31` vs `ui-state/route.ts:24-33` | Unify session identity (httpOnly cookie vs sha256(IP+UA)) |
| D34 | Web | `middleware.ts:11-17` | Matcher runs on all API traffic but only acts on POST /api/resolve — narrow |
| D35 | Web | `app/api/history`, `app/api/records` POST | Add zod validation + size caps (unbounded `result` string = memory-flood vector); validate provider ids against known list (currently silent null → "No results") |
| D36 | Web | `lib/validation.ts:225` vs `Sidebar.tsx:153-157` | maxChars bounds mismatch (zod 100–50000 vs slider 1000–32000) |
| D37 | Web | `lib/validation.ts:264` | `validateResolveRequest` swallows zod detail — surface message |
| D38 | Web | `next.config.mjs:14-37` vs `vercel.json:10-20` | Duplicate security-header config — one source; drop deprecated `X-XSS-Protection` |
| D39 | Web | `lib/resolvers/index.ts:58` vs `routing.ts:70` | Dedupe disagreeing paid-provider sets; remove unused export |
| D40 | Web | `lib/errors.ts` | Wire `classifyError`/`formatErrorForDisplay` user hints into `page.tsx:308-311` (currently raw `${provider}: ${error}`) |
| D41 | Web | `app/help/page.tsx:53-59`, `web/README.md` | Fix cascade drift (Serper missing), "Next.js 15" → 16, phantom word count |
| D42 | Web | `app/api/analytics/route.ts:36-39` | `cacheHitRate` computed as `score>=0.8` ratio — store real hit info or rename |
| D43 | Web | `app/page.tsx:170-209` | Silent prewarm fires 5 POSTs on mount consuming rate budget — gate behind setting / batch |
| D44 | Web | `eslint.config.mjs:35-37` | Re-enable `no-unused-vars`/`no-explicit-any`; delete accumulated dead exports |
| D45 | Web | `app/css.d.ts`, `.ignore` | Remove vestigial files |
| D46 | Web | `playwright.config.ts:11`, `package.json:17` | E2E defaults to **production** URL — default to local; prevent accidental prod mutation |

## Wave E — Testing & CI

| ID | Area | Action |
|----|------|--------|
| E1 | Py | Unit tests for `_cascade_async.py` (~200 lines, zero direct tests): parallel launch, 0.85 early-exit, paid-skip gate, exception→breaker, cancellation, best-free fallback |
| E2 | Py | Make conftest's `plan_provider_order` override opt-in (marker/fixture); real routing (adaptive reorder, tier sort, probabilistic skip) is dead code in every resolve test |
| E3 | CI | `--cov-fail-under=75` (ratchet to 85) + Codecov upload + PR comments; coverage.xml already generated but gates nothing |
| E4 | CI | Weekly perf-regression workflow: `cargo bench` + `pytest -m benchmark`, fail on >20% regression vs baseline — codifies documented <200ms / ≥0.85 semantic-health thresholds (currently hand-run) |
| E5 | CI | `RUST_TEST_THREADS=1` (libsql `Once` poisoning) via `cli/.cargo/config.toml` — currently missing from ci.yml/release.yml |
| E6 | CI | Release smoke test: on publish, download each asset, run `do-wdr --help` + no-key resolve on all 3 OSes |
| E7 | CI | Fix live-test vacuous passes: fail job when expected secret absent (typo'd name = green CI) |
| E8 | CI | Add concurrency group to `ci-integration.yml`; split 3× Python matrix (lint once, full tests on 3.12) |
| E9 | CI | Run `dark-mode` Playwright project + web vitest coverage in ci-ui.yml |
| E10 | Rust | Tests for untested modules: `bias_scorer`, `circuit_breaker`, `negative_cache`, `routing_memory`, `routing`, `startup`, `link_validator`, `semantic_cache/ops+synthesis`, `config/defaults+parsing`, `docling`, `ocr` |
| E11 | Rust | Replace `tests/quality_gate.rs:5-47` re-implementation with tests against the real gate function |
| E12 | Web | Dedupe `tests/api/route.test.ts` local helper re-implementations (own `isUrl`) — import production code |
| E13 | Web | Extract shared `mockAppState` helper (duplicated in 5 e2e specs); `test.skip` instead of silent `return` |
| E14 | Gate | `scripts/quality_gate.sh`: enforce markdownlint (remove `\|\| true`); run web unit tests; extend 500-line check beyond `scripts/*.py` to `web/` + `cli/src/` |
| E15 | Ops | Serper 403 root cause: add key-expiry detection to `monitor_providers.py` (3 consecutive monthly auto-deprioritizations = symptom-only treatment) |
| E16 | Py | Unify nested-loop workarounds on shared thread pool (`_cascade.py:178-184`, `utils/http.py:255-261` spawn fresh executors per call); route `asyncio.to_thread` through `get_shared_pool()` |

## Wave F — Polish & Docs

| ID | Area | Action |
|----|------|--------|
| F1 | Web a11y | Result-card headings (URL-titled cards aren't headings); move `aria-live` off Copy button to status region; `aria-busy` on loading region; visible (non-tooltip) provider key hints; replace full-screen backdrop `<button>`; add `prefers-reduced-motion` + non-pulsing loader |
| F2 | Web | i18n groundwork (message catalog); `lang` handling |
| F3 | Web | Empty-state example queries; paste-detect auto-submit; domain autocomplete (`getTopDomains` exists) |
| F4 | Docs | Fix drift: `cli/ui/AGENTS.md` references nonexistent `deploy-ui.yml`/`e2e-release` job; `agents-docs/DEVELOPMENT.md` says Python 3.10+/Node 18+ (actual ≥3.11/22); AGENTS.md Playwright project count; plans/013 Wave-5 PENDING vs README "All DONE" |
| F5 | Py | `monitor_providers.py:31-80` regex-rewrites `routing.py` source + auto-opens issues — brittle; make manual-review PR |
| F6 | Py | Consistent provider imports (`duckduckgo.py:22` via shim vs `jina.py:26` direct — import-cycle risk) |
| F7 | Py | `scripts/cli.py:17` env-ordering fragility (setdefault after constants import) — document or restructure |
| F8 | Py | Docling/OCR shortcuts (`_url_resolve.py:128-139`) run outside cascade — no negative cache/breaker/budget/memory/semantic-store |
| F9 | Py | Bounded retry/backoff for idempotent provider GETs (currently single-attempt; AGENTS.md advertises `DEFAULT_MAX_RETRIES=3` but neither runtime has retries — Rust parity gap too, see `shared_client.rs` comment) |

## File-Size Violations (repo limit: 500)

| File | Lines | Fix |
|------|------:|-----|
| `cli/src/providers/direct_fetch.rs` | 612 | D16 |
| `cli/src/resolver/url.rs` | 532 | D15 |
| `web/app/page.tsx` | 514 | D29 |
| `cli/src/semantic_cache/ops.rs` | 521 | D17 |
| `cli/src/resolver/query/mod.rs` | 504 | D15 |
| `tests/test_resolve.py` (test, 2200+) | — | still deferred per Plan 21 B3 |

## Suggested Order

1. **Wave A** (security + correctness, all small diffs) — one PR each for A1–A11
2. **Wave B** — behavioral fixes with test coverage
3. **Wave E1–E7** — lock in behavior before refactors
4. **Wave D** — DRY/file-size (D15, D29 biggest)
5. **Wave C** — features build on D's clean foundation
6. **Wave F** — polish

## Verification

1. `pytest -m "not live and not benchmark"` → green incl. new `_cascade_async` tests
2. `cd cli && cargo test` (with `RUST_TEST_THREADS=1`) → green
3. `cd web && npm test && npx playwright test` (local baseURL) → green
4. `./scripts/quality_gate.sh` → exit 0 with markdownlint **enforced**
5. `wc -l` on all five violating files → ≤ 500
6. Standalone skill smoke: `cd .agents/skills/do-web-doc-resolver && python -m scripts.resolve "https://example.com"` works
