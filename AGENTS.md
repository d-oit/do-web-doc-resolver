# AGENTS.md

> Primary entry point for AI agents integrating the resolver as a skill.
> Deep reference is in **[agents-docs/](agents-docs/README.md)**.

## Named Constants

```bash
readonly MAX_LINES_PER_SOURCE_FILE=500
readonly MAX_LINES_PER_SKILL_MD=250
readonly MAX_LINES_AGENTS_MD=200
readonly DEFAULT_MAX_RETRIES=3
readonly DEFAULT_RETRY_DELAY_SECONDS=5
readonly DEFAULT_POLL_INTERVAL_SECONDS=5
readonly DEFAULT_MAX_POLL_ATTEMPTS=12
readonly DEFAULT_TIMEOUT_SECONDS=1800
readonly MAX_COMMIT_SUBJECT_LENGTH=150
readonly MAX_PR_TITLE_LENGTH=150
readonly QUALITY_THRESHOLD_NOISE=6
readonly QUALITY_THRESHOLD_JARGON=3
readonly QUALITY_MIN_CHARS=500
```

## Behavioral Defaults

- **Automation-First**: Execute autonomously within approved plans; minimize confirmation loops.
- **Parallelism**: Use parallel tool calls for independent operations.
- **Direct Action**: Proceed immediately when intent is clear.
- **Diff-Oriented**: Concise diff-focused summaries, not long prose.
- **Always-Fix Pre-Existing Issues**: No deferral — if a CI check or lint warning is failing on main, agents MUST fix it. Only acceptable exit = green CI.

## Triage Protocol for Unfixable Issues

When a pre-existing failure cannot be fixed in the current run:

1. Create an ADR in `plans/` with root cause and why it's out of scope.
2. Create a GOAP task in `plans/GOAP_STATE.md` with status blocked + ADR link.
3. Ensure current commit's quality gate passes regardless.
4. Never skip, suppress, or mark as done an open issue.

## Delegation Routing

| Mode | Trigger |
| :--- | :--- |
| **Self-Execute** | 1 trivial isolated edit (typos, single-line constants) |
| **Delegate** | 2+ files, architectural changes, tasks requiring judgment |
| **Swarm** | 5+ similar independent tasks (batch doc normalization, multi-file refactors) |

## Post-Task Protocol — metrics.jsonl

After every completed task, append to `.agents/metrics.jsonl`:

```json
{
  "timestamp": "YYYY-MM-DDTHH:MM:SSZ",
  "agent": "<agent-id>",
  "task": "<description>",
  "skill_used": "<skill or null>",
  "status": "completed" | "failed" | "partial",
  "tokens_used": 0,
  "duration_seconds": 0,
  "notes": ""
}
```

Append-only. Never truncate. dora-report reads this file.

## YAML Workflow Style Rule

All `.github/workflows/*.yml` must include `# yamllint disable-line rule:truthy` on the `on:` line.

## Session Bootstrap

`docflow.json` drives context injection at agent startup. `hooks/session-start.sh` can be run manually to verify environment readiness.

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

- [Development](agents-docs/DEVELOPMENT.md)
- [Configuration](agents-docs/CONFIG.md)
- [Overview](agents-docs/OVERVIEW.md)
- [Semantic Health](agents-docs/SEMANTIC_HEALTH.md)

## Skills

- `do-web-doc-resolver`: `.agents/skills/do-web-doc-resolver/`
- `anti-ai-slop`: `.agents/skills/anti-ai-slop/`
- `readme-best-practices`: `.agents/skills/readme-best-practices/`
- `skill-creator`: `.agents/skills/skill-creator/`

## Coding Workflow

### Branching & Commits

- Branch naming: `feat/`, `fix/`, `chore/`, `docs/`
- Commit format: Conventional Commits (`type(scope): description`)

### PR Checklist

- `./scripts/quality_gate.sh` passes
- Linting clean (`ruff`, `black`, `cargo fmt`, `cargo clippy`, `npm run lint`)
- No new secrets (verified via Gitleaks)
- `AGENTS.md` updated if structure changed

### CI & Codacy Rules (NEVER SKIP)

**ALL GitHub Actions checks MUST pass before merge.** No exceptions.

**Codacy MUST be up to standards before merge.** If Codacy shows `ACTION_REQUIRED`:

#### Codacy Issue Resolution Protocol

**NEVER skip, suppress, or ignore Codacy issues without following this protocol:**

1. **Analyze**: Run `codacy pull-request gh <org> <repo> <prN> --output json` to get all issues
2. **Research**: For each issue, web-research the pattern against official docs and best practices:
   - Check the rule's official documentation (ESLint, Biome, Semgrep, etc.)
   - Determine if it's a genuine code quality concern or a false positive
   - Document findings in the PR description or comments
3. **Fix**: If the issue is genuine, fix the code. Commit, push, re-verify.
4. **Verify**: Confirm the fix resolves the issue without introducing regressions
5. **Ignore (last resort only)**: If and only if the issue is a verified false positive:
   - Document WHY it's a false positive (with links to docs/best practices)
   - Use `codacy pull-request gh <org> <repo> <prN> --ignore-issue <resultDataId> --ignore-reason FalsePositive`
   - Add an inline comment explaining the rationale

**Key principles:**

- Fix first, ignore never (unless verified false positive)
- Always document the reasoning behind any decision
- Never assume an issue is a false positive without verification
- Web research against official docs is mandatory before dismissing any issue

**Never merge with:**

- Any failing GitHub Action (even if "pre-existing on main")
- Codacy `ACTION_REQUIRED` status
- Merge conflicts
- Required reviews missing

Dependabot PRs are normalized automatically by the `commitlint.yml` `lint-pr-title` workflow (title de-duped, body replaced with a short summary). Do NOT hand-edit dependabot PR titles/bodies or mark them as exceptions in `commitlint.config.cjs`; if a dependabot PR is blocked on the title/body check, re-run the workflow instead.

### Test Commands

- **Python**: `pytest -m "not live"`
- **Rust**: `cd cli && cargo test`
- **Web**: `cd web && npx playwright test --project=desktop --project=mobile --project=tablet`

## Release Workflow

> **Do NOT use `gh release create` manually.** The CI/CD pipeline handles releases automatically.

### Correct Release Steps

```bash
# 1. Bump versions
python scripts/sync_versions.py --set $VERSION

# 2. Commit
git add -A && git commit -m "chore(release): v$VERSION"

# 3. Tag and push (triggers CI/CD)
git tag -a v$VERSION -m "Release v$VERSION"
git push origin main --tags
```

### What CI/CD Does Automatically

- Runs Python + Rust test suites
- Builds binaries: Linux x86_64, macOS aarch64, Windows x86_64
- Generates build attestations
- Extracts changelog from `CHANGELOG.md`
- Creates GitHub release with binaries + install instructions
