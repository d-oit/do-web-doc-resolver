# Sentinel Journal

## 2026-04-10 - Proactive SSRF Protection for Redirect Chains
**Vulnerability:** Server-Side Request Forgery (SSRF) via HTTP redirection. The application was previously validating only the initial URL, allowing attackers to redirect requests to internal/private IP ranges after the initial check.
**Learning:** Reactive SSRF protection (checking `response.history` after the request) is insufficient because the request is already executed against the internal target, which could have side effects.
**Prevention:** Implement proactive redirect validation. Disable automatic redirects in the HTTP client and manually follow redirects, validating each new URL in the chain against blocked network ranges before making the next hop.
