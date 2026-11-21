# ADR-019: Defer the Scrim Provider Behind a Proven Egress Boundary

- **Status**: Accepted
- **Date**: 2026-11-21
- **Issue**: #718
- **Decision owner**: resolver maintainers

## Context

Scrim is a Rust headless browser with a CLI/JSON-lines interface. It could
render JavaScript-heavy documentation locally, but it does not replace the
existing Chrome/Chromium or `agent-browser` path.

Two repository contracts block a normal provider adapter:

1. `ReadonlyResolverProtocol` forbids provider callables from spawning
   subprocesses or writing files. The cascade is designed for in-process
   providers, not browser processes.
2. The resolver's SSRF checks validate the requested URL and each redirect it
   performs. They cannot observe page-initiated subresource requests made by a
   separate browser process.

The upstream implementation was inspected, not just its README:

- `scrim/src/net.rs` constructs separate `ureq::Agent` instances for HTTP and
  HTTPS.
- Every request goes through `agent.run(...)` inside `fetch_net_inner`.
- Redirects are followed manually for up to 20 hops.
- Subresource and prefetch requests reuse the same direct network path.
- No documented proxy configuration, fail-closed proxy mode, or request-policy
  hook was found.

Setting `HTTP_PROXY`/`HTTPS_PROXY` is not evidence that this `ureq` setup
honors a proxy. A Docker/Squid wrapper therefore cannot be assumed to enforce
egress until Scrim demonstrably routes every request and redirect through it.

## Decision

Do not add, register, or enable a Scrim subprocess adapter in either runtime.
Scrim remains disabled and out of the cascade.

The next safe deliverable is one of:

1. upstream Scrim support for explicit HTTP(S) proxy configuration with
   fail-closed behavior for redirects and subresources; or
2. a maintained fork pinned to a reviewed commit with that capability.

Only after that capability is proven end-to-end should the resolver add a
disposable container/network-namespace runner with deny-by-default egress, no
host credentials, a read-only filesystem except a bounded temporary profile,
and CPU/memory/time/output limits.

## Required regression evidence before enabling

- Redirect, DNS rebinding, IPv4/IPv6 private ranges, cloud metadata endpoints,
  and subresource requests cannot escape the allow policy.
- The adapter invokes Scrim with an argv array, never shell interpolation.
- A missing or incompatible binary returns a structured `skipped/not_installed`
  result rather than crashing the resolver.
- Empty-shell, hydration-failure, and low-quality output fall through to the
  existing providers.
- `agent-browser` and full Chromium remain available for media, WebGL/canvas,
  service-worker, extension, and fidelity-sensitive cases.

## Consequences

- Issue #718 stays open and is marked blocked on an upstream capability, not on
  a missing adapter implementation.
- The existing provider cascade, `agent-browser` workflow, and public CLI
  contracts are unchanged. No unsafe execution path is introduced.
- The benchmark for #718 must consume the same proven runner once it exists; it
  must not create an independent browser invocation path.
