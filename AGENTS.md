# AGENTS.md

> Primary entry point for AI agents integrating the resolver as a skill.
> Deep reference documentation is located in **[agents-docs/](agents-docs/README.md)**.

## Named Constants

```bash
readonly MAX_LINES_PER_SOURCE_FILE=500
readonly MAX_LINES_PER_SKILL_MD=250
readonly MAX_LINES_AGENTS_MD=150
readonly DEFAULT_MAX_RETRIES=3
readonly DEFAULT_RETRY_DELAY_SECONDS=5
readonly QUALITY_THRESHOLD_NOISE=6
readonly QUALITY_THRESHOLD_JARGON=3
readonly QUALITY_MIN_CHARS=500
```

## Behavioral Defaults

- **Automation-First**: Execute autonomously within approved plans; minimize confirmation loops.
- **Parallelism**: Use parallel tool calls for independent operations.
- **Direct Action**: Proceed immediately when intent is clear.
- **Diff-Oriented**: Provide concise diff-focused summaries rather than long prose.
- **Always-Fix Pre-Existing Issues**: Address failing lint or CI checks immediately.

## Repository Structure

```text
./
├── scripts/               # Python resolver core
├── cli/                   # Rust CLI (do-wdr)
├── web/                   # Next.js web UI
├── tests/                 # Python test suite
├── docs/                  # Project documentation
├── agents-docs/           # Agent-specific reference
├── .agents/skills/        # Canonical skill definitions
├── assets/                # Visual assets
└── config.toml            # Optional configuration
```

## Project Documentation

Detailed reference material in `agents-docs/`:

| Document | Path | Description |
|---|---|---|
| Assets | `agents-docs/ASSETS.md` | Visual assets and screenshots |
| Configuration | `agents-docs/CONFIG.md` | Configuration guide |
| Dependabot Auto-Merge SOP | `agents-docs/DEPENDABOT_AUTO_MERGE_SOP.md` | Dependabot auto-merge verification runbook |
| Deployment | `agents-docs/DEPLOYMENT.md` | Deployment guide |
| Development | `agents-docs/DEVELOPMENT.md` | Development guide |
| Known Issues | `agents-docs/ISSUES.md` | Known issues and audit findings |
| Overview | `agents-docs/OVERVIEW.md` | Project overview |
| Reference Index | `agents-docs/README.md` | Index for this directory |
| Releases | `agents-docs/RELEASES.md` | Release process |
| Semantic Health | `agents-docs/SEMANTIC_HEALTH.md` | Current semantic health summary |
| Semantic Health — June 2026 | `agents-docs/SEMANTIC_HEALTH_2026_06.md` | June 2026 archive |
| Semantic Health — July 2026 | `agents-docs/SEMANTIC_HEALTH_JULY_2026.md` | July 2026 archive |
| Semantic Health — August 2026 | `agents-docs/SEMANTIC_HEALTH_AUG_2026.md` | August 2026 archive |
| Semantic Health — August 2026 Summary | `agents-docs/SEMANTIC_HEALTH_AUG_2026_SUMMARY.md` | August 2026 analysis and issue summary |
| Semantic Health Issue | `agents-docs/SEMANTIC_HEALTH_ISSUE.md` | Cache hit latency and telemetry investigation |
| Semantic Health Summary | `agents-docs/semantic_health_summary.md` | August 2026 summary (legacy filename) |

## Skills

| Skill | Path | Description |
|---|---|---|
| `agent-browser` | `.agents/skills/agent-browser/` | Browser automation for navigating, filling forms, and screenshots |
| `anti-ai-slop` | `.agents/skills/anti-ai-slop/` | Audit and fix UI, UX, and copy that reads as generic "AI slop" |
| `codacy` | `.agents/skills/codacy/` | Query Codacy analysis, triage issues, suppress false positives |
| `do-github-pr-sentinel` | `.agents/skills/do-github-pr-sentinel/` | Monitor a PR until merged, green, or blocked; diagnose and retry CI |
| `do-harness` | `.agents/skills/do-harness/` | Quality loop sensors for Python, Rust, Web/UI, and cross-cutting checks |
| `do-wdr-assets` | `.agents/skills/do-wdr-assets/` | Capture screenshots and visual assets for documentation |
| `do-wdr-cli` | `.agents/skills/do-wdr-cli/` | Use the compiled `do-wdr` CLI to resolve URLs and queries |
| `do-wdr-issue-impl` | `.agents/skills/do-wdr-issue-impl/` | Implement a single GitHub issue through to a merged PR |
| `do-wdr-issue-swarm` | `.agents/skills/do-wdr-issue-swarm/` | Batch-implement GitHub issues with parallel specialist agents |
| `do-wdr-release` | `.agents/skills/do-wdr-release/` | Manage releases, versioning, changelogs, and tags |
| `do-wdr-ui-component` | `.agents/skills/do-wdr-ui-component/` | Build CSS-only components for the `cli/ui` design system |
| `do-wdr-visual-resolver` | `.agents/skills/do-wdr-visual-resolver/` | Resolve scanned PDFs and JS-heavy SPAs via CLIP embeddings |
| `do-web-doc-resolver` | `.agents/skills/do-web-doc-resolver/` | Python resolver: full cascade, quality scoring, circuit breakers |
| `privacy-first` | `.agents/skills/privacy-first/` | Keep email addresses and personal data out of the codebase |
| `readme-best-practices` | `.agents/skills/readme-best-practices/` | Create and audit README files against 2026 best practices |
| `skill-creator` | `.agents/skills/skill-creator/` | Create, edit, and benchmark agent skills |
| `vercel-cli` | `.agents/skills/vercel-cli/` | Deploy and manage projects on Vercel from the command line |

