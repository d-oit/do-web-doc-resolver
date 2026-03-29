# Codebase Analysis — 2026-03-29

**Status**: Active findings with prioritized action items
**Scope**: CLI (Rust), Web (Next.js), Python skill, CI/CD, testing

---

## Executive Summary

The codebase is in good shape: CI is green, web builds cleanly, CLI passes clippy/tests (default features), and most critical bugs documented earlier have been fixed. However, several **gaps between plans and implementation** remain, plus new issues discovered today.

| Category | Critical | High | Medium | Low |
|----------|----------|------|--------|-----|
| Build/Compile | 1 | 0 | 0 | 0 |
| Code Quality | 0 | 2 | 3 | 2 |
| Missing Implementation | 0 | 3 | 4 | 2 |
| Testing | 0 | 1 | 2 | 1 |
| Security | 0 | 0 | 1 | 0 |

---

## CRITICAL — Build Failures

### C-1: `semantic-cache` feature fails to compile ❌

**Severity**: CRITICAL
**File**: `cli/src/error.rs`, `cli/src/semantic_cache.rs`
**Evidence**: `cargo test --features semantic-cache` → 14 compile errors

**Root cause**: `ResolverError` does not implement `Into<chaotic_semantic_memory::MemoryError>`, and the semantic_cache module uses `?` operator on MemoryError-returning functions within functions that return `Result<_, ResolverError>`.

**Fix**: Add `From<chaotic_semantic_memory::MemoryError>` impl for `ResolverError`:

```rust
// In cli/src/error.rs, add:
#[cfg(feature = "semantic-cache")]
impl From<chaotic_semantic_memory::MemoryError> for ResolverError {
    fn from(err: chaotic_semantic_memory::MemoryError) -> Self {
        ResolverError::Cache(err.to_string())
    }
}
```

**Status**: Blocks Phase 2 of IMPLEMENTATION_PLAN.md (semantic cache testing)
**Plan ref**: IMPLEMENTATION_PLAN.md Phase 2

---

## HIGH — Code Quality

### H-1: `cli/src/resolver.rs` exceeds 500-line limit (990 lines)

**Severity**: HIGH
**File**: `cli/src/resolver.rs` — 990 lines vs 500-line max
**Plan ref**: IMPLEMENTATION_PLAN.md Phase 6.1

Planned split into `resolver/mod.rs`, `cascade.rs`, `url_resolver.rs`, `query_resolver.rs` was never done.

### H-2: `web/app/api/resolve/route.ts` exceeds 500-line limit (663 lines)

**Severity**: HIGH
**File**: `web/app/api/resolve/route.ts` — 663 lines vs 500-line max
**Plan ref**: ADDITIONAL_IMPROVEMENTS_PLAN.md §1.2.1

Provider functions should be extracted to `web/lib/providers/` (directory does not exist yet).

### H-3: Duplicate error variants in `cli/src/error.rs`

**Severity**: HIGH
**File**: `cli/src/error.rs`

`ResolverError` has duplicate semantic variants:
- `Network` + `NetworkError`
- `Auth` + `AuthError`
- `Quota` + `QuotaError`
- `NotFound` + `NotFoundError`
- `Parse` + `ParseError`
- `Unknown` + `UnknownError`

All 6 duplicates have `#[allow(dead_code)]`. This is tech debt that makes matching error types confusing. Should consolidate to one variant per concept.

---

## HIGH — Missing Implementation

### H-4: Skill `__main__.py` uses wrong import path

**Severity**: HIGH
**File**: `.agents/skills/do-web-doc-resolver/__main__.py`
**Plan ref**: IMPLEMENTATION_PLAN.md Phase 1.1

Still uses `from scripts.resolve import main` (absolute) instead of `from .scripts.resolve import main` (relative). The skill cannot run standalone as a package.

### H-5: Skill test coverage is minimal (32 lines)

**Severity**: HIGH
**File**: `.agents/skills/do-web-doc-resolver/tests/test_resolve.py` — 32 lines
**Plan ref**: IMPLEMENTATION_PLAN.md Phases 1.2–1.3

Planned 200+ lines with files for providers, quality, routing, circuit breaker. None created:
- ❌ `tests/test_providers.py`
- ❌ `tests/test_quality.py`
- ❌ `tests/test_routing.py`
- ❌ `tests/test_circuit_breaker.py`

### H-6: CLI semantic cache integration tests empty (0 tests without feature)

**Severity**: HIGH
**File**: `cli/tests/semantic_cache.rs`
**Plan ref**: IMPLEMENTATION_PLAN.md Phase 2

Tests exist (4 async tests) but all behind `#[cfg(feature = "semantic-cache")]` which doesn't compile (C-1). CI job for semantic cache tests never added to `.github/workflows/ci.yml`.

---

## MEDIUM — Missing Implementation

### M-1: No `web/lib/providers/` extraction

**Plan ref**: ADDITIONAL_IMPROVEMENTS_PLAN.md §1.2.1
Directory does not exist. All provider logic remains in the monolithic route.ts.

### M-2: No request deduplication

**Plan ref**: ADDITIONAL_IMPROVEMENTS_PLAN.md §1.2.2
`web/lib/request-dedup.ts` — not created.

### M-3: Missing web UI components from plan

