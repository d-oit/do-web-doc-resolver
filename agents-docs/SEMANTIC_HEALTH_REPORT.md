# Semantic Health Report - June 2026

This report summarizes the performance and efficiency of the `do-wdr` semantic cache and resolution cascade against 5 standard documentation URLs.

## Tested URLs

1.  **Python**: [https://docs.python.org/3/](https://docs.python.org/3/)
2.  **Rust**: [https://doc.rust-lang.org/std/](https://doc.rust-lang.org/std/)
3.  **MDN**: [https://developer.mozilla.org/en-US/docs/Web/JavaScript](https://developer.mozilla.org/en-US/docs/Web/JavaScript)
4.  **Go**: [https://go.dev/doc/](https://go.dev/doc/)
5.  **React**: [https://react.dev/reference/react](https://react.dev/reference/react)

## Performance Metrics

| Metric | Target | Actual (Avg) | Status |
| :--- | :--- | :--- | :--- |
| **Cache Hit Latency** | < 200ms | ~8ms (Semantic) / <1ms (Exact) | ✅ PASS |
| **Quality Score** | > 0.85 | 0.90 | ✅ PASS |
| **Hit Rate** | N/A | 100% (Subsequent runs) | ✅ PASS |

## Bottlenecks & Optimizations

### 1. Latency Reporting Fixed
- **Issue**: `total_latency_ms` was reported as `0ms` for semantic cache hits even when a measurable delay (encoding) occurred.
- **Fix**: Modified `cli/src/resolver/url.rs` and `cli/src/resolver/query/mod.rs` to correctly accumulate and report latency for all cache hits.

### 2. Redundancy Pruning Enhanced
- **Issue**: Risk of cache bloat from extremely similar queries (e.g., varying only by one word).
- **Fix**: Enhanced `cli/src/semantic_cache/ops.rs` to:
    - Skip storing entries if similarity is > 0.995.
    - Skip storing if content is identical to an existing entry with > 0.98 similarity.

### 3. Text Encoder Warm-up
- **Observation**: First-use loading of the text encoder takes ~1s.
- **Status**: Currently mitigated by background warm-up task in `ops.rs` during cache initialization. Exact matches bypass the need for the encoder entirely.

## Semantic Cache Efficiency

The cache successfully handles URL normalization (e.g., `https://docs.python.org/3/` vs `https://docs.python.org/3`) and semantically equivalent queries (e.g., `Python 3 docs` vs `docs for python 3`) with high confidence scores (1.00) and minimal latency (~8ms).

## Recommendations
- Continue monitoring the background warm-up task to ensure it doesn't block critical path during CLI startup if semantic search is needed immediately.
- Consider further aggressive pruning of "cache_alias" entries if the cache size approaches `max_entries`.
