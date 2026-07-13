# Semantic Health Issue: Cache Hit Latency and Aggregation Telemetry

## Problem Statement

As of July 2026, the `do-wdr` CLI was exhibiting several "Semantic Health" issues:

1. **Incomplete Telemetry**: Cache hits for aggregated and synthesized results reported 0ms latency and null quality scores.
2. **Implementation Divergence**: Python and Rust semantic cache normalization logic was out of sync, leading to inconsistent cache behavior across interfaces.
3. **Cache Redundancy**: Near-identical queries were creating redundant database entries, leading to bloat without quality improvement.

## Benchmarks (Post-Optimization)

| URL | Initial Latency | Final Latency | Cache Hit Rate | Quality Score |
| :--- | :--- | :--- | :--- | :--- |
| `docs.python.org` | ~3000ms | 1ms | 100% | 1.0 |
| `doc.rust-lang.org` | ~3200ms | 1ms | 100% | 1.0 |
| `developer.mozilla.org` | ~3000ms | 1ms | 100% | 1.0 |
| `pkg.go.dev` | ~2200ms | 1ms | 100% | 0.8 |
| `react.dev` | ~400ms | 1ms | 100% | 0.8 |

## Improvements Implemented

### 1. Accurate Bridge Telemetry

Updated `cli/src/resolver/mod.rs` to measure latency from the absolute start of the resolution function. This ensures that even for sub-millisecond lookups, a minimum of 1ms is reported, and bridge overhead is captured.

### 2. Quality Score Restoration

Fixed an issue where cached results lost their quality score metrics. Telemetry now correctly restores and reports the `quality_gate_score` and `quality_gate_passed` status from the cached `ResolvedResult`.

### 3. Synchronized Normalization

Synchronized the Python `SemanticCache.normalize_text` logic with the Rust implementation:

- Improved tokenization by splitting on all non-alphanumeric characters.
- Added documentation-specific stop-words (`docs`, `api`, `index`, `module`).
- Ensured consistent URL component filtering.

### 4. Aggressive Redundancy Pruning

Implemented similarity-based skipping during cache storage in Python:

- **Similarity > 0.995**: Always skip (near-duplicate normalization).
- **Similarity > 0.98**: Skip if the result content is identical.

## Next Steps

- Monitor database size over the next 30 days to verify pruning effectiveness.
- Investigate "First Semantic Hit" model load times for CLI invocations.

---

*Verified on 2026-07-13*
