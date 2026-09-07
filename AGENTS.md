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

- [Development](agents-docs/DEVELOPMENT.md)
- [Configuration](agents-docs/CONFIG.md)
- [Overview](agents-docs/OVERVIEW.md)
- [Semantic Health](agents-docs/SEMANTIC_HEALTH.md)

## Skills

- `do-web-doc-resolver`: `.agents/skills/do-web-doc-resolver/`
- `do-wdr-cli`: `.agents/skills/do-wdr-cli/`
- `anti-ai-slop`: `.agents/skills/anti-ai-slop/`
- `readme-best-practices`: `.agents/skills/readme-best-practices/`
- `skill-creator`: `.agents/skills/skill-creator/`

## Coding Workflow

### Branching & Commits

- Branch naming: `feat/`, `fix/`, `chore/`, `docs/`
- Commit format: Conventional Commits (`type(scope): description`)

### PR Checklist

- Quality gate command passes: `./scripts/quality_gate.sh`
- Linting clean (`ruff`, `black`, `cargo fmt`, `cargo clippy`, `npm run lint`)
- No new secrets added
- `AGENTS.md` updated if repository structure or skills change

### Test Commands

- **Python**: `pytest -m "not live"`
- **Rust**: `cd cli && cargo test`
- **Web**: `cd web && npx playwright test --project=desktop`

### File Limits

- Source files must remain under 500 lines per file (`MAX_LINES_PER_SOURCE_FILE=500`).
