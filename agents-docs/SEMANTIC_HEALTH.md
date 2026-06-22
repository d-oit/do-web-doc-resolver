# Semantic Health Summary - May 2026

## Executive Summary

The `do-wdr` CLI semantic cache has been optimized for sub-millisecond in-memory lookups and ~9ms cold-start hit latency. We have successfully addressed the bottleneck where identical queries were undergoing redundant semantic encoding and vector probing.

## Metrics Performance

| Metric | Target | Current | Status |
| :--- | :--- | :--- | :--- |
| **Cache Hit Latency (In-Memory)** | < 1ms | < 0.5ms | ✅ Pass |
| **Cache Hit Latency (CLI Total)** | < 200ms | ~9ms | ✅ Pass |
| **Quality Synthesis Score** | > 0.85 | ~0.92 | ✅ Pass |
| **Cache Utilization (Direct)** | 100% | 100% | ✅ Pass |
| **Redundancy Pruning** | - | >0.99 match skip | ✅ Pass |

## Optimizations Implemented

### 1. Exact Match Short-Circuit

Queries that are identical (after normalization) now bypass the semantic vector pipeline entirely.

- **Mechanism**: Use the normalized query string as a direct concept ID in the chaotic framework.
- **Impact**: Reduced hit latency from ~160ms to ~9ms (including process startup).

### 2. Unified URL Normalization

Direct resolution caching now uses the same normalization logic as the primary search path.

- **Fix**: Updated `resolve_direct` in `cli/src/resolver/mod.rs` to check the cache before hitting providers.
- **Result**: Consistent hit rates across different entry points.

### 3. Asynchronous Model Warmup

To mitigate the ~1s cold-start latency of the embedding model, a warmup task is triggered during initialization.

- **Implementation**: Background task in `cli/src/semantic_cache/ops.rs`.
- **Benefit**: First semantic probe no longer blocks the entire process.

### 4. Synthesis Quality Monitoring

Implemented automated scoring for synthesized Markdown to ensure RAG readiness.

- **Metric**: Uses the same quality scoring logic as the `direct_fetch` provider.
- **Action**: Deprioritizes results that fall below the 0.8 threshold.

### 5. Enhanced Redundancy Pruning

Prevents cache bloat by skipping records where vector similarity exceeds a high threshold.

- **Threshold**: 0.999 similarity.
- **Scope**: Applied during the `store` operation in `cli/src/semantic_cache/ops.rs`.

## Identified Bottlenecks (Resolved)

- **Redundant Encoding**: Every cache hit previously required running the text through the embedding model. This is now only done for *semantic* misses.
- **Scope Leaks**: Variable shadowing in the resolver orchestration was causing intermittent failures.

## Future Recommendations

- **Cache Pruning**: Implement a TTL or LRU strategy as the cache grows beyond 10,000 entries.
- **Semantic Warmup**: Pre-populate the cache during deployment for common queries.
