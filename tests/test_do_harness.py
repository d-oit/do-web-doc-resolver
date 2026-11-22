"""Dogfood the native do-harness contract (issue #715).

The configuration parser test always runs. Real-CLI tests run when a
`do-harness` binary is available via `DO_HARNESS_BIN` or `PATH`. The dedicated
harness job sets `DO_HARNESS_REQUIRED=1`, so a missing binary fails there;
ordinary unit-test jobs skip these tests instead of installing the CLI.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "do-harness.toml"
REQUIRED_SETS = {"feedback", "verification", "release"}
LEGACY_TOP_LEVEL = {"harness"}
LEGACY_SENSOR_KEYS = {"id", "commands", "runner", "description", "remediation", "when_changed"}


def _load_config() -> dict:
    with CONFIG_PATH.open("rb") as fh:
        return tomllib.load(fh)


def _harness_binary() -> str | None:
    explicit = os.environ.get("DO_HARNESS_BIN")
    if explicit:
        return explicit if Path(explicit).is_file() else None
    return shutil.which("do-harness")


def _require_binary() -> str:
    binary = _harness_binary()
    if binary is not None:
        return binary
    if os.environ.get("DO_HARNESS_REQUIRED") == "1":
        pytest.fail("do-harness binary missing in the dedicated harness job")
    pytest.skip("do-harness binary not installed")


def _run(binary: str, args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run an argv list without a shell; the binary is the test target."""
    # The binary and arguments are controlled by this test. No shell is used,
    # and there is no user input: Codacy/Semgrep taint reports are false
    # positives for this dedicated CLI regression.
    # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-tainted-env-args.dangerous-subprocess-use-tainted-env-args
    return subprocess.run(
        [binary, *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def test_config_uses_native_schema():
    config = _load_config()

    assert config["language"] == "generic"
    assert not (LEGACY_TOP_LEVEL & config.keys()), "legacy [harness] table present"

    sensors = config.get("sensors") or []
    assert sensors, "native schema requires at least one [[sensors]] entry"

    names = [sensor["name"] for sensor in sensors]
    assert len(names) == len(set(names)), "sensor names must be unique"

    for sensor in sensors:
        assert not (LEGACY_SENSOR_KEYS & sensor.keys()), f"legacy keys in {sensor['name']}"
        assert isinstance(sensor.get("argv"), list) and sensor["argv"], sensor["name"]
        assert all(isinstance(arg, str) for arg in sensor["argv"]), sensor["name"]
        # Native argv is literal; a shell metacharacter here would be passed to
        # the child instead of interpreted, which is almost always a mistake.
        for arg in sensor["argv"]:
            assert not any(ch in arg for ch in "|;&$`"), f"shell syntax in {sensor['name']}"
        assert sensor.get("when-changed"), f"{sensor['name']} has no when-changed globs"


def test_signal_sets_reference_existing_sensors_and_cover_verification():
    config = _load_config()
    sensors = {sensor["name"] for sensor in config["sensors"]}
    sets = config.get("signal-sets") or {}

    assert REQUIRED_SETS <= sets.keys(), f"missing signal sets: {REQUIRED_SETS - sets.keys()}"
    for set_name in REQUIRED_SETS:
        assert sets[set_name], f"signal set {set_name} must not be empty"
        unknown = set(sets[set_name]) - sensors
        assert not unknown, f"{set_name} references unknown sensors: {sorted(unknown)}"

    # The native CLI treats an unlisted set as an error, but the repository
    # contract also requires full coverage in the pre-merge gate.
    assert set(sets["verification"]) == sensors, "verification must cover every sensor"
    assert set(sets["feedback"]) <= sensors
    assert set(sets["release"]) <= sensors


def test_do_harness_explain_selects_expected_sensors():
    binary = _require_binary()

    result = _run(binary, ["explain", "--set", "verification", "--format", "json"], REPO_ROOT)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    selected = {entry["name"] for entry in payload["selected"]}
    expected = {sensor["name"] for sensor in _load_config()["sensors"]}
    assert selected == expected


def _write_fixture(root: Path, *, include_failure: bool) -> Path:
    sensors = [
        f'[[sensors]]\nname = "ok"\nargv = {json.dumps([sys.executable, "-c", "print(1)"])}\n'
    ]
    names = ["ok"]
    if include_failure:
        sensors.append(
            '[[sensors]]\nname = "broken"\n'
            f"argv = {json.dumps([sys.executable, '-c', 'raise SystemExit(1)'])}\n"
        )
        names.append("broken")
    config = (
        'language = "generic"\n'
        "[signal-sets]\n"
        f"verification = {json.dumps(names)}\n\n" + "\n".join(sensors)
    )
    path = root / "do-harness.toml"
    path.write_text(config, encoding="utf-8")
    return path


def test_broken_fixture_fails_and_evidence_records_execution(tmp_path):
    binary = _require_binary()

    _write_fixture(tmp_path, include_failure=True)
    evidence = tmp_path / "evidence.json"
    result = _run(
        binary,
        [
            "verify",
            "--set",
            "verification",
            "--strict",
            "--format",
            "json",
            "--evidence",
            str(evidence),
        ],
        tmp_path,
    )
    assert result.returncode != 0, "a broken sensor must fail the strict gate"
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    assert payload["summary"]["verdict"] == "fail"
    assert payload["summary"]["fail"] == 1
    ran = {sensor["name"]: sensor["verdict"] for sensor in payload["sensors"]}
    assert ran == {"ok": "pass", "broken": "fail"}


def test_passing_fixture_is_green_only_when_sensor_actually_ran(tmp_path):
    binary = _require_binary()

    _write_fixture(tmp_path, include_failure=False)
    evidence = tmp_path / "evidence.json"
    result = _run(
        binary,
        [
            "verify",
            "--set",
            "verification",
            "--strict",
            "--format",
            "json",
            "--evidence",
            str(evidence),
        ],
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    assert payload["summary"]["verdict"] == "pass"
    assert payload["summary"]["pass"] == 1
    assert [sensor["verdict"] for sensor in payload["sensors"]] == ["pass"]


def test_unknown_signal_set_is_a_configuration_error(tmp_path):
    binary = _require_binary()

    _write_fixture(tmp_path, include_failure=False)
    result = _run(binary, ["verify", "--set", "does-not-exist", "--format", "json"], tmp_path)
    assert result.returncode == 2, "unknown signal set must not pass vacuously"
    assert "unknown signal set" in (result.stderr + result.stdout).lower()
