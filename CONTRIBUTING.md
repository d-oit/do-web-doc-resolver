# Contributing to do-web-doc-resolver

## Development Workflow

### Python

```bash
# Run unit and integration tests
python -m pytest tests/ -v -m "not live"

# Linting and formatting checks
python -m ruff check .
python -m ruff format --check .

# Auto-format code
python -m ruff format .
python -m ruff check --fix .
```

### Rust CLI

```bash
cd cli

# Run tests
cargo test

# Check clippy warnings
cargo clippy -- -D warnings

# Format check
cargo fmt -- --check
```

### Web UI

```bash
cd web

# Run linter
npm run lint

# Check TypeScript types
npm run typecheck

# Run Playwright E2E browser tests
npx playwright test --project=desktop
```

### Quality Gate

Always execute the local quality gate script to verify all requirements before committing:

```bash
./scripts/quality_gate.sh
```

## Standards

- **Python**: Adhere to Ruff formatting and linting rules. Use explicit type hints for all public functions.
- **Rust**: Ensure `cargo clippy` and `cargo fmt` pass without warnings.
- **Commits**: Follow Conventional Commits format (`type(scope): description`):
  - `feat:` new feature
  - `fix:` bug fix
  - `docs:` documentation updates
  - `chore:` maintenance and dependency updates
  - `refactor:` code restructuring without behavior changes
  - `test:` test additions or modifications
- **Branching**: Prefix development branches with `feat/`, `fix/`, `chore/`, or `docs/`.
- **File Size Limit**: Source files must not exceed 500 lines. Refactor and partition into sub-modules if they exceed this limit.

## Pull Request Process

1. Document any user-facing changes in the appropriate docs/ guides.
2. Add unit or integration tests for new functionality.
3. Verify that the quality gate script runs successfully: `./scripts/quality_gate.sh`.
4. Update `AGENTS.md` if repository structure or skill definitions are modified.
