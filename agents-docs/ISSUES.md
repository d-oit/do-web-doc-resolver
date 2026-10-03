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

## Accepted Risk: braces stack-exhaustion DoS (dev-only, unpatched)

- **Date**: 2026-10-03
- **Advisory**: [GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm) / CVE-2026-93687, CVSS 8.7 High, EPSS 0.74%
- **Issue**: `npm audit --audit-level=high` fails on `braces` 3.0.3 — recursive AST walkers have no depth guard, so a deeply nested brace pattern exhausts the call stack. Affects `<= 3.0.3`; **patched versions: None** (`micromatch/braces` PR #72 still open), so it cannot be upgraded away.
- **Exposure**: dev-only. `npm ls braces --omit=dev` is empty. The chain is `@next/eslint-plugin-next@16.3.6 → fast-glob@3.3.1 → micromatch@4.0.8 → braces@3.0.3`, reached only when ESLint expands glob patterns from this repo's own `eslint.config.mjs`. There is no path from an HTTP request or any untrusted input to `braces()`.
- **Rejected**: `npm audit fix --force` downgrades `@next/eslint-plugin-next` 16.3.6 → 14.2.35, a breaking major downgrade that drops Next 16 lint rules.
- **Action Taken**: `.github/workflows/security-scan.yml` gates shipped dependencies with `npm audit --omit=dev --audit-level=high` and dev toolchain with `--audit-level=critical`. Runtime exposure is still fully gated at high; only dev deps are relaxed.
- **Status**: Accepted until upstream ships a patched `braces`. Re-evaluate when PR #72 releases or when `@next/eslint-plugin-next` drops `fast-glob`.
- **Prevention**: Revisit this gate whenever a new `high` advisory appears in the dev tree — do not lower the dev threshold again to absorb a second one.

## Semantic Health Audit: September 2026

- **Date**: 2026-09-14
- **Summary**: Executed `do-wdr` CLI benchmark audit across 5 standard documentation URLs (`docs.python.org/3/library/os.html`, `doc.rust-lang.org/std/fs/index.html`, `developer.mozilla.org/en-US/docs/Web/JavaScript`, `docs.python.org/3/library/sys.html`, `doc.rust-lang.org/std/path/struct.Path.html`).
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
