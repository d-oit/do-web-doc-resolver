"""Unit tests for the do-harness verification selector (issue #730).

Covers path classification per runtime component, rename/delete-aware
changed-file collection, and the conservative fallback to full verification
whenever change detection is uncertain.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.harness_select import (
    SENSORS_BY_COMPONENT,
    classify,
    collect_changed_paths,
    print_fix_hints,
    read_config,
    select,
    select_sensors,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

FIXTURE_CONFIG: dict = {
    "sensors": [
        {"name": "py-test", "when-changed": ["scripts/**", "tests/**", "pyproject.toml"]},
        {"name": "rs-test", "when-changed": ["cli/src/**", "cli/Cargo.toml"]},
        {"name": "web-test", "when-changed": ["web/**"]},
        {
            "name": "mirror",
            "when-changed": ["scripts/**", ".agents/skills/do-web-doc-resolver/**"],
        },
        {"name": "docs", "when-changed": ["docs/**", "AGENTS.md"]},
    ]
}


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "test")
    for directory in ("scripts", "cli/src", "web", "docs"):
        (tmp_path / directory).mkdir(parents=True)
    (tmp_path / "scripts" / "a.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "cli" / "src" / "lib.rs").write_text("fn main() {}\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "init")
    return tmp_path


def test_classify_maps_paths_to_runtime_components():
    buckets = classify(
        [
            "scripts/resolve.py",
            "tests/test_resolve.py",
            "pyproject.toml",
            "cli/src/main.rs",
            "cli/Cargo.toml",
            "web/app/page.tsx",
            "cli/ui/tokens/main.css",
            "AGENTS.md",
            ".github/workflows/ci.yml",
            ".agents/skills/do-harness/SKILL.md",
            "docs/index.md",
        ]
    )

    assert buckets["unclassified"] == []
    assert buckets["python"] == ["pyproject.toml", "scripts/resolve.py", "tests/test_resolve.py"]
    assert buckets["rust"] == ["cli/Cargo.toml", "cli/src/main.rs"]
    assert buckets["web"] == ["web/app/page.tsx"]
    assert buckets["cli-ui"] == ["cli/ui/tokens/main.css"]
    assert ".github/workflows/ci.yml" in buckets["cross-cutting"]
    assert "docs/index.md" in buckets["cross-cutting"]


def test_generated_paths_are_ignored_not_unclassified():
    buckets = classify(
        [
            "cli/target/release/do-wdr",
            "web/.next/server/page.js",
            "web/node_modules/next/index.js",
            ".do-harness/evidence.json",
            ".pytest_cache/v/cache/stepwise",
            "coverage.xml",
        ]
    )

    assert buckets["unclassified"] == []
    assert set(buckets) == {"unclassified"}


def test_unclassified_path_is_reported_for_fallback():
    buckets = classify(["new-top-level.bin"])

    assert buckets["unclassified"] == ["new-top-level.bin"]


def test_leading_dot_directories_keep_their_dot_prefix():
    buckets = classify([".agents/skills/do-harness/SKILL.md", ".github/workflows/ci.yml"])

    assert buckets["unclassified"] == []
    assert buckets["cross-cutting"] == [
        ".agents/skills/do-harness/SKILL.md",
        ".github/workflows/ci.yml",
    ]


def test_collect_captures_renames_deletions_and_untracked(git_repo: Path):
    _git(git_repo, "mv", "scripts/a.py", "scripts/b.py")
    _git(git_repo, "rm", "-q", "cli/src/lib.rs")
    (git_repo / "web" / "new.ts").write_text("export {};\n", encoding="utf-8")
    (git_repo / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")

    paths, reasons = collect_changed_paths(git_repo)

    assert reasons == []
    assert set(paths) >= {
        "scripts/a.py",
        "scripts/b.py",
        "cli/src/lib.rs",
        "web/new.ts",
        "pyproject.toml",
    }


def test_clean_changeset_falls_back_to_full(git_repo: Path):
    result = select(git_repo, FIXTURE_CONFIG, mode="auto")

    assert result["mode"] == "full"
    assert "no local changes detected" in result["reasons"]


def test_harness_contract_change_falls_back_to_full(git_repo: Path):
    (git_repo / "do-harness.toml").write_text('language = "generic"\n', encoding="utf-8")

    result = select(git_repo, FIXTURE_CONFIG, mode="auto")

    assert result["mode"] == "full"
    assert any("verification contract" in reason for reason in result["reasons"])


def test_workflow_change_falls_back_to_full(git_repo: Path):
    workflows = git_repo / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text("name: CI\n", encoding="utf-8")

    result = select(git_repo, FIXTURE_CONFIG, mode="auto")

    assert result["mode"] == "full"


def test_not_a_git_repo_falls_back_to_full(tmp_path: Path):
    result = select(tmp_path, FIXTURE_CONFIG, mode="auto")

    assert result["mode"] == "full"
    assert result["reasons"], "an uncertain git state must be reported as a reason"


def test_merge_in_progress_falls_back_to_full(git_repo: Path):
    (git_repo / ".git" / "MERGE_HEAD").write_text("refs/heads/other\n", encoding="utf-8")

    result = select(git_repo, FIXTURE_CONFIG, mode="auto")

    assert result["mode"] == "full"
    assert any("merge" in reason for reason in result["reasons"])


def test_changed_mode_selects_affected_sensors_only(git_repo: Path):
    (git_repo / "scripts" / "a.py").write_text("x = 2\n", encoding="utf-8")
    (git_repo / "cli" / "src" / "lib.rs").write_text("fn main() { () }\n", encoding="utf-8")

    result = select(git_repo, FIXTURE_CONFIG, mode="auto")

    assert result["mode"] == "changed"
    assert result["reasons"] == []
    assert result["components"] == ["python", "rust"]
    assert set(result["sensors"]) == {"py-test", "rs-test", "mirror"}
    assert "--changed" in result["command"]


def test_unclassified_change_downgrades_changed_mode_to_full(git_repo: Path):
    (git_repo / "stranger.bin").write_text("?\n", encoding="utf-8")

    result = select(git_repo, FIXTURE_CONFIG, mode="auto")

    assert result["mode"] == "full"
    assert any("match no component" in reason for reason in result["reasons"])


def test_change_without_sensor_coverage_falls_back_to_full(git_repo: Path):
    (git_repo / "package.json").write_text("{}\n", encoding="utf-8")

    result = select(git_repo, FIXTURE_CONFIG, mode="auto")

    assert result["mode"] == "full"
    assert any("no configured sensor" in reason for reason in result["reasons"])


def test_explicit_full_mode_overrides_changed_selection(git_repo: Path):
    (git_repo / "scripts" / "a.py").write_text("x = 3\n", encoding="utf-8")

    result = select(git_repo, FIXTURE_CONFIG, mode="full")

    assert result["mode"] == "full"
    assert "--changed" not in result["command"]


def test_select_sensors_matches_when_changed_globs():
    assert select_sensors(FIXTURE_CONFIG, ["scripts/x.py"]) == ["py-test", "mirror"]
    assert select_sensors(FIXTURE_CONFIG, ["docs/guide.md"]) == ["docs"]
    assert select_sensors(FIXTURE_CONFIG, []) == []


def test_cli_reports_mode_and_machine_readable_selection(git_repo: Path):
    (git_repo / "scripts" / "a.py").write_text("x = 4\n", encoding="utf-8")

    mode = subprocess.run(
        [
            sys.executable,
            "scripts/harness_select.py",
            "--repo-root",
            str(git_repo),
            "--format",
            "mode",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert mode.returncode == 0, mode.stderr
    assert mode.stdout.strip() == "changed"

    payload = subprocess.run(
        [
            sys.executable,
            "scripts/harness_select.py",
            "--repo-root",
            str(git_repo),
            "--format",
            "json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert payload.returncode == 0, payload.stderr
    result = json.loads(payload.stdout)
    assert result["mode"] == "changed"
    assert "python" in result["components"]
    assert result["command"].startswith("do-harness verify --set verification")


def test_real_config_sensors_select_classifiable_paths():
    config = read_config()
    for sensor in config["sensors"]:
        probe_glob = sensor["when-changed"][0]
        probe = probe_glob[:-3] if probe_glob.endswith("/**") else probe_glob
        probe = f"{probe}/probe.ext" if probe_glob.endswith("/**") else probe

        buckets = classify([probe])

        assert buckets["unclassified"] == [], (
            f"sensor {sensor['name']} matches {probe_glob}, which the "
            "component classification does not cover; such changes would "
            "silently force full verification"
        )


def test_real_config_verification_covers_component_sensor_map():
    config = read_config()
    configured = {sensor["name"] for sensor in config["sensors"]}
    verification = set(config["signal-sets"]["verification"])

    for component, sensors in SENSORS_BY_COMPONENT.items():
        assert (
            set(sensors) <= configured
        ), f"{component} sensors not in do-harness.toml: {sorted(set(sensors) - configured)}"
        missing = set(sensors) - verification
        assert not missing, f"{component} sensors missing from verification: {sorted(missing)}"


def test_fix_hints_reads_failed_sensors_from_evidence(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    evidence = tmp_path / "evidence.json"
    evidence.write_text(
        json.dumps(
            {
                "sensors": [
                    {"name": "py-test", "verdict": "fail"},
                    {"name": "web-test", "verdict": "pass"},
                ]
            }
        ),
        encoding="utf-8",
    )
    config = {"sensors": [{"name": "py-test", "fix": "Run pytest -x."}]}

    code = print_fix_hints(evidence, config)

    assert code == 1
    assert "py-test: Run pytest -x." in capsys.readouterr().out
