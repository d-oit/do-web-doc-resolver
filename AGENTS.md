# AGENTS.md

> AI agent integration reference for the web doc resolver.
> Deep reference is in **[agents-docs/README.md](agents-docs/README.md)**.

## Named Constants

```bash
readonly MAX_LINES_PER_SOURCE_FILE=500
readonly MAX_LINES_PER_SKILL_MD=250
readonly MAX_LINES_AGENTS_MD=150
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

## YAML Workflow Style Rule

All `.github/workflows/*.yml` must include `# yamllint disable-line rule:truthy` on the `on:` line.

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

- **Branch Naming**: Prefix branches with `feat/`, `fix/`, `chore/`, or `docs/`.
- **Commit Format**: Conventional Commits style: `type(scope): description`.
- **PR Checklist**:
  1. All tests must pass successfully.
  2. Linting must be completely clean (`ruff`, `ruff-format`, `cargo fmt`, `cargo clippy`, `npm run lint`).
  3. Verify that no new secrets are introduced (via Gitleaks).
  4. Ensure `AGENTS.md` is updated if there are structural or tree modifications.
- **Quality Gate Command**: `./scripts/quality_gate.sh`
- **Test Commands per Layer**:
  - Python: `pytest -m "not live"`
  - Rust: `cd cli && cargo test`
  - Web: `cd web && npx playwright test --project=desktop`
- **File Size Limit**: Source files must not exceed 500 lines max per source file.
