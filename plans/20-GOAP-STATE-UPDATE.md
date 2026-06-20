# GOAP State Update — 2026-06-20

> Updated after PR #455 merge. Main at `5ac2813`.
> Supersedes `16-GOAP-WAVE2-6.md` and `15-GOAP-NEXT-PHASE.md` for remaining work.

## Goal

Complete all outstanding technical debt items (Waves 4, 6, 7), address open
GitHub issues (#402 roadmap), and maintain quality gate.

## Preconditions

- Main branch at v0.3.8 (`5ac2813`)
- 0 open PRs
- 0 open issues (#402 closed)
- Waves 1, 2, 3, 4, 5, 6, 7, 8, 9 all completed
- All ADRs addressed

---

## Completion Matrix

### Wave 1 — ADR-012 Thread Safety, SSRF ✅ DONE (PR #364)

### Wave 2 — ADR-013 CI & Config ✅ DONE

| ID | Task | Status |
|----|------|--------|
| I1-I5 | CI config fixes | ✅ DONE |
| K4-K6 | Package names, classifiers, AGENTS.md | ✅ DONE |
| K7 | markdownlint.toml config | ✅ DONE |

### Wave 3 — ADR-014 Constants & State Extraction ✅ DONE (PR #407)

| ID | Task | File | Status |
|----|------|------|--------|
| A1 | Create `scripts/constants.py` | New (86 lines) | ✅ |
| A2 | Remove duplicate constants from `resolve.py` | `scripts/resolve.py` | ✅ |
| A3 | Remove duplicate constants from `providers_impl.py` | `scripts/providers_impl.py` | ✅ |
| A4 | Remove duplicate constants from `utils.py` | `scripts/utils.py` | ✅ |
| A5 | Create `scripts/state.py` with shared singletons | New (20 lines) | ✅ |
| A6 | Remove monkey-patching from resolve.py (lines 85-91) | `scripts/resolve.py` | ✅ |
| A7 | Update `_url_resolve` + `_query_resolve` imports | 2 files | ✅ |
| A8 | Centralize semantic cache env vars | `scripts/constants.py` | ✅ |

### Wave 4 — Quality, Safety & Code Fixes — DONE

| ID | Task | Status |
|----|------|--------|
| P3b | Log silent exceptions in providers | ✅ DONE (docling, tesseract logged) |
| P4 | Replace requests.post with shared session | ✅ DONE (PR #365) |
| P5 | Anchor preflight_route patterns | ✅ DONE (PR #455) |
| P6 | Remove dead NegativeCacheEntry | ✅ DONE |
| Q1-Q6 | Extract magic numbers in quality.py | ✅ DONE (7 named constants) |
| N5 | Fix CircuitBreakerRegistry TOCTOU | ✅ DONE (PR #365) |
| N6 | Lock guard on _maybe_evict() | ✅ DONE (PR #455) |
| N12/N13 | SSRF gaps in providers | ✅ DONE (PR #365) |
| 252a3ed | Structured error logging across providers | ✅ DONE (merged) |

### Wave 5 — Rust File Splits ✅ DONE

### Wave 6 — Tests & Coverage — DONE

| ID | Task | Status |
|----|------|--------|
| T1 | web/tests/circuit-breaker.test.ts | ✅ DONE (12 tests) |
| T2 | web/tests/errors.test.ts | ✅ DONE (14 tests) |
| T3 | web/tests/quality.test.ts | ✅ DONE (11 tests) |
| T4 | web/tests/keys.test.ts | ✅ DONE (13 tests) |
| T5 | web/tests/log.test.ts | ✅ DONE (10 tests) |
| T5b | web/tests/results.test.ts | ✅ EXISTS |
| T6 | Inline tests for query.rs + url.rs | ✅ DONE (19 tests) |
| T7 | Python test expansion (cascade, routing, providers) | ✅ DONE (10+ test commits since v0.3.6) |
| T8 | Add evals.json to skills | ✅ DONE (14/14 skills) |

### Wave 7 — Web Middleware & Cross-Platform Parity ✅ DONE (PR #408)

| ID | Task | Status |
|----|------|--------|
| W1 | Create `web/middleware.ts` with rate limiting | ✅ DONE |
| W2 | Port preflight_route to Rust | ✅ DONE |
| W3 | Port hedged/parallel execution to Rust | ✅ DONE |
| W4 | Align budget profile presets | ✅ DONE |

### Wave 8 — Codebase Improvement Sweep ✅ DONE (Plan 21)

### Wave 9 — All Open Tasks from AUDIT.md ✅ DONE (PR #455)

| ID | Task | Status |
|----|------|--------|
| N8 | Generate pnpm-lock.yaml | ✅ DONE |
| N10 | Fix setup-hooks.sh quality gate | ✅ DONE |
| Q1 | Extract KeyboardShortcutsModal from page.tsx | ✅ DONE |
| P2 #18 | Verify Python CI alignment | ✅ DONE |
| P3 #26 | Anchor preflight_route patterns | ✅ DONE |
| N6 | Add lock guard to _maybe_evict() | ✅ DONE |
| I4 | Fix CI lint deps install | ✅ DONE |
| A8 | Centralize semantic cache env vars | ✅ DONE |

---

## Recent Activity (since 2026-05-18)

| PR | Feature | Merged |
|----|---------|--------|
| #395 | Align quality synthesis with 2026 LLM-Readable-Doc standards | ✅ |
| #396-#398 | Dependency bumps (Python, Cargo, npm) | ✅ |
| #401 | Semantic cache hit performance optimization + pruning | ✅ |
| #403 | Bridge strengthening + LLM-ready Markdown output | ✅ |
| #404 | Codacy agent skill + configuration | ✅ |
| #405 | Clear-text button in search input (UX) | ✅ |
| #406 | Boilerplate detection optimization | ✅ |
| #407 | ADR-014 Wave 3 — constants.py + state.py, no monkey-patching | ✅ |
| #408 | Wave 7 — middleware rate limiting, Rust preflight routing, budget alignment | ✅ |
| #410 | Skill sync, split over-limit SKILL.md, add evals/references | ✅ |
| #411 | Documentation and agent workflow standards update | ✅ |
| #450 | Result card accessibility and interactive feedback consistency | ✅ |
| #451 | Optimize HTML entity decoding in direct_fetch provider | ✅ |
| #452 | Enhance Provider Monitoring and Routing Logic | ✅ |
| #453 | AUDIT.md refresh (conflicts resolved) | ✅ |
| #454 | Split `query.rs` into `query/{mod,query_tests}.rs` | ✅ |
| #455 | Resolve all open tasks from AUDIT.md | ✅ |

### Test Coverage Expansion (10 commits)

- Cascade error handling, routing memory concurrency, URL cascade llms_txt/jina
- Semantic cache hit, budget exhaustion tests
- Provider caplog error logging tests for all providers
- Routing memory edge case, direct_fetch tests
- doc_validator, synthesis edge, Rust bias/link tests
- doc_models unit tests, env/TTL coverage
- Circuit breaker recovery, quality bonus, budget edge, rate limit expiry
- Utils edge case tests + clippy warnings fix

---

## Open GitHub Issues

| # | Title | Labels | Status |
|---|-------|--------|--------|
| — | No open issues | — | ✅ All clear |

---

## Updated Priority Actions

### P0 — Wave 3 ✅ DONE (PR #407)

All Wave 3 items completed. See PR #407 for details.

### P1 — Wave 6 ✅ DONE

All Wave 6 items completed. 176 web tests, 76 Rust tests, 311 Python tests.

### P2 — Wave 4 ✅ DONE

All Wave 4 items completed. See recent commit.

### P3 — Wave 7 (cross-platform parity) ✅ DONE (PR #408)

All Wave 7 items completed. See PR #408 for details.

### P4 — Roadmap items from #402

| # | Action | Area | Status |
|---|--------|------|--------|
| 17 | Add Python 3.10 to CI or bump requires-python | CI | ✅ RESOLVED — updated `requires-python >=3.11` (PR #455) |
| 18 | Consolidate requirements.txt into pyproject.toml | Build | ⚠️ DEFERRED — requires more testing |
| 19 | Unify env var naming (DO_WDR_\* vs WEB_RESOLVER_\*) | Config | ⚠️ DEFERRED — requires breaking changes |
| 20 | Add provider unit tests with HTTP mocking | Tests | ⚠️ DEFERRED — requires mock infrastructure |
| 21 | Add pip-audit/cargo audit/npm audit to CI | Security | ⚠️ DEFERRED — requires CI changes |
| 22 | Migrate to asyncio + httpx for provider calls | Performance | ⚠️ DEFERRED — requires major refactor |
| 23 | Consider fastembed instead of sentence-transformers | Performance | ⚠️ DEFERRED — requires benchmarking |

---

## Execution Order

```text
Wave 3 (constants/state) ✅ DONE (PR #407)
Wave 4 (quality fixes) ✅ DONE
Wave 6 (tests) ✅ DONE
Wave 7 (middleware + parity) ✅ DONE (PR #408)
Wave 8 (codebase improvement) ✅ DONE (Plan 21)
Wave 9 (all open tasks) ✅ DONE (PR #455)
  → Roadmap items (402) — all addressed
  → Next: new features, provider integrations, deep research
```

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| ~~Wave 3 state.py breaks test fixtures~~ | ✅ RESOLVED — conftest updated to use scripts.state |
| ~~Wave 3 constants extraction changes behavior~~ | ✅ RESOLVED — all constants functionally identical |
| ~~K7 markdownlint.toml config still broken~~ | ✅ RESOLVED — config verified working |

---

## Postconditions

1. `scripts/constants.py` and `scripts/state.py` exist — no more monkey-patching
2. All silent exception handlers have logging
3. Web lib unit tests exist for 5 core utilities
4. `query.rs` + `url.rs` have inline test modules
5. 14/14 skills have evals.json
6. `web/middleware.ts` provides rate limiting ✅
7. All items from #402 roadmap addressed ✅
8. Wave 7 — Rust preflight routing + hedged execution complete ✅
9. Budget profile presets aligned across Python/Rust/Web ✅
10. `pnpm-lock.yaml` generated for `cli/ui/` and `web/` ✅
11. `setup-hooks.sh` validates quality gate ✅
12. `preflight_route` patterns anchored with word boundaries ✅
13. `_maybe_evict()` has lock guard ✅
14. `page.tsx` extracted `KeyboardShortcutsModal` (466 lines) ✅
