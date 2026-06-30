# Contributing to do-web-doc-resolver

## Development Workflow

### Python

The Python core uses Ruff for linting and Black for formatting.

```bash
python -m ruff check .
python -m black .
python -m pytest tests/ -m "not live"
```

### Rust CLI

The Rust components require `cargo fmt` and `cargo clippy`.

```bash
cd cli
cargo fmt
cargo clippy -- -D warnings
cargo test
```

### Web UI

The frontend uses ESLint, TypeScript type-checking, and Playwright for E2E tests.

```bash
cd web
npm run lint
npm run typecheck
npx playwright test --project=desktop
```

### Quality Gate

Before submitting any changes, run the unified quality gate script:

```bash
./scripts/quality_gate.sh
```

## Standards

- **File Size**: Python source files in `scripts/` must not exceed 500 lines.
- **Commits**: Use Conventional Commits (`type(scope): description`).
- **Branching**: Use `feat/`, `fix/`, `chore/`, or `docs/` prefixes.
- **Documentation**: Update `AGENTS.md` if the repository structure or skills change.

## Pull Request Process

1. Fork the repository and create a branch.
2. Implement changes and add tests.
3. Ensure `./scripts/quality_gate.sh` passes.
4. Submit the PR for review.
