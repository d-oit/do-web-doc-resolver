# Known Issues

## Rust dependency warnings requiring upstream changes

- **Reviewed**: 2026-11-03; `cargo audit` and `cargo deny` exit successfully.
- **Unmaintained serialization**:
  [RUSTSEC-2025-0141](https://rustsec.org/advisories/RUSTSEC-2025-0141)
  has no patched bincode release. Both `chaotic_semantic_memory` and `libsql` depend
  on bincode 1.3.3; even cache library 0.3.8 still requires it.
- **HTTP/2**: [RUSTSEC-2026-0258](https://rustsec.org/advisories/RUSTSEC-2026-0258)
  is fixed only in h2 >=0.4.16. The existing exception covers h2 0.3.27 through
  `libsql` / `tonic` 0.11 / `hyper` 0.14. It cannot be patched within that API line.
- **Duplicate versions**: the old libsql HTTP stack and reqwest's modern stack
  require incompatible major versions. Cargo deny continues reporting these;
  no broad suppression or forced incompatible dependency unification is added.
- **Policy cleanup**: removed unused license grants and an unused ring license
  clarification; ShellCheck no longer encounters dead changelog path assignments.

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

## Resolved: npm tooling audit warnings

- **Date**: 2026-11-03
- **Action**: Removed unused legacy ESLint configuration packages, constrained the
  remaining named-API minimatch consumers to patched 11.0.4, and updated Joi to 18.3.1.
- **Advisories**: [minimatch amplification](https://github.com/advisories/GHSA-g3hv-75wg-m249)
  and [Joi quadratic splitting](https://github.com/advisories/GHSA-4528-x5fx-h6hg).
- **Status**: `npm audit --audit-level=low` reports zero vulnerabilities, including
  development dependencies. The prior braces exception is obsolete; the existing
  micromatch-to-picomatch override removes that dependency.
- **Prevention**: CI audits all dependency severities rather than keeping separate
  relaxed development and production thresholds.

## Semantic Health Audit: September 2026

- **Date**: 2026-09-14
- **Summary**: Executed `do-wdr` CLI benchmark audit across 5 standard documentation URLs (`docs.python.org/3/library/os.html`, `doc.rust-lang.org/std/fs/index.html`, `developer.mozilla.org/en-US/docs/Web/JavaScript`, `docs.python.org/3/library/sys.html`, `doc.rust-lang.org/std/path/struct.Path.html`).
- **Results**: Semantic cache hit rate = 100% (5/5), Cache hit latency = 1ms (well within the < 200ms threshold), Quality synthesis score = 1.0 (exceeds the >= 0.85 threshold).
- **Status**: Healthy. Python-Rust bridge integration operating with zero bottlenecks; embedding retrieval logic and cache redundancy pruning remain fully optimized.

## Semantic Health Audit: October 2026

- **Date**: 2026-10-12
- **Summary**: Executed `do-wdr` CLI benchmark audit across 5 standard documentation URLs (`docs.python.org/3/library/stdtypes.html`, `doc.rust-lang.org/std/index.html`, `developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array`, `pkg.go.dev/std`, `react.dev/learn`).
- **Results**: Semantic cache hit rate = 100% (5/5), Cache hit latency = 1ms (well within the < 200ms threshold), Quality synthesis score = 1.0 (exceeds the >= 0.85 threshold).
- **Status**: Healthy. Python-Rust bridge integration operating with zero bottlenecks; embedding retrieval logic and cache redundancy pruning remain fully optimized.

## Semantic Health Audit: October 19, 2026

- **Date**: 2026-10-19
- **Summary**: Executed `do-wdr` CLI benchmark audit across 5 standard documentation URLs (`docs.python.org/3/library/os.html`, `doc.rust-lang.org/std/fs/index.html`, `developer.mozilla.org/en-US/docs/Web/JavaScript`, `pkg.go.dev/net/http`, `react.dev/reference/react`).
- **Results**: Semantic cache hit rate = 100% (5/5), Cache hit latency = 1ms (well within the < 200ms threshold), Quality synthesis score = 1.0 (exceeds the >= 0.85 threshold).
- **Status**: Healthy. Python-Rust bridge integration operating with zero bottlenecks; embedding retrieval logic and cache redundancy pruning remain fully optimized.

## Semantic Health Audit: October 26, 2026

- **Date**: 2026-10-26
- **Summary**: Executed `do-wdr` CLI benchmark audit across 5 standard documentation URLs (`docs.python.org/3/library/os.html`, `doc.rust-lang.org/std/fs/index.html`, `developer.mozilla.org/en-US/docs/Web/JavaScript`, `pkg.go.dev/net/http`, `react.dev/reference/react`).
- **Results**: Semantic cache hit rate = 100% (5/5), Cache hit latency = 1ms (well within the < 200ms threshold), Quality synthesis score = 1.0 (exceeds the >= 0.85 threshold).
- **Status**: Healthy. Python-Rust bridge integration operating with zero bottlenecks; embedding retrieval logic and cache redundancy pruning remain fully optimized.

## Semantic Health Audit: November 2026

- **Date**: 2026-11-02
- **Summary**: Executed `do-wdr` CLI benchmark audit across 5 standard documentation URLs (`docs.python.org/3/library/os.html`, `doc.rust-lang.org/std/fs/index.html`, `developer.mozilla.org/en-US/docs/Web/JavaScript`, `pkg.go.dev/net/http`, `react.dev/reference/react`).
- **Results**: Semantic cache hit rate = 100% (5/5), Cache hit latency = 1ms (well within the < 200ms threshold), Quality synthesis score = 1.0 (exceeds the >= 0.85 threshold).
- **Status**: Healthy. Python-Rust bridge integration operating with zero bottlenecks; embedding retrieval logic and cache redundancy pruning remain fully optimized.

## Known Gap: session cookie is not authorization

- **Date**: 2026-10-03
- **Issue**: `DELETE /api/cache` and `DELETE /api/records` require a `ui-session` cookie, but the cookie value is client-supplied and unverified. Anyone can obtain one by calling any endpoint that sets it, so the check stops anonymous `curl` and nothing more.
- **Why it is still worth having**: the realistic abuse is an unauthenticated script, and the cookie check is the cheapest thing that raises the bar. It is not an access control boundary and should not be described as one.
- **Follow-up**: sign the session value server-side (HMAC over a random secret, or a platform-issued session) so the check becomes real authorization. `hasSessionCookie` in `app/api/records/route.ts` carries the same caveat in code.
- **Related**: the records store in `lib/records.ts` is a single process-global map with no per-session partitioning, so `GET /api/records` returns every user's records and `GET /api/records?q=` searches across them. Partitioning is a schema change and is out of scope for the current work.
- **Status**: Open.

## Known Gap: request-body limits are per-handler

- **Date**: 2026-10-03
- **Issue**: `readJsonWithLimit` in `web/lib/body-limit.ts` bounds the body for handlers that call it (currently `POST /api/records`). Other handlers still use bare `request.json()`.
- **Why**: App Router has no `bodyParser.sizeLimit` equivalent, so the cap has to be applied in code at each entry point.
- **Status**: Open. Apply to `POST /api/resolve` and `POST /api/history` when they are next touched.
