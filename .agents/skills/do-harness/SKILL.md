---
name: do-harness
description: Run repository quality loop sensors configured in do-harness.toml for Python, Rust CLI, Web/UI, and cross-cutting documentation/version checks.
license: MIT
compatibility: Python 3.11+, Rust 1.85+, Node 22+
allowed-tools: Bash(python scripts/harness.py:*) Read
metadata:
  author: d-oit
  version: "1.0.0"
  source: https://github.com/d-oit/do-web-doc-resolver
---

# Quality Harness Skill (`do-harness.toml`)

Declarative multi-runtime quality loop sensor configuration for `do-web-doc-resolver`.

## Overview

The repository spans Python, Rust, and Node/TypeScript stacks. The `do-harness.toml` configuration maps file paths (`when_changed` / `when-changed`) to quality sensors wrapping exact repository checks.

## Sensor Groups

1. **Python Quality Loop** (`scripts/**`, `tests/**`, `pyproject.toml`):
   - `python-lint`: `ruff check . && black --check . && mypy scripts/ --ignore-missing-imports`
   - `python-test`: `python -m pytest -m "not live and not benchmark" --tb=short`

2. **Rust CLI Quality Loop** (`cli/src/**`, `cli/tests/**`, `cli/Cargo.toml`):
   - `rust-fmt`: `cargo fmt --manifest-path cli/Cargo.toml --check`
   - `rust-clippy`: `cargo clippy --manifest-path cli/Cargo.toml -- -D warnings`
   - `rust-test`: `cargo test --manifest-path cli/Cargo.toml`
   - `rust-build`: `cargo build --release --manifest-path cli/Cargo.toml`

3. **Web & UI Quality Loop** (`web/**`, `cli/ui/**`):
   - `web-lint`: `npm --prefix web run lint`
   - `web-typecheck`: `npm --prefix web run typecheck`
   - `web-test`: `npm --prefix web test`
   - `cli-ui-lint`: `pnpm --dir cli/ui run lint`
   - `cli-ui-test`: `pnpm --dir cli/ui run test`

4. **Cross-Cutting & Mirror Validation** (`docs/**`, `agents-docs/**`, `scripts/`):
   - `validate-version`: `python scripts/sync_versions.py`
   - `validate-skill-mirror`: `python scripts/sync_skill.py --check`
   - `validate-symlink`: `python scripts/validate_skill_symlink.py`
   - `validate-docs`: `python scripts/validate_docs.py`

## Usage Examples

### Inspect Active Sensors for Changed Files

```bash
python scripts/harness.py --check
python scripts/harness.py --check --files scripts/resolve.py
```

### Run Sensors for Specific Changes

```bash
python scripts/harness.py
```

### Run Specific Sensor by ID

```bash
python scripts/harness.py --sensor python-lint
```

## Fallback Commands

If `do-harness` or a specific runner tool is missing, use the canonical quality gate shell script:

```bash
./scripts/quality_gate.sh
```
