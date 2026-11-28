# Scrim Evaluation — Optional Local JavaScript-Rendering Provider

Evaluation of [strelov1/scrim](https://github.com/strelov1/scrim) (v0.1.1, MIT) as an
optional, local browser-rendering backend for URL resolution.

## Verdict

**Integrate as a strictly opt-in provider, disabled by default, pending a committed
benchmark before it is placed anywhere in the default cascade.**

The adapter (`scripts/providers/scrim.py`) is merged and inert unless
`DO_WDR_SCRIM_ENABLED=1` is set. Routing never selects `scrim` unless it is
explicitly passed as a custom provider order or enabled and benchmarked in.

## What Scrim is

A single-binary Rust headless browser with no layout, no paint, no images or fonts. It
keeps the DOM, page JavaScript (QuickJS for small scripts, V8 for large ones), CSS
cascade rules that hide content, cookies, navigation and forms. Upstream claims
(34-task agent suite, 100.0 %/99.9 % visible-text recall/precision vs Chrome's
`innerText`, 20 MB peak memory, 8.5 ms startup) come from a separate research corpus
and must be reproduced on our own corpus before any routing decision.

## Fit with the resolver

| Requirement | Assessment |
|---|---|
| Local, no API key | Yes — free tier candidate for JS-heavy pages |
| Text/markdown extraction | Yes — `scrim fetch <url> --dump markdown`, JSON-lines `serve` mode |
| Interactions | Yes — `goto/click/fill/snapshot` (not needed for read-only extraction) |
| Replaces Chromium/agent-browser | No — no layout fidelity, media, WebGL, service workers, extensions |
| Replaces hosted providers | No — no anti-detect, no remote scale |

## Security (mandatory before enabling)

- **Page JavaScript and all page-controlled URLs are untrusted.** The adapter
  SSRF-checks the initial URL with `is_safe_url` before invoking the binary, but
  **Scrim's own subresource fetches (images, XHR, redirects) are outside the
  adapter's control** and are not covered by the resolver's DNS-pinning boundary.
  Until upstream provides connection-time address pinning, Scrim must only run
  against origins where subresource SSRF risk is acceptable, or under a
  network-isolation wrapper (netns/proxy allowlist).
- Process isolation: arguments are passed as an argv array (no shell), with a strict
  timeout (`SCRIM_TIMEOUT`, default 30 s), an output-size cap
  (`SCRIM_MAX_OUTPUT_BYTES`, default 5 MB) and subprocess cleanup on failure.
- Ambient state: the default stateless invocation carries no host cookies; a
  session directory must be a fresh temp dir per session if ever used.
- **Scrim is not a security boundary by itself.**

## Known compatibility limits (upstream)

- Dynamic `import()` from classic inline scripts fails — Vite/SvelteKit/Astro apps
  serve SSR HTML but never hydrate.
- No WebGL, canvas pixels, media playback, service workers or extensions.
- macOS 14+ (Apple Silicon) binaries or source build (prebuilt V8 archive); Nix on
  x86_64 Linux.

## Benchmark plan (required before cascade placement)

Corpus: static docs pages; JS-rendered docs pages; SPA hydration pages; redirect/
lazy-load/cookie-banner pages; a Vite dynamic-import hydration failure case;
adversarial SSRF subresource cases. Compare Scrim vs the current cascade vs full
Chromium on extraction correctness and quality score, median/p95 latency, peak
memory/CPU, startup overhead, failure classification and fallback correctness.

**Committed routing decision:** until that benchmark is committed, `scrim` is
registered in the provider registry and tier map (provisionally at
`FetchTier.PAID_BROWSER`, the last tier) but excluded from all default cascade
orders. A benchmark run must change `scripts/constants.py` (`PROVIDER_TIERS`) and
`scripts/routing.py` (`plan_provider_order`) explicitly.

## Operational notes

- Enable: `DO_WDR_SCRIM_ENABLED=1` with `SCRIM_BIN` (or `scrim` on `PATH`).
- Disable: unset `DO_WDR_SCRIM_ENABLED` (or set `0`); resolver behavior is then
  byte-identical to pre-integration.
- Missing binary: structured `skipped/not_installed` log, resolver falls through.
- Quality: Scrim output passes the same `MIN_CHARS`/quality gates as every other
  provider; empty shells or low-quality output never suppress a better fallback.
