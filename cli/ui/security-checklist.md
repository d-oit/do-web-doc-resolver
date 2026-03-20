# XSS Penetration Test Checklist — Issue #87

## DOM-Based XSS Vectors

| # | Vector | Status | Notes |
|---|---|---|---|
| 1 | `document.write()` / `document.writeln()` |  | Must not be used anywhere |
| 2 | `innerHTML` / `outerHTML` assignment |  | Use `textContent` or sanitized DOM |
| 3 | `eval()` / `Function()` / `setTimeout(string)` |  | Forbidden; use function references |
| 4 | `location.href` / `location.replace()` |  | Validate via `sanitizeUrl()` |
| 5 | `window.name` assignment from user input |  | Should be read-only or cleared |
| 6 | `history.pushState` / `replaceState` with user data |  | Sanitize before push |
| 7 | `postMessage` listener with unvalidated origin |  | Check `event.origin` strictly |
| 8 | URL fragment `#` parsing without encoding |  | Decode then escape |

## Reflected XSS Vectors

| # | Vector | Status | Notes |
|---|---|---|---|
| 9 | Query parameter rendered in page without escaping |  | Escape all `?key=val` outputs |
| 10 | Search input reflected in results without sanitization |  | Apply `sanitizeQuery()` |
| 11 | Error messages echoing user input |  | Escape before display |
| 12 | Form action URL built from user input |  | Validate via `sanitizeUrl()` |

## Stored XSS Vectors

| # | Vector | Status | Notes |
|---|---|---|---|
| 13 | API keys stored and rendered in UI |  | Use `maskApiKey()` — never render raw |
| 14 | Resolved markdown content rendered unsanitized |  | Sanitize markdown output |
| 15 | History entries with arbitrary query text |  | Escape before rendering |
| 16 | Provider name from config rendered as HTML |  | Treat as user input |

## CSP Validation

| # | Check | Status | Notes |
|---|---|---|---|
| 17 | `default-src 'none'` — no fallback permissiveness |  | Verified in `csp-config.ts` |
| 18 | `script-src` uses nonce with `'strict-dynamic'` |  | No `'unsafe-eval'` or `'unsafe-inline'` |
| 19 | `style-src` — `'unsafe-inline'` only for CSS-in-CSS |  | No inline event handlers |
| 20 | `object-src 'none'` blocks Flash/Java |  | Confirmed |
| 21 | `base-uri 'self'` prevents base tag injection |  | Confirmed |
| 22 | `frame-ancestors 'none'` prevents clickjacking |  | Confirmed |
| 23 | `frame-src 'none'` prevents iframe loads |  | Confirmed |
| 24 | `connect-src` restricted to same-origin + https/wss |  | No wildcards |
| 25 | `report-to` endpoint configured and tested |  | POST to `/api/csp-report` |

## Input Sanitization Coverage

| # | Check | Status | Notes |
|---|---|---|---|
| 26 | All `escapeHtml()` calls cover `& < > " ' /` |  | Six-char escape map |
| 27 | `sanitizeUrl()` blocks `javascript:` and `vbscript:` |  | Protocol whitelist |
| 28 | `sanitizeUrl()` rejects control characters |  | `\x00-\x1f` blocked |
| 29 | `sanitizeQuery()` has max length cap |  | 2000 chars |
| 30 | `sanitizeLogValue()` redacts API keys before logging |  | Regex-based redaction |

## API Key Security

| # | Check | Status | Notes |
|---|---|---|---|
| 31 | Raw keys never in `console.log` |  | `sanitizeLogValue()` applied |
| 32 | Keys masked in all UI (`maskApiKey()`) |  | First 4 + last 4 visible |
| 33 | Keys not in URL query strings |  | POST body or encrypted storage |
| 34 | Keys not in localStorage unencrypted |  | Web Crypto AES-GCM (#85) |
| 35 | Key validation enforces provider-specific format |  | `validateApiKey()` patterns |

## Response Header Checks

| # | Header | Expected Value | Status |
|---|---|---|---|
| 36 | `Content-Security-Policy` | Strict policy with nonce |  |
| 37 | `X-Content-Type-Options` | `nosniff` |  |
| 38 | `X-Frame-Options` | `DENY` |  |
| 39 | `X-XSS-Protection` | `0` (disabled — CSP supersedes) |  |
| 40 | `Referrer-Policy` | `strict-origin-when-cross-origin` |  |
| 41 | `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` |  |
| 42 | `Strict-Transport-Security` | `max-age=63072000; includeSubDomains; preload` |  |

## Service Worker / Fetch Interceptor

| # | Check | Status | Notes |
|---|---|---|---|
| 43 | SW `fetch` handler does not forward auth headers to third parties |  | Validate `event.request.url` origin |
| 44 | SW does not cache API key values |  | Strip Authorization header before cache |
| 45 | SW blocks requests to known exfil domains |  | Domain blocklist |

## Regression Test Matrix

| Test ID | Description | Automated | Pass |
|---|---|---|---|
| XSS-01 | `<script>alert(1)</script>` in query input | Playwright |  |
| XSS-02 | `javascript:alert(1)` in URL field | Playwright |  |
| XSS-03 | `<img onerror=alert(1)>` in result content | Playwright |  |
| XSS-04 | API key visible in network tab on key entry | Playwright |  |
| XSS-05 | `eval()` usage detection in bundle scan | ESLint rule |  |
| XSS-06 | CSP violation event fires and reports | Playwright |  |
| XSS-07 | `document.domain` override blocked | Unit test |  |
| XSS-08 | `<base>` tag injection blocked | Unit test |  |
