#!/usr/bin/env python3
"""Changed-file classification and verification-mode selection for do-harness.

Issue #730 declares one canonical verification entry point:
`do-harness verify --set verification [--changed] --strict` (driven by
`scripts/verify.sh`). This module owns the part the external CLI cannot own:
rename/delete-aware changed-file collection, path classification per runtime
component, sensor selection from the checked-in `do-harness.toml`, and the
conservative fallback to full verification whenever detection is uncertain.

Machine-readable output: `--format json`. Fix hints for failed sensors are
read back from harness evidence with the `fix-hints` subcommand.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "do-harness.toml"
CANONICAL_SET = "verification"
EVIDENCE_PATH = ".do-harness/evidence.json"

CHANGED_COMMAND = (
    f"do-harness verify --set {CANONICAL_SET} --changed --strict "
    "--format json --evidence .do-harness/evidence.json"
)
FULL_COMMAND = (
    f"do-harness verify --set {CANONICAL_SET} --strict "
    "--format json --evidence .do-harness/evidence.json"
)

# Build output and tool caches never drive verification. They are filtered
# before classification so a rebuilt artifact cannot silently narrow the run.
GENERATED_GLOBS: tuple[str, ...] = (
    ".do-harness/**",
    ".cache/**",
    ".pytest_cache/**",
    "cli/target/**",
    "web/.next/**",
    "web/coverage/**",
    "web/playwright-report/**",
    "web/test-results/**",
    "**/node_modules/**",
    "**/__pycache__/**",
    ".coverage",
    "coverage.xml",
)

# Repository-relative globs per runtime component. Anything changed that fits
# no component is treated as uncertain and forces full verification.
COMPONENT_GLOBS: dict[str, tuple[str, ...]] = {
    "python": (
        "scripts/**",
        "tests/**",
        "pyproject.toml",
        "requirements.txt",
        "mypy.ini",
        "config.toml",
    ),
    "rust": (
        "cli/src/**",
        "cli/tests/**",
        "cli/benches/**",
        "cli/Cargo.toml",
        "cli/Cargo.lock",
        "deny.toml",
    ),
    "web": ("web/**",),
    "cli-ui": ("cli/ui/**",),
    "cross-cutting": (
        ".agents/**",
        ".github/**",
        "agents-docs/**",
        "docs/**",
        "AGENTS.md",
        "README.md",
        "CHANGELOG.md",
        "SECURITY.md",
        "CODE_OF_CONDUCT.md",
        "CONTRIBUTING.md",
        "LICENSE",
        "commitlint*.cjs",
        "package.json",
        "package-lock.json",
        ".markdownlint*",
        ".yamllint.yml",
        ".gitleaks.toml",
        ".deepsource.toml",
        ".codacy.yml",
        ".pre-commit-config.yaml",
        ".gitattributes",
        ".gitignore",
        ".cleanup-ignore",
        ".actrc",
        ".python-version",
    ),
}

# Changes here can redefine the verification contract itself, so they always
# run the full sensor set instead of a changed-only selection.
FALLBACK_GLOBS: tuple[str, ...] = (
    "do-harness.toml",
    ".github/**",
)

MERGE_MARKERS: tuple[str, ...] = (
    ".git/MERGE_HEAD",
    ".git/REBASE_HEAD",
    ".git/CHERRY_PICK_HEAD",
    ".git/rebase-merge",
    ".git/rebase-apply",
)

SENSORS_BY_COMPONENT: dict[str, tuple[str, ...]] = {
    "python": ("python-lint", "python-format", "python-typecheck", "python-test"),
    "rust": ("rust-fmt", "rust-clippy", "rust-test", "rust-build", "rust-semantic-cache"),
    "web": ("web-lint", "web-typecheck", "web-test", "web-build"),
    "cli-ui": ("cli-ui-lint", "cli-ui-test"),
    "cross-cutting": (
        "validate-version",
        "validate-skill-mirror",
        "validate-symlink",
        "validate-docs",
    ),
}


def normalize(path: str) -> str:
    """Return a repo-relative POSIX form of `path`."""
    path = path.replace("\\", "/")
    if path.startswith("./"):
        path = path[2:]
    return path


def matches_any(path: str, globs: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(path, glob) for glob in globs)


def classify(paths: list[str]) -> dict[str, list[str]]:
    """Bucket normalized paths by component; unmatched paths go to `unclassified`."""
    buckets: dict[str, list[str]] = {"unclassified": []}
    for path in sorted(set(paths)):
        if matches_any(path, GENERATED_GLOBS):
            continue
        for component, globs in COMPONENT_GLOBS.items():
            if matches_any(path, globs):
                buckets.setdefault(component, []).append(path)
                break
        else:
            buckets["unclassified"].append(path)
    return buckets


def collect_changed_paths(repo_root: Path) -> tuple[list[str], list[str]]:
    """Collect working-tree changes; return (paths, uncertainty reasons).

    Uses `git status --porcelain=v1 -z` so staged, unstaged, untracked,
    deleted, and renamed paths are all captured (rename entries carry both
    the new and the original path in the `-z` stream). Any git failure or
    in-progress merge/rebase yields reasons instead of a partial answer.
    """
    if shutil.which("git") is None:
        return [], ["git is not available"]
    if any((repo_root / marker).exists() for marker in MERGE_MARKERS):
        return [], ["merge, rebase, or cherry-pick in progress"]

    def run_git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )

    toplevel = run_git("rev-parse", "--show-toplevel")
    if toplevel.returncode != 0:
        detail = (
            toplevel.stderr.strip().splitlines()[-1] if toplevel.stderr.strip() else "git failed"
        )
        return [], [f"not inside a git worktree ({detail})"]
    if Path(toplevel.stdout.strip()).resolve() != repo_root.resolve():
        return [], [f"{repo_root} is not the git worktree root"]

    status = run_git("status", "--porcelain=v1", "-z", "--untracked-files=all")
    if status.returncode != 0:
        detail = (
            status.stderr.strip().splitlines()[-1] if status.stderr.strip() else "git status failed"
        )
        return [], [f"git status failed ({detail})"]

    tokens = status.stdout.split("\0")
    paths: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        index += 1
        if not token:
            continue
        xy = token[:2]
        paths.append(token[3:])
        if ("R" in xy or "C" in xy) and index < len(tokens):
            paths.append(tokens[index])
            index += 1
    return sorted(set(paths)), []


def read_config(repo_root: Path | None = None) -> dict:
    config_path = (repo_root or REPO_ROOT) / "do-harness.toml"
    with config_path.open("rb") as handle:
        return tomllib.load(handle)


def select_sensors(config: dict, paths: list[str]) -> list[str]:
    """Return sensor names whose `when-changed` globs match any changed path."""
    selected: list[str] = []
    for sensor in config.get("sensors", []):
        globs = tuple(sensor.get("when-changed", []))
        if globs and any(matches_any(path, globs) for path in paths):
            selected.append(sensor["name"])
    return selected


def _force_full_reasons(
    paths: list[str],
    buckets: dict[str, list[str]],
    git_reasons: list[str],
    sensors: list[str],
) -> list[str]:
    reasons = list(git_reasons)
    unclassified = buckets.get("unclassified", [])
    if unclassified:
        sample = ", ".join(unclassified[:3])
        reasons.append(f"{len(unclassified)} changed path(s) match no component: {sample}")
    fallback_hits = sorted(path for path in paths if matches_any(path, FALLBACK_GLOBS))
    if fallback_hits:
        reasons.append(f"verification contract touched: {', '.join(fallback_hits[:3])}")
    if paths and not sensors:
        reasons.append("no configured sensor covers the changed files")
    if not paths:
        reasons.append("no local changes detected")
    return reasons


def select(
    repo_root: Path,
    config: dict,
    mode: str = "auto",
    changed_paths: list[str] | None = None,
) -> dict:
    """Decide changed-only versus full verification and name the command.

    `mode="auto"` applies the fallback policy: git uncertainty, contract or
    workflow changes, unclassified paths, an empty changeset, or a change no
    sensor covers all downgrade to full verification. Explicit `changed` or
    `full` modes are honored as user overrides.
    """
    git_reasons: list[str] = []
    if changed_paths is None:
        changed_paths, git_reasons = collect_changed_paths(repo_root)
    paths = [normalize(path) for path in changed_paths]
    buckets = classify(paths)
    sensors = select_sensors(config, paths)
    force_full = _force_full_reasons(paths, buckets, git_reasons, sensors)

    if mode == "full" or (mode == "auto" and force_full):
        final_mode = "full"
    else:
        final_mode = "changed"
    components = sorted(set(buckets) - {"unclassified"})
    expected = sorted(
        sensor for component in components for sensor in SENSORS_BY_COMPONENT[component]
    )
    return {
        "mode": final_mode,
        "reasons": force_full,
        "changed_paths": sorted(set(paths)),
        "components": components,
        "expected_sensors": expected,
        "sensors": sensors,
        "command": FULL_COMMAND if final_mode == "full" else CHANGED_COMMAND,
    }


def print_fix_hints(evidence_path: Path, config: dict) -> int:
    """Print the configured fix command for every sensor that did not pass."""
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    fixes = {sensor["name"]: sensor.get("fix", "") for sensor in config.get("sensors", [])}
    hints = 0
    for sensor in evidence.get("sensors", []):
        if sensor.get("verdict") == "pass":
            continue
        hints += 1
        fix = fixes.get(sensor.get("name", ""), "")
        print(f"{sensor.get('name', 'unknown')}: {fix or 'no fix hint configured'}")
    return 1 if hints else 0


def _print_text(result: dict) -> None:
    print(f"mode: {result['mode']}")
    for reason in result["reasons"]:
        print(f"reason: {reason}")
    print(f"components: {', '.join(result['components']) or 'none'}")
    print(f"sensors: {', '.join(result['sensors']) or 'all (full run)'}")
    print(f"command: {result['command']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--mode", choices=("auto", "changed", "full"), default="auto")
    parser.add_argument("--format", choices=("text", "json", "mode"), default="text")
    sub = parser.add_subparsers(dest="subcommand")
    hints = sub.add_parser("fix-hints", help="print fix commands for failed sensors")
    hints.add_argument("evidence", type=Path)
    args = parser.parse_args(argv)

    if args.subcommand == "fix-hints":
        return print_fix_hints(args.evidence, read_config())

    result = select(args.repo_root, read_config(), mode=args.mode)
    if args.format == "json":
        print(json.dumps(result, indent=2))
    elif args.format == "mode":
        print(result["mode"])
    else:
        _print_text(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
