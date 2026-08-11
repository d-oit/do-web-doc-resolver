## [0.3.10] - 2026-08-11

### Added

- **CLI**: close out cache pre-warming — offline integration tests, `[routing.prewarm]` config block, documentation (#570)
- **CI**: nightly integration test for JS-heavy LLM-ready markdown (#571)
- **Cascade**: FetchTier enum and stealth escalation layer for provider tier mapping (#509, #488)
- **Resolver**: ReadonlyResolverProtocol for typed provider callables (#508)
- **Resolver**: visual_clip provider wired into URL resolution cascade
- **Resolver**: trafilatura/readability content-clean mode for improved extraction (#505)
- **Providers**: bot-challenge detection and auto-escalation signal in direct_fetch (#512)
- **UX**: close button to mobile sidebar (#535)
- **UX**: navigation accessibility with proper ARIA states (#506, #510)
- **UX**: accessibility and micro-UX improvements to web interface (#434)
- **Security**: comprehensive security-scan workflow (ShellCheck, Trivy, CodeQL, dependency audit)
- **Security**: cloud metadata endpoints hardened in BLOCKED_NETWORKS (#503)
- **CI**: yaml-lint, markdown-lint, and commitlint workflows
- **Agents**: do-wdr-visual-resolver skill scaffold
- **Agents**: Codacy issue resolution protocol in AGENTS.md and codacy skill

### Changed

- **CLI**: refactor dead-code removal, split utils into package, expand config output (#575)
- **CLI**: drop unnecessary Sync bound on prewarm resolve closure (#573)
- **Resolver**: align synthesis logic with 2026 LLM-ready standards (#511)
- **CLI**: optimize semantic cache metrics and redundancy pruning
- **CLI**: optimize deterministic merge reducing line allocations
- **CLI**: optimize content compaction and quality scoring
- **CLI**: optimize quality scoring with regex early-exit (#507)
- **Web**: ProfileCombobox keyboard accessibility and focus management (#471)
- build(deps): bump the npm-deps group across multiple updates (#502, #522)
- build(deps): bump regex from 1.12.4 to 1.13.0 in /cli
- build(deps): bump mockall from 0.14.0 to 0.15.0 in /cli
- ci(deps): bump EmbarkStudios/cargo-deny-action
- ci(deps): bump the github-actions group with multiple updates

### Fixed

- **Security**: resolve npm audit vulnerabilities and fix pre-existing CI failures (#502)
- **Security**: add CVE-2026-41305 to Trivy ignore for postcss
- **Resolver**: improve HTML stripping with quote-aware tag parsing
- **Resolver**: preserve indentation in direct_fetch code blocks
- **Resolver**: optimize semantic cache telemetry and sync logic
- **Test**: fix unawaited coroutine warning in mock_thread_func
- **CI**: resolve DeepSource Python warnings in skills snapshot (#504)
- **CI**: resolve pre-existing markdownlint and cargo deny failures
- **CI**: set cargo-deny manifest-path to ./cli/Cargo.toml
- **CI**: update cargo-deny-action to v2.0.20 for CVSS 4.0 support
- **CI**: bump Rust toolchain to 1.89 for cargo-audit compatibility
- **CI**: exclude Bandit checks in test files
- **CI**: fix action versions in lint workflows

## [0.3.9] - 2026-06-20

### Added

- **CLI**: enable semantic-cache by default
- **Web**: enhance result card accessibility and interactive feedback consistency (#450)
- async-aware locks for Rust CLI (Plan 03 Opt 8)
- shared reqwest Client for Rust CLI (Plan 03 Opt 7)
- Python async migration + CI improvements
- **Web**: improve input intent and button accessibility (#434)

### Changed

- **Docs**: update plans/ folder with latest progress
- **Docs**: update AUDIT.md and README.md after PR #455 merge
- **Docs**: refresh AUDIT.md timestamp, add merged PRs #450-#452, flag query.rs over limit (#453)
- Optimize HTML entity decoding in direct_fetch provider (#451) (be0df36)
- Enhance Provider Monitoring and Routing Logic (#452) (5b2a156)
- build(deps)(deps-dev): bump js-yaml from 4.1.1 to 4.2.0 in /web (#447) (2a53733)
- build(deps)(deps-dev): bump form-data from 4.0.5 to 4.0.6 in /web (#448) (8a9f958)
- build(deps)(deps-dev): bump vite from 8.0.10 to 8.0.16 in /web (#445) (7058076)
- Optimize and harden Python-Rust bridge parsing (#446) (40bb016)
- **Performance**: optimize semantic cache and achieve parity
- **Performance**: optimize semantic cache and fix config merge
- build(deps)(deps-dev): bump the npm-deps group in /web with 7 updates (e09318f)
- build(deps)(deps-dev): bump @next/eslint-plugin-next in /web (071e5a0)
- build(deps)(deps): bump next from 15.5.18 to 16.2.9 in /web (c394498)
- build(deps)(deps): bump regex (48bd9e9)
- request coalescing (Plan 03 Opt 10)
- reuse ThreadPoolExecutor (Plan 03 Opt 1)
- true parallel provider launch (Plan 03 Opt 9)
- L1 in-memory TTL cache (Plan 03 Opt 4)
- HTTP/2 + keep-alive for Python and Rust (Plan 03 Opt 3)
- early quality exit in Python cascade (Plan 03 Opt 6)
- eliminate busy-polling in Python cascade (Plan 03 Opt 2)
- **Web**: reduce cyclomatic complexity and fix JS-0067 anti-patterns in results.ts (#438)
- **Web**: reduce component complexity and improve regex correctness (#436)
- Align quality synthesis logic with 2026 standards (#437) (2ce80f2)
- **CLI**: optimize quality scoring with single-pass regex and efficient line counting (#435)
- Update badge links and improve README formatting (b9c1260)
- Improve LaTeX and JS-heavy site parsing in Rust CLI (#433) (9394d31)

### Fixed

- **Security**: add content security policy and security headers (#449)
- address DeepSource provider merge warning (#444)
- reduce config merge complexity (#444)
- address PR review feedback (#444)
- black formatting for providers
- mypy and black compatibility for Python 3.12
- black formatting
- ruff lint errors in cache and tavily
- update test mocks and add get_session to providers_impl exports
- make cargo-audit install non-blocking in CI
- make security audit non-blocking, increase semantic cache latency threshold

### Dependencies

- bump actions/checkout in the github-actions group
## [0.3.8] - 2026-06-08

### Added

- **Synthesis**: Optimize Semantic Cache Retrieval and Pruning (#432)

### Changed

- **UX**: Ensure Clear button is visible when results are present (#421)
- **CI**: Bump actions/checkout in the github-actions group (#427)
- **Docs**: Update release workflow to use CI/CD pipeline (#419)
- **Performance**: Optimize content scoring by avoiding allocations and redundant passes (#420)

### Dependencies

- bump chrono in /cli in the cargo-deps group (#426)
- bump the npm-deps group in /web with 6 updates (#428)
- bump eslint-config-next in /web (#430)

## [0.3.7] - 2026-06-02

### Fixed

- **Scripts**: Remove unused imports in resolve.py (cache_negative, quality, routing)
- **Scripts**: Add explicit `check=False` to subprocess.run calls in docling provider
- **Providers**: Merge status code comparisons with `in` in jina and serper providers

## [0.3.6] - 2026-05-22

### Added

- **Synthesis**: align with 2026 LLM-readable-doc standards
- **Web**: enhance accessibility and address review feedback
- **Web**: enhance search interaction focus and accessibility

### Changed

- **CI**: add serper CI job with CLI smoke test and semantic cache coverage
- **Docs**: compact learnings and update plans after GOAP orchestration
- **Web**: upgrade to TypeScript 6.0.3 and ESLint 10
- **Performance**: optimize cache pruning and documentation quality scoring
- **Scripts**: optimize and harden HTML extraction with tests
- **Scripts**: optimize extract_text_from_html by lifting class and compiling regex

### Fixed

- **Security**: implement rate limiting for resolve endpoint

### Dependencies

- bump tokio in /cli in the cargo-deps group
## [0.3.5] - 2026-05-18

### Added

- **Synthesis**: Align output format with 2026 LLM-readable-doc standards
- **CI**: Serper integration job with CLI smoke test and semantic cache DB coverage

### Changed

- **Web**: Upgrade to TypeScript 6.0.3 and ESLint 10
- **Web**: Improve accessibility — focus management, keyboard navigation, and screen reader support across search and results
- **Performance**: Optimize semantic cache pruning and documentation quality scoring heuristics
- **Performance**: Optimize HTML extraction with compiled regex and lifted class patterns
- **Docs**: Compact accumulated learnings and update plans after GOAP orchestration

### Fixed

- **Resolver**: Eliminate double call to `fetch_llms_txt` in `resolve_direct` lambda
- **Security**: Implement rate limiting for the resolve endpoint
- **CI**: Correct Rust CLI subcommand for serper smoke test
- **Resolver**: Fix `llms_txt` signature mismatch in `resolve_direct`

### Removed

- **Config**: Delete `.opencode/skills` symlink (opencode reads `.agents/skills/` directly — permanent)

### Dependencies

- Bump `tokio` in `/cli` (`cargo-deps` group)

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.1] - 2026-04-20

### Changed

- **Dependencies**: Prevent grouped npm major Dependabot updates for `/web` and `/packages` so incompatible toolchain jumps land in isolated PRs.
- **Dependencies**: Align Dependabot labels with the repository's actual label set to remove configuration-noise warnings.
- **Docs**: Document deterministic dependency compatibility triage in `AGENTS.md`, `agents-docs/DEVELOPMENT.md`, and the PR sentinel heuristics.

### Fixed

- **CI UI**: Close the incompatible grouped npm major update path that broke the Next.js lint stack under `eslint@10`.
- **Rust CLI**: Update patchable transitive dependencies in `cli/Cargo.lock`, including `rustls-webpki` and `rand`, without widening the direct dependency surface.
- **Release Prep**: Verify production deployment and core resolve flow on the live Vercel site across desktop, tablet, and mobile sanity checks.

### Known Issues

- The optional `semantic-cache` feature still pulls an upstream-constrained `chaotic_semantic_memory -> libsql` dependency chain that keeps several Rust security alerts open.
- Upstream tracking issue: `d-o-hub/chaotic_semantic_memory#88`.

## [0.3.0] - 2026-03-25

### Changed

- **CLI**: Rename the binary to `do-wdr` and update Clap command name
- **Config**: Move env vars to `DO_WDR_*` and config/cache paths to `do-wdr`
- **Skills**: Rename skill folders to `do-wdr-*` and update references
- **UI**: Rename CSS tokens/classes to `do-wdr-*` across the design system
- **CI/Release**: Update workflow artifacts and sample runs to `do-wdr`

### Breaking

- `wdr` command, `WDR_*` env vars, and `~/.config/wdr` paths are now `do-wdr`, `DO_WDR_*`, and `~/.config/do-wdr`

## [0.2.0] - 2026-03-22

### Added

- **Web UI**: Complete redesign with Swiss brutalist aesthetic
  - Dark mode only (#0c0c0c background)
  - Geist Mono font throughout
  - Zero border radius (technical brutalism)
  - Acid green accent (#00ff41)
- **Web UI**: CLI parity with profiles, provider selection, advanced options
  - Profile selector (Free/Balanced/Fast/Quality)
  - Provider toggles with availability status
  - Advanced options: max chars, skip cache, deep research
- **API**: `maxChars` parameter support
- **API**: Provider tracking in response
- **API**: Mistral web search and browser extraction providers
- **Skills**: Anti-AI-Slop skill for UI/UX auditing
- **Skills**: Responsive design validation (mobile/tablet/desktop)
- **Docs**: Comprehensive skill marketplace documentation

### Changed

- **Project name**: Renamed to do-web-doc-resolver
- **Web UI**: Removed emoji badges, replaced with CSS dots
- **Web UI**: Settings page with local/server key status
- **CI**: Simplified to Git-based Vercel deployment

### Fixed

- Turbo.json causing Vercel build failure (removed)
- .opencode/skills symlinks pointing to wrong location
- API route TypeScript type errors

## [0.1.1] - 2026-03-19

### Added
- GitHub Release workflow with automated PyPI publish and multi-platform binary builds
- SKILL.md version tracking for agent skill integration

### Fixed
- CI integration test invocations (use `python -m scripts.resolve` instead of `python scripts/resolve.py`)

### Changed
- Updated ADR-001 status to Implemented

## [0.1.0] - 2026-03-14

### Added
- Python library with provider cascade (llms.txt → Jina → Firecrawl → Mistral Browser → DuckDuckGo)
- Query search cascade (Exa MCP → Exa SDK → Tavily → DuckDuckGo → Mistral WebSearch)
- Rust CLI (`do-wdr`) with all providers
- Agent skill integration (SKILL.md, AGENTS.md)
- GitHub Actions CI/CD workflows
- Comprehensive test suite (93 Python tests, 35 Rust tests)
- Quality gate script and pre-commit hooks

### Fixed
- Mistral import paths updated for mistralai>=2.0.0
- CI workflow YAML indentation fixes
- Cache clearing for llms.txt tests

### Dependencies
- Updated actions/checkout from v5 to v6
- Updated actions/upload-artifact from v4 to v7
