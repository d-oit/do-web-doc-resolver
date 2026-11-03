"""Tests for do-harness.toml configuration and scripts/harness.py."""

from __future__ import annotations

import subprocess
import sys

from scripts.harness import (
    HARNESS_CONFIG,
    REPO_ROOT,
    check_runner_availability,
    is_sensor_triggered,
    load_harness_config,
    match_pattern,
    run_sensor,
)


def test_do_harness_toml_exists_and_parses():
    """Verify do-harness.toml exists and parses as valid TOML."""
    assert HARNESS_CONFIG.exists(), "do-harness.toml should exist in repository root"

    config = load_harness_config(HARNESS_CONFIG)
    assert config.get("language") == "generic"
    assert config.get("version") == "1.0"

    sensors = config.get("sensor") or config.get("sensors") or []
    assert len(sensors) >= 10, "Should have at least 10 sensors configured"


def test_sensor_schema_and_remediation():
    """Verify all sensors define required fields and remediation instructions."""
    config = load_harness_config()
    sensors = config.get("sensor") or config.get("sensors") or []

    for sensor in sensors:
        assert "id" in sensor, f"Sensor missing 'id': {sensor}"
        assert "name" in sensor, f"Sensor missing 'name': {sensor}"
        assert "command" in sensor, f"Sensor missing 'command': {sensor}"
        assert "runner" in sensor, f"Sensor missing 'runner': {sensor}"
        assert "remediation" in sensor, f"Sensor missing 'remediation': {sensor}"

        # Ensure path filters are present
        patterns = sensor.get("when_changed") or sensor.get("when-changed")
        assert patterns is not None, f"Sensor {sensor['id']} missing when_changed / when-changed"
        assert isinstance(patterns, list) and len(patterns) > 0

        # Ensure remediation is descriptive
        assert len(sensor["remediation"].strip()) > 10


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


def test_command_mapping_uses_existing_scripts():
    """Verify sensors map to existing scripts or standard CLI binaries."""
    config = load_harness_config()
    sensors = config.get("sensor") or config.get("sensors") or []

    script_sensors = {
        "validate-version": "scripts/sync_versions.py",
        "validate-skill-mirror": "scripts/sync_skill.py",
        "validate-symlink": "scripts/validate_skill_symlink.py",
        "validate-docs": "scripts/validate_docs.py",
    }

    for sensor in sensors:
        sid = sensor["id"]
        cmd = sensor["command"]
        if sid in script_sensors:
            rel_script = script_sensors[sid]
            script_path = REPO_ROOT / rel_script
            assert script_path.exists(), f"Script referenced by {sid} should exist: {rel_script}"
            assert rel_script in cmd


def test_missing_runner_reporting():
    """Verify missing runner tools report skipped/warned status with remediation context."""
    dummy_sensor = {
        "id": "test-missing-runner",
        "name": "Test Missing Runner",
        "command": "nonexistent_fake_tool_xyz123 --check",
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


def test_harness_cli_check_command():
    """Verify python scripts/harness.py --check executes cleanly."""
    res = subprocess.run(
        [sys.executable, "scripts/harness.py", "--check", "--files", "scripts/resolve.py"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert res.returncode == 0
    assert "Triggered 3 sensor(s)" in res.stdout
    assert "[python-lint]" in res.stdout
