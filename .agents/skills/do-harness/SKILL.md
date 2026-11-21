---
name: do-harness
description: Run and troubleshoot the repository's native do-harness verification contract for Python, Rust CLI, Web/UI, and cross-cutting checks.
license: MIT
compatibility: do-harness v0.4.7, Python 3.11+, Rust 1.85+, Node 22+
allowed-tools: Bash(do-harness:*) Bash(./scripts/quality_gate.sh:*) Read
metadata:
  author: d-oit
  version: "2.0.0"
  source: https://github.com/d-o-hub/do-harness
---

# Native do-harness Workflow

`do-harness` is the authoritative verification CLI for this repository. The
checked-in `do-harness.toml` uses the strict native schema: top-level
`language`, `hooks`, `signal-sets`, `[[sensors]]`, and optional `jobs`. The
repository no longer ships a Python harness runner.

## Install the pinned CLI

Use the tested release, never floating `main`:

```bash
curl -fsSL https://raw.githubusercontent.com/d-o-hub/do-harness/v0.4.7/scripts/install.sh \
  | sh -s -- --version v0.4.7
```

The installer verifies the release `checksums.txt` and installs to
`$HOME/.local/bin` (override with `--bin-dir` or `DO_HARNESS_INSTALL_DIR`).

## Commands

```bash
# Diagnose binary resolution, hooks, and state database
do-harness doctor

# Fast local feedback set
do-harness verify --set feedback --changed

# Full pre-merge gate with machine-readable evidence
do-harness verify --set verification --changed --strict \
  --format json --evidence .do-harness/evidence.json

# Report evidence freshness without re-running sensors
do-harness status --set verification

# List/explain selected sensors without running them
do-harness explain --set verification --changed
do-harness list
```

`--changed` selects sensors whose `when-changed` globs match the working tree.
Without `--changed`, every sensor in the set runs. CI runs the full
`verification` set so no required sensor can be silently skipped. An unknown or
empty signal set is a configuration error, not a pass.

## Configuration Contract

```toml
language = "generic"
jobs = 2

[hooks]
pre-commit = ["python-lint"]

[signal-sets]
feedback = ["python-lint", "rust-fmt"]
verification = ["python-lint", "python-test", "rust-test"]

[[sensors]]
name = "python-test"
argv = ["python", "-m", "pytest", "-m", "not live and not benchmark"]
when-changed = ["scripts/**", "tests/**", "pyproject.toml"]
inputs = ["scripts/**", "tests/**", "pyproject.toml"]
timeout = 1800
fix = "Run the failing test with pytest -x."
```

Rules:

- `sensors` use `name`, literal `argv` (program first), and `when-changed`.
  Shell operators, expansion, and redirection are never interpreted.
- `signal-sets` name sensors; they never embed command lines. `feedback`,
  `verification`, and `release` must all be non-empty.
- `inputs` opts a sensor into unchanged-input evidence reuse. Declare it only
  when the command is deterministic and reads no undeclared environment,
  network, or generated output.
- `severity = "warn"` is advisory in non-strict runs. `--strict` fails warnings
  outside `feedback`; do not use `warn` to hide a required gate.
- `timeout` and `fix` are remediation aids, not substitutes for a passing gate.

## Sensor Coverage

| Set | Sensors |
|---|---|
| `feedback` | Python lint/format, Rust fmt, web lint/typecheck, version, skill mirror, symlinks, docs |
| `verification` | All Python, Rust, web, CLI UI, version, skill mirror, symlink, and docs sensors |
| `release` | Python/Rust/web tests, Rust release build, web build, version/mirror checks |

Heavy sensors (`python-test`, `rust-build`, `web-build`) are required in
`verification`. Keep them runnable from a clean checkout; a missing tool is a
failure, not a skip.

## Dogfood Regression

`tests/test_do_harness.py` parses the real configuration and, when
`DO_HARNESS_BIN` or `do-harness` is available, exercises the real CLI:

1. `explain` proves the expected sensor names are selected.
2. A deliberately broken temporary fixture must exit non-zero.
3. A missing signal set must exit non-zero rather than pass vacuously.

CI installs v0.4.7 in the dedicated harness job and sets
`DO_HARNESS_REQUIRED=1`; ordinary unit-test jobs skip the real-CLI checks.

## Fallback

`./scripts/quality_gate.sh` remains the legacy fallback until the native
sensor set has demonstrated equivalent coverage. It is not a second authority;
report divergence rather than silently accepting a weaker gate.

## Troubleshooting

- `sensor config unreadable`: the file uses a legacy schema. Remove unknown
  top-level tables and use `when-changed` (hyphen), not `when_changed`.
- `missing signal set`: add the set to `[signal-sets]`; empty sets are invalid.
- `doctor` reports a missing state database: run `do-harness init-db`.
- Evidence is stale after an input edit: re-run `verify`; `status` is
  freshness-only, not proof.
