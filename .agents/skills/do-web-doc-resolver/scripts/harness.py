#!/usr/bin/env python3
"""do-harness runner and validation script.

Parses do-harness.toml, maps changed files to quality loop sensors,
inspects tool availability, and executes checks with remediation feedback.
"""

from __future__ import annotations

import argparse
import asyncio
import fnmatch
import shutil
import sys
import tomllib
from pathlib import Path
from typing import cast

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
    """Resolve a command's executable to an absolute path."""
    executable = sys.executable if runner == "python" else shutil.which(runner)
    return str(Path(executable).resolve()) if executable else None


def _sensor_commands(sensor: dict) -> list[list[str]]:
    """Resolve trusted repository configuration without invoking a shell."""
    commands = []
    for arguments in sensor["commands"]:
        executable = get_runner_executable(arguments[0])
        if executable is None:
            raise FileNotFoundError(f"Runner '{arguments[0]}' is not installed or not in PATH")
        commands.append([executable, *arguments[1:]])
    return commands


def check_runner_availability(sensor: dict) -> tuple[bool, str]:
    """Check every executable used by a sensor, including sequential checks."""
    try:
        commands = _sensor_commands(sensor)
        return True, commands[0][0]
    except FileNotFoundError as exc:
        return False, str(exc)


async def _run_command(command: list[str]) -> tuple[int, str, str]:
    """Execute an absolute executable and literal arguments; never a command shell."""
    # Reviewed audit boundary: only repository-configured argv or fixed Git arguments.
    # No external URL/query data reaches this call; no shell interprets its arguments.
    # https://docs.python.org/3/library/asyncio-subprocess.html#asyncio.create_subprocess_exec
    # nosemgrep: python.lang.security.audit.dangerous-asyncio-create-exec-audit.dangerous-asyncio-create-exec-audit
    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=REPO_ROOT,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    return (
        cast(int, process.returncode),
        stdout.decode(errors="replace"),
        stderr.decode(errors="replace"),
    )


def get_changed_files() -> list[str]:
    """Detect changed files in git repository."""
    git = get_runner_executable("git")
    if git is None:
        return []
    try:
        returncode, stdout, _ = asyncio.run(_run_command([git, "status", "--porcelain"]))
        if returncode != 0:
            return []
        files = []
        for line in stdout.splitlines():
            if line.strip():
                parts = line.strip().split(maxsplit=1)
                if len(parts) == 2:
                    files.append(parts[1])
        if not files:
            _, stdout, _ = asyncio.run(_run_command([git, "diff", "--name-only", "HEAD"]))
            files = [f.strip() for f in stdout.splitlines() if f.strip()]
        return files
    except OSError:
        return []


def run_sensor(sensor: dict, verbose: bool = False) -> tuple[bool, str]:
    """Execute a single sensor command and return status and log output."""
    commands = sensor["commands"]
    sensor_id = sensor.get("id", "unknown")
    remediation = sensor.get("remediation", "No remediation instructions provided.")

    available, reason = check_runner_availability(sensor)
    if not available:
        return False, f"[SKIP/WARN] {sensor_id}: {reason}\n  Remediation: {remediation}"

    print(f"--> Running sensor [{sensor_id}]: {sensor.get('name', '')}")
    if verbose:
        print(f"    Commands: {commands}")

    output: list[str] = []
    for command in _sensor_commands(sensor):
        returncode, stdout, stderr = asyncio.run(_run_command(command))
        output.extend(part for part in (stdout, stderr) if part)
        if returncode != 0:
            full_output = "\n".join(output)
            err_msg = (
                f"[FAIL] Sensor [{sensor_id}] failed with exit code {returncode}\n"
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
