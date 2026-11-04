"""Tests for do-harness.toml configuration and scripts/harness.py."""

from __future__ import annotations

import sys

from scripts.harness import (
    check_runner_availability,
    is_sensor_triggered,
    load_harness_config,
    match_pattern,
    run_sensor,
)


def test_path_selection_python_only():
    """Verify Python-only edits trigger Python sensors but not Rust or Web sensors."""
    config = load_harness_config()
    sensors = config.get("sensor") or config.get("sensors") or []

    python_files = ["scripts/resolve.py", "tests/test_resolve.py"]

    triggered_ids = {s["id"] for s in sensors if is_sensor_triggered(s, python_files)}

    assert "python-lint" in triggered_ids
    assert "python-test" in triggered_ids
    assert "validate-skill-mirror" in triggered_ids

    # Should not trigger Rust CLI or Web UI
    assert "rust-fmt" not in triggered_ids
    assert "rust-clippy" not in triggered_ids
    assert "rust-test" not in triggered_ids
    assert "rust-build" not in triggered_ids
    assert "web-lint" not in triggered_ids
    assert "web-typecheck" not in triggered_ids
    assert "web-test" not in triggered_ids
    assert "cli-ui-lint" not in triggered_ids


def test_path_selection_rust_only():
    """Verify Rust CLI edits trigger Rust sensors but not Python or Web sensors."""
    config = load_harness_config()
    sensors = config.get("sensor") or config.get("sensors") or []

    rust_files = ["cli/src/main.rs", "cli/Cargo.toml"]

    triggered_ids = {s["id"] for s in sensors if is_sensor_triggered(s, rust_files)}

    assert "rust-fmt" in triggered_ids
    assert "rust-clippy" in triggered_ids
    assert "rust-test" in triggered_ids
    assert "rust-build" in triggered_ids

    # Should not trigger Python or Web UI
    assert "python-lint" not in triggered_ids
    assert "python-test" not in triggered_ids
    assert "web-lint" not in triggered_ids
    assert "web-test" not in triggered_ids


def test_path_selection_ui_only():
    """Verify Web UI and CLI UI edits trigger UI sensors but not Python or Rust sensors."""
    config = load_harness_config()
    sensors = config.get("sensor") or config.get("sensors") or []

    web_files = ["web/app/page.tsx", "web/package.json"]
    cli_ui_files = ["cli/ui/components/button.css", "cli/ui/package.json"]

    web_triggered = {s["id"] for s in sensors if is_sensor_triggered(s, web_files)}
    cli_ui_triggered = {s["id"] for s in sensors if is_sensor_triggered(s, cli_ui_files)}

    assert "web-lint" in web_triggered
    assert "web-typecheck" in web_triggered
    assert "web-test" in web_triggered
    assert "rust-fmt" not in web_triggered
    assert "python-lint" not in web_triggered

    assert "cli-ui-lint" in cli_ui_triggered
    assert "cli-ui-test" in cli_ui_triggered
    assert "rust-fmt" not in cli_ui_triggered


def test_path_selection_cross_cutting():
    """Verify documentation and version changes trigger cross-cutting sensors."""
    config = load_harness_config()
    sensors = config.get("sensor") or config.get("sensors") or []

    doc_files = ["docs/standards.md", "README.md"]
    version_files = ["pyproject.toml", "cli/Cargo.toml", "web/package.json"]

    doc_triggered = {s["id"] for s in sensors if is_sensor_triggered(s, doc_files)}
    version_triggered = {s["id"] for s in sensors if is_sensor_triggered(s, version_files)}

    assert "validate-docs" in doc_triggered
    assert "validate-version" in version_triggered


def test_pattern_matching_helper():
    """Verify glob pattern matching handles double wildcard and exact paths."""
    assert match_pattern("scripts/**", "scripts/resolve.py")
    assert match_pattern("scripts/**", "scripts/utils/fetch.py")
    assert match_pattern("cli/**", "cli/src/main.rs")
    assert match_pattern("pyproject.toml", "pyproject.toml")
    assert not match_pattern("cli/**", "scripts/resolve.py")


def test_missing_runner_reporting():
    """Verify missing runner tools report skipped/warned status with remediation context."""
    dummy_sensor = {
        "id": "test-missing-runner",
        "name": "Test Missing Runner",
        "commands": [["nonexistent_fake_tool_xyz123", "--check"]],
        "runner": "nonexistent_fake_tool_xyz123",
        "remediation": "Install fake_tool_xyz123 to resolve this check.",
    }

    available, reason = check_runner_availability(dummy_sensor)
    assert not available
    assert "nonexistent_fake_tool_xyz123" in reason

    success, msg = run_sensor(dummy_sensor)
    assert not success
    assert "[SKIP/WARN]" in msg
    assert "Install fake_tool_xyz123" in msg


def test_sensor_arguments_are_literal_and_preserve_spaces(tmp_path):
    """Shell syntax in a command argument must never start another process."""
    output = tmp_path / "literal arguments.txt"
    injected = tmp_path / "injected"
    argument = f"value with spaces; touch {injected}"
    sensor = {
        "id": "literal",
        "commands": [
            [
                sys.executable,
                "-c",
                "import pathlib,sys; pathlib.Path(sys.argv[1]).write_text(sys.argv[2])",
                str(output),
                argument,
            ]
        ],
    }

    success, _ = run_sensor(sensor)

    assert success
    assert output.read_text() == argument
    assert not injected.exists()


def test_sensor_stops_after_first_failure(tmp_path):
    """A failed check must prevent subsequent commands from running."""
    output = tmp_path / "must-not-exist"
    sensor = {
        "id": "failure",
        "remediation": "Repair the failed check.",
        "commands": [
            [sys.executable, "-c", "import sys; sys.stderr.write('check failed'); sys.exit(5)"],
            [
                sys.executable,
                "-c",
                "import pathlib,sys; pathlib.Path(sys.argv[1]).touch()",
                str(output),
            ],
        ],
    }

    success, message = run_sensor(sensor)

    assert not success
    assert "exit code 5" in message
    assert "check failed" in message
    assert "Repair the failed check." in message
    assert not output.exists()
