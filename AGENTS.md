# AGENTS.md

> **do-web-doc-resolver** — resolves queries or URLs into clean Markdown via a provider cascade.
> See [agents.md](https://agents.md) for spec.

## Coding Workflow

- **Branch naming**: `feat/`, `fix/`, `chore/`, `docs/`
- **Commit format**: Conventional Commits (`type(scope): description`)
- **File size limit**: 500 lines max per source file
- **Quality gate command**: `./scripts/quality_gate.sh`
- **Pre-commit hooks**: `pre-commit run --all-files` (requires `pip install pre-commit`)
- **Secret scanning**: Gitleaks (`.gitleaks.toml`)
- **Test commands**:
  - Python: `pytest -m "not live"`
  - Rust: `cd cli && cargo test`
  - Web: `cd web && npx playwright test --project=desktop`
- **Local CI**: `act` (requires Docker, see `.actrc`)
- **Web dependencies**: Use `npm ci --legacy-peer-deps` (ESLint 10 peer conflict)
- **PR Checklist**:
  - `scripts/quality_gate.sh` passes
  - Linting clean (ruff/black, cargo fmt/clippy, npm run lint)
  - Markdown linting passes (`markdownlint`)
  - No new secrets committed (Gitleaks)
  - Check `plans/README.md` — ensure changes align with roadmap
  - Consult relevant [Regression Prevention](#regression-prevention) references before merging
  - `AGENTS.md` updated if repository structure changed

## Repository Structure

```
./
├── scripts/               # Core Python logic
├── cli/                   # Rust CLI (do-wdr)
│   └── ui/                # Design system (tokens, components, Storybook)
├── web/                   # Next.js web UI (Vercel deployment)
├── tests/                 # Python test suite
├── docs/                  # Standards & examples
├── agents-docs/           # Reference for agents
├── plans/                 # Roadmap & architecture plans (see plans/README.md)
├── .agents/skills/        # Canonical skill definitions
├── .githooks/             # Git hooks (pre-commit, etc.)
├── .github/               # GitHub workflows & templates
└── assets/                # Visual assets
```

### Configuration Files (from github-template-ai-agents)
- `.gitleaks.toml` - Secret scanning configuration
- `.pre-commit-config.yaml` - Pre-commit hooks (Gitleaks, shellcheck, markdownlint)
- `commitlint.config.cjs` - Commit message linting
- `markdownlint.toml` - Markdown linting rules
- `.actrc` - Local CI testing with `act`

## Project Documentation

Detailed domain knowledge is located in `agents-docs/`.

| Topic | File |
|---|---|
| Development | [agents-docs/DEVELOPMENT.md](agents-docs/DEVELOPMENT.md) |
| Configuration | [agents-docs/CONFIG.md](agents-docs/CONFIG.md) |
| Deployment | [agents-docs/DEPLOYMENT.md](agents-docs/DEPLOYMENT.md) |
| Releases | [agents-docs/RELEASES.md](agents-docs/RELEASES.md) |
| Assets | [agents-docs/ASSETS.md](agents-docs/ASSETS.md) |
| Overview | [agents-docs/OVERVIEW.md](agents-docs/OVERVIEW.md) |
| Cascade | [.agents/skills/do-web-doc-resolver/references/CASCADE.md](.agents/skills/do-web-doc-resolver/references/CASCADE.md) |

## Skills

| Skill | Path |
|---|---|
| do-web-doc-resolver | .agents/skills/do-web-doc-resolver/ |
| do-wdr-cli | .agents/skills/do-wdr-cli/ |
| do-wdr-assets | .agents/skills/do-wdr-assets/ |
| do-wdr-release | .agents/skills/do-wdr-release/ |
| do-wdr-ui-component | .agents/skills/do-wdr-ui-component/ |
| do-wdr-issue-swarm | .agents/skills/do-wdr-issue-swarm/ |
| do-github-pr-sentinel | .agents/skills/do-github-pr-sentinel/ |
| agent-browser | .agents/skills/agent-browser/ |
| privacy-first | .agents/skills/privacy-first/ |
| skill-creator | .agents/skills/skill-creator/ |
| readme-best-practices | .agents/skills/readme-best-practices/ |
| anti-ai-slop | .agents/skills/anti-ai-slop/ |
| vercel-cli | .agents/skills/vercel-cli/ |

## Regression Prevention

Key reference files in `.agents/skills/` that help prevent regressions:

| Topic | Reference File | Prevents |
|---|---|---|
| Provider cascade logic | [.agents/skills/do-web-doc-resolver/references/CASCADE.md](.agents/skills/do-web-doc-resolver/references/CASCADE.md) | Provider status, cascade order issues |
| Provider configuration | [.agents/skills/do-web-doc-resolver/references/PROVIDERS.md](.agents/skills/do-web-doc-resolver/references/PROVIDERS.md) | API key validation, provider availability |
| Testing strategy | [.agents/skills/do-web-doc-resolver/references/TESTING.md](.agents/skills/do-web-doc-resolver/references/TESTING.md) | CI gaps, missing test coverage |
| CI automation | [.agents/skills/vercel-cli/references/ci-automation.md](.agents/skills/vercel-cli/references/ci-automation.md) | Redundant builds, workflow inefficiencies |
| Browser testing | [.agents/skills/agent-browser/references/commands.md](.agents/skills/agent-browser/references/commands.md) | UI regressions, state management bugs |
| UI components | [.agents/skills/do-wdr-ui-component/](.agents/skills/do-wdr-ui-component/) | Frontend component inconsistencies |
| Architecture plans | [plans/README.md](plans/README.md) | Design regressions, architectural drift |

### Pre-implementation Checklist

Before implementing changes, consult:
1. `plans/README.md` — Check if change aligns with roadmap
2. Relevant skill reference files above — Understand existing patterns
3. Run `agent-browser` tests for web UI changes (see [agent-browser skill](.agents/skills/agent-browser/))
4. Update `AGENTS.md` if new skills or plans affect workflow
