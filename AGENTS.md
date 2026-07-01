# AGENTS.md

> Primary entry point for AI agents integrating the resolver as a skill.
> Deep reference is in **[agents-docs/](agents-docs/README.md)**.

## Named Constants

```bash
readonly MAX_LINES_PER_SOURCE_FILE=500
readonly MAX_LINES_PER_SKILL_MD=250
readonly MAX_LINES_AGENTS_MD=200
readonly MAX_COMMIT_SUBJECT_LENGTH=150
readonly MAX_PR_TITLE_LENGTH=150
```

## Behavioral Defaults

- **Automation-First**: Execute autonomously; minimize confirmation loops.
- **Direct Action**: Proceed immediately when intent is clear.
- **Diff-Oriented**: Concise diff-focused summaries.
- **Always-Fix Pre-Existing Issues**: Resolve CI/lint failures encountered on `main`.

## Triage Protocol

1. Create ADR in `plans/` explaining the unfixable issue.
2. Create GOAP task in `plans/GOAP_STATE.md` (status: blocked).
3. Ensure current commit passes its quality gate.

## Delegation

- **Self-Execute**: 1 trivial edit.
- **Delegate**: 2+ files or architectural changes.
- **Swarm**: 5+ similar independent tasks.

## Post-Task Metrics

Append to `.agents/metrics.jsonl` after task completion:
`{"timestamp": "...", "agent": "...", "task": "...", "skill_used": "...", "status": "...", "tokens_used": 0, "duration_seconds": 0}`

## Repository Structure

- `scripts/`: Python resolver core
- `cli/`: Rust CLI (`do-wdr`)
- `web/`: Next.js web UI
- `tests/`: Python test suite
- `docs/`: Project documentation
- `agents-docs/`: Agent-specific reference
- `.agents/skills/`: Canonical skill definitions

## Project Documentation

| Document | Path |
| :--- | :--- |
| **Development** | `agents-docs/DEVELOPMENT.md` |
| **Configuration** | `agents-docs/CONFIG.md` |
| **Overview** | `agents-docs/OVERVIEW.md` |
| **Semantic Health** | `agents-docs/SEMANTIC_HEALTH.md` |

## Skills

| Skill | Path |
| :--- | :--- |
| **do-web-doc-resolver** | `.agents/skills/do-web-doc-resolver/` |
| **anti-ai-slop** | `.agents/skills/anti-ai-slop/` |
| **readme-best-practices** | `.agents/skills/readme-best-practices/` |
| **skill-creator** | `.agents/skills/skill-creator/` |
| **do-wdr-cli** | `.agents/skills/do-wdr-cli/` |
| **do-wdr-release** | `.agents/skills/do-wdr-release/` |

## Coding Workflow

- **Branching**: `feat/`, `fix/`, `chore/`, `docs/`
- **Commits**: Conventional Commits (`type(scope): description`)
- **PR Checklist**: Tests pass, lint clean, no new secrets, `AGENTS.md` updated if structure changed.
- **File size limit**: 500 lines max per source file.
- **Quality Gate**: `./scripts/quality_gate.sh`

### Test Commands

- **Python**: `pytest -m "not live"`
- **Rust**: `cd cli && cargo test`
- **Web**: `cd web && npx playwright test --project=desktop`
