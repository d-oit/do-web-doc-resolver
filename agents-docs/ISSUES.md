# Known Issues

## Provider Alert: DuckDuckGo unstable

- **Date**: 2026-04-20
- **Issue**: DuckDuckGo provider is consistently returning empty results or failing connectivity checks in the current environment.
- **Action Taken**: Deprioritized DuckDuckGo in the routing logic.
- **Status**: Monitoring for stability.

## Provider Regression: Firecrawl missing in Web UI

- **Date**: 2026-05-05
- **Issue**: Firecrawl provider was functional in backend runtimes but omitted from `web/app/constants.ts`, causing it to be hidden from the Sidebar and Settings.
- **Action Taken**: Restored 'firecrawl' to `PROVIDERS` list and `PROFILES` in `web/app/constants.ts`. Added `web/tests/e2e/firecrawl-visibility.spec.ts` to verify UI visibility.
- **Status**: Resolved.
- **Prevention**: Any new provider added to the backend MUST also be registered in `web/app/constants.ts` to be visible in the Web UI.

## Provider Alert: serper unstable

- **Date**: 2026-06-20
- **Issue**: Status code 403: {"message":"Unauthorized.","statusCode":403}
- **Action Taken**: Deprioritized serper in the routing logic.
- **Status**: Monitoring for stability.

## Provider Alert: firecrawl unstable

- **Date**: 2026-06-20
- **Issue**: The read operation timed out
- **Action Taken**: Deprioritized firecrawl in the routing logic.
- **Status**: Monitoring for stability.

## Provider Alert: serper unstable

- **Date**: 2026-07-20
- **Issue**: Status code 403: {"message":"Unauthorized.","statusCode":403}
- **Action Taken**: Deprioritized serper in the routing logic.
- **Status**: Monitoring for stability.

## Provider Alert: serper unstable

- **Date**: 2026-08-20
- **Issue**: Status code 403: {"message":"Unauthorized.","statusCode":403}
- **Action Taken**: Deprioritized serper in the routing logic.
- **Status**: Monitoring for stability.

## Semantic Health Audit: September 2026

- **Date**: 2026-09-07
- **Summary**: Verified semantic cache hit rate, response latency, and quality synthesis score across 5 standard documentation URLs (Python docs, Rust std docs, MDN JS).
- **Results**: Cache hit rate = 100% (5/5), Cache hit latency = 1ms (< 200ms threshold), Quality score = 1.0 (>= 0.85 threshold).
- **Status**: Healthy. No Python-Rust bridge bottlenecks detected or cache optimizations needed.
