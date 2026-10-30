# Contributing to do-web-doc-resolver

## Development Workflow

### Python

```bash
# Run unit tests
pytest tests/ -v -m "not live"

# Linting and formatting
ruff check .
black --check .
```

### Rust CLI

```bash
cd cli
cargo test
cargo clippy --all-targets --all-features -- -D warnings
cargo fmt -- --check
```

### Web UI

```bash
cd web
npm run lint
npm run typecheck
npx playwright test --project=desktop
```

### Quality Gate

Run the full quality gate before submitting:

```bash
./scripts/quality_gate.sh
```

## Standards

- **Python**: Follow Black formatting and Ruff linting rules (`ruff check .`, `black .`). Use type hints for public functions. Source files must not exceed 500 lines.
- **Rust**: Ensure `cargo clippy --all-targets --all-features -- -D warnings` and `cargo fmt` pass without errors.
- **Web UI**: Ensure `npm run lint`, `npm run typecheck`, and Playwright desktop E2E tests pass (`npx playwright test --project=desktop`).
- **Commits**: Use [Conventional Commits](https://www.conventionalcommits.org/) (`type(scope): description`):
  - Types: `build`, `chore`, `ci`, `docs`, `feat`, `fix`, `perf`, `refactor`, `revert`, `style`, `test`
  - Scopes: `resolver`, `cli`, `web`, `ci`, `docs`, `deps`, `security`, `release`, `agents`, `test`, `ux`
- **Branching**: Use `feat/`, `fix/`, `chore/`, or `docs/` prefixes.
- **Pull Requests**:
  1. Ensure unit and E2E tests pass across layers.
  2. Maintain zero new secrets or credentials.
  3. Ensure the quality gate script passes (`./scripts/quality_gate.sh`).
  4. Update `AGENTS.md` if repository structure or skills change.