## Coding Workflow

### Branching & Commits

```text
<type>(<scope>): <subject>

<body: what changed and why>

<footer: BREAKING CHANGE / Refs: #123>
```

- `type` ∈ `build` `chore` `ci` `docs` `feat` `fix` `perf` `refactor` `revert` `style` `test`; always include a `scope`: `resolver` `cli` `web` `ci` `docs` `deps` `security` `release` `agents` `test` `ux`
- `subject`: imperative mood, no trailing period, header ≤ 150 chars; `!` after the scope marks a breaking change; blank lines between sections, body/footer lines ≤ 100 chars
- Example: `fix(resolver): retry transient 429 from Serper`, with `Refs: #682` in the footer
- Branch naming `feat/`, `fix/`, `chore/`, `docs/`; squash WIP/fixup commits — commitlint lints every commit in the PR range, so a malformed type, scope, or subject anywhere fails CI

### Keeping an Open PR Green

```bash
git fetch origin main
git rebase origin/main              # keep history linear; never merge main into a branch
git commit --fixup <sha>            # stage review follow-ups as fixups
git rebase -i --autosquash origin/main
git push --force-with-lease         # never bare --force; never rewrite main
```

- Rebase before pushing whenever `main` moved. A release tag landing on `main` fails `validate-version` on a stale branch: rebase, then run `python scripts/sync_versions.py --set <tag-without-v>` if the manifest regressed.
- Rebasing rewrites SHAs, so push once, then wait for CI on the new head before touching the branch again.
- gitleaks scans full PR history: rewrite the branch locally to drop a secret. A later removal commit does not clear the failure.
- Prefer fix-forward commits while checks run; reserve force-pushes for conflict resolution or secret removal.

### Pre-Push Gate

`./scripts/quality_gate.sh` covers Python, Rust and web lint/typecheck, Python/Rust tests, docs, skill symlinks, version sync and PII checks. It does **not** cover every CI gate — run the extras that match your diff. `.githooks/pre-push` automates this table by changed path; install it once with `./scripts/setup-hooks.sh`:

| Diff touches | Also run |
|---|---|
| `scripts/**` | `python scripts/sync_skill.py` — the gate's `--check` fails until the skill mirror is refreshed |
| `*.md` | `npx markdownlint-cli .` — the quality gate ignores markdownlint errors |
| `*.yml`, `.github/**` | `yamllint .` and actionlint |
| `cli/**` | `cd cli && cargo clippy --all-targets --all-features -- -D warnings && cargo bench --features semantic-cache --no-run` — the gate lints default features only |
| `web/**` | `cd web && npm test && npm run build` |
| `web/package*.json` | `cd web && npm ci --legacy-peer-deps` — `npm ci` fails on a stale lockfile |

- Commit lockfile changes with `package.json`; no opportunistic dependency upgrades in feature PRs.
- `npm install` once at the repo root to lint messages on every commit; check a whole range with `npm run lint:commits` (or `npx commitlint --config commitlint.config.cjs --from origin/main --to HEAD`).

### PR Metadata

- The PR title becomes the squash subject: valid `type(scope): description`, allowed scope, ≤ 150 chars — update it with `gh pr edit <number> --title "..."`.
- PR body ≤ 2000 chars (hard failure); keep lines ≤ 100 chars — longer lines only warn, since the squash commit is generated text.
- Every PR changes at least one file; a zero-file PR squashes into an empty commit
  on `main` — report verification-only runs on the issue instead.
- No new secrets; `AGENTS.md` updated if repository structure or skills change.

### Quality Harness

- **Harness**: `python scripts/harness.py` (uses `do-harness.toml` path filters)
- **Fallback**: `./scripts/quality_gate.sh`

### Test Commands

- **Python**: `pytest -m "not live"`
- **Rust**: `cd cli && cargo test`
- **Web**: `cd web && npx playwright test --project=desktop`

### File Limits

- Source files must remain under 500 lines per file (`MAX_LINES_PER_SOURCE_FILE=500`).
- `AGENTS.md` must stay under 150 lines (`MAX_LINES_AGENTS_MD=150`).
