#!/usr/bin/env python3
"""do-harness runner and validation script.

Parses do-harness.toml, maps changed files to quality loop sensors,
inspects tool availability, and executes checks with remediation feedback.
"""

from __future__ import annotations

import argparse
import fnmatch
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HARNESS_CONFIG = REPO_ROOT / "do-harness.toml"


def load_harness_config(config_path: Path = HARNESS_CONFIG) -> dict:
    """Load and parse do-harness.toml configuration."""
    if not config_path.exists():
        raise FileNotFoundError(f"Harness config not found at {config_path}")

    with open(config_path, "rb") as f:
        return tomllib.load(f)


def match_pattern(pattern: str, filepath: str) -> bool:
    """Check if a file path matches a harness glob pattern."""
    filepath = filepath.lstrip("./")
    pattern = pattern.lstrip("./")

    if pattern == filepath:
        return True

    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        if filepath == prefix or filepath.startswith(prefix + "/"):
            return True

    if fnmatch.fnmatch(filepath, pattern):
        return True

    return False


def is_sensor_triggered(sensor: dict, changed_files: list[str]) -> bool:
    """Determine if any changed file matches the sensor's path filters."""
    patterns = sensor.get("when_changed") or sensor.get("when-changed") or []
    if not patterns:
        return True

    for filepath in changed_files:
        for pattern in patterns:
            if match_pattern(pattern, filepath):
                return True
    return False


def get_runner_executable(runner: str) -> str | None:
    """Resolve the required runner tool executable path."""
    if runner in ("python", "pytest"):
        return sys.executable
    return shutil.which(runner)


def check_runner_availability(sensor: dict) -> tuple[bool, str]:
    """Check if the sensor's runner tool is available."""
    runner = sensor.get("runner") or "sh"
    if runner in ("python", "pytest"):
        return True, sys.executable

    exe = shutil.which(runner)
    if exe is not None:
        return True, exe

    # Fallback: check if first token of command exists in PATH
    cmd_parts = sensor.get("command", "").split()
    if cmd_parts:
        base_cmd = cmd_parts[0]
        exe = shutil.which(base_cmd)
        if exe is not None:
            return True, exe

    return False, f"Runner '{runner}' is not installed or not in PATH"


def get_changed_files() -> list[str]:
    """Detect changed files in git repository."""
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=True,
        )
        files = []
        for line in res.stdout.splitlines():
            if line.strip():
                parts = line.strip().split(maxsplit=1)
                if len(parts) == 2:
                    files.append(parts[1])
        if not files:
            res_diff = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
            )
            files = [f.strip() for f in res_diff.stdout.splitlines() if f.strip()]
        return files
    except Exception:
        return []


def run_sensor(sensor: dict, verbose: bool = False) -> tuple[bool, str]:
    """Execute a single sensor command and return status and log output."""
    cmd = sensor.get("command", "")
    sensor_id = sensor.get("id", "unknown")
    remediation = sensor.get("remediation", "No remediation instructions provided.")

    available, reason = check_runner_availability(sensor)
    if not available:
        return False, f"[SKIP/WARN] {sensor_id}: {reason}\n  Remediation: {remediation}"

    print(f"--> Running sensor [{sensor_id}]: {sensor.get('name', '')}")
    if verbose:
        print(f"    Command: {cmd}")

    res = subprocess.run(
        cmd,
        shell=True,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    output = []
    if res.stdout:
        output.append(res.stdout)
    if res.stderr:
        output.append(res.stderr)

    full_output = "\n".join(output)

    if res.returncode != 0:
        err_msg = (
            f"[FAIL] Sensor [{sensor_id}] failed with exit code {res.returncode}\n"
            f"=== Output ===\n{full_output}\n"
            f"=== Remediation ===\n{remediation}\n"
        )
        return False, err_msg

    return True, f"[PASS] Sensor [{sensor_id}] passed."


def main() -> int:
    """CLI entrypoint for running do-harness sensors."""
    parser = argparse.ArgumentParser(description="Run do-harness quality loop sensors.")
    parser.add_argument(
        "--files",
        nargs="*",
        help="Explicit list of changed files to test path matching.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="List triggered sensors without executing them.",
    )
    parser.add_argument(
        "--sensor",
        type=str,
        help="Run a specific sensor by ID regardless of path filters.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output.")
    args = parser.parse_args()

    config = load_harness_config()
    sensors = config.get("sensor") or config.get("sensors") or []

    if args.files is not None:
        changed_files = args.files
    else:
        changed_files = get_changed_files()

    print(f"Language: {config.get('language')}")
    print(f"Version:  {config.get('version')}")
    if changed_files:
        preview = ", ".join(changed_files[:5])
        suffix = "..." if len(changed_files) > 5 else ""
        print(f"Changed files ({len(changed_files)}): {preview}{suffix}")
    else:
        print("No changed files detected.")

    triggered = []
    for s in sensors:
        if args.sensor:
            if s.get("id") == args.sensor:
                triggered.append(s)
        else:
            if is_sensor_triggered(s, changed_files):
                triggered.append(s)

    if not triggered:
        print("No sensors triggered for the specified changes.")
        return 0

    print(f"\nTriggered {len(triggered)} sensor(s):")
    for s in triggered:
        available, reason = check_runner_availability(s)
        status_str = "AVAILABLE" if available else f"MISSING ({reason})"
        print(f"  - [{s.get('id')}] {s.get('name')} -> {status_str}")

    if args.check:
        return 0

    failures = 0
    skips = 0
    print("\nExecuting sensors...")
    for s in triggered:
        success, msg = run_sensor(s, verbose=args.verbose)
        print(msg)
        if not success:
            if "[SKIP/WARN]" in msg:
                skips += 1
            else:
                failures += 1

    if failures > 0:
        print(f"\n❌ Harness failed with {failures} failing check(s) and {skips} skipped check(s).")
        return 1

    passed_count = len(triggered) - skips
    print(f"\n✅ All {passed_count} active sensor check(s) passed ({skips} skipped).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