**Plan ref**: ADDITIONAL_IMPROVEMENTS_PLAN.md
Not created:
- ❌ `web/app/components/ErrorBoundary.tsx`
- ❌ `web/app/components/Toast.tsx`
- ❌ `web/app/components/SkeletonLoader.tsx`
- ❌ `web/app/components/ProgressIndicator.tsx`
- ❌ `web/app/components/ShortcutsModal.tsx`
- ❌ `web/lib/sanitize.ts` (input sanitization with DOMPurify)
- ❌ `web/lib/encryption.ts`
- ❌ `web/lib/monitoring.ts`
- ❌ `web/lib/logger.ts` (structured logging)

### M-4: `scripts/resolve.py` at 544 lines — near 500-line limit

**File**: `scripts/resolve.py`
Should be monitored; any additions will push it over the 500-line limit.

### M-5: BUG-6 `--synthesize` still broken

**File**: `cli/src/synthesis.rs`
**Plan ref**: BUGS_AND_ISSUES.md BUG-6
Depends on Mistral API key working. Even with valid key, format validation may fail. No tests exist for synthesis module.

---

## MEDIUM — Testing Gaps

### M-6: Python tests won't run (pytest not installed)

**Evidence**: `python -m pytest` → `No module named pytest`
`requirements.txt` likely lists pytest but the venv is not set up.

### M-7: No E2E tests for history feature

**Plan ref**: ADDITIONAL_IMPROVEMENTS_PLAN.md §6.2.1
`web/tests/e2e/history.spec.ts` — not created. History feature shipped (PR #148) but has no E2E coverage.

### M-8: No integration tests for web API

**Plan ref**: ADDITIONAL_IMPROVEMENTS_PLAN.md §6.1.2
`web/tests/integration/resolve.test.ts` — not created.

---

## MEDIUM — Security

### M-9: Validation exists but no DOMPurify sanitization

**Plan ref**: ADDITIONAL_IMPROVEMENTS_PLAN.md §2.1.1
`web/lib/validation.ts` exists with Zod schemas (good), but the deeper `sanitize.ts` with DOMPurify and SSRF IP blocking was not created.

---

## LOW — Code Quality

### L-1: No `React.memo` / `useCallback` optimization

**Plan ref**: ADDITIONAL_IMPROVEMENTS_PLAN.md §1.3
`web/app/page.tsx` doesn't use `React.memo` or `useCallback`.

### L-2: No API documentation

**Plan ref**: ADDITIONAL_IMPROVEMENTS_PLAN.md §8.1
`web/docs/API.md` — not created.

### L-3: Skill SKILL.md frontmatter incomplete

**Plan ref**: IMPLEMENTATION_PLAN.md Phase 6.2
6 skills missing license/compatibility/metadata fields.

### L-4: No performance monitoring

**Plan ref**: ADDITIONAL_IMPROVEMENTS_PLAN.md §7.1
`web/lib/monitoring.ts` — not created.

---

## What's Working Well ✅

| Area | Status |
|------|--------|
| CLI default build | ✅ `cargo clippy` clean, all tests pass |
| Web build | ✅ Next.js builds successfully, 11 routes |
| CI pipeline | ✅ All checks green on main |
| Web unit tests | ✅ 80 tests across validation, rate-limit, cache, records, routing, providers |
| Web E2E tests | ✅ 55/60 pass (5 skipped for API keys) |
| CLI bug fixes | ✅ exa_mcp, quality gate, duckduckgo all fixed |
| Provider cascade | ✅ Both URL and query cascades working |
| Input validation | ✅ Zod schemas in place |
| Rate limiting | ✅ Module implemented |
| LRU cache eviction | ✅ Implemented with max 1000 entries |
| Records FIFO eviction | ✅ Implemented with max 500 entries |
| Accessibility | ✅ ARIA labels, skip-to-content, keyboard shortcuts |
| History feature | ✅ CRUD API with search/load/delete |

---

## Recommended Action Priority

### Immediate (blocks CI/features)
1. **C-1**: Fix semantic-cache feature compilation
2. **H-4**: Fix skill `__main__.py` import path

### Short-term (code quality debt)
3. **H-1**: Split `resolver.rs` (990 → <500 lines)
4. **H-2**: Extract providers from `route.ts` (663 → <500 lines)
5. **H-3**: Consolidate duplicate error variants

### Medium-term (complete planned features)
6. **H-5/H-6**: Expand skill tests + fix semantic cache CI
7. **M-5**: Test and fix `--synthesize` mode
8. **M-7/M-8**: Add missing E2E and integration tests

### Low priority (nice to have)
9. **M-3**: Missing UI components (ErrorBoundary, Toast, etc.)
10. **L-2**: API documentation
11. **L-3**: Skill frontmatter cleanup

---

## Plans File Status

| Plan File | Status | Notes |
|-----------|--------|-------|
| IMPLEMENTATION_PLAN.md | ⚠️ Outdated | Shows phases 1-5 "complete" but Phase 1 import fix (H-4) and Phase 2 compile (C-1) remain broken |
| ADDITIONAL_IMPROVEMENTS_PLAN.md | ⚠️ Partially done | Security/perf done; components, logging, monitoring not started |
| BUGS_AND_ISSUES.md | ✅ Accurate | BUG-6 still valid; others correctly documented |
| PROGRESS_UPDATE.md | ⚠️ Outdated | Shows everything "complete" but misses remaining gaps |
| UI_ENHANCEMENTS_PLAN.md | ✅ Complete | All planned UI work shipped |
| COMPREHENSIVE_VALIDATION_PROGRESS.md | ✅ Accurate | Final validation matches reality |

---

*Analysis performed: 2026-03-29*
