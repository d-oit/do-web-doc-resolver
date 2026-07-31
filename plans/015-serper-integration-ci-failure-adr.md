# ADR 015: Serper Integration CI Failure Triage

## Status
Blocked

## Context
The `Serper Integration` GitHub Actions check run fails when executed on pull request branches or fork environments that lack access to the `SERPER_API_KEY` repository secret. Because Serper is a paid provider requiring this API key, its availability is set to false in key-less environments.

While the query resolver cascade is designed to gracefully fallback to DuckDuckGo, the GHA runner shared IP pool faces heavy rate-limiting and CAPTCHA blocking when attempting unauthenticated/free queries to DuckDuckGo via the Jina Reader proxy (`https://r.jina.ai/https://html.duckduckgo.com/html/?q=...`). This results in a final resolution timeout and raises the error `No query resolution method available`.

## Root Cause
1. **Repository Secret Access**: The GHA workflow runs integration tests on external pull request/head branches where secrets like `SERPER_API_KEY` are not populated, disabling the Serper provider.
2. **DuckDuckGo/Jina Rate-Limiting**: The fallback DuckDuckGo provider is blocked or rate-limited under GHA shared IP pools, returning a resolution failure and failing the entire query cascade with no active providers left.

## Mitigation / Action Items (Future Scope)
1. Configure dummy/mocked query responses for the release and integration tests when live keys are absent.
2. Update the `ci-integration.yml` GHA workflow to gracefully skip the live `Smoke test CLI (Serper)` step if `SERPER_API_KEY` is not present, or if it has a masked/empty value.

## Scope of Current Task
This pre-existing issue is out of scope for the current micro-UX accessibility focus indicators improvement task. This ADR is documented under the `AGENTS.md` triage protocol for unfixable pre-existing failures.
